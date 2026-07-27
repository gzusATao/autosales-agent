"""
对话 API
处理客户消息，运行 Agent 流程并返回回复
"""

import datetime
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.models import Customer, ConversationSession
from backend.agent.state import SalesAgentState
from backend.agent.graph import run_agent
from backend.schemas.schemas import ChatRequest, ChatResponse, ToolTraceItem

router = APIRouter(prefix="/api/chat", tags=["对话"])


@router.post("/message", response_model=ChatResponse)
def chat_message(req: ChatRequest, db: Session = Depends(get_db)):
    """处理用户消息并返回 Agent 回复"""

    # 确保客户存在
    customer_id = _ensure_customer(db, req)
    # 确保会话存在
    session_id = _ensure_session(db, customer_id, req.session_id)

    # 保存用户消息
    _save_user_message(db, session_id, req.message)

    # 构建 Agent 状态
    state = SalesAgentState(
        session_id=session_id,
        customer_id=str(customer_id),
        user_message=req.message,
    )

    # 运行 Agent
    try:
        result = run_agent(state)
    except Exception as e:
        print(f"[Agent Error] {e}")
        result = state
        result["final_response"] = "抱歉，我现在遇到了一些技术问题，请稍后再试。"

    reply = result.get("final_response", "感谢您的咨询，请问还有什么可以帮助您的？")
    intent = result.get("current_intent", "")
    purchase_intent = result.get("purchase_intent", {})
    tool_trace = result.get("tool_trace", [])
    missing_slots = result.get("missing_slots", [])
    customer_profile = result.get("customer_profile", {})

    # 保存 Agent 回复
    _save_agent_message(db, session_id, reply, tool_trace)

    return ChatResponse(
        reply=reply,
        session_id=session_id,
        customer_id=str(customer_id),
        current_intent=intent,
        purchase_intent=purchase_intent,
        customer_profile=customer_profile,
        tool_trace=[
            ToolTraceItem(
                tool_name=t.get("tool_name", ""),
                input=t.get("input", {}),
                output=t.get("output", {}),
                timestamp=t.get("timestamp", ""),
            )
            for t in tool_trace
        ],
        missing_slots=missing_slots,
    )


def _ensure_customer(db: Session, req: ChatRequest) -> int:
    """确保客户存在，返回 customer_id"""
    if req.customer_id:
        try:
            cid = int(req.customer_id)
            customer = db.query(Customer).filter(Customer.id == cid).first()
            if customer:
                return customer.id
        except ValueError:
            pass

    # 创建新客户
    customer = Customer(name="", phone="")
    db.add(customer)
    db.flush()
    return customer.id


def _ensure_session(db: Session, customer_id: int, session_id: str) -> str:
    """确保会话存在，返回 session_id"""
    if session_id:
        sess = db.query(ConversationSession).filter(
            ConversationSession.session_id == session_id
        ).first()
        if sess:
            return sess.session_id

    # 创建新会话
    new_id = session_id or f"S{uuid.uuid4().hex[:8].upper()}"
    sess = ConversationSession(
        session_id=new_id,
        customer_id=customer_id,
    )
    db.add(sess)
    db.commit()
    return new_id


def _save_user_message(db: Session, session_id: str, content: str):
    """保存用户消息"""
    from backend.models.models import ConversationMessage
    msg = ConversationMessage(
        session_id=session_id,
        role="user",
        content=content,
    )
    db.add(msg)
    db.commit()


def _save_agent_message(db: Session, session_id: str, content: str, tool_trace: list):
    """保存 Agent 回复"""
    from backend.models.models import ConversationMessage
    msg = ConversationMessage(
        session_id=session_id,
        role="assistant",
        content=content,
        tool_trace=tool_trace,
    )
    db.add(msg)
    db.commit()
