import asyncio
import os
import json
import time
import logging
import sys
from time import sleep

import names
from gologin import GoLogin
from gologin.http_client import make_request

from selenium.webdriver import Keys, ActionChains
from seleniumbase import SB

from db.models import AccountGPT
# ВАЖНО: почта из твоего модуля
from .email_api import TempMailClient


# ---- ВСПОМОГАТЕЛЬНЫЕ УТИЛИТЫ -------------------------------------------------

def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sanitize_cookie_for_bundle(c):
    """
    Приводим куки к универсальному виду для хранения и последующего импорта.
    Selenium get_cookies() -> {name, value, domain, path, secure, httpOnly, expiry?}
    В бандле храним:
      - name, value, domain, path, secure, httpOnly, sameSite?, expirationDate (sec)
    """
    out = {
        "name": c.get("name"),
        "value": c.get("value"),
        "domain": c.get("domain"),
        "path": c.get("path", "/"),
        "secure": bool(c.get("secure", False)),
        "httpOnly": bool(c.get("httpOnly", False)),
    }
    if "sameSite" in c and c["sameSite"]:
        out["sameSite"] = c["sameSite"].lower()
    # expiry (int seconds) или expirationDate (иногда мс). Приведём к сек.
    expiry = c.get("expiry", None)
    if expiry is None:
        expiry = c.get("expirationDate", None)
    if expiry is not None:
        # Если вдруг пришло в миллисекундах
        if expiry > 2_147_483_647:  # > int32
            expiry = int(expiry / 1000)
        out["expirationDate"] = int(expiry)
    return out

def get_local_storage_map(sb):
    """
    Считываем весь localStorage текущего origin через JS.
    Возвращает dict {key: value}
    """
    script = """
    var out = {};
    for (var i = 0; i < localStorage.length; i++) {
        var k = localStorage.key(i);
        out[k] = localStorage.getItem(k);
    }
    return out;
    """
    return sb.execute_script(script)

def set_local_storage_map(sb, data: dict):
    """
    Восстанавливаем localStorage текущего origin.
    """
    if not data:
        return
    # Уничтожим перед вставкой (чтобы не мешались старые ключи)
    sb.execute_script("localStorage.clear();")
    for k, v in data.items():
        sb.execute_script("localStorage.setItem(arguments[0], arguments[1]);", k, v)

def try_link_proxy(gl_token: str, profile_id: str, country_code="US", is_dc=True, is_mobile=False):
    """
    Сохраняем «рецепт» прокси в бандл, а здесь — вспомогалка для линковки прокси к профилю.
    Используем тот же endpoint, что и у тебя работал в Postman.
    """
    api_url = "https://api.gologin.com"
    payload = {
        "countryCode": country_code,
        "isDC": bool(is_dc),
        "isMobile": bool(is_mobile),
        "profileIdToLink": profile_id,
    }
    resp = make_request(
        "POST",
        f"{api_url}/users-proxies/mobile-proxy",
        headers={
            "Authorization": f"Bearer {gl_token}",
            "User-Agent": "gologin-api",
            "Content-Type": "application/json",
        },
        json_data=payload,
    )
    try:
        data = resp.json()
    except Exception:
        data = {"raw": str(resp)}
    return data

# ---- ОСНОВНОЙ КЛАСС ---------------------------------------------------------

