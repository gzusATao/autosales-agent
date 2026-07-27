"""
AutoLead Agent 配置模块
支持通过环境变量覆盖，默认使用 SQLite 开发模式
"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "汽车销售顾问"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # 数据库配置 — 默认使用 SQLite（开发模式），生产建议 PostgreSQL
    DATABASE_URL: str = "sqlite:///./autosales.db"
    # PostgreSQL 示例: "postgresql://postgres:password@localhost:5432/autosales"

    # Redis 配置
    REDIS_URL: str = "redis://localhost:6379/0"

    # LLM 配置
    LLM_PROVIDER: str = "deepseek"  # mock | openai | dashscope | deepseek
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.deepseek.com"
    OPENAI_MODEL: str = "deepseek-chat"
    DASHSCOPE_API_KEY: str = ""

    # Embedding 配置
    EMBEDDING_PROVIDER: str = "mock"  # mock | dashscope | bge
    DASHSCOPE_EMBEDDING_MODEL: str = "text-embedding-v3"
    BGE_MODEL_PATH: str = "BAAI/bge-small-zh-v1.5"

    # pgvector 配置（使用 SQLite 的简单向量搜索替代）
    VECTOR_DIMENSION: int = 384

    # 会话配置
    SESSION_EXPIRE_MINUTES: int = 60

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
