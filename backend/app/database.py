from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args={
        "connect_timeout": 10,  # 10 second timeout for connection attempts
        "options": "-c statement_timeout=30000"  # 30 second query timeout
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency that provides a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_columns():
    """Safely adds newly introduced columns to existing database tables if missing."""
    from sqlalchemy import text
    with engine.connect() as conn:
        cols = [
            ("diag_count", "INTEGER DEFAULT 1"),
            ("proc_count", "INTEGER DEFAULT 1"),
            ("line_count", "INTEGER DEFAULT 1"),
            ("state", "VARCHAR(10)"),
            ("raw_extracted_features", "VARCHAR(2000)"),
        ]
        for name, col_type in cols:
            try:
                conn.execute(text(f"ALTER TABLE claims ADD COLUMN {name} {col_type}"))
                conn.commit()
            except Exception:
                pass

try:
    ensure_columns()
except Exception as e:
    print(f"[DB MIGRATE] Column migration notice: {e}")
