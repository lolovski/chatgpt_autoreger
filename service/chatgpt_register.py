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
        profile = GoLoginProfile(api_token=token)
        name = names.get_full_name()
        try:
            email = await email_client.create_account()
            logger.info(f"[GPT] Почта создана: {email}")

            profile.create_profile()
            profile.start_profile()

            # держим браузер открытым до конца
            with profile.open_sb() as sb:

                def sync_signup():
                    sb.uc_open("https://chatgpt.com/auth/login")
                    if not wait_for_element_safe(sb, 'button[data-testid="signup-button"]', 20):
                        raise RuntimeError("Не найдена кнопка SignUp")
                    sb.uc_click('button[data-testid="signup-button"]')

                    if not wait_for_element_safe(sb, 'input[name="email"]', 20):
                        raise RuntimeError("Поле email не найдено")
                    sb.type('input[name="email"]', email)
                    sb.uc_click('button[type="submit"]')

                    if not wait_for_element_safe(sb, 'input[name="new-password"]', 20):
                        raise RuntimeError("Поле пароля не найдено")
                    sb.type('input[name="new-password"]', email_client.password)
                    sb.uc_click('button[type="submit"]')

                await asyncio.to_thread(sync_signup)

                # ждём код из почты
                code = await email_client.wait_for_code()
                if not code:
                    raise RuntimeError("Не удалось получить код подтверждения")
                logger.info(f"[GPT] Код подтверждения: {code}")

                def sync_with_code():
                    if not wait_for_element_safe(sb, 'input[name="code"]', 20):
                        raise RuntimeError("Поле ввода кода не найдено")
                    sb.type('input[name="code"]', code)
                    sb.uc_click('button[type="submit"]')

                    if not wait_for_element_safe(sb, 'input[name="name"]', 20):
                        raise RuntimeError("Поле имени не найдено")
                    sb.type('input[name="name"]', name)

                    sb.click("span._typeableLabel_afhkj_73:contains('Birthday')")
                    day = random.randint(5, 27)
                    month = random.randint(5, 11)
                    year = 2000
                    for ch in f"{day}{month}{year}":
                        ActionChains(sb.driver).send_keys(ch).perform()

                    sb.uc_click('button[type="submit"]')

                    sb.wait_for_ready_state_complete()

                await asyncio.to_thread(sync_with_code)

            profile.stop_profile(sb=sb)
            return {
                'email_address': email,
                'id': profile.profile_id,
                'password': email_client.password,
                'name': name
            }

        except Exception as e:
            profile.stop_profile(e=True)
            logger.error(f"[GPT] Ошибка регистрации: {e}", exc_info=True)
            raise
        finally:
            await email_client.close()

    process_manager.start(process_name, _job())
    return await process_manager.result(process_name)

