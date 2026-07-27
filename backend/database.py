"""
数据库连接和会话管理
开发模式使用 SQLite，可切换 PostgreSQL
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, scoped_session, sessionmaker

from backend.config import settings


# 根据 db 类型配置 engine
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=settings.DEBUG,
)

# 启用 SQLite WAL 模式和 foreign keys
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if settings.DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False))


class Base(DeclarativeBase):
    pass


def get_db():
    """获取数据库会话（FastAPI 依赖注入）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """创建所有表"""
    from backend.models.models import (  # noqa: F401 — 确保模型被导入
        Car,
        Customer,
        CustomerProfile,
        Inventory,
        TestDriveAppointment,
        ConversationSession,
        ConversationMessage,
        KnowledgeDocument,
        KnowledgeChunk,
    )
    Base.metadata.create_all(bind=engine)
