from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from urllib.parse import quote_plus
import os

DATABASE_URL = os.getenv("DATABASE_URL", "")

# Правильно обрабатываем @ в пароле
if DATABASE_URL and "postgresql" in DATABASE_URL:
    try:
        prefix = "postgresql+psycopg2://"
        if not DATABASE_URL.startswith(prefix):
            DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", prefix)
            DATABASE_URL = DATABASE_URL.replace("postgresql://", prefix)

        rest = DATABASE_URL[len(prefix):]
        at_positions = [i for i, c in enumerate(rest) if c == '@']

        if len(at_positions) > 1:
            last_at = at_positions[-1]
            credentials = rest[:last_at]
            host_part = rest[last_at+1:]
            colon_pos = credentials.index(':')
            user = credentials[:colon_pos]
            password = credentials[colon_pos+1:]
            encoded_password = quote_plus(password)
            DATABASE_URL = f"{prefix}{user}:{encoded_password}@{host_part}"
    except Exception as e:
        print(f"URL parsing warning: {e}")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

def get_db():
    with SessionLocal() as session:
        try:
            yield session
        finally:
            session.close()
