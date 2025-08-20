from sqlalchemy.ext.asyncio import AsyncSession

from db import Base, session
from sqlalchemy import Column, String, ForeignKey, select, Integer
from sqlalchemy.orm import relationship, Mapped, mapped_column, Session


class AccountGPT(Base):
    __tablename__ = 'accountGPT'
    id = Column(String, primary_key=True)
    name = Column(String)
    email_address = Column(String, unique=True)
    password = Column(String)
    cookies_path = Column(String)
    accountGoLogin_id = Column(
        ForeignKey('accountGoLogin.id', ondelete="SET NULL"),
        nullable=True
    )
    accountGoLogin = relationship('AccountGoLogin', back_populates="accountsGPT", lazy='selectin', foreign_keys=[accountGoLogin_id])

    def __init__(self, name: str, email_address: str, password: str, id: str, accountGoLogin_id: int = None):
        self.id = id
        self.name = name
        self.email_address = email_address
        self.password = password
        self.cookies_path = f'cookies/{id}.json'
        self.accountGoLogin_id = accountGoLogin_id

    async def create(self):
        db_session = await session()
        db_session.add(self)
        await db_session.commit()
        await db_session.close()
        return self

    @classmethod
    async def get_last(cls):
        db_session = await session()
        result = await db_session.execute(select(cls))
        await db_session.close()
        return result.scalars().first()

    @classmethod
    async def get_multi(cls, limit: int = 10, offset: int = 0):
        db_session = await session()
        result = await db_session.execute(select(cls).limit(limit).offset(offset))
        await db_session.close()
        return result.scalars().all()

    @classmethod
    async def get(cls, id: str):
        db_session = await session()
        result = await db_session.execute(select(cls).where(cls.id == id))
        await db_session.close()
        return result.scalars().first()





