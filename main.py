import asyncio
import locale
import logging
import sys


from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from handlers import main_router
from core import settings
from middleware import *

locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')
bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

dp = Dispatcher()
dp.update.middleware.register(UserMiddleware())




async def main():
    dp.include_router(main_router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
