"""
记忆系统模块
短期记忆（Redis 会话缓存）+ 长期记忆（PostgreSQL/SQLite 客户画像）
"""

import json
from datetime import datetime, timedelta
from typing import Optional

from backend.database import SessionLocal
from backend.models.models import Customer, CustomerProfile, ConversationSession, ConversationMessage


class SessionMemory:
    """短期记忆：当前会话上下文"""

    def __init__(self, session_id: str, customer_id: str = ""):
        self.session_id = session_id
        self.customer_id = customer_id
        self.history: list[dict] = []

    def add_message(self, role: str, content: str, tool_trace: list = None):
        """添加消息到历史"""
        self.history.append({
            "role": role,
            "content": content,
            "tool_trace": tool_trace or [],
            "timestamp": datetime.now().isoformat(),
        })
        # 保存到数据库
        self._persist_message(role, content, tool_trace or [])

    def get_recent(self, n: int = 10) -> list[dict]:
        """获取最近 N 条消息"""
        return self.history[-n:]

    def _persist_message(self, role: str, content: str, tool_trace: list):
        """持久化消息到数据库"""
        db = SessionLocal()
        try:
            msg = ConversationMessage(
                session_id=self.session_id,
                role=role,
                content=content,
                tool_trace=tool_trace,
            )
            db.add(msg)
            db.commit()
        except Exception as e:
            print(f"[Memory] persist error: {e}")
            db.rollback()
        finally:
            db.close()


class LongTermMemory:
    """长期记忆：客户画像管理"""

    @staticmethod
    def get_profile(customer_id: int) -> Optional[dict]:
        """获取客户画像"""
        db = SessionLocal()
        try:
            customer = db.query(Customer).filter(Customer.id == customer_id).first()
            if not customer:
                return None

            profile = db.query(CustomerProfile).filter(
                CustomerProfile.customer_id == customer_id
            ).first()

            return {
                "id": customer.id,
                "name": customer.name,
                "phone": customer.phone,
                "city": customer.city,
                "budget": profile.budget if profile else "",
                "car_type": profile.car_type if profile else "",
                "energy_type": profile.energy_type if profile else "",
                "usage": profile.usage if profile else "",
                "concerns": profile.concerns if profile else [],
                "intent_models": profile.intent_models if profile else [],
                "purchase_time": profile.purchase_time if profile else "",
                "lead_level": profile.lead_level if profile else "低意向",
                "follow_up_summary": profile.follow_up_summary if profile else "",
                "updated_at": profile.updated_at.isoformat() if profile and profile.updated_at else "",
            }
        finally:
            db.close()

    @staticmethod
    def get_all_leads() -> list[dict]:
        """获取所有线索"""
        db = SessionLocal()
        try:
            results = (
                db.query(Customer, CustomerProfile)
                .outerjoin(CustomerProfile, Customer.id == CustomerProfile.customer_id)
                .order_by(Customer.updated_at.desc())
                .all()
            )
            leads = []
            for customer, profile in results:
                leads.append({
                    "id": customer.id,
                    "name": customer.name,
                    "phone": customer.phone,
                    "budget": profile.budget if profile else "",
                    "intent_models": profile.intent_models if profile else [],
                    "lead_level": profile.lead_level if profile else "低意向",
                    "purchase_time": profile.purchase_time if profile else "",
                    "follow_up_summary": profile.follow_up_summary if profile else "",
                    "last_contact_time": customer.updated_at.isoformat() if customer.updated_at else "",
                })
            return leads
        finally:
            db.close()
