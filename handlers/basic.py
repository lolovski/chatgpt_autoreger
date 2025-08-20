import os

from aiogram import Router, Bot
from aiogram.types import Message
from dotenv import load_dotenv

from core import settings

basic_router = Router(name='basic')
load_dotenv()

telegram_id = settings.telegram_id


@basic_router.startup()
async def on_startup(bot: Bot):
    from core import set_commands
    await set_commands(bot)
    await bot.send_message(telegram_id, text=f'Бот запустился в работу!')


@basic_router.shutdown()
async def on_shutdown(bot: Bot):
    await bot.send_message(telegram_id, text=f'Бот отключился')