from collections.abc import Generator
from contextlib import contextmanager
import os
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DEFAULT_SQLITE_URL = f"sqlite:///{(DATA_DIR / 'team_balancer.db').as_posix()}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL)


class Base(DeclarativeBase):
    pass


engine_kwargs: dict[str, object] = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def run_migrations() -> None:
    inspector = inspect(engine)
    if "users" in inspector.get_table_names():
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "is_active" not in user_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1"))
                connection.execute(text("UPDATE users SET is_active = 1 WHERE is_active IS NULL"))
        if "is_approved" not in user_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE users ADD COLUMN is_approved BOOLEAN DEFAULT 1"))
                connection.execute(text("UPDATE users SET is_approved = 1 WHERE is_approved IS NULL"))

    if "players" not in inspector.get_table_names():
        return

    player_columns = {column["name"] for column in inspector.get_columns("players")}
    if "image_url" not in player_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE players ADD COLUMN image_url VARCHAR(500)"))
    if "name_fa" not in player_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE players ADD COLUMN name_fa VARCHAR(100)"))
            connection.execute(text("UPDATE players SET name_fa = display_name WHERE name_fa IS NULL"))
    if "name_en" not in player_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE players ADD COLUMN name_en VARCHAR(100)"))
            connection.execute(text("UPDATE players SET name_en = display_name WHERE name_en IS NULL"))

    if "comparisons" in inspector.get_table_names():
        comparison_columns = {column["name"] for column in inspector.get_columns("comparisons")}
        if "comparison_value" not in comparison_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE comparisons ADD COLUMN comparison_value INTEGER DEFAULT 1"))
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE comparisons "
                    "SET comparison_value = CASE "
                    "WHEN winner_player_id = player_a_id THEN 1 "
                    "WHEN winner_player_id = player_b_id THEN -1 "
                    "ELSE comparison_value END"
                )
            )
