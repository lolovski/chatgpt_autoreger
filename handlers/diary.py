from aiogram import Router, Bot, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.deep_linking import create_start_link

from FSM import *
from callbacks import *
from db.models import *
from keyboard import *
from phrases import *

diary_router = Router(name='diary')


@diary_router.message(CommandStart())
async def main_menu_handler(message: Message, bot: Bot, state: FSMContext):
    await state.clear()
    await message.answer(text=main_menu_text, reply_markup=main_menu_keyboard())


@diary_router.callback_query(NavigationCallback.filter(F.menu == 'main'))
async def main_menu_handler(callback: CallbackQuery, bot: Bot, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(text=main_menu_text, reply_markup=main_menu_keyboard())

