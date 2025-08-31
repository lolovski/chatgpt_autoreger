from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from callbacks import *


def main_menu_keyboard():
    buttons = [
        [
            # ChatGPT теперь сверху
            InlineKeyboardButton(text='🤖 ChatGPT', callback_data=NavigationCallback(menu='chatGPT').pack())
        ],
        [
            # GoLogin теперь снизу
            InlineKeyboardButton(text='⚙️ GoLogin', callback_data=NavigationCallback(menu='GoLogin').pack())
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)