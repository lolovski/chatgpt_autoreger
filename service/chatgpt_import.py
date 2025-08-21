import asyncio
import json
import logging
from service.gologin_profile import GoLoginProfile
from service.sb_utils import restore_local_storage
from service.process_manager import process_manager

logger = logging.getLogger(__name__)


async def import_chatgpt_account(token: str, bundle_path: str, process_name: str = "gpt-import"):
    """Импорт аккаунта ChatGPT из сохраненного bundle"""
    async def _job():
        profile = GoLoginProfile(token)
        try:
            profile.create_profile()
            profile.start_profile()

            def sync_job():
                with open(bundle_path, "r", encoding="utf-8") as f:
                    bundle = json.load(f)

                with profile.open_sb() as sb:
                    for origin, cookies in bundle["cookies"].items():
                        sb.uc_open(origin)
                        for c in cookies:
                            try:
                                sb.driver.add_cookie(c)
                            except Exception:
                                pass
                        restore_local_storage(sb, bundle["localStorage"].get(origin, {}))
                        sb.refresh()

            await asyncio.to_thread(sync_job)

        except Exception as e:
            logger.error(f"[GPT] Ошибка импорта: {e}", exc_info=True)
            raise


    return process_manager.start(process_name, _job())