class AccountGPTReg:
    """
    1) Создаёт профиль в GoLogin и стартует его.
    2) Выполняет авторегистрацию ChatGPT (chatgpt.com / auth.openai.com).
    3) Экспортирует переносимый бандл: fingerprint + navigator + UA + proxy recipe + cookies + localStorage.
    """
    def __init__(self, token):
        self.TOKEN = token
        self.bundle = None
        self.API_URL = "https://api.gologin.com"
        self.name = names.get_full_name()
        self.email_client = TempMailClient()
        self.email_address = None
        # создаём профиль со случайным фингерпринтом (Windows)
        self.profile = GoLogin({"token": self.TOKEN})
        prof = self.profile.createProfileRandomFingerprint({"os": "win", "name": f"autoreg-{int(time.time())}"})
        self.profile_id = prof["id"]

        # привяжем DC/US прокси (как у тебя в Postman)
        _ = try_link_proxy(self.TOKEN, self.profile_id, country_code="US", is_dc=True, is_mobile=False)

        # подготовим объект, привязанный к профилю
        self.profile = GoLogin({"token": self.TOKEN, "profile_id": self.profile_id})
        self.debugger_address = self.profile.start()

    def _open_sb(self):
        host, port = self.debugger_address.split(":")
        return SB(
            uc=True,
            locale="en",
            headed=True,
            test=True,
            chromium_arg=[
                f"--remote-debugging-address={host}",
                f"--remote-debugging-port={port}",
            ],
        )

    async def _do_registration_flow(self, sb: SB):
        """
        Минимальный рабочий флоу: логика из твоих примеров.
        Если у тебя есть своя расширенная логика — можно подставить.
        """

        sb.uc_open("https://chatgpt.com/auth/login")
        sb.wait_for_element('button[data-testid="signup-button"]')
        sb.uc_click('button[data-testid="signup-button"]')

        # страница create account
        sb.type('input[name="email"]', self.email_address)
        sb.uc_click('button[type="submit"]')

        sb.wait_for_element('input[name="new-password"]')
        sb.type('input[name="new-password"]', self.email_client.password)
        sb.uc_click('button[type="submit"]')

        code = await self.email_client.wait_for_code()
        sb.wait_for_element('input[name="code"]')
        sb.type('input[name="code"]', code)
        sb.uc_click('button[type="submit"]')

        # Имя + ДР (как делал ранее)
        sb.wait_for_element('input[name="name"]')
        sb.type('input[name="name"]', self.name)

        sb.click("span._typeableLabel_afhkj_73:contains('Birthday')")  # активируем
        sleep(0.2)
        # Пример: 11/11/2001
        for ch in "11112001":
            ActionChains(sb.driver).send_keys(ch).perform()
        sb.uc_click('button[type="submit"]')

        # Небольшая пауза на редирект в основное приложение
        sb.wait_for_ready_state_complete()
        sleep(1.5)

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
            sleep(0.5)

            # cookies текущего origin
            raw = sb.driver.get_cookies()
            norm = [sanitize_cookie_for_bundle(c) for c in raw]
            bundle_cookies[origin] = norm

            # localStorage
            ls = get_local_storage_map(sb)
            bundle_local[origin] = ls

        # Профиль/фингерпринт из GoLogin
        prof_json = self.profile.getProfile(self.profile_id)

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

    async def run(self):

        with self._open_sb() as sb:
            self.email_address = await self.email_client.create_account()
            await self._do_registration_flow(sb)
            self._collect_portable_state(sb)
            await self.email_client.close()
            self.profile.stop()

        return self

    async def save_bundle(self, account):
        # Сохраняем переносимый бандл на диск
        out_name = account.cookies_path
        with open(out_name, "w", encoding="utf-8") as f:
            json.dump(self.bundle, f, ensure_ascii=False, indent=2)
        print(f"✅ Сохранён переносимый бандл: {out_name}")
        print(f"   Профиль-источник: {self.profile_id}")
        return


def cookie_for_selenium(c):
    """
    Преобразование куки из бандла в формат add_cookie().
    """
    out = {
        "name": c["name"],
        "value": c["value"],
        "path": c.get("path", "/"),
        "domain": c.get("domain"),
        "secure": bool(c.get("secure", False)),
        "httpOnly": bool(c.get("httpOnly", False)),
    }
    exp = c.get("expirationDate", None)
    if exp is not None:
        # Selenium ждёт 'expiry' в секундах (int)
        out["expiry"] = int(exp)
    return out


def set_local_storage(sb, data: dict):
    sb.execute_script("localStorage.clear();")
    for k, v in (data or {}).items():
        sb.execute_script("localStorage.setItem(arguments[0], arguments[1]);", k, v)


