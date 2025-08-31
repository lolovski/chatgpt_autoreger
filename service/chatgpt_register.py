# service/chatgpt_register.py

import asyncio
import logging
import random
import names
from service.gologin_profile import GoLoginProfile
from service.email_api import TempMailClient

logger = logging.getLogger(__name__)


async def register_chatgpt(token: str):
    """Авторегистрация ChatGPT в GoLogin-профиле с использованием pyppeteer."""
    email_client = TempMailClient()
    profile = GoLoginProfile(api_token=token)
    full_name = names.get_full_name()
    registration_data = None

    try:
        email = await email_client.create_account()
        logger.info(f"[GPT Register] Почта создана: {email}")

        async with profile as page:
            await page.goto("https://chatgpt.com/auth/login", {'waitUntil': 'networkidle0'})

            # ИСПРАВЛЕНО: Ждем навигацию после клика
            await asyncio.gather(
                page.waitForNavigation({'waitUntil': 'networkidle0'}),
                page.click('button[data-testid="signup-button"]')
            )

            await page.waitForSelector('input[name="email"]', {'timeout': 20000})
            await page.type('input[name="email"]', email)
            # ИСПРАВЛЕНО: Ждем навигацию после клика
            await asyncio.gather(
                page.waitForNavigation({'waitUntil': 'networkidle0'}),
                page.click('button[type="submit"]')
            )

            await page.waitForSelector('input[name="new-password"]', {'timeout': 20000})
            await page.type('input[name="new-password"]', email_client.password)
            # ИСПРАВЛЕНО: Ждем навигацию после клика
            await asyncio.gather(
                page.waitForNavigation({'waitUntil': 'networkidle0'}),
                page.click('button[type="submit"]')
            )

            code = await email_client.wait_for_code()
            if not code:
                raise RuntimeError("Не удалось получить код подтверждения с почты")
            logger.info(f"[GPT Register] Код подтверждения: {code}")

            await page.waitForSelector('input[name="code"]', {'timeout': 20000})
            await page.type('input[name="code"]', code)
            await asyncio.gather(
                page.waitForNavigation({'waitUntil': 'networkidle0'}),
                page.click('button[type="submit"]')
            )

            await page.waitForSelector('input[name="name"]', {'timeout': 20000})
            await page.type('input[name="name"]', full_name)

            day = str(random.randint(10, 28)).zfill(2)
            month = str(random.randint(10, 12)).zfill(2)
            year = str(random.randint(2000, 2002))
            await page.keyboard.press('Tab')
            # await page.click("button[role='combobox']")
            await page.keyboard.type(f"{month}{day}{year}")

            # ИСПРАВЛЕНО: Ждем навигацию после финального клика
            await asyncio.gather(
                page.waitForNavigation({'waitUntil': 'networkidle0'}),
                page.click('button[type="submit"]')
            )

            await page.waitForSelector('#prompt-textarea', {'timeout': 40000})
            logger.info("Регистрация успешно завершена!")

            cookies_path = f'cookies/{profile.profile_id}.json'
            await profile.save_cookies(cookies_path, domains=['chatgpt.com', 'openai.com'])

            registration_data = {
                'email_address': email,
                'id': profile.profile_id,
                'password': email_client.password,
            }

        return registration_data

    except Exception as e:
        logger.error(f"[GPT Register] Ошибка регистрации: {e}", exc_info=True)
        raise
    finally:
        await email_client.close()