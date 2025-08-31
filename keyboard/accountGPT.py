# keyboard/accountGPT.py

from typing import List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from callbacks import *
from db.models import AccountGPT

ACCOUNTS_PER_PAGE = 5

def gpt_menu_keyboard(accounts: List[AccountGPT], page: int, total_pages: int):
    buttons = [
        [InlineKeyboardButton(text='➕ Создать аккаунт', callback_data=AccountGPTCallback(action='create').pack())]
    ]

    # Список аккаунтов
    for account in accounts:
        buttons.append([
            InlineKeyboardButton(text=f'👤 {account.name}', callback_data=AccountGPTCallback(action='account', params=account.id).pack())
        ])

    # Кнопки пагинации
    if total_pages > 1:
        paginator_buttons = []
        if page > 1:
            paginator_buttons.append(
                InlineKeyboardButton(text='⬅️ Назад', callback_data=NavigationCallback(menu='gpt_page', params=page - 1).pack())
            )
        if page < total_pages:
            paginator_buttons.append(
                InlineKeyboardButton(text='Вперед ➡️', callback_data=NavigationCallback(menu='gpt_page', params=page + 1).pack())
            )
        buttons.append(paginator_buttons)

    buttons.append([InlineKeyboardButton(text='⬅️ Главное меню', callback_data=NavigationCallback(menu='main').pack())])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def choice_create_gpt_account_keyboard():
    buttons = [
        [InlineKeyboardButton(text='⚙️ Автоматическое создание', callback_data=AccountGPTCallback(action='auto_create').pack())],
        [InlineKeyboardButton(text='✍️ Ввести вручную', callback_data=AccountGPTCallback(action='manual_create').pack())],
        [InlineKeyboardButton(text='⬅️ Назад', callback_data=NavigationCallback(menu='chatGPT').pack())]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def gpt_account_keyboard(account: AccountGPT):
    buttons = [
        [InlineKeyboardButton(text='🚀 Запустить', callback_data=AccountGPTCallback(action='launch', params=account.id).pack())],
        [
            InlineKeyboardButton(text='✏️ Переименовать', callback_data=AccountGPTCallback(action='rename', params=account.id).pack()),
            InlineKeyboardButton(text='🗑 Удалить', callback_data=AccountGPTCallback(action='delete', params=account.id).pack())
        ],
        [InlineKeyboardButton(text='⬅️ К списку', callback_data=NavigationCallback(menu='chatGPT').pack())]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def confirm_delete_keyboard(account_id: str):
    buttons = [
        [
            InlineKeyboardButton(text='✅ Да, удалить', callback_data=AccountGPTCallback(action='confirm_delete', params=account_id).pack()),
            InlineKeyboardButton(text='❌ Отмена', callback_data=AccountGPTCallback(action='account', params=account_id).pack())
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def cancel_fsm_keyboard(menu: str = 'chatGPT'):
    """Клавиатура для отмены состояния FSM."""
    buttons = [
        [InlineKeyboardButton(text='⬅️ Отмена', callback_data=NavigationCallback(menu=menu).pack())]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)