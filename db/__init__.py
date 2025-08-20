from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncAttrs
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, DeclarativeBase, declared_attr, Mapped, mapped_column
from core.config import settings

engine = create_async_engine(settings.database_url, echo=False)
Session = sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


async def session():
    return Session()

Base = declarative_base()



