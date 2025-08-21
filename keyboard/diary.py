from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from callbacks import *


def main_menu_keyboard():
    buttons = [
        [
            InlineKeyboardButton(text='⚙️ GoLogin', callback_data=NavigationCallback(menu='GoLogin').pack())
        ],
        [
            InlineKeyboardButton(text='🤖 ChatGPT', callback_data=NavigationCallback(menu='chatGPT').pack())
        ],

    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)