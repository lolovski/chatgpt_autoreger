from aiogram.fsm.state import StatesGroup, State


class AccountGPTForm(StatesGroup):
    account_data = State()
    wait_for_2fa_code = State()
