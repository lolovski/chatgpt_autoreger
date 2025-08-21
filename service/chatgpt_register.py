import asyncio
import logging
import random

import names
from selenium.webdriver import ActionChains

from service.gologin_profile import GoLoginProfile
from service.sb_utils import wait_for_element_safe
from service.email_api import TempMailClient
from service.process_manager import process_manager

logger = logging.getLogger(__name__)

async def register_chatgpt(token: str, process_name: str = "gpt-register"):
    """Авторегистрация ChatGPT в GoLogin-профиле"""
    async def _job():
        email_client = TempMailClient()
        profile = GoLoginProfile(token)
        name = names.get_full_name()
        try:
            email = await email_client.create_account()
            logger.info(f"[GPT] Почта создана: {email}")

            profile.create_profile()
            profile.start_profile()

            def sync_job():
                with profile.open_sb() as sb:
                    sb.uc_open("https://chatgpt.com/auth/login")
                    if not wait_for_element_safe(sb, 'button[data-testid="signup-button"]', 20):
                        raise RuntimeError("Не найдена кнопка SignUp")
                    sb.uc_click('button[data-testid="signup-button"]')

                    sb.type('input[name="email"]', email)
                    sb.uc_click('button[type="submit"]')

                    if not wait_for_element_safe(sb, 'input[name="new-password"]', 20):
                        raise RuntimeError("Поле пароля не найдено")
                    sb.type('input[name="new-password"]', email_client.password)
                    sb.uc_click('button[type="submit"]')

                    code = asyncio.run(email_client.wait_for_code())
                    sb.type('input[name="code"]', code)
                    sb.uc_click('button[type="submit"]')
                    wait_for_element_safe(sb, 'input[name="name"]')
                    sb.type('input[name="name"]', name)

                    sb.click("span._typeableLabel_afhkj_73:contains('Birthday')")  # активируем
                    day = random.randint(1, 27)
                    month = random.randint(1, 11)
                    year = random.randint(1980, 2000)
                    for ch in f"{day}{month}{year}":
                        ActionChains(sb.driver).send_keys(ch).perform()
                    sb.uc_click('button[type="submit"]')

                    # Небольшая пауза на редирект в основное приложение
                    sb.wait_for_ready_state_complete()

            await asyncio.to_thread(sync_job)
            return email, email_client.password, name, profile.profile_id

        except Exception as e:
            logger.error(f"[GPT] Ошибка регистрации: {e}", exc_info=True)
            raise
        finally:
            profile.stop_profile()
            await email_client.close()

    return process_manager.start(process_name, _job())
