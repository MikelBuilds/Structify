from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,declarative_base

from app.config import settings

if not settings.DATABASE_URL:
    raise RuntimeError("DATABASE_URL must be configured")

#create postgres engine

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True
    )

#database session

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

#base class for models
Base = declarative_base()

#dependency for fastAPI
def get_db():
    db= SessionLocal()

    try:
        yield db

    finally:
        db.close()