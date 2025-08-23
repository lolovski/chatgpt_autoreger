import asyncio
import logging
from service.gologin_profile import GoLoginProfile
from service.sb_utils import wait_for_element_safe
from service.email_api import TempMailClient
from service.process_manager import process_manager

logger = logging.getLogger(__name__)


async def login_chatgpt_account(token: str, email_address: str, password: str, process_name: str = "gpt-register"):
    """Автовход в ChatGPT в GoLogin-профиле"""
    async def _job():
        profile = GoLoginProfile(api_token=token)
        try:
            profile.create_profile()
            profile.start_profile()

            def sync_job():
                with profile.open_sb() as sb:
                    sb.uc_open("https://chatgpt.com/auth/login")
                    if not wait_for_element_safe(sb, 'button[data-testid="login-button"]', 20):
                        raise RuntimeError("Не найдена кнопка login")
                    sb.uc_click('button[data-testid="login-button"]')
                    sb.type('input[name="email"]', email_address)
                    sb.uc_click('button[type="submit"]')

                    if not wait_for_element_safe(sb, 'input[name="current-password"]', 20):
                        raise RuntimeError("Поле пароля не найдено")
                    sb.type('input[name="current-password"]', password)
                    sb.uc_click('button[type="submit"]')

                    if sb.is_element_visible('input[name="code"]'):
                        code = input('Введите код')
                        sb.type('input[name="code"]', code)
                        sb.uc_click('button[type="submit"]')

                    sb.wait_for_ready_state_complete()
                    profile.stop_profile(sb=sb)

            await asyncio.to_thread(sync_job)
            return profile.profile_id

        except Exception as e:
            logger.error(f"[GPT] Ошибка входа: {e}", exc_info=True)
            profile.stop_profile(e=True)
            raise

    process_manager.start(process_name, _job())
    return await process_manager.result(process_name)
