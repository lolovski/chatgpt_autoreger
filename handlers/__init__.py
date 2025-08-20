from aiogram import Router
from .accountGoLogin import *
from .basic import basic_router
from .diary import *
from .accountGPT import *


main_router = Router(name='main')
main_router.include_routers(
    basic_router,
    diary_router,
    accountGoLogin_router,
    accountGPT_router
)