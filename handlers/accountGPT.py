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
from service.chatgpt_login import login_chatgpt_account

accountGPT_router = Router(name='accountGPT')


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
async def manual_create_gpt_account_email_handler(callback: CallbackQuery, callback_data: AccountGPTCallback, bot: Bot, state: FSMContext):
    go_login_id = int(callback_data.params)
    account_go_login = await AccountGoLogin.get(id=go_login_id)
    data = await state.get_data()
    try:
        email_address, password, name = data.get('account_data').split(":")
        account_id = await login_chatgpt_account(
            token=account_go_login.api_token,
            email_address=email_address,
            password=password,
        )

        db_account = await AccountGPT(
            email_address=email_address,
            password=password,
            name=name,
            accountGoLogin_id=account_go_login.id,
            id=account_id
        ).create()
        await state.clear()
        await callback.message.edit_text(text=create_gpt_account_success_text+gpt_account_text(db_account), reply_markup=gpt_account_keyboard(account=db_account))
    except Exception as e:
    
        await callback.message.edit_text(text=create_gpt_account_error_text,
                                         reply_markup=main_menu_keyboard())


@accountGPT_router.callback_query(AccountGPTCallback.filter(F.action == 'account'))
async def gpt_account_handler(callback: CallbackQuery, callback_data: AccountGPTCallback, bot: Bot):
    db_account = await AccountGPT.get(id=callback_data.params)
    await callback.message.edit_text(text=gpt_account_text(db_account), reply_markup=gpt_account_keyboard(account=db_account))


@accountGPT_router.callback_query(AccountGPTCallback.filter(F.action == 'auto_create'))
async def auto_create_gpt_account_handler(callback: CallbackQuery, callback_data: AccountGPTCallback, bot: Bot, state: FSMContext):
    go_login_accounts = await AccountGoLogin.get_multi()
    await callback.message.edit_text(text=choose_go_login_account_text,
                         reply_markup=choice_go_login_account_keyboard(accounts=go_login_accounts, action='auto_gologin'))


@accountGPT_router.callback_query(AccountGPTCallback.filter(F.action == 'auto_gologin'))
async def auto_gologin_gpt_account_handler(callback: CallbackQuery, callback_data: AccountGPTCallback, bot: Bot, state: FSMContext):
    await callback.message.edit_text(wait_manual_create_gpt_account_text)
    go_login_id = int(callback_data.params)
    account_go_login = await AccountGoLogin.get(id=go_login_id)
    try:
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


@accountGPT_router.callback_query(AccountGPTCallback.filter(F.action == 'launch'))
async def launch_account_gpt_handler(callback: CallbackQuery, callback_data: AccountGPTCallback, bot: Bot, state: FSMContext):
    await callback.message.edit_text(text=wait_manual_create_gpt_account_text)
    db_account = await AccountGPT.get(id=callback_data.params)
    account_go_login = await AccountGoLogin.get(id=db_account.accountGoLogin_id)
    if account_go_login is None:
        token = (await AccountGoLogin.get_first_valid()).api_token
        await restart_chatgpt_account(
                token=token,
                account=db_account,
                valid=False
            )
        return await callback.message.edit_text(launch_account_gpt_text + gpt_account_text(account=db_account),
                                         reply_markup=gpt_account_keyboard(account=db_account))
    if not account_go_login.valid:
        token = (await AccountGoLogin.get_first_valid()).api_token
        await restart_chatgpt_account(
            token=token,
            account=db_account,
            valid=False
        )
        return await callback.message.edit_text(launch_account_gpt_text + gpt_account_text(account=db_account),
                                         reply_markup=gpt_account_keyboard(account=db_account))

    await restart_chatgpt_account(
        token=account_go_login.api_token,
        account=db_account,
        valid=account_go_login.valid
    )
    await callback.message.edit_text(launch_account_gpt_text+gpt_account_text(account=db_account), reply_markup=gpt_account_keyboard(account=db_account))


