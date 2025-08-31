# handlers/accountGPT.py

import math
from aiogram import Router, Bot, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from FSM import *
from callbacks import *
from db.models import *
from keyboard.accountGPT import ACCOUNTS_PER_PAGE  # Импортируем константу
from keyboard import *
from phrases import *
from service import *
from service.exceptions import TwoFactorRequiredError

accountGPT_router = Router(name='accountGPT')



# --- ГЛАВНОЕ МЕНЮ И ПАГИНАТОР ---
@accountGPT_router.callback_query(NavigationCallback.filter(F.menu.in_(['chatGPT', 'gpt_page'])))
async def gpt_menu_handler(callback: CallbackQuery, state: FSMContext, callback_data: NavigationCallback):
    await state.clear()
    page = int(callback_data.params) if callback_data.menu == 'gpt_page' else 1

    total_accounts = await AccountGPT.get_count()
    if total_accounts == 0:
        # Если аккаунтов нет, показываем "пустое" меню
        return await callback.message.edit_text(
            text=gpt_menu_text,
            reply_markup=gpt_menu_keyboard(accounts=[], page=1, total_pages=1)
        )

    total_pages = math.ceil(total_accounts / ACCOUNTS_PER_PAGE)
    offset = (page - 1) * ACCOUNTS_PER_PAGE
    accounts = await AccountGPT.get_multi(limit=ACCOUNTS_PER_PAGE, offset=offset)

    await callback.message.edit_text(
        text=f"{gpt_menu_text}\n\n{paginator_text(page, total_pages)}",
        reply_markup=gpt_menu_keyboard(accounts=accounts, page=page, total_pages=total_pages)
    )


# --- ПРОСМОТР АККАУНТА ---
@accountGPT_router.callback_query(AccountGPTCallback.filter(F.action == 'account'))
async def gpt_account_handler(callback: CallbackQuery, callback_data: AccountGPTCallback, state: FSMContext):
    await state.clear()
    db_account = await AccountGPT.get(id=callback_data.params)
    if not db_account:
        await callback.answer("Аккаунт не найден, возможно, он был удален.", show_alert=True)
        # Обновляем меню на случай, если аккаунт удалили
        await gpt_menu_handler(callback, state, NavigationCallback(menu='chatGPT', params='1'))
        return

    await callback.message.edit_text(
        text=gpt_account_text(db_account),
        reply_markup=gpt_account_keyboard(account=db_account)
    )


# --- БЛОК СОЗДАНИЯ АККАУНТОВ ---
@accountGPT_router.callback_query(AccountGPTCallback.filter(F.action == 'create'))
async def create_gpt_account_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        text=choice_create_gpt_account_text,
        reply_markup=choice_create_gpt_account_keyboard()
    )


# --- Автоматическое создание ---
@accountGPT_router.callback_query(AccountGPTCallback.filter(F.action == 'auto_create'))
async def auto_create_gpt_account_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AccountGPTForm.auto_create_name)
    await callback.message.edit_text(
        text=auto_create_name_prompt_text,
        reply_markup=cancel_fsm_keyboard()
    )


@accountGPT_router.message(AccountGPTForm.auto_create_name)
async def auto_create_name_handler(message: Message, state: FSMContext):
    account_name = message.text
    await state.clear()
    await message.answer(wait_manual_create_gpt_account_text)

    try:
        # ИЗМЕНЕНО: Используем ротатор
        data, used_gologin = await execute_with_gologin_rotation(
            operation=register_chatgpt,
            message_interface=message
        )
        db_account = await AccountGPT(
            **data,
            name=account_name,
            accountGoLogin_id=used_gologin.id,  # Привязываем использованный аккаунт
            auto_create=True
        ).create()

        await message.answer(
            create_gpt_account_success_text + "\n\n" + gpt_account_text(db_account),
            reply_markup=gpt_account_keyboard(db_account)
        )
    except NoValidGoLoginAccountsError:
        await message.answer(no_valid_gologin_accounts_error, reply_markup=main_menu_keyboard())
    except Exception as e:
        await message.answer(
            create_gpt_account_error_text + f"\n\nОшибка: {e}",
            reply_markup=main_menu_keyboard()
        )


# --- Ручное создание ---
@accountGPT_router.callback_query(AccountGPTCallback.filter(F.action == 'manual_create'))
async def manual_create_gpt_account_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AccountGPTForm.account_data)
    await callback.message.edit_text(
        text=gpt_manual_prompt_text,
        reply_markup=cancel_fsm_keyboard()
    )