class AccountGPTImport:
    def __init__(self, account: AccountGPT, token: str):
        self.account = account
        self.TOKEN = token
        with open(account.cookies_path, "r", encoding="utf-8") as f:
            self.bundle = json.load(f)

        # Подготовим payload профиля к созданию
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

    def create_profile(self):
        gl = GoLogin({"token": self.TOKEN})
        new_prof = gl.create(self.create_payload)
        self.new_profile_id = new_prof
        self.gl_profile = GoLogin({"token": self.TOKEN, "profile_id": self.new_profile_id})

        # Привяжем прокси по рецепту из бандла
        recipe = self.bundle.get("proxy_recipe", {"countryCode": "US", "isDC": True, "isMobile": False})
        _ = try_link_proxy(
            self.TOKEN,
            self.new_profile_id,
            country_code=recipe.get("countryCode", "US"),
            is_dc=bool(recipe.get("isDC", True)),
            is_mobile=bool(recipe.get("isMobile", False)),
        )

    def start_and_restore(self):
        dbg = self.gl_profile.start()
        host, port = dbg.split(":")
        with SB(
            uc=True,
            locale="en",
            headed=True,
            test=True,
            chromium_arg=[
                f"--remote-debugging-address={host}",
                f"--remote-debugging-port={port}",
            ],
        ) as sb:
            # 1) Восстановим обе_origin: localStorage + cookies, затем refresh
            for origin in ("https://chatgpt.com", "https://auth.openai.com"):
                sb.uc_open(origin)
                sb.wait_for_ready_state_complete()
                sleep(0.5)

                # localStorage
                ls_map = self.bundle.get("localStorage", {}).get(origin, {})
                set_local_storage(sb, ls_map)

                # cookies
                # Selenium требует для add_cookie: быть на нужном домене
                raw = self.bundle.get("cookies", {}).get(origin, [])
                for c in raw:
                    try:
                        sb.driver.add_cookie(cookie_for_selenium(c))
                    except Exception as e:
                        # Некоторые httpOnly/secure домены может не дать поставить до первого ответа —
                        # не критично: часть была положена через storage при create,
                        # а часть обновится при первом визите.
                        pass

                sb.refresh()
                sb.wait_for_ready_state_complete()
                sleep(0.8)

            # Финальная проверка: открываем chatgpt.com
            sb.uc_open("https://chatgpt.com/")
            sb.wait_for_ready_state_complete()

            if sb.find_text('Welcome back'):
                sb.type('input[name="email"]', self.account.email_address)

                sb.click('button[type="submit"]')
                sb.wait_for_ready_state_complete()
                sb.type('input[type="password"]', self.account.password)
                sb.click('button[type="submit"]')
                sb.wait_for_ready_state_complete()
                print("✅ Профиль импортирован и открыт")
            else:
                print("✅ Профиль импортирован и открыт. Если куки ещё действительны — вы уже залогинены.")

    def run(self):
        self.create_profile()
        self.start_and_restore()
        print(f"Новый профиль создан: {self.new_profile_id}")


class AccountGPTRestart:
    def __init__(self, account: AccountGPT, token: str):
        self.account = account
        self.TOKEN = token

    def login_profile(self):
        self.gl_profile = GoLogin({"token": self.TOKEN, "profile_id": self.account.id})
        _ = try_link_proxy(
            self.TOKEN,
            self.account.id,
            country_code="US",
            is_dc=True,
            is_mobile=False,
        )

    def start_and_restore(self):
        dbg = self.gl_profile.start()
        host, port = dbg.split(":")
        with SB(
                uc=True,
                locale="en",
                headed=True,
                test=True,
                chromium_arg=[
                    f"--remote-debugging-address={host}",
                    f"--remote-debugging-port={port}",
                ],
        ) as sb:
            # 1) Восстановим обе_origin: localStorage + cookies, затем refresh
            sb.uc_open("https://chatgpt.com/")
            sb.wait_for_ready_state_complete()
            sb.wait(10)
            if sb.is_text_visible('Log in'):
                sb.uc_open("https://chatgpt.com/auth/login")
                sb.wait_for_element('button[data-testid="login-button"]')
                sb.uc_click('button[data-testid="login-button"]')
            sb.wait(10)
            if sb.is_text_visible('Welcome back'):
                sb.type('input[name="email"]', self.account.email_address)

                sb.uc_click('button[type="submit"]')
                sb.wait_for_ready_state_complete()
                sb.type('input[type="password"]', self.account.password)
                sb.uc_click('button[type="submit"]')
                sb.wait_for_ready_state_complete()
                print("✅ Профиль импортирован и открыт")
            else:
                print("✅ Профиль импортирован и открыт. Если куки ещё действительны — вы уже залогинены.")

    def run(self):
        self.login_profile()
        self.start_and_restore()


