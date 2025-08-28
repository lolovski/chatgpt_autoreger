# service/chatgpt_login.py

import asyncio
import logging
from service.gologin_profile import GoLoginProfile
from service.sb_utils import wait_for_element_safe
from service.email_api import TempMailClient
from service.process_manager import process_manager
from service.exceptions import TwoFactorRequiredError  # ИЗМЕНЕНО: импорт исключения

logger = logging.getLogger(__name__)


# ИЗМЕНЕНО: Добавлен параметр 'code'
async def login_chatgpt_account(token: str, email_address: str, password: str, code: str = None,
                                process_name: str = "gpt-login"):
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

                    # ИЗМЕНЕНО: Блок обработки 2FA без input()
                    if sb.is_element_visible('input[name="code"]'):
                        if code:
                            # Если код был предоставлен, вводим его
                            sb.type('input[name="code"]', code)
                            sb.uc_click('button[type="submit"]')
                            profile.stop_profile(sb=sb)
                        else:
                            # Если код требуется, но не был предоставлен, выбрасываем исключение
                            profile.stop_profile(e=True)

                            raise TwoFactorRequiredError("Требуется код двухфакторной аутентификации")

                    sb.wait_for_ready_state_complete()


            await asyncio.to_thread(sync_job)
            return profile.profile_id

        except Exception as e:
            logger.error(f"[GPT] Ошибка входа: {e}", exc_info=True)
            profile.stop_profile(e=True)
            # Перебрасываем исключение, чтобы его мог поймать хендлер
            raise

    # Вместо process_manager, который скрывает исключения, вызываем напрямую
    # Это позволит нам ловить TwoFactorRequiredError в хендлере
    return await _job()