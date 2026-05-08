from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from urllib.parse import quote_plus, urlparse
import os
import socket

DATABASE_URL = os.getenv("DATABASE_URL", "")

# Normalize to postgresql+psycopg:// — handles all common URL schemes:
#   postgres://           (Render injects this form)
#   postgresql://         (Supabase dashboard "direct connection")
#   postgresql+asyncpg://
#   postgresql+psycopg2://
# Set DATABASE_URL in Render to the Supabase direct connection string:
#   postgresql://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres
if DATABASE_URL:
    try:
        prefix = "postgresql+psycopg://"
        for old in (
            "postgresql+asyncpg://",
            "postgresql+psycopg2://",
            "postgresql://",
            "postgres://",
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

# Force IPv4 for Render free tier (no IPv6 support).
# uvicorn[standard] uses uvloop whose libuv DNS resolver bypasses socket.getaddrinfo,
# so a monkey-patch has no effect. Instead we pre-resolve the hostname to IPv4
# synchronously at startup (before the event loop starts) and pass it as psycopg3's
# `hostaddr` parameter. When hostaddr is set psycopg3 skips its own DNS resolution
# entirely and dials that IP directly; `host` in the URL is still used for SSL SNI.
_connect_args: dict = {"prepare_threshold": None}
try:
    _host = urlparse(DATABASE_URL).hostname
    if _host:
        _ipv4 = socket.getaddrinfo(_host, None, socket.AF_INET)[0][4][0]
        _connect_args["hostaddr"] = _ipv4
        print(f"DB: resolved {_host} → {_ipv4}")
except Exception as _e:
    print(f"DB: IPv4 pre-resolve skipped ({_e}), hostaddr not set")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args=_connect_args,
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
