from aiogram.filters.callback_data import CallbackData


class AccountGPTCallback(CallbackData, prefix='accountGPT'):
    action: str
    params: str | int | None = None