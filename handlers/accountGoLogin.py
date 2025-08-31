import math

from aiogram import Router, Bot, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.deep_linking import create_start_link

from FSM import *
from callbacks import *
from db.models import *
from keyboard import *
from phrases import *
from service import create_account_go_login

accountGoLogin_router = Router(name='accountGoLogin')


@accountGoLogin_router.callback_query(NavigationCallback.filter(F.menu.in_(['GoLogin', 'gologin_page'])))
async def go_login_menu_handler(callback: CallbackQuery, state: FSMContext, callback_data: NavigationCallback):
    await state.clear()
    page = int(callback_data.params) if callback_data.menu == 'gologin_page' else 1

    total_accounts = await AccountGoLogin.get_count()
    if total_accounts == 0:
        return await callback.message.edit_text(
            text=go_login_menu_text,
            reply_markup=go_login_menu_keyboard(accounts=[], page=1, total_pages=1)
        )

    total_pages = math.ceil(total_accounts / ACCOUNTS_PER_PAGE_GOLOGIN)
    offset = (page - 1) * ACCOUNTS_PER_PAGE_GOLOGIN
    accounts = await AccountGoLogin.get_multi(limit=ACCOUNTS_PER_PAGE_GOLOGIN, offset=offset)

    await callback.message.edit_text(
        text=f"{go_login_menu_text}\n\n{paginator_gologin_text(page, total_pages)}",
        reply_markup=go_login_menu_keyboard(accounts=accounts, page=page, total_pages=total_pages)
    )


@accountGoLogin_router.callback_query(AccountGoLoginCallback.filter(F.action == 'account'))
async def account_go_login_handler(callback: CallbackQuery, state: FSMContext, callback_data: AccountGoLoginCallback):
    db_account = await AccountGoLogin.get(id=int(callback_data.params))
    if not db_account:
        await callback.answer("Аккаунт не найден.", show_alert=True)
        await go_login_menu_handler(callback, state, NavigationCallback(menu='GoLogin', params='1'))
        return

    await callback.message.edit_text(
        text=go_login_account_text(account=db_account),
        reply_markup=go_login_account_keyboard(account=db_account)
    )


# --- Удаление ---
@accountGoLogin_router.callback_query(AccountGoLoginCallback.filter(F.action == 'delete'))
async def delete_go_login_handler(callback: CallbackQuery, callback_data: AccountGoLoginCallback):
    account_id = int(callback_data.params)
    await callback.message.edit_text(
        text=confirm_delete_gologin_text(account_id),
        reply_markup=confirm_delete_gologin_keyboard(account_id=account_id)
    )


@accountGoLogin_router.callback_query(AccountGoLoginCallback.filter(F.action == 'confirm_delete'))
async def confirm_delete_go_login_handler(callback: CallbackQuery, state: FSMContext, callback_data: AccountGoLoginCallback):
    db_account = await AccountGoLogin.get(id=int(callback_data.params))
    if db_account:
        await db_account.delete()

    await callback.answer(gologin_deleted_text, show_alert=True)
    await go_login_menu_handler(callback, state, NavigationCallback(menu='GoLogin', params='1'))


@accountGoLogin_router.callback_query(AccountGoLoginCallback.filter(F.action == 'create'))
async def create_go_login_handler(callback: CallbackQuery, bot: Bot, state: FSMContext):
    await callback.message.edit_text(text=create_go_login_text, reply_markup=create_go_login_keyboard())


@accountGoLogin_router.callback_query(AccountGoLoginCallback.filter(F.action == 'manual_create'))
async def manual_create_go_login_handler(callback: CallbackQuery, bot: Bot, state: FSMContext):
    await callback.message.edit_text(text=token_create_go_login_text, reply_markup=token_create_go_login_keyboard())
    await state.set_state(AccountGoLoginForm.token)


@accountGoLogin_router.message(AccountGoLoginForm.token)
async def token_create_go_login_handler(message: Message, bot: Bot, state: FSMContext,):
    api_token = message.text
    db_account = await AccountGoLogin(api_token=api_token, email_address='user@email.com').create()
    await message.answer(
        text=create_go_login_success_text + "\n\n" + go_login_account_text(account=db_account),
        reply_markup=go_login_account_keyboard(account=db_account)
    )


@accountGoLogin_router.callback_query(AccountGoLoginCallback.filter(F.action == 'auto_create'))
async def auto_create_go_login_handler(callback: CallbackQuery, bot: Bot, state: FSMContext):
    await callback.message.edit_text(text=wait_create_go_login_text)
    email_address, token = await create_account_go_login()
    db_account = await AccountGoLogin(api_token=token, email_address=email_address).create()
    await callback.message.edit_text(
        text=create_go_login_success_text + "\n\n" + go_login_account_text(account=db_account),
        reply_markup=go_login_account_keyboard(account=db_account)
    )
