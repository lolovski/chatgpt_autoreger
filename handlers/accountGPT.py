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
from service import *

accountGPT_router = Router(name='accountGPT')


@accountGPT_router.callback_query(NavigationCallback.filter(F.menu == 'chatGPT'))
async def gpt_menu_handler(callback: CallbackQuery, bot: Bot, state: FSMContext):
    await state.clear()
    accounts = await AccountGPT.get_multi()
    await callback.message.edit_text(text=gpt_menu_text, reply_markup=gpt_menu_keyboard(accounts=accounts))


@accountGPT_router.callback_query(AccountGPTCallback.filter(F.action == 'create'))
async def create_gpt_account_handler(callback: CallbackQuery, bot: Bot, state: FSMContext):
    go_login_accounts = await AccountGoLogin.get_multi()
    await callback.message.edit_text(text=choose_go_login_account_text, reply_markup=choice_go_login_account_keyboard(accounts=go_login_accounts, action='choice_create'))


@accountGPT_router.callback_query(AccountGPTCallback.filter(F.action == 'choice_create'))
async def choice_create_gpt_account_handler(callback: CallbackQuery, bot: Bot, state: FSMContext, callback_data: AccountGPTCallback):
    go_login_id = int(callback_data.params)
    await state.set_state(AccountGPTForm.go_login_id)
    await state.update_data(go_login_id=go_login_id)
    await callback.message.edit_text(text=choice_create_gpt_account_text, reply_markup=choice_create_gpt_account_keyboard())


@accountGPT_router.callback_query(AccountGPTCallback.filter(F.action == 'manual_create'))
async def manual_create_gpt_account_handler(callback: CallbackQuery, bot: Bot, state: FSMContext):
    await state.set_state(AccountGPTForm.name)
    await callback.message.edit_text(text=manual_create_gpt_account_text, reply_markup=manual_create_gpt_account_keyboard())


@accountGPT_router.message(AccountGPTForm.name)
async def manual_create_gpt_account_name_handler(message: Message, bot: Bot, state: FSMContext, text: str):
    await state.update_data(name=text)
    await state.set_state(AccountGPTForm.email_address)
    await message.answer(text=manual_create_gpt_account_email_text, reply_markup=manual_create_gpt_account_keyboard())


@accountGPT_router.message(AccountGPTForm.email_address)
async def manual_create_gpt_account_email_handler(message: Message, bot: Bot, state: FSMContext):
    await state.update_data(email_address=message.text)
    await state.set_state(AccountGPTForm.password)
    await message.answer(text=manual_create_gpt_account_password_text, reply_markup=manual_create_gpt_account_keyboard())


@accountGPT_router.message(AccountGPTForm.password)
async def manual_create_gpt_account_password_handler(message: Message, bot: Bot, state: FSMContext, text: str):
    await state.update_data(password=message.text)
    data = await state.get_data()
    await message.answer(wait_manual_create_gpt_account_text)

    account_go_login = await AccountGoLogin.get(id=data.get('go_login_id'))
    try:
        app = AccountGPTAdd(email_address=data.get('email_address'), password=data.get('password'), token=account_go_login.api_token)
        await app.run()

        db_account = await AccountGPT(
            **data
        ).create()
        await app.save_bundle(account=db_account)
        await state.clear()

        await message.answer(text=create_gpt_account_success_text+gpt_account_text(db_account), reply_markup=gpt_account_keyboard())
    except Exception as e:
        await message.answer(text=create_gpt_account_error_text,
                                         reply_markup=main_menu_keyboard())


@accountGPT_router.callback_query(AccountGPTCallback.filter(F.action == 'account'))
async def gpt_account_handler(callback: CallbackQuery, callback_data: AccountGPTCallback, bot: Bot):
    db_account = await AccountGPT.get(id=callback_data.params)
    await callback.message.edit_text(text=gpt_account_text(db_account), reply_markup=gpt_account_keyboard(account=db_account))


@accountGPT_router.callback_query(AccountGPTCallback.filter(F.action == 'auto_create'))
async def auto_create_gpt_account_handler(callback: CallbackQuery, callback_data: AccountGPTCallback, bot: Bot, state: FSMContext):

    await callback.message.edit_text(wait_manual_create_gpt_account_text)
    go_login_id = (await state.get_data()).get('go_login_id')
    account_go_login = await AccountGoLogin.get(id=go_login_id)
    try:
        accountGPT_reg = AccountGPTReg(token=account_go_login.api_token)
        account_date = await accountGPT_reg.run()
        db_account = await AccountGPT(
            email_address=account_date.email_address,
            id=account_date.profile_id,
            password=account_date.email_client.password,
            name=account_date.name,
            accountGoLogin_id=go_login_id

        ).create()
        await state.clear()
        await callback.message.edit_text(text=create_gpt_account_success_text + gpt_account_text(db_account),
                                         reply_markup=gpt_account_keyboard(db_account))
        await accountGPT_reg.save_bundle(account=db_account)

    except Exception as e:
        await callback.message.edit_text(text=create_gpt_account_error_text,
                                         reply_markup=main_menu_keyboard())


@accountGPT_router.callback_query(AccountGPTCallback.filter(F.action == 'launch'))
async def launch_account_gpt_handler(callback: CallbackQuery, callback_data: AccountGPTCallback, bot: Bot, state: FSMContext):

    db_account = await AccountGPT.get(id=callback_data.params)
    account_go_login = await AccountGoLogin.get(id=db_account.accountGoLogin_id)
    if account_go_login is None:
        data = await state.get_data()
        account_go_login = await AccountGoLogin.get(id=data.get('go_login_id'))
        app = AccountGPTImport(token=account_go_login.api_token, account=db_account)
        return app.run()

    app = AccountGPTRestart(token=account_go_login.api_token, account=db_account)
    return app.run()

