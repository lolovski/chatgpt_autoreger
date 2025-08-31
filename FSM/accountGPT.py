# FSM/accountGPT.py

from aiogram.fsm.state import StatesGroup, State


class AccountGPTForm(StatesGroup):
    # Ручное создание
    account_data = State()
    wait_for_2fa_code = State()

    # Автоматическое создание
    auto_create_name = State()

    # Редактирование
    rename_account = State()