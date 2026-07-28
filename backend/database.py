"""
数据库连接和会话管理
开发模式使用 SQLite，可切换 PostgreSQL
"""

from sqlalchemy import create_engine, event, inspect, text
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
        AgentFeedback,
        AgentRunMetric,
        KnowledgeDocument,
        KnowledgeChunk,
    )
    Base.metadata.create_all(bind=engine)
    _ensure_agent_run_metric_feedback_columns()
    _backfill_agent_run_metric_feedbacks()


def _ensure_agent_run_metric_feedback_columns():
    """Add feedback columns for existing SQLite demo databases."""
    inspector = inspect(engine)
    if "agent_run_metrics" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("agent_run_metrics")}
    ddl = {
        "feedback_id": "ALTER TABLE agent_run_metrics ADD COLUMN feedback_id INTEGER DEFAULT 0",
        "feedback_rating": "ALTER TABLE agent_run_metrics ADD COLUMN feedback_rating VARCHAR(16) DEFAULT ''",
        "feedback_reason": "ALTER TABLE agent_run_metrics ADD COLUMN feedback_reason VARCHAR(64) DEFAULT ''",
    }
    missing = [sql for name, sql in ddl.items() if name not in existing]
    if not missing:
        return

    with engine.begin() as conn:
        for sql in missing:
            conn.execute(text(sql))


def _backfill_agent_run_metric_feedbacks():
    """Copy existing feedback records onto matching runtime metric rows."""
    from backend.models.models import AgentFeedback, AgentRunMetric

    db = SessionLocal()
    try:
        feedbacks = (
            db.query(AgentFeedback)
            .order_by(AgentFeedback.created_at.asc())
            .all()
        )
        changed = False
        for feedback in feedbacks:
            query = db.query(AgentRunMetric).filter(
                AgentRunMetric.session_id == feedback.session_id,
                AgentRunMetric.customer_id == feedback.customer_id,
                AgentRunMetric.question == feedback.question,
                AgentRunMetric.intent == feedback.intent,
            )
            metric = query.order_by(AgentRunMetric.created_at.desc()).first()
            if not metric and feedback.session_id:
                metric = (
                    db.query(AgentRunMetric)
                    .filter(AgentRunMetric.session_id == feedback.session_id)
                    .order_by(AgentRunMetric.created_at.desc())
                    .first()
                )
            if not metric or metric.feedback_rating:
                continue

            metric.feedback_id = feedback.id
            metric.feedback_rating = feedback.rating
            metric.feedback_reason = feedback.reason if feedback.rating == "bad" else ""
            changed = True

        if changed:
            db.commit()
    finally:
        db.close()
