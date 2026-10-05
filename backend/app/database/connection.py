from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings


def database_url(value):
    try:
        url = make_url(value)
        if url.get_backend_name() not in ("postgres", "postgresql") or not url.host or not url.database:
            raise ValueError()
        url = url.set(drivername="postgresql+psycopg")
        # Preserve explicit SSL options; Neon connections always require TLS.
        if url.host.endswith(".neon.tech") and url.query.get("sslmode") not in ("require", "verify-ca", "verify-full"):
            url = url.update_query_dict({"sslmode": "require"})
        return url
    except Exception:
        raise RuntimeError("DATABASE_URL must be a valid PostgreSQL connection URL with host and database") from None


engine = create_engine(
    database_url(settings.DATABASE_URL), pool_pre_ping=True,
    pool_size=3, max_overflow=2, connect_args={"connect_timeout": 10},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
Base = declarative_base()


def get_db():
    with SessionLocal() as db:
        yield db
