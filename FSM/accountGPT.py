from aiogram.fsm.state import StatesGroup, State


class AccountGPTForm(StatesGroup):
    email_address = State()
    password = State()
    name = State()
    go_login_id = State()
