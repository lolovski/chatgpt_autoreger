# service/gologin_rotator.py

import logging
from typing import Callable, Awaitable, Any, Tuple  # <--- Добавляем Tuple

from db.models import AccountGoLogin
from service.GoLoginAPIClient import GoLoginAPIError
from service.exceptions import NoValidGoLoginAccountsError

logger = logging.getLogger(__name__)


# ИЗМЕНЕНО: Тип возвращаемого значения
async def execute_with_gologin_rotation(
        operation: Callable[..., Awaitable[Any]],
        **kwargs: Any
) -> Tuple[Any, AccountGoLogin]:  # <--- Возвращаем кортеж (результат, использованный_аккаунт)
    """
    Выполняет операцию, используя валидные GoLogin аккаунты.
    Возвращает результат операции и объект AccountGoLogin, который был использован.
    """
    while True:
        gologin_account = await AccountGoLogin.get_first_valid()
        if not gologin_account:
            raise NoValidGoLoginAccountsError()

        logger.info(f"Ротатор: Выполнение операции с использованием GoLogin аккаунта ID: {gologin_account.id}")

        try:
            result = await operation(token=gologin_account.api_token, **kwargs)
            # ИЗМЕНЕНО: Возвращаем результат И сам объект аккаунта
            return result, gologin_account

        except GoLoginAPIError as e:
            if e.status_code == 403 and "free API requests limit" in e.text:
                logger.warning(
                    f"Ротатор: GoLogin аккаунт {gologin_account.id} исчерпал лимит. Помечаем как невалидный.")
                await gologin_account.mark_as_invalid()
                continue
            else:
                raise e

        except Exception as e:
            raise e