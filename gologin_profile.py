import asyncio
import json
import logging
from typing import Optional, List

from pyppeteer.browser import Browser
from pyppeteer.page import Page
from pyppeteer import connect

from service.GoLoginAPIClient import GoLoginAPIClient, GoLoginAPIError


logger = logging.getLogger(__name__)


class GoLoginProfile:
    """
    Асинхронный менеджер для управления профилями GoLogin.
    Использует pyppeteer для подключения к запущенному профилю.
    """

    def __init__(self, api_token: str, profile_id: Optional[str] = None):
        self.api_client = GoLoginAPIClient(api_token=api_token)
        self.persistent_profile = bool(profile_id)
        self.profile_id: Optional[str] = profile_id

        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    async def __aenter__(self) -> Page:
        try:
            if not self.persistent_profile:
                logger.info("Creating a quick profile...")
                profile_data = await self.api_client.create_quick_profile()
                self.profile_id = profile_data.get("id")
                if not self.profile_id:
                    raise GoLoginAPIError(0, f"Failed to get id from quick profile: {profile_data}")
                await self.api_client.set_proxy(profile_id=self.profile_id)

            logger.info(f"Starting profile: {self.profile_id}")
            ws_url = await self.api_client.start_profile(profile_id=self.profile_id)

            logger.info("Connecting via pyppeteer...")
            self.browser = await connect(
                browserURL=f"http://{ws_url}",
                defaultViewport=None
            )
            self.page = await self.browser.newPage()
            return self.page

        except Exception as e:
            logger.error(f"Failed to setup GoLogin profile: {e}", exc_info=True)
            await self.__aexit__(type(e), e, e.__traceback__)
            raise

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        logger.info(f"Cleaning up resources for profile: {self.profile_id}")
        if self.browser:
            await self.browser.close()
            logger.info("pyppeteer browser instance closed.")

        if self.profile_id and not self.persistent_profile:
            logger.info(f"Deleting quick profile: {self.profile_id}")
            await self.api_client.delete_profile(profile_id=self.profile_id)

        await self.api_client.close()
        logger.info("Cleanup complete.")

    async def save_cookies(self, file_path: str, domains: List[str]):
        if not self.page:
            raise RuntimeError("Browser page is not running.")

        all_cookies = await self.page.cookies()
        domain_cookies = [c for c in all_cookies if any(d in c["domain"] for d in domains)]

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(domain_cookies, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(domain_cookies)} cookies to {file_path}")

    async def load_cookies(self, file_path: str):
        if not self.page:
            raise RuntimeError("Browser page is not running.")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                cookies = json.load(f)

            await self.page.setCookie(*cookies)
            logger.info(f"Loaded {len(cookies)} cookies from {file_path}")
        except FileNotFoundError:
            logger.warning(f"Cookie file not found: {file_path}. Skipping load.")
        except Exception as e:
            logger.error(f"Failed to load cookies from {file_path}: {e}")


# --- Пример использования ---

async def example_task(api_token: str):
    cookies_file = "my_session_cookies.json"

    print("--- Running first session to login and save cookies ---")

    profile_manager_1 = GoLoginProfile(api_token=api_token)
    async with profile_manager_1 as page:
        await page.goto("https://httpbin.org/cookies")
        print("Initial cookies:", await page.content())

        # Устанавливаем cookie
        await page.setCookie({
            "name": "auth_token",
            "value": "12345-secret",
            "domain": "httpbin.org"
        })

        await page.goto("https://httpbin.org/cookies")
        print("Cookies after login:", await page.content())

        await profile_manager_1.save_cookies(cookies_file, domains=['httpbin.org'])

    print("\n--- Running second session to load cookies and verify ---")

    profile_manager_2 = GoLoginProfile(api_token=api_token)
    async with profile_manager_2 as tab:
        await tab.goto("https://httpbin.org/cookies")
        print("Cookies before loading:", await tab.content())

        await profile_manager_2.load_cookies(cookies_file)

        await tab.reload()
        print("Cookies after loading and reload:", await tab.content())


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    GOLOGIN_API_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2OGIwYjlhNGRmMDBhMTM1NGVhYWUyYTEiLCJ0eXBlIjoiZGV2Iiwiand0aWQiOiI2OGIwYjllZGQzYWE0MjA1Yjc2NzE3YTAifQ.y8kz5dmtv2SQD8IxJpbAUOAytIQ9TvJD58RuE1iRKas"

    if GOLOGIN_API_TOKEN == "YOUR_GOLOGIN_API_TOKEN":
        print("Please replace 'YOUR_GOLOGIN_API_TOKEN' with your actual token.")
    else:
        asyncio.run(example_task(api_token=GOLOGIN_API_TOKEN))
