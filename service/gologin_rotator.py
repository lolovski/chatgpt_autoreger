# service/gologin_rotator.py

import logging
from typing import Callable, Awaitable, Any, Tuple  # <--- Добавляем Tuple

from db.models import AccountGoLogin
from service import create_account_go_login
from service.GoLoginAPIClient import GoLoginAPIError, GoLoginAPIClient
from service.exceptions import NoValidGoLoginAccountsError

logger = logging.getLogger(__name__)


# ИЗМЕНЕНО: Тип возвращаемого значения

async def get_valid_gologin_account(message_interface) -> AccountGoLogin:
    """
    Умный провайдер GoLogin аккаунтов.
    1. Ищет в цикле первый валидный аккаунт, проверяя его через API.
    2. Помечает нерабочие аккаунты как невалидные.
    3. Если валидных не осталось, создает новый.
    """
    while True:
        candidate = await AccountGoLogin.get_first_valid()

        if not candidate:
            # Валидных аккаунтов в базе не осталось, нужно создать новый.
            logger.warning("Валидные GoLogin аккаунты закончились. Запуск авто-создания.")

            # Информируем пользователя через предоставленный интерфейс
            reply_func = message_interface.answer if hasattr(message_interface,
                                                             'text') else message_interface.message.answer
            await reply_func("<b>⚠️ Свободные GoLogin аккаунты закончились. Создаю новый...</b>")

            try:
                email, token = await create_account_go_login()
                new_account = await AccountGoLogin(email_address=email, api_token=token).create()
                await reply_func(f"<b>✅ Новый GoLogin аккаунт <code>{email}</code> создан!</b>")
                return new_account
            except Exception as e:
                logger.error(f"Критическая ошибка при авто-создании GoLogin: {e}", exc_info=True)
                await reply_func("<b>❌ Не удалось автоматически создать GoLogin аккаунт.</b>")
                raise NoValidGoLoginAccountsError("Failed to auto-create a GoLogin account.")

        # Кандидат есть, проверяем его токен через API
        api_client = GoLoginAPIClient(api_token=candidate.api_token)
        is_token_ok = await api_client.test_token()
        await api_client.close()

        if is_token_ok:
            logger.info(f"Токен для GoLogin аккаунта {candidate.id} валиден. Используем его.")
            return candidate  # Нашли рабочий аккаунт, выходим из цикла
        else:
            # Токен не прошел проверку, помечаем аккаунт как невалидный
            logger.warning(f"Токен для GoLogin аккаунта {candidate.id} не прошел проверку. Помечаем как невалидный.")
            await candidate.mark_as_invalid()
            # Цикл while продолжится и на следующей итерации возьмет уже следующий валидный аккаунт
            continue


async def execute_with_gologin_rotation(
        operation: Callable[..., Awaitable[Any]],
        message_interface,  # Интерфейс для отправки сообщений (Message или CallbackQuery)
        **kwargs: Any
) -> Tuple[Any, AccountGoLogin]:
    """
    Выполняет операцию, гарантированно используя валидный GoLogin аккаунт.
    """
    # 1. Получаем гарантированно рабочий аккаунт
    gologin_account = await get_valid_gologin_account(message_interface)

    # 2. Выполняем операцию с его токеном
    try:
        result = await operation(token=gologin_account.api_token, **kwargs)
        return result, gologin_account
    except GoLoginAPIError as e:
        # Эта проверка нужна на случай, если лимит исчерпался ПРЯМО во время операции
        if e.status_code == 403:
            await AccountGoLogin.update(id=gologin_account.id, is_valid=False)
        raise  # Пробрасываем ошибку дальше в хэндлер