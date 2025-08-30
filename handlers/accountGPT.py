# handlers/accountGPT.py

from aiogram import Router, Bot, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from FSM import *
from callbacks import *
from db.models import *
from keyboard import *
from phrases import *
from service import *


accountGPT_router = Router(name='accountGPT')


# ... (хендлеры gpt_menu_handler, create_gpt_account_handler, manual_create_gpt_account_handler, manual_create_gpt_account_data_handler остаются без изменений)
@accountGPT_router.callback_query(NavigationCallback.filter(F.menu == 'chatGPT'))
async def gpt_menu_handler(callback: CallbackQuery, bot: Bot, state: FSMContext):
    await state.clear()
    accounts = await AccountGPT.get_multi()
    await callback.message.edit_text(text=gpt_menu_text, reply_markup=gpt_menu_keyboard(accounts=accounts))


@accountGPT_router.callback_query(AccountGPTCallback.filter(F.action == 'create'))
async def create_gpt_account_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(text=choice_create_gpt_account_text,
                                     reply_markup=choice_create_gpt_account_keyboard())


@accountGPT_router.callback_query(AccountGPTCallback.filter(F.action == 'manual_create'))
async def manual_create_gpt_account_handler(callback: CallbackQuery, bot: Bot, state: FSMContext):
    await state.set_state(AccountGPTForm.account_data)
    await callback.message.edit_text(text=gpt_manual_prompt_text, reply_markup=manual_create_gpt_account_keyboard())


@accountGPT_router.message(AccountGPTForm.account_data)
async def manual_create_gpt_account_data_handler(message: Message, bot: Bot, state: FSMContext):
    try:
        email, password, name = message.text.split(":")
        await state.update_data(account_data=f'{email}:{password}:{name}')
    except ValueError as e:
        return await message.answer(text=chatgpt_error_format_text)
    go_login_accounts = await AccountGoLogin.get_multi()
    await message.answer(text=choose_go_login_account_text,
                         reply_markup=choice_go_login_account_keyboard(accounts=go_login_accounts,
                                                                       action='manual_gologin'))

@accountGPT_router.callback_query(AccountGPTCallback.filter(F.action == 'manual_gologin'))
async def manual_create_gpt_account_email_handler(callback: CallbackQuery, callback_data: AccountGPTCallback, bot: Bot,
                                                  state: FSMContext):
    go_login_id = int(callback_data.params)
    account_go_login = await AccountGoLogin.get(id=go_login_id)
    data = await state.get_data()
    email_address, password, name = data.get('account_data').split(":")

    await callback.message.edit_text("Попытка входа в аккаунт...")

    try:
        # ИЗМЕНЕНО: login_chatgpt_account теперь возвращает ID нового профиля
        new_profile_id = await login_chatgpt_account(
            token=account_go_login.api_token,
            email_address=email_address,
            password=password,
        )

        db_account = await AccountGPT(
            email_address=email_address,
            password=password,
            name=name,
            accountGoLogin_id=account_go_login.id,
            id=new_profile_id # Используем полученный ID
        ).create()
        await state.clear()
        await callback.message.edit_text(text=create_gpt_account_success_text + gpt_account_text(db_account),
                                         reply_markup=gpt_account_keyboard(account=db_account))

    except TwoFactorRequiredError:
        await state.update_data(
            action_type='manual_login',
            go_login_id=go_login_id,
            email_address=email_address,
            password=password,
            name=name
        )
        await state.set_state(AccountGPTForm.wait_for_2fa_code)
        await callback.message.edit_text("⚠️ Требуется код 2FA. Отправьте его следующим сообщением.")

    except Exception as e:
        await state.clear()
        await callback.message.edit_text(text=create_gpt_account_error_text + f"\n\nОшибка: {e}",
                                         reply_markup=main_menu_keyboard())


@accountGPT_router.callback_query(AccountGPTCallback.filter(F.action == 'account'))
async def gpt_account_handler(callback: CallbackQuery, callback_data: AccountGPTCallback, bot: Bot):
    db_account = await AccountGPT.get(id=callback_data.params)
    await callback.message.edit_text(text=gpt_account_text(db_account),
                                     reply_markup=gpt_account_keyboard(account=db_account))


@accountGPT_router.callback_query(AccountGPTCallback.filter(F.action == 'auto_create'))
async def auto_create_gpt_account_handler(callback: CallbackQuery, callback_data: AccountGPTCallback, bot: Bot,
                                          state: FSMContext):
    go_login_accounts = await AccountGoLogin.get_multi()
    await callback.message.edit_text(text=choose_go_login_account_text,
                                     reply_markup=choice_go_login_account_keyboard(accounts=go_login_accounts,
                                                                                   action='auto_gologin'))


