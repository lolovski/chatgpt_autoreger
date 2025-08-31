# service/gologin_api_client.py
import asyncio
import json
import logging
import os

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from gologin import GoLogin

logger = logging.getLogger(__name__)

# Определяем класс исключений, при которых нужно повторять запрос
RETRYABLE_EXCEPTIONS = (
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.NetworkError,
)


class GoLoginAPIError(Exception):
    """Кастомное исключение для ошибок GoLogin API."""
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text
        super().__init__(f"GoLogin API Error {status_code}: {text}")


class GoLoginAPIClient:
    """
    Асинхронный, надежный клиент для GoLogin API с таймаутами и повторными попытками.
    """
    def __init__(self, api_token: str, timeout: int = 10):
        self.base_url = "https://api.gologin.com"
        self.api_token = api_token
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {api_token}",
                "User-Agent": "TelegramBotGoLoginClient/1.0",
            },
            timeout=timeout,  # Жесткий таймаут на все операции
        )

    @retry(
        stop=stop_after_attempt(3),  # Повторить до 3 раз
        wait=wait_exponential(multiplier=1, min=2, max=10),  # Ожидание между попытками: 2s, 4s, 8s...
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS), # Повторять только при сетевых ошибках
        before_sleep=lambda retry_state: logger.warning(
            f"GoLogin API request failed, retrying in {retry_state.next_action.sleep:.2f}s... "
            f"Attempt: {retry_state.attempt_number}"
        )
    )
    async def _request(self, method: str, endpoint: str, **kwargs):
        """Обертка для всех HTTP-запросов с обработкой ошибок."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = await self.client.request(method, url, **kwargs)
            if response.status_code >= 400:
                raise GoLoginAPIError(response.status_code, response.text)
            if not response.text:
                # Успешный ответ, но с пустым телом.
                return {}
            try:
                # Пытаемся декодировать JSON из успешного ответа.
                return response.json()
            except json.JSONDecodeError:
                # Редкий случай: успешный код, но тело - не JSON.
                # Логируем это как серьезную ошибку API.
                logger.error(
                    f"GoLogin API вернул не-JSON ответ для успешного запроса ({response.status_code}). "
                    f"Текст: {response.text[:200]}"
                )
                # Вызываем ошибку, чтобы не продолжать работу с некорректными данными.
                raise GoLoginAPIError(response.status_code, "Invalid JSON in successful response from GoLogin API.")

        except GoLoginAPIError as e:
            logger.error(f"GoLogin API returned an error: {e}")
            raise
        except httpx.TimeoutException as e:
            logger.error(f"GoLogin API request timed out: {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred during GoLogin API request: {e}", exc_info=True)
            raise

    async def create_quick_profile(self, name: str = 'api-generate', os: str = "win") -> dict:
        """Создает новый профиль со случайным отпечатком."""

        logger.info(f"Creating GoLogin profile with name: {name}")
        payload = {
            "name": name,
            "os": os,
        }
        return await self._request("POST", "/browser/quick", json=payload)

    async def set_proxy(self, profile_id: str):
        """Устанавливает прокси для профиля."""
        logger.info(f"Setting proxy for profile {profile_id}")
        payload = {
            "countryCode": 'us',
            "isDC": True,
            "isMobile": False,
            "profileIdToLink": profile_id,
        }
        return await self._request(
            method='POST',
            endpoint=r'/users-proxies/mobile-proxy',
            json=payload
        )

    async def get_profile(self, profile_id: str) -> dict:
        """Получает данные профиля по ID."""
        logger.info(f"Fetching data for profile {profile_id}")
        return await self._request("GET", f"/browser/{profile_id}")

    async def delete_profile(self, profile_id: str):
        """Удаляет профиль по ID."""
        logger.info(f"Deleting profile {profile_id}")
        await self._request("DELETE", f"/browser/{profile_id}")


    @retry(
        stop=stop_after_attempt(3),  # до 3 попыток
        wait=wait_exponential(multiplier=1, min=2, max=10),  # задержка 2s, 4s, 8s
        retry=retry_if_exception_type((GoLoginAPIError, asyncio.TimeoutError, OSError)),
        reraise=True
    )
    async def start_profile(self, profile_id: str) -> str:
        """Запускает удаленный профиль Orbita и возвращает wsUrl с таймаутом и ретраями."""
        logger.info(f"Starting remote profile {profile_id}")

        project_root = os.getcwd()
        profiles_dir = os.path.join(project_root, 'gologin_profiles')
        os.makedirs(profiles_dir, exist_ok=True)
        profile_path = os.path.join(profiles_dir, profile_id)

        gl = GoLogin(
            {
                "token": self.api_token,
                "profile_id": profile_id,
                "tmpdir": profile_path

            }
        )

        try:
            # Запускаем синхронную библиотеку в отдельном потоке
            response = await asyncio.wait_for(
                asyncio.to_thread(gl.start), timeout=self.timeout
            )

            # Библиотека gologin.start() возвращает словарь, а не просто wsUrl
            if not response:
                raise GoLoginAPIError(0, f"Failed to get wsUrl for profile {profile_id}. Response: {response}")

            logger.info(f"Profile {profile_id} started successfully.")
            return response

        except asyncio.TimeoutError:
            raise GoLoginAPIError(0, f"Timeout while starting profile {profile_id}")

            # НОВЫЙ БЛОК ОБРАБОТКИ ОШИБКИ
        except ValueError as e:
            logger.error(f"Corrupted fingerprint detected for profile {profile_id}. Error: {e}")
            raise GoLoginAPIError(
                status_code=422,  # 422 Unprocessable Entity - подходящий код для "битых" данных
                text="Profile fingerprint is corrupted or incomplete. Cannot start."
            )

    async def close(self):
        """Закрывает HTTP-клиент."""
        await self.client.aclose()

    async def test_token(self) -> bool:
        """
        Проверяет валидность токена, делая легкий запрос к API.
        Возвращает True, если токен рабочий, и False, если он невалиден или исчерпал лимиты.
        """
        try:
            # Делаем простой запрос, который должен работать с любым валидным токеном
            await self._request("GET", "/user")
            return True
        except GoLoginAPIError as e:
            # Если поймали ошибку лимита (403) или неверного токена (401), токен невалиден.
            if e.status_code in [401, 403]:
                logger.warning(f"Тест токена провален (статус {e.status_code}). Токен невалиден или исчерпал лимит.")
                return False
            # Если другая ошибка, лучше ее пробросить, но для простой проверки можно считать невалидным
            logger.error(f"Непредвиденная ошибка API при тесте токена: {e}")
            return False
        except Exception as e:
            logger.error(f"Сетевая ошибка при тесте токена: {e}")
            return False


"""async def main():
    gl = GoLoginAPIClient(
        api_token='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2OGFmNWEwYjk5MDdiMWFlNzEyN2MyYmEiLCJ0eXBlIjoiZGV2Iiwiand0aWQiOiI2OGFmNWEyNWU1NDc0YzAzZGZiYjU2MmUifQ.TS0NbPDtd0cIp-y2oSlekb2hKvOn1YFBoq954VtB2YA')
    profile = await gl.create_quick_profile()
    profile_id = profile.get('id')
    await gl.set_proxy(profile_id=profile_id)
    ws_url = await gl.start_profile(profile_id=profile_id)
    print(ws_url)
    await gl.close()

if __name__ == '__main__':

    asyncio.run(main())"""