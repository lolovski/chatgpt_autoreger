from aiogram.filters.callback_data import CallbackData


class AccountGoLoginCallback(CallbackData, prefix='accountGoLogin'):
    action: str
    params: str | int | None = None