@accountGPT_router.callback_query(AccountGPTCallback.filter(F.action == 'auto_gologin'))
async def auto_gologin_gpt_account_handler(callback: CallbackQuery, callback_data: AccountGPTCallback, bot: Bot,
                                           state: FSMContext):
    await callback.message.edit_text(wait_manual_create_gpt_account_text)
    go_login_id = int(callback_data.params)
    account_go_login = await AccountGoLogin.get(id=go_login_id)
    try:
        # register_chatgpt теперь тоже полностью асинхронный
        data = await register_chatgpt(account_go_login.api_token)
        db_account = await AccountGPT(
            **data,
            accountGoLogin_id=go_login_id
        ).create()
        await state.clear()
        await callback.message.edit_text(text=create_gpt_account_success_text + gpt_account_text(db_account),
                                         reply_markup=gpt_account_keyboard(db_account))

    except Exception as e:
        print(e)
        await callback.message.edit_text(text=create_gpt_account_error_text,
                                         reply_markup=main_menu_keyboard())


# УПРОЩЕНО
@accountGPT_router.callback_query(AccountGPTCallback.filter(F.action == 'launch'))
async def launch_account_gpt_handler(callback: CallbackQuery, callback_data: AccountGPTCallback, bot: Bot,
                                     state: FSMContext):
    await callback.message.edit_text(text=wait_manual_create_gpt_account_text)
    db_account = await AccountGPT.get(id=callback_data.params)

    # ИЗМЕНЕНО: Логика выбора токена упрощена. Мы всегда пытаемся использовать привязанный.
    # Если он невалиден, GoLoginAPI вернет ошибку.
    # Для гибкости можно оставить поиск валидного, как было. Выберем более простой вариант.
    if not db_account.accountGoLogin or not db_account.accountGoLogin.valid:
        await callback.message.edit_text("❌ Привязанный GoLogin аккаунт не найден или невалиден.",
                                         reply_markup=gpt_account_keyboard(account=db_account))
        return

    token = db_account.accountGoLogin.api_token

    try:
        # Убрали флаг valid, т.к. сервис сам разберется, нужна ли повторная авторизация
        await restart_chatgpt_account(
            token=token,
            account=db_account
        )
        await callback.message.edit_text(launch_account_gpt_text + gpt_account_text(account=db_account),
                                         reply_markup=gpt_account_keyboard(account=db_account))

    except TwoFactorRequiredError:
        await state.update_data(
            action_type='restart',
            account_id=db_account.id,
            token=token
        )
        await state.set_state(AccountGPTForm.wait_for_2fa_code)
        await callback.message.edit_text("⚠️ Требуется код 2FA. Отправьте его следующим сообщением.")

    except Exception as e:
        await callback.message.edit_text(error_launch_account_gpt_text + f"\n\nОшибка: {e}",
                                         reply_markup=gpt_account_keyboard(account=db_account))


# НОВЫЙ ХЕНДЛЕР: Обрабатывает ввод 2FA кода от пользователя (логика почти не изменилась)
@accountGPT_router.message(AccountGPTForm.wait_for_2fa_code)
async def process_2fa_code_handler(message: Message, bot: Bot, state: FSMContext):
    code = message.text
    data = await state.get_data()
    action_type = data.get('action_type')
    await message.answer("Принял код, продолжаю работу...")

    try:
        if action_type == 'manual_login':
            go_login_id = data.get('go_login_id')
            account_go_login = await AccountGoLogin.get(id=go_login_id)
            email_address = data.get('email_address')
            password = data.get('password')
            name = data.get('name')

            # Вызываем сервис еще раз, но уже с кодом
            new_profile_id = await login_chatgpt_account(
                token=account_go_login.api_token,
                email_address=email_address,
                password=password,
                code=code
            )

            db_account = await AccountGPT(
                email_address=email_address, password=password, name=name,
                accountGoLogin_id=account_go_login.id, id=new_profile_id
            ).create()

            await state.clear()
            await message.answer(text=create_gpt_account_success_text + gpt_account_text(db_account),
                                 reply_markup=gpt_account_keyboard(account=db_account))

        elif action_type == 'restart':
            db_account = await AccountGPT.get(id=data.get('account_id'))
            token = data.get('token')

            # Вызываем сервис еще раз, но уже с кодом
            await restart_chatgpt_account(
                token=token,
                account=db_account,
                code=code
            )
            await state.clear()
            await message.answer(launch_account_gpt_text + gpt_account_text(account=db_account),
                                 reply_markup=gpt_account_keyboard(account=db_account))
        else:
            raise RuntimeError("Неизвестный тип действия в состоянии 2FA")

    except Exception as e:
        await state.clear()
        await message.answer(text=create_gpt_account_error_text + f"\n\nОшибка: {e}",
                             reply_markup=main_menu_keyboard())