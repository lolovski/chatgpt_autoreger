import contextlib
import logging
import os
import re
from typing import Callable, Awaitable, Any, Dict

from aiogram import BaseMiddleware
from aiogram import Bot
from aiogram.types import Message
from aiogram.types import Update
from core import settings
from db import session
from phrases import *


class UserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:

        current_event = event.message or event.callback_query
        telegram_id = current_event.from_user.id
        if int(telegram_id) != int(settings.telegram_id):
            return await current_event.answer(user_error)

        first_name = re.sub(r'[^a-zA-Z0-9а-яА-ЯёЁ\s]', '', current_event.from_user.first_name) or None
        data['first_name'] = first_name

        data['text'] = (re.sub(r'[^a-zA-Z0-9а-яА-ЯёЁ\s]', '',
                               current_event.text) or None if current_event.text is not None else None) if event.message else None

        await handler(event, data)
