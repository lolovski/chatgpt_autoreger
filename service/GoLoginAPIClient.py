# service/gologin_api_client.py
import asyncio
import logging
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
            return response.json() if response.text else {}
        except GoLoginAPIError as e:
            logger.error(f"GoLogin API returned an error: {e}")
            raise  # Перебрасываем исключение, чтобы не делать retry на 4xx/5xx ошибках
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

        gl = GoLogin(
            {
                "token": self.api_token,
                "profile_id": profile_id
            }
        )

        try:
            ws_url = await asyncio.wait_for(
                asyncio.to_thread(gl.start), timeout=self.timeout
            )
        except asyncio.TimeoutError:
            raise GoLoginAPIError(0, f"Timeout while starting profile {profile_id}")

        if not ws_url:
            raise GoLoginAPIError(0, f"Failed to get wsUrl for profile {profile_id}")

        logger.info(f"Profile {profile_id} started successfully: {ws_url}")
        return ws_url


    async def close(self):
        """Закрывает HTTP-клиент."""
        await self.client.aclose()


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