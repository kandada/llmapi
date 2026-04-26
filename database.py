from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import contextlib
from typing import Generator

from models.base import Base

_engine = None
_SessionLocal = None


def get_database_url() -> str:
    from config import config
    if config.SQL_DSN:
        return config.SQL_DSN
    return f"sqlite:///{config.SQLite_Path}?timeout={config.SQLITE_BUSY_TIMEOUT}"


def init_db():
    global _engine, _SessionLocal

    from config import config
    database_url = get_database_url()

    if database_url.startswith("sqlite"):
        _engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=config.DEBUG,
        )
    else:
        _engine = create_engine(
            database_url,
            echo=config.DEBUG,
            pool_size=config.SQL_MAX_OPEN_CONNS,
            max_overflow=config.SQL_MAX_OPEN_CONNS - config.SQL_MAX_IDLE_CONNS,
            pool_recycle=config.SQL_MAX_LIFETIME,
        )

    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)

    from models import user, channel, token, redemption, log, option, ability, package, order
    Base.metadata.create_all(bind=_engine)

    create_root_user_if_need()


def create_root_user_if_need():
    from models.user import User
    from utils.hash import hash_password
    from utils.random import generate_uuid
    from utils.time import get_timestamp
    from config import config

    session = _SessionLocal()
    try:
        root = session.query(User).filter(User.role == 100).first()
        if not root:
            hashed_password = hash_password("123456")
            access_token = generate_uuid()
            if config.InitialRootAccessToken:
                access_token = config.InitialRootAccessToken

            root = User(
                username="root",
                password=hashed_password,
                role=100,
                status=1,
                display_name="Root User",
                access_token=access_token,
                quota=500000000000000,
            )
            session.add(root)
            session.commit()
            print("Root user created: username=root, password=123456")

            if config.InitialRootToken:
                from models.token import Token
                root_token = Token(
                    user_id=root.id,
                    key=config.InitialRootToken,
                    status=1,
                    name="Initial Root Token",
                    created_time=get_timestamp(),
                    accessed_time=get_timestamp(),
                    expired_time=-1,
                    remain_quota=500000000000000,
                    unlimited_quota=True,
                )
                session.add(root_token)
                session.commit()
                print(f"Root token created: {config.InitialRootToken}")
    except Exception as e:
        session.rollback()
        print(f"Error creating root user: {e}")
    finally:
        session.close()


def get_session() -> Generator[Session, None, None]:
    session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()


@contextlib.contextmanager
def get_db_session():
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def close_db():
    if _engine:
        _engine.dispose()
