import asyncio
import logging

from win32con import SB_CTL

from db.models import AccountGPT
from service.gologin_profile import GoLoginProfile
from service.sb_utils import wait_for_element_safe
from service.process_manager import process_manager

logger = logging.getLogger(__name__)


async def restart_chatgpt_account(token: str, account: AccountGPT, process_name: str = "gpt-restart", valid: bool = False):
    """Рестарт существующего ChatGPT профиля"""
    def login(sb):
        sb.uc_open("https://chatgpt.com/auth/login")
        if not wait_for_element_safe(sb, 'button[data-testid="login-button"]', 20):
            raise RuntimeError("Не найдена кнопка login")
        sb.uc_click('button[data-testid="login-button"]')
        sb.type('input[name="email"]', account.email_address)
        sb.uc_click('button[type="submit"]')

        if not wait_for_element_safe(sb, 'input[name="current-password"]', 20):
            raise RuntimeError("Поле пароля не найдено")
        sb.type('input[name="current-password"]', account.password)
        sb.uc_click('button[type="submit"]')

        if sb.is_element_visible('input[name="code"]'):
            code = input('Введите код')
            sb.type('input[name="code"]', code)
            sb.uc_click('button[type="submit"]')

        sb.wait_for_ready_state_complete()

    async def _job():
        if valid:
            profile = GoLoginProfile(
                api_token=token,
                profile_id=account.id,
            )
            try:
                profile.create_profile(valid=valid)
                profile.start_profile()

                def sync_job():
                    with profile.open_sb() as sb:
                        sb.uc_open("https://chatgpt.com/")
                        sb.wait_for_ready_state_complete()
                        url = sb.get_current_url()
                        if url == 'https://auth.openai.com/log-in' or sb.is_element_visible('button[data-testid="login-button"]'):
                            login(sb)
                        profile.stop_profile(cookies_path=account.cookies_path, sb=sb)
                await asyncio.to_thread(sync_job)

            except Exception as e:
                logger.error(f"[GPT] Ошибка рестарта: {e}", exc_info=True)
                profile.stop_profile(e=True)
                raise

        else:
            profile = GoLoginProfile(
                api_token=token,
                profile_id=account.id,
            )
            try:
                profile.create_profile(valid=valid)
                profile.start_profile()

                def sync_job():
                    with profile.open_sb() as sb:
                        login(sb)
                        profile.stop_profile(cookies_path=account.cookies_path, sb=sb)

                await asyncio.to_thread(sync_job)

            except Exception as e:
                logger.error(f"[GPT] Ошибка входа: {e}", exc_info=True)
                profile.stop_profile(e=True)
                raise

    process_manager.start(process_name, _job())
    return await process_manager.result(process_name)



