import asyncio
import json
import logging
import time
from typing import Optional, Dict
from gologin import GoLogin
import requests
from seleniumbase import SB

from service.sb_utils import *

logger = logging.getLogger(__name__)


class GoLoginProfileError(Exception):
    """Ошибка работы с профилем GoLogin"""
    pass


class GoLoginProfile:
    """
    Класс для управления профилем GoLogin и работы через SeleniumBase.
    """

    def __init__(self, api_token: str, profile_id: Optional[str] = None, process_name: str = f"GoLoginProfile-{int(time.time())}", bundle: Optional[Dict] = None):
        self.api_token = api_token
        self.bundle = bundle
        self.profile_id = profile_id
        self.process_name = process_name
        self.driver_url: Optional[str] = None
        self.create_payload: Optional[Dict] = None
        self.gl = GoLogin({"token": self.api_token})
        self.base_url = "https://api.gologin.com"
        self.headers={
            "Authorization": f"Bearer {self.api_token}",
            "User-Agent": "gologin-api",
            "Content-Type": "application/json",
        },

    # ================= API =================

    def _request(self, method: str, endpoint: str, **kwargs):
        url = f"{self.base_url}{endpoint}"
        resp = requests.request(method, url, headers=self.headers, **kwargs)
        if resp.status_code >= 400:
            raise GoLoginProfileError(f"GoLogin API error {resp.status_code}: {resp.text}")
        return resp.json() if resp.text else {}

    def try_link_proxy(self):
        payload = {
            "countryCode": 'us',
            "isDC": True,
            "isMobile": False,
            "profileIdToLink": self.profile_id,
        }
        self._request(
            method='POST',
            endpoint=r'/users-proxies/mobile-proxy',
            json=payload
        )
    def setup_bundle(self):
        base_payload = dict(self.bundle.get("profile_payload", {}))
        # Гарантируем обновление имени (чтобы не конфликтовало)
        base_payload["name"] = base_payload.get("name", "clone") + f"-import-{int(time.time())}"
        # Сохраним подпись
        note = base_payload.get("notes", "")
        base_payload["notes"] = f"{note} | imported:{now_iso()}"
        # Обновим UA (если требуется строго соответствовать)
        ua = self.bundle.get("user_agent")
        if ua:
            nav = base_payload.get("navigator", {})
            nav["userAgent"] = ua
            base_payload["navigator"] = nav

        # Добавим cookies прямо в storage профиля (на момент create)
        storage = base_payload.get("storage", {})
        storage_cookies = []
        for origin, cookies in self.bundle.get("cookies", {}).items():
            # GoLogin принимает список cookies без жёсткой привязки к origin
            for c in cookies:
                storage_cookies.append(c)
        storage["cookies"] = storage_cookies
        base_payload["storage"] = storage

        self.create_payload = base_payload

    def create_profile(self, name: str = f"ChatGPTprofile-{int(time.time())}") -> str:
        """Создаёт новый профиль GoLogin и возвращает его ID"""
        if self.profile_id:
            self.gl.setProfileId(profile_id=self.profile_id)
            logger.info("[%s] Используется существующий профиль GoLogin: %s", self.process_name, self.profile_id)
            return self.profile_id
        if self.bundle:
            self.setup_bundle()
            profile = self.gl.create(self.create_payload)
            self.profile_id = profile
        else:
            profile = self.gl.createProfileRandomFingerprint({"os": "win", "name": name})
            self.profile_id = profile.get("id")

        self.try_link_proxy()

        if not self.profile_id:
            raise GoLoginProfileError("Не удалось создать профиль GoLogin (нет id)")
        self.gl.setProfileId(profile_id=self.profile_id)
        logger.info("[%s] Создан профиль GoLogin: %s", self.process_name, self.profile_id)
        return self.profile_id

    def delete_profile(self):
        """Удаляет профиль GoLogin"""
        if not self.profile_id:
            return
        self.gl.delete(profile_id=self.profile_id)
        logger.info("[%s] Удалён профиль %s", self.process_name, self.profile_id)

    def start_profile(self, timeout: int = 30):
        """Запускает профиль GoLogin и возвращает remote driver url"""
        if not self.profile_id:
            raise GoLoginProfileError("profile_id не задан")

        ws_url = self.gl.start()

        if not ws_url:
            raise GoLoginProfileError("Не удалось получить wsUrl для профиля")

        self.driver_url = ws_url
        logger.info("[%s] Профиль %s запущен, wsUrl=%s", self.process_name, self.profile_id, ws_url)
        return ws_url

    def stop_profile(self, sb=None, e=None):
        """Останавливает профиль GoLogin"""
        if e:
            self.gl.stop()
            logger.info("[%s] Профиль %s остановлен", self.process_name, self.profile_id)
        if not self.profile_id:
            return
        try:
            self._collect_portable_state(sb)
            self.save_bundle()
            self.gl.stop()
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

        host, port = self.driver_url.split(":")
        sb = SB(
            uc=True,
            locale='en',
            headed=not headless,
            remote_url=self.driver_url,
        )
        return sb

    # ================= High-level helpers =================

    def _collect_portable_state(self, sb: SB):
        """
        Собираем всё нужное для бандла: UA, cookies, localStorage, профильные настройки.
        """
        # userAgent
        ua = sb.execute_script("return navigator.userAgent;")

        # Куки и LocalStorage по обоим доменам
        bundle_cookies = {}
        bundle_local = {}

        for origin in ("https://chatgpt.com", "https://auth.openai.com"):
            sb.uc_open(origin)
            sb.wait_for_ready_state_complete()
            sb.sleep(1)
            # cookies текущего origin
            raw = sb.driver.get_cookies()
            norm = [sanitize_cookie_for_bundle(c) for c in raw]
            bundle_cookies[origin] = norm

            # localStorage
            ls = get_local_storage_map(sb)
            bundle_local[origin] = ls

        # Профиль/фингерпринт из GoLogin
        prof_json = self.gl.getProfile(self.profile_id)

        # Мини-санация: удалим id, чтобы случайно не передать его при create
        profile_payload = {k: v for k, v in prof_json.items() if k not in ("id", "_id", "profile_id")}
        # Обновим заметку, чтобы отслеживать происхождение
        profile_payload["notes"] = f"cloned-from:{self.profile_id}; saved:{now_iso()}"

        # Составим «рецепт» прокси (мы знаем что устанавливали DC/US)
        proxy_recipe = {"countryCode": "US", "isDC": True, "isMobile": False}

        bundle = {
            "schema": 1,
            "saved_at": now_iso(),
            "source_profile_id": self.profile_id,
            "user_agent": ua,
            "proxy_recipe": proxy_recipe,
            "cookies": bundle_cookies,
            "localStorage": bundle_local,
            "profile_payload": profile_payload,   # fingerprint/navigator/etc.
        }
        self.bundle = bundle

    def save_bundle(self):
        out_name = f'cookies/{self.profile_id}'
        with open(out_name, "w", encoding="utf-8") as f:
            json.dump(self.bundle, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ Сохранён переносимый бандл: {out_name}")
        logger.info(f"   Профиль-источник: {self.profile_id}")


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
