import asyncio
import logging
from service.email_api import TempMailClient
from service.sb_utils import *
logger = logging.getLogger(__name__)


class GoLoginRegistrationError(Exception):
    """Ошибка при создании GoLogin аккаунта"""
    pass

async def create_account_go_login(process_name: str = "gologin-create"):
    """
        Создаёт аккаунт GoLogin через обычный Chrome (не через GoLoginProfile).
        Использует TempMail для почты и возвращает (email, token).
        """
    email_client = TempMailClient()
    try:
        # 1. Создаём временную почту
        email = await email_client.create_account()
        password = email_client.password
        logger.info("[%s] Создан ящик %s", process_name, email)
        # 2. В браузере проходим регистрацию GoLogin
        with SB(browser="chrome", uc=True, headed=False) as sb:
            def sync_register():
                    sb.uc_open("https://app.gologin.com/sign_up")
                    sb.type('input[placeholder="Email address"]', email)
                    sb.type('input[placeholder="Password"]', password)
                    sb.type('input[placeholder="Confirm password"]', password)
                    sb.uc_click('button[type="submit"]')
                    sb.wait_for_ready_state_complete()

                    # Проверка успешной регистрации
                    if not wait_for_text_safe(text="Let’s customize GoLogin for your needs", timeout=25, sb=sb):
                        raise GoLoginRegistrationError("Не отобразился экран приветствия после регистрации")

                    # Переходим к странице токенов
                    sb.uc_open("https://app.gologin.com/personalArea/TokenApi")

                    # Создаём новый токен
                    if wait_for_element_safe(selector='span:contains("New Token")', timeout=15, sb=sb):
                        sb.uc_click('span:contains("New Token")')
                        if wait_for_element_safe(selector='span:contains("Confirm")', timeout=10, sb=sb):
                            sb.uc_click('span:contains("Confirm")')

            await asyncio.to_thread(sync_register)

            # --- асинхронная часть: ждём подтверждение на почте
            confirm_link = await email_client.wait_confirm_link()
            if not confirm_link:
                raise RuntimeError("Не пришло письмо подтверждения")

            # --- кликаем по ссылке подтверждения в отдельном браузере
            def sync_confirm():
                sb.uc_open(confirm_link)
                sb.uc_open('https://app.gologin.com/personalArea/TokenApi')
                sb.click('span:contains("New Token")')
                sb.wait_for_element_present('span:contains("Reveal token")', timeout=20)
                sb.js_click('span:contains("Reveal token")')
                sb.wait_for_element('div.css-8ojdky-InputToken')
                api_token = sb.get_text('div.css-8ojdky-InputToken')

                return api_token

            token = await asyncio.to_thread(sync_confirm)
        return email, token

    finally:
        await email_client.close()

