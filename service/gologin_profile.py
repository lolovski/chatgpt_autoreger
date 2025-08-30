import asyncio
import json
import logging
from typing import Optional, List, Dict

from pyppeteer import connect
from pyppeteer.browser import Browser
from pyppeteer.page import Page

from service.GoLoginAPIClient import GoLoginAPIClient, GoLoginAPIError

logger = logging.getLogger(__name__)


class GoLoginProfile:
    """
    Асинхронный менеджер для управления профилями GoLogin.

    Этот класс предоставляет асинхронный контекстный менеджер (__aenter__/__aexit__)
    для автоматизации жизненного цикла профиля GoLogin: создание (при необходимости),
    запуск, подключение через pyppeteer и последующая очистка (остановка и удаление).

    Использует `GoLoginAPIClient` для всех взаимодействий с GoLogin API.

    Атрибуты:
        api_client (GoLoginAPIClient): Клиент для работы с GoLogin API.
        profile_id (Optional[str]): ID существующего профиля GoLogin или None для создания временного.
        persistent_profile (bool): Флаг, указывающий, является ли профиль постоянным.
        browser (Optional[Browser]): Экземпляр браузера pyppeteer.
        page (Optional[Page]): Экземпляр страницы pyppeteer.
    """

    def __init__(self, api_token: str, profile_id: Optional[str] = None):
        """
        Инициализирует менеджер профиля GoLogin.

        Args:
            api_token (str): Ваш API токен от GoLogin.
            profile_id (Optional[str]): Если указан, менеджер будет работать
                с этим существующим профилем. Если None, будет создан и
                автоматически удален временный профиль.
        """
        self.api_client = GoLoginAPIClient(api_token=api_token)
        self.profile_id: Optional[str] = profile_id
        self.persistent_profile = bool(profile_id)

        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    async def __aenter__(self) -> Page:
        """
        Вход в асинхронный контекст: создает (если нужно), запускает профиль и подключается к нему.
        """
        try:
            if not self.persistent_profile:
                logger.info("Создание временного профиля GoLogin...")
                profile_data = await self.api_client.create_quick_profile()
                self.profile_id = profile_data.get("id")
                if not self.profile_id:
                    raise GoLoginAPIError(0, f"Не удалось получить ID из созданного профиля: {profile_data}")
                # Примечание: установка прокси для quick-профилей обычно не требуется,
                # так как они создаются с уже настроенным гео.
                await self.api_client.set_proxy(profile_id=self.profile_id)

            logger.info(f"Запуск профиля: {self.profile_id}")
            # Метод start_profile из GoLoginAPIClient уже содержит логику ожидания и повторов
            ws_url = await self.api_client.start_profile(profile_id=self.profile_id)

            logger.info("Connecting via pyppeteer...")
            self.browser = await connect(
                browserURL=f"http://{ws_url}",
                defaultViewport=None
            )
            pages = await self.browser.pages()
            self.page = pages[0] if pages else await self.browser.newPage()
            return self.page

        except Exception as e:
            logger.error(f"Ошибка при настройке профиля GoLogin ({self.profile_id}): {e}", exc_info=True)
            # Гарантируем очистку ресурсов при любой ошибке на входе
            await self.__aexit__(type(e), e, e.__traceback__)
            raise

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        ИЗМЕНЕНО: Выход из контекста теперь не закрывает браузер, а отсоединяется от него.
        Профиль остается работать в приложении GoLogin.
        """
        logger.info(f"Отсоединение от профиля: {self.profile_id}, оставляя его открытым.")

        if self.browser:
            await self.browser.disconnect()
            logger.info("Соединение pyppeteer разорвано. Браузер остается открытым.")

        # ИЗМЕНЕНО: ПОЛНОСТЬЮ УДАЛЕНА ЛОГИКА УДАЛЕНИЯ ПРОФИЛЯ.
        # Даже временные профили теперь не удаляются, так как по условию задачи
        # они должны остаться доступными для ручной работы.

        # Закрываем HTTP-клиент к API, он больше не нужен.
        await self.api_client.close()
        logger.info(f"Отсоединение от профиля {self.profile_id} завершено.")

    async def save_cookies(self, file_path: str, domains: List[str]):
        """
        Сохраняет cookie для указанных доменов в JSON-файл.

        Args:
            file_path (str): Путь к файлу для сохранения cookie.
            domains (List[str]): Список доменов, cookie которых нужно сохранить.
        """
        if not self.page:
            raise RuntimeError("Страница браузера не активна. Вызовите save_cookies внутри блока 'async with'.")

        all_cookies = await self.page.cookies()
        # Фильтруем cookie, чтобы сохранить только те, что относятся к нужным доменам
        domain_cookies = [c for c in all_cookies if any(d in c.get("domain", "") for d in domains)]

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(domain_cookies, f, ensure_ascii=False, indent=2)
        logger.info(f"Сохранено {len(domain_cookies)} cookie для доменов {domains} в файл {file_path}")

    async def load_cookies(self, file_path: str):
        """
        Загружает cookie из JSON-файла в текущую сессию браузера.

        Args:
            file_path (str): Путь к файлу с cookie.
        """
        if not self.page:
            raise RuntimeError("Страница браузера не активна. Вызовите load_cookies внутри блока 'async with'.")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                cookies = json.load(f)

            # Удаляем старые cookie перед загрузкой новых, чтобы избежать конфликтов
            await self.page.deleteCookie(*await self.page.cookies())

            await self.page.setCookie(*cookies)
            logger.info(f"Загружено {len(cookies)} cookie из файла {file_path}")
        except FileNotFoundError:
            logger.warning(f"Файл с cookie не найден: {file_path}. Загрузка пропущена.")
        except Exception as e:
            logger.error(f"Ошибка при загрузке cookie из файла {file_path}: {e}")

