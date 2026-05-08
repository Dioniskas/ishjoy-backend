from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from urllib.parse import quote_plus
import os

DATABASE_URL = os.getenv("DATABASE_URL", "")

# Normalize to postgresql+psycopg:// — handles postgres:// (Render), postgresql://,
# postgresql+asyncpg://, postgresql+psycopg2://
if DATABASE_URL:
    try:
        prefix = "postgresql+psycopg://"
        for old in (
            "postgresql+asyncpg://",
            "postgresql+psycopg2://",
            "postgresql://",
            "postgres://",          # Render provides this bare form
        ):
            if DATABASE_URL.startswith(old):
                DATABASE_URL = prefix + DATABASE_URL[len(old):]
                break

        rest = DATABASE_URL[len(prefix):]
        at_positions = [i for i, c in enumerate(rest) if c == '@']

        if len(at_positions) > 1:
            last_at = at_positions[-1]
            credentials = rest[:last_at]
            host_part = rest[last_at + 1:]
            colon_pos = credentials.index(':')
            user = credentials[:colon_pos]
            password = credentials[colon_pos + 1:]
            encoded_password = quote_plus(password)
            DATABASE_URL = f"{prefix}{user}:{encoded_password}@{host_part}"
    except Exception as e:
        print(f"URL parsing warning: {e}")

# prepare_threshold=None disables prepared statements, required for Supabase
# Supavisor transaction-mode pooler (port 6543)
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"prepare_threshold": None},
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
