# service/gpt_login_processor.py

import logging
import asyncio
from db.models import AccountGPT
from service.gologin_profile import GoLoginProfile
from service.exceptions import VerificationCodeRequiredError
from service.email_api import TempMailClient

logger = logging.getLogger(__name__)


async def execute_login_flow(page, account: AccountGPT, code: str = None):
    """
    Универсальный обработчик логина, который умеет автоматически получать код.
    """
    logger.info(f"Начинаем процесс входа для {account.email_address}")
    await page.goto("https://chatgpt.com/auth/login", {'waitUntil': 'networkidle0'})

    # ... (код для клика по кнопке Login, ввода email и пароля)
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

    # Проверяем, нужен ли код подтверждения
    try:
        # OpenAI показывает заголовок "Check your email"
        await page.waitForSelector('input[name="code"]', {'timeout': 7000})
        is_code_needed = True
    except Exception:
        is_code_needed = False

    if not is_code_needed:
        return  # Код не нужен, выходим

    # --- ЛОГИКА ОБРАБОТКИ КОДА ---

    # Если код уже передан (например, от пользователя через FSM), просто вводим его
    if code:
        await page.type('input[name="code"]', code)
        await asyncio.gather(
            page.waitForNavigation({'waitUntil': 'networkidle0'}),
            page.click('button[type="submit"]')
        )
        return

    # Если аккаунт был создан автоматически, пытаемся получить код сами
    if account.auto_create:
        logger.info(f"Аккаунт {account.email_address} требует код. Пытаюсь получить автоматически...")
        email_client = TempMailClient()
        try:
            await email_client.restart(email=account.email_address, password=account.password)
            verification_code = await email_client.wait_for_code()
            logger.info(f"Код для {account.email_address} успешно получен: {verification_code}")
            await page.type('input[name="code"]', verification_code)
            await asyncio.gather(
                page.waitForNavigation({'waitUntil': 'networkidle0'}),
                page.click('button[type="submit"]')
            )
        except Exception as e:
            logger.error(
                f"Не удалось автоматически получить код для {account.email_address}: {e}. Запрашиваем у пользователя.")
            raise VerificationCodeRequiredError("Автоматическое получение кода не удалось.",
                                                is_manual_input_needed=True)
        finally:
            await email_client.close()
    else:
        # Если аккаунт ручной, всегда просим код у пользователя
        logger.info(f"Аккаунт {account.email_address} требует код. Запрашиваем у пользователя.")
        raise VerificationCodeRequiredError("Требуется код подтверждения с почты.", is_manual_input_needed=True)