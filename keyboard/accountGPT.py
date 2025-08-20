from datetime import datetime
from typing import List

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from callbacks import *
from db.models import AccountGPT, AccountGoLogin


def gpt_menu_keyboard(accounts: List[AccountGPT]):
    buttons = [
        [
            InlineKeyboardButton(text='Создать', callback_data=AccountGPTCallback(action='create').pack())
        ]
    ]
    for account in accounts:
        buttons.append(
            [
                InlineKeyboardButton(text=account.name, callback_data=AccountGPTCallback(action='account', params=str(account.id)).pack())
            ]
        )
    buttons.append(
        [
            InlineKeyboardButton(text='Назад', callback_data=NavigationCallback(menu='main').pack())
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def choice_create_gpt_account_keyboard():
    buttons = [
        [
            InlineKeyboardButton(text='Автоматическое создание', callback_data=AccountGPTCallback(action='auto_create').pack())
        ],
        [
            InlineKeyboardButton(text='Ручное создание', callback_data=AccountGPTCallback(action='manual_create').pack())
        ],
        [
            InlineKeyboardButton(text='Назад', callback_data=NavigationCallback(menu='chatGPT').pack())
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def manual_create_gpt_account_keyboard():
    buttons = [
        [
            InlineKeyboardButton(text='Отмена', callback_data=AccountGPTCallback(action='create').pack())
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def gpt_account_keyboard(account: AccountGPT):
    buttons = [
        [
            InlineKeyboardButton(text='Запустить', callback_data=AccountGPTCallback(action='launch', params=account.id).pack())
        ],
        [
            InlineKeyboardButton(text='Назад', callback_data=NavigationCallback(menu='chatGPT').pack())
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def choice_go_login_account_keyboard(accounts: List[AccountGoLogin], action):
    buttons = [
        [
            InlineKeyboardButton(text='Назад', callback_data=NavigationCallback(menu='chatGPT').pack())
        ]
    ]
    for account in accounts:
        buttons.append(
            [
                InlineKeyboardButton(text=f'{account.id} - {account.registration_date.strftime('%d.%m.%y')}', callback_data=AccountGPTCallback(action=action, params=str(account.id)).pack())
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)