@accountGPT_router.message(AccountGPTForm.account_data)
async def manual_create_gpt_account_data_handler(message: Message, state: FSMContext):
    try:
        email, password, name = message.text.split(":")
    except ValueError:
        return await message.answer(text=chatgpt_error_format_text)

    await state.clear()
    await message.answer(wait_manual_create_gpt_account_text)

    # Автоматический выбор GoLogin профиля
    try:
        new_profile_id, used_gologin = await execute_with_gologin_rotation(
            operation=login_chatgpt_account,
            message_interface=message,
            email_address=email, password=password, name=name
        )

        db_account = await AccountGPT(
            email_address=email, password=password, name=name,
            accountGoLogin_id=used_gologin.id, id=new_profile_id,
            auto_create=False
        ).create()

        await message.answer(
            create_gpt_account_success_text + "\n\n" + gpt_account_text(db_account),
            reply_markup=gpt_account_keyboard(db_account)
        )
    except VerificationCodeRequiredError as e: # <-- Ловим новое исключение
        if e.is_manual_input_needed:
            await state.update_data(
                action_type='manual_login',
                email_address=email, password=password, name=name
            )
            await state.set_state(AccountGPTForm.wait_for_2fa_code)
            await message.answer(code_input_text) # <-- Используем фразу
    except NoValidGoLoginAccountsError:
        await message.answer(no_valid_gologin_accounts_error, reply_markup=main_menu_keyboard())
    except Exception as e:
        await message.answer(
            create_gpt_account_error_text + f"\n\nОшибка: {e}",
            reply_markup=main_menu_keyboard()
        )


# --- БЛОК УПРАВЛЕНИЯ АККАУНТОМ ---

# --- Запуск ---
@accountGPT_router.callback_query(AccountGPTCallback.filter(F.action == 'launch'))
async def launch_account_gpt_handler(callback: CallbackQuery, state: FSMContext, callback_data: AccountGPTCallback):
    await callback.message.edit_text(text=launch_account_gpt_text)
    db_account = await AccountGPT.get(id=callback_data.params)

    try:
        # Просто вызываем наш "умный" сервис
        final_account, used_gologin = await execute_with_gologin_rotation(
            operation=restart_and_heal_chatgpt_account,  # Используем простой сервис
            message_interface=callback,
            account=db_account  # Передаем доп. аргумент
        )
        # Показываем пользователю финальный, актуальный результат
        await callback.message.edit_text(
            f"<b>✅ Профиль запущен и готов к работе!</b>\n\n{gpt_account_text(final_account)}",
            reply_markup=gpt_account_keyboard(account=final_account)
        )

    except NoValidGoLoginAccountsError:
        await callback.message.edit_text(
            no_valid_gologin_accounts_error,
            reply_markup=gpt_account_keyboard(account=db_account)
        )
    except VerificationCodeRequiredError as e:  # <-- Ловим новое исключение
        if e.is_manual_input_needed:
            await state.update_data(action_type='restart', account_id=db_account.id)
            await state.set_state(AccountGPTForm.wait_for_2fa_code)
            await callback.message.answer(code_input_text)  # <-- Используем фразу
        else:
            await callback.message.edit_text(
                error_launch_account_gpt_text + "\n\n<b>Ошибка:</b> <code>Не удалось автоматически получить код подтверждения.</code>",
                reply_markup=gpt_account_keyboard(account=db_account)
            )
    except Exception as e:
        await callback.message.edit_text(
            error_launch_account_gpt_text + f"\n\n<b>Ошибка:</b> <code>{e}</code>",
            reply_markup=gpt_account_keyboard(account=db_account)
        )


# --- Переименование ---
@accountGPT_router.callback_query(AccountGPTCallback.filter(F.action == 'rename'))
async def rename_gpt_account_handler(callback: CallbackQuery, state: FSMContext, callback_data: AccountGPTCallback):
    await state.set_state(AccountGPTForm.rename_account)
    await state.update_data(account_id=callback_data.params)
    await callback.message.edit_text(
        text=rename_prompt_text,
        reply_markup=cancel_fsm_keyboard()
    )


