"""
AutoLead Agent Pydantic Schemas
请求/响应模型定义
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ─── 对话 ─────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: str = ""
    customer_id: str = ""
    message: str


class ToolTraceItem(BaseModel):
    tool_name: str
    input: dict
    output: dict
    timestamp: str = ""


class ChatResponse(BaseModel):
    reply: str
    session_id: str = ""
    customer_id: str = ""
    current_intent: str = ""
    purchase_intent: dict = {}
    customer_profile: dict = {}
    tool_trace: list[ToolTraceItem] = []
    missing_slots: list[str] = []


# ─── 客户 ─────────────────────────────────────────

class CustomerProfileResponse(BaseModel):
    id: int
    name: str
    phone: str
    city: str
    budget: str = ""
    car_type: str = ""
    energy_type: str = ""
    usage: str = ""
    concerns: list = []
    intent_models: list = []
    purchase_time: str = ""
    lead_level: str = ""
    follow_up_summary: str = ""
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─── 车型 ─────────────────────────────────────────

class CarItem(BaseModel):
    id: int
    brand: str
    model: str
    price: float
    car_type: str
    energy_type: str
    seat_count: int = 5
    fuel_consumption: str = ""
    range_km: str = ""
    highlights: list = []

    class Config:
        from_attributes = True


class CompareRequest(BaseModel):
    models: list[str] = Field(..., min_length=2, max_length=4)


class CompareResult(BaseModel):
    model: str
    brand: str
    price: float
    energy_type: str
    fuel_consumption: str
    seat_count: int
    highlights: list
    recommendation: str = ""


class CompareResponse(BaseModel):
    cars: list[CompareResult]


# ─── 分期试算 ────────────────────────────────────

class LoanRequest(BaseModel):
    car_price: float = Field(..., gt=0)
    down_payment_rate: float = Field(default=0.3, ge=0.1, le=0.7)
    years: int = Field(default=3, ge=1, le=5)
    annual_rate: float = Field(default=0.045, ge=0.01, le=0.2)


class LoanResponse(BaseModel):
    down_payment: float
    loan_amount: float
    monthly_payment: float
    total_interest: float
    estimated_total_cost: float


# ─── 库存 ────────────────────────────────────────

class InventoryQuery(BaseModel):
    model: str
    city: str = ""
    color: str = ""


class InventoryItem(BaseModel):
    model: str
    brand: str
    city: str
    store_name: str
    color: str
    stock_count: int
    delivery_time: str
    price: float


class InventoryResponse(BaseModel):
    results: list[InventoryItem]


# ─── 试驾预约 ────────────────────────────────────

class AppointmentCreate(BaseModel):
    customer_name: str
    phone: str
    model: str
    store: str
    appointment_time: str


class AppointmentResponse(BaseModel):
    appointment_id: str
    status: str = "预约成功"
    message: str = ""


# ─── 线索 ────────────────────────────────────────

class LeadItem(BaseModel):
    id: int
    customer_id: int
    name: str
    phone: str
    budget: str
    intent_models: list
    lead_level: str
    purchase_time: str
    follow_up_summary: str
    last_contact_time: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── 知识库 ──────────────────────────────────────

class KnowledgeSearchRequest(BaseModel):
    query: str
    top_k: int = 5


class KnowledgeDoc(BaseModel):
    id: int
    title: str
    content: str
    doc_type: str
    score: float = 0.0

    class Config:
        from_attributes = True


class KnowledgeSearchResponse(BaseModel):
    docs: list[KnowledgeDoc]


class KnowledgeUploadRequest(BaseModel):
    title: str
    doc_type: str = "general"
    content: str
    metadata: dict = {}
