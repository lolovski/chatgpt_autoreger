from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from callbacks import *


def main_menu_keyboard():
    buttons = [
        [
            InlineKeyboardButton(text='Профили GoLogin', callback_data=NavigationCallback(menu='GoLogin').pack())
        ],
        [
            InlineKeyboardButton(text='Профили ChatGPT', callback_data=NavigationCallback(menu='chatGPT').pack())
        ],

    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)