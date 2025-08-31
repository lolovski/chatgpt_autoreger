from datetime import datetime
from datetime import datetime
from sqlalchemy import Column, String, select, Integer, DateTime, Boolean, update, delete, func # <--- Добавляем func, delete, update
from sqlalchemy.orm import relationship
from pytz import timezone

from db import Base, session

moscow_tz = timezone('Europe/Moscow')

class AccountGoLogin(Base):
    __tablename__ = 'accountGoLogin'
    id = Column(Integer, primary_key=True, autoincrement=True)
    email_address = Column(String, unique=True)
    api_token = Column(String)
    registration_date = Column(DateTime, default=datetime.now(moscow_tz))
    valid = Column(Boolean, default=True)
    accountsGPT = relationship("AccountGPT", back_populates="accountGoLogin")

    def __init__(self, email_address: str, api_token: str):
        self.email_address = email_address
        self.api_token = api_token

    async def create(self):
        db_session = await session()
        db_session.add(self)
        await db_session.commit()
        await db_session.close()
        return self

    async def delete(self):
        db_session = await session()
        await db_session.execute(delete(AccountGoLogin).where(AccountGoLogin.id == self.id))
        await db_session.commit()
        await db_session.close()

    async def mark_as_invalid(self):
        db_session = await session()
        await db_session.execute(update(AccountGoLogin).where(AccountGoLogin.id == self.id).values(valid=False))
        await db_session.commit()
        await db_session.close()

    @classmethod
    async def get_count(cls):
        db_session = await session()
        result = await db_session.execute(select(func.count(cls.id)))
        await db_session.close()
        return result.scalar_one()

    @classmethod
    async def get_multi(cls, limit: int = 5, offset: int = 0):
        db_session = await session()
        result = await db_session.execute(select(cls).order_by(cls.registration_date.desc()).limit(limit).offset(offset))
        await db_session.close()
        return result.scalars().all()

    @classmethod
    async def get(cls, id: int):
        db_session = await session()
        result = await db_session.execute(select(cls).where(cls.id == id))
        await db_session.close()
        return result.scalars().first()

    @classmethod
    async def get_by_token(cls, token: str):
        db_session = await session()
        result = await db_session.execute(select(cls).where(cls.api_token == token))
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




