import time
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
