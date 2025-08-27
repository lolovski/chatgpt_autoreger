import asyncio
import logging


from db.models import AccountGPT
from service import TempMailClient
from service.gologin_profile import GoLoginProfile
from service.sb_utils import wait_for_element_safe
from service.process_manager import process_manager

logger = logging.getLogger(__name__)


async def restart_chatgpt_account(token: str, account: AccountGPT, process_name: str = "gpt-restart", valid: bool = False):

    """Рестарт существующего ChatGPT профиля"""
    def login(sb, profile, email_client):

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
            return {
                "email_client": email_client,
                "profile": profile
            }

        sb.wait_for_ready_state_complete()

    async def _job():
        email_client = None
        if account.auto_create:
            email_client = TempMailClient()
            await email_client.restart(
                email=account.email_address,
                password=account.password
            )
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
                            login(sb, profile, email_client)
                        profile.stop_profile(cookies_path=account.cookies_path, sb=sb)
                await asyncio.to_thread(sync_job)

            except Exception as e:
                logger.error(f"[GPT] Ошибка рестарта: {e}", exc_info=True)
                profile.stop_profile(e=True)
                raise
            finally:
                if email_client is not None:
                    await email_client.close()


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
                        login(sb, profile, email_client)
                        profile.stop_profile(cookies_path=account.cookies_path, sb=sb)

                await asyncio.to_thread(sync_job)

            except Exception as e:
                logger.error(f"[GPT] Ошибка входа: {e}", exc_info=True)
                profile.stop_profile(e=True)
                raise
            finally:
                if email_client is not None:
                    await email_client.close()

    process_manager.start(process_name, _job())
    return await process_manager.result(process_name)


async def code_chatgpt_account(profile, email_client=None, code: str = None,  process_name: str = "gpt-code",):
    if email_client is None and code is None:
        raise ValueError("Необходимо указать email_client или code")

    async def _job():
        if email_client is not None:
            code = email_client.get_code()
        try:
            with profile.open_sb() as sb:

                sb.wait_for_element('input[name="code"]', timeout=10)
                sb.type('input[name="code"]', code)
                sb.click('button[type="submit"]')
                sb.wait_for_ready_state_complete()
                profile.stop_profile(sb=sb)
        except Exception as e:
            logger.error(f"[GPT] Ошибка входа: {e}", exc_info=True)
            profile.stop_profile(e=True)
            raise
        finally:
            if email_client is not None:
                await email_client.close()

    process_manager.start(process_name, _job())
    return await process_manager.result(process_name)