from aiogram.fsm.state import StatesGroup, State


class AccountGPTForm(StatesGroup):
    account_data = State()
    verification_code = State()
    verification_attempts = State()
    profile_data = State()
