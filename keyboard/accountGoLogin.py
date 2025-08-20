from datetime import datetime
from typing import List

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from callbacks import *
from db.models import AccountGoLogin


def go_login_menu_keyboard(accounts: List[AccountGoLogin]):
    buttons = [
        [
            InlineKeyboardButton(text='Создать', callback_data=AccountGoLoginCallback(action='create').pack())
        ]
    ]
    for account in accounts:
        buttons.append(
            [
                InlineKeyboardButton(text=f'{account.id} - {account.registration_date.strftime('%d.%m.%y')}', callback_data=AccountGoLoginCallback(action='account', params=str(account.id)).pack())
            ]
        )
    buttons.append(
        [
            InlineKeyboardButton(text='Назад', callback_data=NavigationCallback(menu='main').pack())
        ]
    )
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


def go_login_account_keyboard(account):
    buttons = [

        [
            InlineKeyboardButton(text='Назад', callback_data=NavigationCallback(menu='GoLogin').pack())
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

