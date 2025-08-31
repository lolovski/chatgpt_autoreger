# db/models/accountGPT.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, String, ForeignKey, select, Integer, Boolean, update, delete, func
from sqlalchemy.orm import relationship

from db import Base, session

class AccountGPT(Base):
    __tablename__ = 'accountGPT'
    id = Column(String, primary_key=True)
    name = Column(String)
    email_address = Column(String, unique=True)
    password = Column(String)
    cookies_path = Column(String)
    auto_create = Column(Boolean, default=True)
    accountGoLogin_id = Column(
        ForeignKey('accountGoLogin.id', ondelete="SET NULL"),
        nullable=True
    )
    accountGoLogin = relationship('AccountGoLogin', back_populates="accountsGPT", lazy='selectin', foreign_keys=[accountGoLogin_id])

    def __init__(self, name: str, email_address: str, password: str, id: str, accountGoLogin_id: int = None, auto_create: bool = True):
        self.id = id
        self.name = name
        self.email_address = email_address
        self.password = password
        self.cookies_path = f'cookies/{id}.json'
        self.accountGoLogin_id = accountGoLogin_id
        self.auto_create = auto_create

    async def create(self):
        db_session = await session()
        db_session.add(self)
        await db_session.commit()
        await db_session.close()
        return self

    # НОВЫЙ МЕТОД
    async def update(self, **kwargs):
        db_session = await session()
        await db_session.execute(update(AccountGPT).where(AccountGPT.id == self.id).values(**kwargs))
        await db_session.commit()
        await db_session.close()

    # НОВЫЙ МЕТОД
    async def delete(self):
        db_session = await session()
        await db_session.execute(delete(AccountGPT).where(AccountGPT.id == self.id))
        await db_session.commit()
        await db_session.close()
        return self

    @classmethod
    async def get_count(cls):
        db_session = await session()
        result = await db_session.execute(select(func.count(cls.id)))
        await db_session.close()
        return result.scalar_one()

    @classmethod
    async def get_multi(cls, limit: int = 5, offset: int = 0):
        db_session = await session()
        result = await db_session.execute(select(cls).limit(limit).offset(offset).order_by(cls.name))
        await db_session.close()
        return result.scalars().all()

    @classmethod
    async def get(cls, id: str):
        db_session = await session()
        result = await db_session.execute(select(cls).where(cls.id == id))
        await db_session.close()
        return result.scalars().first()