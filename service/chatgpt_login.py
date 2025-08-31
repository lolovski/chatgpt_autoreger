# service/chatgpt_login.py

import logging
import asyncio  # Добавляем импорт

from db.models import AccountGPT
from service.gpt_login_processor import execute_login_flow
from service.gologin_profile import GoLoginProfile
from service.exceptions import TwoFactorRequiredError

logger = logging.getLogger(__name__)


async def login_chatgpt_account(token: str, email_address: str, password: str, name: str, code: str = None) -> str:
    temp_account = AccountGPT(name=name, email_address=email_address, password=password, id="temp", auto_create=False)
    profile = GoLoginProfile(api_token=token)

    try:
        async with profile as page:
            await execute_login_flow(page, temp_account, code)

            await page.waitForSelector('#prompt-textarea', {'timeout': 30000})
            await profile.save_cookies(f'cookies/{profile.profile_id}.json', domains=['chatgpt.com', 'openai.com'])
            return profile.profile_id
    except Exception:
        raise