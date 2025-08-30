# service/chatgpt_login.py

import logging
import asyncio  # Добавляем импорт
from service.gologin_profile import GoLoginProfile
from service.exceptions import TwoFactorRequiredError

logger = logging.getLogger(__name__)


async def login_chatgpt_account(token: str, email_address: str, password: str, code: str = None) -> str:
    profile = GoLoginProfile(api_token=token)
    created_profile_id = None

    try:
        async with profile as page:
            await page.goto("https://chatgpt.com/auth/login", {'waitUntil': 'networkidle0'})

            # ИСПРАВЛЕНО: Ждем навигацию
            await asyncio.gather(
                page.waitForNavigation({'waitUntil': 'networkidle0'}),
                page.click('button[data-testid="login-button"]')
            )

            await page.waitForSelector('input[name="email"]', {'timeout': 20000})
            await page.type('input[name="email"]', email_address)
            # ИСПРАВЛЕНО: Ждем обновление страницы
            await asyncio.gather(
                page.waitForNavigation({'waitUntil': 'networkidle0'}),
                page.click('button[type="submit"]')
            )

            await page.waitForSelector('input[name="current-password"]', {'timeout': 20000})
            await page.type('input[name="current-password"]', password)
            # ИСПРАВЛЕНО: Ждем финальную навигацию
            await asyncio.gather(
                page.waitForNavigation({'waitUntil': 'networkidle0'}),
                page.click('button[type="submit"]')
            )

            try:
                await page.waitForSelector('input[name="code"]', {'timeout': 5000})
                is_2fa_visible = True
            except Exception:
                is_2fa_visible = False

            if is_2fa_visible:
                if code:
                    await page.type('input[name="code"]', code)
                    await asyncio.gather(
                        page.waitForNavigation({'waitUntil': 'networkidle0'}),
                        page.click('button[type="submit"]')
                    )
                else:
                    raise TwoFactorRequiredError("Требуется код двухфакторной аутентификации")

            await page.waitForSelector('#prompt-textarea', {'timeout': 30000})
            logger.info(f"Успешный вход для {email_address}.")

            cookies_path = f'cookies/{profile.profile_id}.json'
            await profile.save_cookies(cookies_path, domains=['chatgpt.com', 'openai.com'])

            created_profile_id = profile.profile_id

        return created_profile_id

    except Exception as e:
        logger.error(f"[GPT Login] Ошибка входа для {email_address}: {e}", exc_info=True)
        raise