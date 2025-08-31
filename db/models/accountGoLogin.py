from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from pytz import timezone
from db import Base, session
from sqlalchemy import Column, String, ForeignKey, select, Integer, DateTime, Boolean
from sqlalchemy.orm import relationship, Mapped, mapped_column, Session
moscow_tz = timezone('Europe/Moscow')


class AccountGoLogin(Base):
    __tablename__ = 'accountGoLogin'
    id = Column(Integer, primary_key=True, autoincrement=True)
    email_address = Column(String, unique=True)
    api_token = Column(String)
    registration_date = Column(DateTime, default=datetime.now(moscow_tz))
    valid = Column(Boolean, default=True)
    accountsGPT = relationship("AccountGPT", back_populates="accountGoLogin", )
    auto_create = Column(Boolean, default=True)

    def __init__(self, email_address: str, api_token: str):
        self.email_address = email_address
        self.api_token = api_token

    async def create(self):
        db_session = await session()
        db_session.add(self)
        await db_session.commit()
        await db_session.close()
        return self

    @classmethod
    async def get_multi(cls, limit: int = 10, offset: int = 0):
        db_session = await session()
        result = await db_session.execute(select(cls).limit(limit).offset(offset).order_by(cls.registration_date.asc()))
        await db_session.close()
        return result.scalars().all()

    @classmethod
    async def get(cls, id: int):
        db_session = await session()
        result = await db_session.execute(select(cls).where(cls.id == id))
        await db_session.close()
        return result.scalars().first()

    @classmethod
    async def get_first_valid(cls):
        db_session = await session()
        result = await db_session.execute(select(cls).where(cls.valid == 1).order_by(cls.registration_date.asc()))
        await db_session.close()
        return result.scalars().first()

    @classmethod
    async def update(cls, id: int, **kwargs):
        db_session = await session()
        result = await db_session.execute(select(cls).where(cls.id == id))
        account = result.scalars().first()
        for key, value in kwargs.items():
            setattr(account, key, value)
        await db_session.commit()
        await db_session.close()
        return account




