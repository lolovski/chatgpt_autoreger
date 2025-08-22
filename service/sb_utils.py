import time

from gologin.http_client import make_request
from seleniumbase import SB
from selenium.common.exceptions import TimeoutException, NoSuchElementException


def wait_for_element_safe(sb: SB, selector: str, timeout: int = 20):
    try:
        sb.wait_for_element(selector, timeout=timeout)
        return True
    except TimeoutException:
        return False

def wait_for_text_safe(sb: SB, text: str, timeout: int = 20):
    try:
        sb.wait_for_text(text, timeout=timeout)
        return True
    except TimeoutException:
        return False


def safe_click(sb: SB, selector: str, timeout: int = 10):
    if sb.is_element_visible(selector, timeout=timeout):
        sb.click(selector)
        return True
    return False


def get_local_storage_map(sb: SB):
    script = """
    var out = {};
    for (var i = 0; i < localStorage.length; i++) {
        var k = localStorage.key(i);
        out[k] = localStorage.getItem(k);
    }
    return out;
    """
    return sb.execute_script(script)


def restore_local_storage(sb: SB, data: dict):
    sb.execute_script("localStorage.clear();")
    for k, v in (data or {}).items():
        sb.execute_script("localStorage.setItem(arguments[0], arguments[1]);", k, v)


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