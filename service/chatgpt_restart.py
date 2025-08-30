# service/chatgpt_restart.py

import logging
import asyncio # Добавляем импорт
from db.models import AccountGPT
from service.gologin_profile import GoLoginProfile
from service.exceptions import TwoFactorRequiredError

logger = logging.getLogger(__name__)

async def _perform_login(page, account: AccountGPT, code: str = None):
    """Вспомогательная функция для выполнения логина на странице."""
    logger.info(f"Сессия невалидна для {account.email_address}. Выполняется повторный вход.")
    await page.goto("https://chatgpt.com/auth/login", {'waitUntil': 'networkidle0'})

    # ИСПРАВЛЕНО: Все клики, ведущие к навигации, обернуты в asyncio.gather
    await asyncio.gather(
        page.waitForNavigation({'waitUntil': 'networkidle0'}),
        page.click('button[data-testid="login-button"]')
    )

    await page.waitForSelector('input[name="email"]', {'timeout': 20000})
    await page.type('input[name="email"]', account.email_address)
    await asyncio.gather(
        page.waitForNavigation({'waitUntil': 'networkidle0'}),
        page.click('button[type="submit"]')
    )

    await page.waitForSelector('input[name="current-password"]', {'timeout': 20000})
    await page.type('input[name="current-password"]', account.password)
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

# Остальная часть файла restart_chatgpt_account остается без изменений
async def restart_chatgpt_account(token: str, account: AccountGPT, code: str = None):
    """
    Перезапускает существующий профиль ChatGPT, используя сохраненные cookie.
    Если сессия истекла, выполняет повторный вход.
    """
    profile = GoLoginProfile(api_token=token, profile_id=account.id)

    try:
        async with profile as page:
            logger.info(f"Загрузка cookie из {account.cookies_path} для профиля {account.id}")
            await profile.load_cookies(account.cookies_path)

            logger.info(f"Переход на главную страницу ChatGPT для профиля {account.id}")
            await page.goto("https://chatgpt.com/", {'waitUntil': 'networkidle0'})

            is_login_needed = "auth" in page.url or await page.querySelector('button[data-testid="login-button"]')

            if is_login_needed:
                await _perform_login(page, account, code)

            logger.info(f"Профиль {account.id} успешно запущен.")

            await profile.save_cookies(account.cookies_path, domains=['chatgpt.com', 'openai.com'])

    except Exception as e:
        logger.error(f"[GPT Restart] Ошибка перезапуска для аккаунта {account.id}: {e}", exc_info=True)
        raise