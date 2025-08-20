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


@accountGoLogin_router.callback_query(NavigationCallback.filter(F.menu == 'GoLogin'))
async def go_login_menu_handler(callback: CallbackQuery, bot: Bot, state: FSMContext):
    await state.clear()
    accounts = await AccountGoLogin.get_multi()
    await callback.message.edit_text(text=go_login_menu_text, reply_markup=go_login_menu_keyboard(accounts=accounts))


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
    db_account = await AccountGoLogin(
        api_token=api_token,
        email_address='user@email.com'
    ).create()
    await message.answer(text=create_go_login_success_text+go_login_account_text(account=db_account), reply_markup=go_login_account_keyboard(account=db_account))


@accountGoLogin_router.callback_query(AccountGoLoginCallback.filter(F.action == 'account'))
async def account_go_login_handler(callback: CallbackQuery, bot: Bot, state: FSMContext, callback_data: AccountGoLoginCallback):
    id = int(callback_data.params)
    db_account = await AccountGoLogin.get(id=id)
    await callback.message.edit_text(text=go_login_account_text(account=db_account),
                         reply_markup=go_login_account_keyboard(account=db_account))


@accountGoLogin_router.callback_query(AccountGoLoginCallback.filter(F.action == 'auto_create'))
async def auto_create_go_login_handler(callback: CallbackQuery, bot: Bot, state: FSMContext):
    await callback.message.edit_text(text=wait_create_go_login_text)
    email_address, token = await create_account_go_login()
    db_account = await AccountGoLogin(
        api_token=token,
        email_address=email_address
    ).create()
    await callback.message.edit_text(text=create_go_login_success_text+go_login_account_text(account=db_account), reply_markup=go_login_account_keyboard(account=db_account))


