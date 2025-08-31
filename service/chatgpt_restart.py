# service/chatgpt_restart.py

import logging
import asyncio # Добавляем импорт
import os

from db.models import AccountGPT, AccountGoLogin
from service import GoLoginAPIError, GoLoginAPIClient
from service.gologin_profile import GoLoginProfile
from service.exceptions import TwoFactorRequiredError, NoValidGoLoginAccountsError

logger = logging.getLogger(__name__)


async def _perform_login(page, account: AccountGPT, code: str = None):
    """Вспомогательная функция для выполнения логина на странице."""
    logger.info(f"Сессия невалидна для {account.email_address}. Выполняется повторный вход.")
    await page.goto("https://chatgpt.com/auth/login", {'waitUntil': 'networkidle0'})

    # ИСПРАВЛЕНО: Все клики, ведущие к навигации, обернуты в asyncio.gather
    await asyncio.gather(
        page.waitForNavigation({'waitUntil': 'networkidle0'}),
        page.click('button[data-testid="login-button"]')
    )

    await page.waitForSelector('input[name="email"]', {'timeout': 20000})
    await page.type('input[name="email"]', account.email_address)
    await asyncio.gather(
        page.waitForNavigation({'waitUntil': 'networkidle0'}),
        page.click('button[type="submit"]')
    )

    await page.waitForSelector('input[name="current-password"]', {'timeout': 20000})
    await page.type('input[name="current-password"]', account.password)
    await asyncio.gather(
        page.waitForNavigation({'waitUntil': 'networkidle0'}),
        page.click('button[type="submit"]')
    )

    try:
        await page.waitForSelector('input[name="code"]', {'timeout': 5000})
        is_2fa_visible = True
    except Exception:
        is_2fa_visible = False

    if is_2fa_visible:
        if code:
            await page.type('input[name="code"]', code)
            await asyncio.gather(
                page.waitForNavigation({'waitUntil': 'networkidle0'}),
                page.click('button[type="submit"]')
            )
        else:
            raise TwoFactorRequiredError("Требуется код двухфакторной аутентификации")

    await page.waitForSelector('#prompt-textarea', {'timeout': 30000})


async def restart_and_heal_chatgpt_account(account: AccountGPT, token: str, code: str = None) -> AccountGPT:
    """
    "Лечит" и перезапускает аккаунт ChatGPT.
    1. Пытается запустить существующий профиль с привязанным токеном.
    2. Если профиль или токен невалидны, создает НОВЫЙ профиль с рабочим токеном,
       переносит куки и обновляет запись в БД.
    Возвращает финальный, актуальный объект AccountGPT.
    """

    # --- Попытка №1: "Счастливый путь" с существующими данными ---
    linked_gologin = account.accountGoLogin
    if linked_gologin and linked_gologin.valid:
        logger.info(f"Пробуем запустить профиль {account.id} с привязанным токеном {linked_gologin.id}")
        try:
            # Пытаемся запустить текущий профиль
            await _run_browser_session(token=linked_gologin.api_token, account=account, code=code)
            logger.info("Успешный запуск с существующими данными.")
            return account  # Если все хорошо, возвращаем исходный аккаунт
        except GoLoginAPIError as e:
            # Если профиль "битый" (422) или не найден (404), или токен исчерпан (403) - переходим к "лечению"
            if e.status_code in [403, 404, 422]:
                logger.warning(
                    f"Не удалось запустить существующий профиль ({e.status_code}). Причина: {e.text}. Начинаем процедуру восстановления.")
                if e.status_code == 403:  # Если проблема в токене, помечаем его
                    await AccountGoLogin.update(linked_gologin.id, valid=False)
            else:
                raise  # Другие ошибки API пробрасываем
        except Exception:
            raise

    # --- Попытка №2: "Лечение" - создание нового профиля и перенос сессии ---
    logger.info(f"Начинаем поиск рабочего GoLogin аккаунта для создания нового профиля.")

    if not token:
        raise NoValidGoLoginAccountsError()
    working_gologin = await AccountGoLogin.get_by_token(token)
    api_client = GoLoginAPIClient(api_token=token)
    try:
        # 1. Создаем абсолютно новый профиль GoLogin
        logger.info(f"Создаем новый профиль GoLogin с помощью токена {working_gologin.id}")
        new_profile_data = await api_client.create_quick_profile(name=f"healed_{account.name}")
        new_profile_id = new_profile_data.get("id")

        # 2. Создаем временный объект AccountGPT для запуска браузерной сессии
        temp_new_account = AccountGPT(
            id=new_profile_id, name=account.name,
            email_address=account.email_address, password=account.password
        )

        # 3. Запускаем сессию в НОВОМ профиле и переносим куки из СТАРОГО
        await _run_browser_session(
            token=working_gologin.api_token,
            account=temp_new_account,
            cookies_to_load_path=account.cookies_path, # <--- Ключевой момент!
            code=code
        )

        # 4. Если все прошло успешно, обновляем базу данных
        logger.info("Перенос сессии прошел успешно. Обновляем базу данных.")
        account = await account.delete()
        # Создаем финальную новую запись
        final_new_account = await AccountGPT(
            id=new_profile_id,
            name=account.name,
            email_address=account.email_address,
            password=account.password,
            accountGoLogin_id=working_gologin.id
        ).create()

        # Удаляем старый файл cookie, если он есть
        if os.path.exists(account.cookies_path):
            os.remove(account.cookies_path)

        await api_client.close()
        return final_new_account  # Возвращаем новый, "вылеченный" аккаунт

    except GoLoginAPIError as e:
        if e.status_code == 403:  # Если и этот токен исчерпан
            logger.warning(f"Токен {working_gologin.id} тоже исчерпан. Ищем следующий.")
            await AccountGoLogin.update(working_gologin.id, valid=False)
            await api_client.close()

        else:
            await api_client.close()
            raise
    except Exception:
        await api_client.close()
        raise


async def _run_browser_session(token: str, account: AccountGPT, cookies_to_load_path: str = None, code: str = None):
    """Вспомогательная функция, которая запускает браузер и управляет сессией."""
    profile = GoLoginProfile(api_token=token, profile_id=account.id)
    async with profile as page:

        # Если указан путь для загрузки - грузим куки (сценарий "лечения")
        # Иначе - грузим куки самого аккаунта (сценарий "счастливого пути")
        path_to_load = cookies_to_load_path or account.cookies_path
        logger.info(f"Загрузка cookie из {path_to_load} для профиля {account.id}")

        try:
            await profile.load_cookies(path_to_load)
        except FileNotFoundError:
            logger.warning(f"Файл cookie {path_to_load} не найден. Пробуем войти без него.")

        await page.goto("https://chatgpt.com/", {'waitUntil': 'networkidle0'})

        is_login_needed = "auth" in page.url or await page.querySelector('button[data-testid="login-button"]')
        if is_login_needed:
            await _perform_login(page, account, code)

        logger.info(f"Сессия в профиле {account.id} активна. Сохраняем cookie.")
        await profile.save_cookies(account.cookies_path, domains=['chatgpt.com', 'openai.com'])