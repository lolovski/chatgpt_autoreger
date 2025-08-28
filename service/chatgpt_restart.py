# service/chatgpt_restart.py

import asyncio
import logging
from db.models import AccountGPT
from service.gologin_profile import GoLoginProfile
from service.sb_utils import wait_for_element_safe
from service.process_manager import process_manager
from service.exceptions import TwoFactorRequiredError  # ИЗМЕНЕНО: импорт исключения

logger = logging.getLogger(__name__)


# ИЗМЕНЕНО: Добавлен параметр 'code'
async def restart_chatgpt_account(token: str, account: AccountGPT, code: str = None, process_name: str = "gpt-restart",
                                  valid: bool = False):
    """Рестарт существующего ChatGPT профиля"""

    def login(sb):
        if sb.get_current_url().startswith('https://auth.openai.com/'):
            ...
        else:
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

        # ИЗМЕНЕНО: Блок обработки 2FA без input()
        if sb.is_element_visible('input[name="code"]'):
            if code:
                # Если код был предоставлен, вводим его
                sb.type('input[name="code"]', code)
                sb.uc_click('button[type="submit"]')
            else:
                # Если код требуется, но не был предоставлен, выбрасываем исключение
                raise TwoFactorRequiredError("Требуется код двухфакторной аутентификации")

        sb.wait_for_ready_state_complete()

    async def _job():
        profile = GoLoginProfile(
            api_token=token,
            profile_id=account.id,
        )
        try:
            profile.create_profile(valid=valid)
            profile.start_profile()

            def sync_job():
                with profile.open_sb() as sb:
                    if valid:
                        sb.uc_open("https://chatgpt.com/")
                        sb.wait_for_ready_state_complete()
                        url = sb.get_current_url()
                        if url.startswith('https://auth.openai.com/') or sb.is_element_visible(
                                'button[data-testid="login-button"]'):
                            logger.warning(f"[GPT] Сессия для {account.id} невалидна, требуется повторный вход.")
                            login(sb)
                    else:
                        login(sb)

                    profile.stop_profile(cookies_path=account.cookies_path, sb=sb)

            await asyncio.to_thread(sync_job)

        except Exception as e:
            logger.error(f"[GPT] Ошибка рестарта/входа: {e}", exc_info=True)
            profile.stop_profile(e=True)
            # Перебрасываем исключение, чтобы его мог поймать хендлер
            raise

    # Вызываем напрямую для обработки исключений в хендлере
    return await _job()