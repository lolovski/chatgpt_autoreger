from aiogram.fsm.state import StatesGroup, State


class AccountGPTForm(StatesGroup):
    account_data = State()