class AccountGPTAdd:
    def __init__(self, token: str, email_address: str, password: str):
        self.TOKEN = token
        self.bundle = None
        self.API_URL = "https://api.gologin.com"
        self.name = names.get_full_name()

        self.email_address = email_address
        self.password = password

        self.profile = GoLogin({"token": self.TOKEN})
        prof = self.profile.createProfileRandomFingerprint({"os": "win", "name": f"autoreg-{int(time.time())}"})
        self.profile_id = prof["id"]

        # привяжем DC/US прокси (как у тебя в Postman)
        _ = try_link_proxy(self.TOKEN, self.profile_id, country_code="US", is_dc=True, is_mobile=False)

        # подготовим объект, привязанный к профилю
        self.profile = GoLogin({"token": self.TOKEN, "profile_id": self.profile_id})
        self.debugger_address = self.profile.start()

    def _open_sb(self):
        host, port = self.debugger_address.split(":")
        return SB(
            uc=True,
            locale="en",
            headed=True,
            test=True,
            chromium_arg=[
                f"--remote-debugging-address={host}",
                f"--remote-debugging-port={port}",
            ],
        )

    async def _do_login_flow(self, sb: SB):
        """
        Минимальный рабочий флоу: логика из твоих примеров.
        Если у тебя есть своя расширенная логика — можно подставить.
        """

        sb.uc_open("https://chatgpt.com/auth/login")
        sb.wait_for_element('button[data-testid="login-button"]')
        sb.uc_click('button[data-testid="login-button"]')

        # страница create account
        sb.type('input[name="email"]', self.email_address)
        sb.uc_click('button[type="submit"]')

        sb.wait_for_element('input[name="current-password"]')
        sb.type('input[name="current-password"]', self.password)
        sb.uc_click('button[type="submit"]')

        if sb.is_element_present('input[name="code"]'):
            code = input('Введите код')
            sb.type('input[name="code"]', code)
            sb.uc_click('button[type="submit"]')

        # Небольшая пауза на редирект в основное приложение
        sb.wait_for_ready_state_complete()
        sleep(1.5)

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
            sleep(0.5)

            # cookies текущего origin
            raw = sb.driver.get_cookies()
            norm = [sanitize_cookie_for_bundle(c) for c in raw]
            bundle_cookies[origin] = norm

            # localStorage
            ls = get_local_storage_map(sb)
            bundle_local[origin] = ls

        # Профиль/фингерпринт из GoLogin
        prof_json = self.profile.getProfile(self.profile_id)

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
            "profile_payload": profile_payload,  # fingerprint/navigator/etc.
        }
        self.bundle = bundle

    async def run(self):

        with self._open_sb() as sb:
            await self._do_login_flow(sb)
            self._collect_portable_state(sb)
            self.profile.stop()

        return self

    async def save_bundle(self, account):
        # Сохраняем переносимый бандл на диск
        out_name = account.cookies_path
        with open(out_name, "w", encoding="utf-8") as f:
            json.dump(self.bundle, f, ensure_ascii=False, indent=2)
        print(f"✅ Сохранён переносимый бандл: {out_name}")
        print(f"   Профиль-источник: {self.profile_id}")


