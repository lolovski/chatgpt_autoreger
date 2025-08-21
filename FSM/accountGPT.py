from aiogram.fsm.state import StatesGroup, State


class AccountGPTForm(StatesGroup):
    data = State()
