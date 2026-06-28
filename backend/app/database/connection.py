from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,declarative_base

from app.config import settings

#create postgres engine

engine = create_engine(
    settings.DATABASE_URL,
    echo=True,
    future=True
    )

#database session

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

#base class for models
Base = declarative_base()

#dependency for fastAPI
def get_db():
    db= SessionLocal()

    try:
        yield db

    finally:
        db.close()