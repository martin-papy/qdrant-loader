import os

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

DATABASE_URL = os.environ["QDRANT_LOADER_DATABASE_URL"]

engine = create_async_engine(DATABASE_URL, echo=False)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


async def get_rds_session():
    async with AsyncSessionLocal() as session:
        yield session
