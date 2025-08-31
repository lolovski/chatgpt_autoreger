from datetime import datetime
from typing import List

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from callbacks import *
from db.models import AccountGoLogin


ACCOUNTS_PER_PAGE_GOLOGIN = 5

def go_login_menu_keyboard(accounts: List[AccountGoLogin], page: int, total_pages: int):
    buttons = [
        [InlineKeyboardButton(text='➕ Добавить аккаунт', callback_data=AccountGoLoginCallback(action='create').pack())]
    ]

    for account in accounts:
        status_emoji = '✅' if account.valid else '⚠️'
        buttons.append([
            InlineKeyboardButton(
                text=f"{status_emoji} ID: {account.id} ({account.email_address})",
                callback_data=AccountGoLoginCallback(action='account', params=account.id).pack()
            )
        ])

    if total_pages > 1:
        paginator_buttons = []
        if page > 1:
            paginator_buttons.append(
                InlineKeyboardButton(text='⬅️ Назад', callback_data=NavigationCallback(menu='gologin_page', params=page - 1).pack())
            )
        if page < total_pages:
            paginator_buttons.append(
                InlineKeyboardButton(text='Вперед ➡️', callback_data=NavigationCallback(menu='gologin_page', params=page + 1).pack())
            )
        buttons.append(paginator_buttons)

    buttons.append([InlineKeyboardButton(text='⬅️ Главное меню', callback_data=NavigationCallback(menu='main').pack())])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def go_login_account_keyboard(account: AccountGoLogin):
    buttons = [
        [InlineKeyboardButton(text='🗑 Удалить', callback_data=AccountGoLoginCallback(action='delete', params=account.id).pack())],
        [InlineKeyboardButton(text='⬅️ К списку', callback_data=NavigationCallback(menu='GoLogin').pack())]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_delete_gologin_keyboard(account_id: int):
    buttons = [
        [
            InlineKeyboardButton(text='✅ Да, удалить', callback_data=AccountGoLoginCallback(action='confirm_delete', params=account_id).pack()),
            InlineKeyboardButton(text='❌ Отмена', callback_data=AccountGoLoginCallback(action='account', params=account_id).pack())
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_go_login_keyboard():
    buttons = [
        [
            InlineKeyboardButton(text='Автоматическое создание', callback_data=AccountGoLoginCallback(action='auto_create').pack()),
        ],
        [
            InlineKeyboardButton(text='Ручное создание',
                                 callback_data=AccountGoLoginCallback(action='manual_create').pack())
        ],
        [
            InlineKeyboardButton(text='Назад', callback_data=NavigationCallback(menu='GoLogin').pack())
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def token_create_go_login_keyboard():
    buttons = [
        [
            InlineKeyboardButton(text='Назад', callback_data=AccountGoLoginCallback(action='create').pack())
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)