"""
AutoLead Agent 数据库模型定义
涵盖客户、车型、库存、试驾预约、对话记录、知识库
"""

import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship

from backend.database import Base


class Customer(Base):
    """客户基本信息"""
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), default="")
    phone = Column(String(20), default="")
    city = Column(String(64), default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    profile = relationship("CustomerProfile", back_populates="customer", uselist=False)
    appointments = relationship("TestDriveAppointment", back_populates="customer")
    sessions = relationship("ConversationSession", back_populates="customer")


class CustomerProfile(Base):
    """客户画像（长期记忆）"""
    __tablename__ = "customer_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, unique=True)
    budget = Column(String(64), default="")
    car_type = Column(String(32), default="")
    energy_type = Column(String(32), default="")
    usage = Column(String(64), default="")
    concerns = Column(JSON, default=list)
    intent_models = Column(JSON, default=list)
    purchase_time = Column(String(64), default="")
    lead_level = Column(String(16), default="低意向")
    follow_up_summary = Column(Text, default="")
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    customer = relationship("Customer", back_populates="profile")


class Car(Base):
    """车型信息"""
    __tablename__ = "cars"

    id = Column(Integer, primary_key=True, autoincrement=True)
    brand = Column(String(64), nullable=False)
    model = Column(String(128), nullable=False)
    price = Column(Float, nullable=False)
    car_type = Column(String(32), nullable=False)     # SUV / 轿车 / MPV
    energy_type = Column(String(32), nullable=False)  # 燃油 / 混动 / 纯电 / 插电混动
    seat_count = Column(Integer, default=5)
    fuel_consumption = Column(String(32), default="")  # 油耗 (L/100km) 或电耗
    range_km = Column(String(32), default="")           # 续航里程
    highlights = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    inventories = relationship("Inventory", back_populates="car")


class Inventory(Base):
    """库存信息"""
    __tablename__ = "inventories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    car_id = Column(Integer, ForeignKey("cars.id"), nullable=False)
    city = Column(String(64), nullable=False)
    store_name = Column(String(128), nullable=False)
    color = Column(String(32), default="白色")
    stock_count = Column(Integer, default=0)
    delivery_time = Column(String(64), default="")
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    car = relationship("Car", back_populates="inventories")


class TestDriveAppointment(Base):
    """试驾预约"""
    __tablename__ = "test_drive_appointments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    appointment_id = Column(String(32), unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    car_id = Column(Integer, ForeignKey("cars.id"), nullable=False)
    store_name = Column(String(128), nullable=False)
    appointment_time = Column(String(64), nullable=False)
    status = Column(String(16), default="预约成功")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    customer = relationship("Customer", back_populates="appointments")
    car = relationship("Car")


class ConversationSession(Base):
    """对话会话"""
    __tablename__ = "conversation_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    summary = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    customer = relationship("Customer", back_populates="sessions")
    messages = relationship("ConversationMessage", back_populates="session", order_by="ConversationMessage.created_at")


class ConversationMessage(Base):
    """对话消息"""
    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), ForeignKey("conversation_sessions.session_id"), nullable=False)
    role = Column(String(16), nullable=False)  # user / assistant / system
    content = Column(Text, nullable=False)
    tool_trace = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    session = relationship("ConversationSession", back_populates="messages")


class AgentFeedback(Base):
    """User feedback for one completed Agent answer."""
    __tablename__ = "agent_feedbacks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), default="", index=True)
    customer_id = Column(String(32), default="", index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    intent = Column(String(64), default="", index=True)
    rating = Column(String(16), nullable=False, index=True)
    reason = Column(String(64), default="", index=True)
    tool_names = Column(JSON, default=list)
    tool_trace = Column(JSON, default=list)
    rag_chunks = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class AgentRunMetric(Base):
    """Runtime metrics for one completed Agent turn."""
    __tablename__ = "agent_run_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), default="", index=True)
    customer_id = Column(String(32), default="", index=True)
    question = Column(Text, default="")
    intent = Column(String(64), default="", index=True)
    success = Column(Boolean, default=True, index=True)
    response_time_ms = Column(Integer, default=0)
    tool_names = Column(JSON, default=list)
    failed_tool_names = Column(JSON, default=list)
    error_type = Column(String(64), default="", index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class KnowledgeDocument(Base):
    """知识库文档"""
    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(256), nullable=False)
    doc_type = Column(String(32), default="general")  # car_config / policy / sales_script / competitor
    content = Column(Text, nullable=False)
    doc_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    chunks = relationship("KnowledgeChunk", back_populates="document", cascade="all, delete-orphan")


class KnowledgeChunk(Base):
    """知识库文档块（含向量）"""
    __tablename__ = "knowledge_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("knowledge_documents.id"), nullable=False)
    chunk_text = Column(Text, nullable=False)
    embedding = Column(Text, default="")  # 向量以 JSON 字符串存储（SQLite 兼容）
    chunk_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    document = relationship("KnowledgeDocument", back_populates="chunks")
