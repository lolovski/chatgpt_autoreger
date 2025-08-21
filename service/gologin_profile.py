import asyncio
import json
import logging
import time
from typing import Optional

import requests
from seleniumbase import SB

logger = logging.getLogger(__name__)


class GoLoginProfileError(Exception):
    """Ошибка работы с профилем GoLogin"""
    pass


class GoLoginProfile:
    """
    Класс для управления профилем GoLogin и работы через SeleniumBase.
    """

    def __init__(self, api_token: str, profile_id: Optional[str] = None, process_name: str = "gologin-profile"):
        self.api_token = api_token
        self.profile_id = profile_id
        self.process_name = process_name
        self.driver_url: Optional[str] = None

        self.base_url = "https://api.gologin.com"
        self.headers = {"Authorization": f"Bearer {self.api_token}"}

    # ================= API =================

    def _request(self, method: str, endpoint: str, **kwargs):
        url = f"{self.base_url}{endpoint}"
        resp = requests.request(method, url, headers=self.headers, **kwargs)
        if resp.status_code >= 400:
            raise GoLoginProfileError(f"GoLogin API error {resp.status_code}: {resp.text}")
        return resp.json() if resp.text else {}

    def create_profile(self, name: str = "ChatGPT profile", proxy: Optional[dict] = None) -> str:
        """Создаёт новый профиль GoLogin и возвращает его ID"""
        payload = {"name": name, "browserType": "chrome"}
        if proxy:
            payload["proxy"] = proxy
        data = self._request("POST", "/browser", json=payload)
        self.profile_id = data.get("id")
        if not self.profile_id:
            raise GoLoginProfileError("Не удалось создать профиль GoLogin (нет id)")
        logger.info("[%s] Создан профиль GoLogin: %s", self.process_name, self.profile_id)
        return self.profile_id

    def delete_profile(self):
        """Удаляет профиль GoLogin"""
        if not self.profile_id:
            return
        self._request("DELETE", f"/browser/{self.profile_id}")
        logger.info("[%s] Удалён профиль %s", self.process_name, self.profile_id)

    def start_profile(self, timeout: int = 30):
        """Запускает профиль GoLogin и возвращает remote driver url"""
        if not self.profile_id:
            raise GoLoginProfileError("profile_id не задан")

        data = self._request("GET", f"/browser/{self.profile_id}/start?tz=UTC")
        ws_url = data.get("wsUrl")
        if not ws_url:
            raise GoLoginProfileError("Не удалось получить wsUrl для профиля")

        self.driver_url = ws_url
        logger.info("[%s] Профиль %s запущен, wsUrl=%s", self.process_name, self.profile_id, ws_url)
        return ws_url

    def stop_profile(self):
        """Останавливает профиль GoLogin"""
        if not self.profile_id:
            return
        try:
            self._request("GET", f"/browser/{self.profile_id}/stop")
            logger.info("[%s] Профиль %s остановлен", self.process_name, self.profile_id)
        except Exception as e:
            logger.error("[%s] Ошибка при остановке профиля %s: %s", self.process_name, self.profile_id, e)

    # ================= SeleniumBase =================

    def open_sb(self, headless: bool = False) -> SB:
        """
        Открывает SeleniumBase, подключённый к профилю GoLogin.
        Возвращает объект SB, который можно использовать как контекстный менеджер.
        """
        if not self.driver_url:
            raise GoLoginProfileError("Сначала вызови start_profile()")

        sb = SB(
            browser="chrome",
            uc=True,
            headed=not headless,
            remote_url=self.driver_url,
        )
        return sb

    # ================= High-level helpers =================

    async def __aenter__(self):
        """Асинхронный вход в контекст (start profile + SB)"""
        await asyncio.to_thread(self.start_profile)
        self.sb = self.open_sb()
        await asyncio.to_thread(self.sb.__enter__)
        return self.sb

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Асинхронный выход (close SB + stop profile)"""
        try:
            await asyncio.to_thread(self.sb.__exit__, exc_type, exc_val, exc_tb)
        finally:
            await asyncio.to_thread(self.stop_profile)
