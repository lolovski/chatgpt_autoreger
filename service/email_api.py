import aiohttp
import asyncio
import re
import random
import string
import logging

logger = logging.getLogger(__name__)

class TempMailClient:
    BASE_URL = "https://api.mail.tm"

    def __init__(self):
        self.session = None
        self.token = None
        self.address = None
        self.password = None

    async def _get_domains(self):
        async with self.session.get(f"{self.BASE_URL}/domains") as resp:
            data = await resp.json()
            return data["hydra:member"][0]["domain"]

    def _random_string(self, length=10):
        return ''.join(random.choices(string.ascii_lowercase, k=length)) + str(int(asyncio.get_event_loop().time()*1000))

    async def create_account(self):
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)
        domain = await self._get_domains()
        self.address = f"{self._random_string()}@{domain}"
        self.password = self._random_string(12)

        payload = {"address": self.address, "password": self.password}
        async with self.session.post(f"{self.BASE_URL}/accounts", json=payload) as resp:
            if resp.status not in (200, 201):
                text = await resp.text()
                raise RuntimeError(f"Не удалось создать почту: {text}")

        await self.login()
        return self.address

    async def login(self):
        payload = {"address": self.address, "password": self.password}
        async with self.session.post(f"{self.BASE_URL}/token", json=payload) as resp:
            data = await resp.json()
            if "token" not in data:
                raise RuntimeError(f"Не удалось получить токен: {data}")
            self.token = data["token"]

    async def restart(self, email, password):
        self.address = email
        self.password = password
        await self.login()

    async def _get_messages(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        async with self.session.get(f"{self.BASE_URL}/messages", headers=headers) as resp:
            return await resp.json()

    async def wait_for_code(self, timeout=120, check_interval=5):
        end_time = asyncio.get_event_loop().time() + timeout
        code_pattern = re.compile(r"\b\d{6}\b")
        while asyncio.get_event_loop().time() < end_time:
            messages = await self._get_messages()
            for msg in messages.get("hydra:member", []):
                headers = {"Authorization": f"Bearer {self.token}"}
                async with self.session.get(f"{self.BASE_URL}/messages/{msg['id']}", headers=headers) as r:
                    full_msg = await r.json()
                    text_content = full_msg.get("text", "") or full_msg.get("html", "")
                    match = code_pattern.search(text_content)
                    if match:
                        return match.group(0)
            await asyncio.sleep(check_interval)
        raise TimeoutError("Код не пришёл вовремя")

    async def wait_confirm_link(self, timeout=120, check_interval=5):
        end_time = asyncio.get_event_loop().time() + timeout
        pattern = re.compile(r"https:\/\/api\.gologin\.com\/user\/email\/confirm\/\S+")
        while asyncio.get_event_loop().time() < end_time:
            messages = await self._get_messages()
            for msg in messages.get("hydra:member", []):
                headers = {"Authorization": f"Bearer {self.token}"}
                async with self.session.get(f"{self.BASE_URL}/messages/{msg['id']}", headers=headers) as r:
                    full_msg = await r.json()
                    text_content = full_msg.get("text", "") or full_msg.get("html", "")
                    match = pattern.search(text_content)
                    if match:
                        return match.group(0)
            await asyncio.sleep(check_interval)
        raise TimeoutError("Ссылка подтверждения не пришла")

    async def close(self):
        if self.session:
            await self.session.close()
            logger.info(f"[TempMail] Сессия {self.address} закрыта")