@accountGPT_router.message(AccountGPTForm.rename_account)
async def process_rename_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    account_id = data.get('account_id')
    new_name = message.text

    db_account = await AccountGPT.get(id=account_id)
    await db_account.update(name=new_name)
    await state.clear()

    # Обновляем информацию в сообщении
    db_account.name = new_name  # Обновляем локальный объект для отображения
    await message.answer(rename_success_text)
    await message.answer(
        text=gpt_account_text(db_account),
        reply_markup=gpt_account_keyboard(account=db_account)
    )


# --- Удаление ---
@accountGPT_router.callback_query(AccountGPTCallback.filter(F.action == 'delete'))
async def delete_gpt_account_handler(callback: CallbackQuery, callback_data: AccountGPTCallback):
    db_account = await AccountGPT.get(id=callback_data.params)
    await callback.message.edit_text(
        text=confirm_delete_text(db_account.name),
        reply_markup=confirm_delete_keyboard(account_id=db_account.id)
    )


@accountGPT_router.callback_query(AccountGPTCallback.filter(F.action == 'confirm_delete'))
async def confirm_delete_gpt_account_handler(callback: CallbackQuery, state: FSMContext,
                                             callback_data: AccountGPTCallback):
    db_account = await AccountGPT.get(id=callback_data.params)
    await db_account.delete()
    await callback.answer(account_deleted_text, show_alert=True)
    # Возвращаем пользователя в меню, которое само обновит список
    await gpt_menu_handler(callback, state, NavigationCallback(menu='chatGPT', params='1'))


@accountGPT_router.message(AccountGPTForm.wait_for_2fa_code)
async def process_2fa_code_handler(message: Message, bot: Bot, state: FSMContext):
    code = message.text
    data = await state.get_data()
    action_type = data.get('action_type')
    await message.answer("Принял код, продолжаю работу...")

    try:
        if action_type == 'manual_login':

            email_address = data.get('email_address')
            password = data.get('password')
            name = data.get('name')
            try:
                new_profile_id, used_gologin = await execute_with_gologin_rotation(
                    operation=login_chatgpt_account,
                    message_interface=message,
                    email_address=email_address, password=password, name=name, code=code
                )
                db_account = await AccountGPT(
                    email_address=email_address, password=password, name=name,
                    accountGoLogin_id=used_gologin.id, id=new_profile_id
                ).create()

                await message.answer(
                    create_gpt_account_success_text + "\n\n" + gpt_account_text(db_account),
                    reply_markup=gpt_account_keyboard(db_account)
                )
            except NoValidGoLoginAccountsError:
                await message.answer(no_valid_gologin_accounts_error, reply_markup=main_menu_keyboard())
            # except Exception as e:
            #     await message.answer(
            #         create_gpt_account_error_text + f"\n\nОшибка: {e}",
            #         reply_markup=main_menu_keyboard()
            #     )

        elif action_type == 'restart':
            db_account = await AccountGPT.get(id=data.get('account_id'))
            try:
                # Просто вызываем наш "умный" сервис
                final_account, used_gologin = await execute_with_gologin_rotation(
                    operation=restart_and_heal_chatgpt_account,  # Используем простой сервис
                    message_interface=message,
                    account=db_account,
                    code=code# Передаем доп. аргумент
                )
                # Показываем пользователю финальный, актуальный результат
                await message.answer(
                    f"<b>✅ Профиль запущен и готов к работе!</b>\n\n{gpt_account_text(final_account)}",
                    reply_markup=gpt_account_keyboard(account=final_account)
                )

            except NoValidGoLoginAccountsError:
                await message.answer(
                    no_valid_gologin_accounts_error,
                    reply_markup=gpt_account_keyboard(account=db_account)
                )
            except Exception as e:
                await message.answer(
                    error_launch_account_gpt_text + f"\n\n<b>Ошибка:</b> <code>{e}</code>",
                    reply_markup=gpt_account_keyboard(account=db_account)
                )

            await state.clear()
            updated_account = await AccountGPT.get(id=db_account.id)
            await message.answer(launch_account_gpt_text + gpt_account_text(account=updated_account),
                                 reply_markup=gpt_account_keyboard(account=updated_account))
        else:
            raise RuntimeError("Неизвестный тип действия в состоянии 2FA")

    except Exception as e:
        await state.clear()
        await message.answer(text=create_gpt_account_error_text + f"\n\nОшибка: {e}",
                             reply_markup=main_menu_keyboard())