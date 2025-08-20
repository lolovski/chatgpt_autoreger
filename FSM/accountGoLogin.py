from aiogram.fsm.state import StatesGroup, State


class AccountGoLoginForm(StatesGroup):
    email_address = State()
    token = State()
