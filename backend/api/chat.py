"""
Chat API.

Keeps the normal HTTP endpoint and exposes a shared processing function so the
WebSocket endpoint can stream the same Agent result without duplicating logic.
"""

import re
import uuid
import json
import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.agent.graph import run_agent
from backend.agent.state import SalesAgentState
from backend.database import get_db
from backend.models.models import AgentRunMetric, ConversationSession, Customer
from backend.schemas.schemas import ChatRequest, ChatResponse, ToolTraceItem

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/message", response_model=ChatResponse)
def chat_message(req: ChatRequest, db: Session = Depends(get_db)):
    """Handle one user message and return the full Agent response."""
    return process_chat_message(req, db)


def process_chat_message(req: ChatRequest, db: Session) -> ChatResponse:
    """Run one chat turn. Shared by HTTP and WebSocket transports."""
    started_at = time.perf_counter()
    customer_id = _ensure_customer(db, req)
    session_id = _ensure_session(db, customer_id, req.session_id)

    _save_user_message(db, session_id, req.message)

    previous_intent = _load_session_intent(db, session_id)

    state = SalesAgentState(
        session_id=session_id,
        customer_id=str(customer_id),
        user_message=req.message,
        purchase_intent=previous_intent,
    )

    try:
        result = run_agent(state)
    except Exception as exc:
        print(f"[Agent Error] {exc}")
        result = state
        result["final_response"] = "抱歉，我这边遇到了一点技术问题，请稍后再试。"
        result["runtime_error"] = type(exc).__name__

    reply = _polish_reply(
        result.get("final_response") or "收到，您可以再补充一下预算、车型或用途，我继续帮您分析。"
    )
    intent = result.get("current_intent", "")
    purchase_intent = result.get("purchase_intent", {})
    tool_trace = result.get("tool_trace", [])
    missing_slots = result.get("missing_slots", [])
    customer_profile = result.get("customer_profile", {})

    _save_session_intent(db, session_id, purchase_intent)

    _save_agent_message(db, session_id, reply, tool_trace)
    try:
        _save_run_metric(
            db=db,
            session_id=session_id,
            customer_id=str(customer_id),
            question=req.message,
            intent=intent,
            tool_trace=tool_trace,
            response_time_ms=int((time.perf_counter() - started_at) * 1000),
            error_type=result.get("runtime_error", ""),
        )
    except Exception as exc:
        db.rollback()
        print(f"[Metrics Error] {exc}")

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
    """Ensure the customer exists and return customer_id."""
    if req.customer_id:
        try:
            cid = int(req.customer_id)
            customer = db.query(Customer).filter(Customer.id == cid).first()
            if customer:
                return customer.id
        except ValueError:
            pass

    customer = Customer(name="", phone="")
    db.add(customer)
    db.flush()
    return customer.id


def _ensure_session(db: Session, customer_id: int, session_id: str) -> str:
    """Ensure the conversation session exists and return session_id."""
    if session_id:
        sess = db.query(ConversationSession).filter(
            ConversationSession.session_id == session_id
        ).first()
        if sess:
            return sess.session_id

    new_id = session_id or f"S{uuid.uuid4().hex[:8].upper()}"
    sess = ConversationSession(
        session_id=new_id,
        customer_id=customer_id,
    )
    db.add(sess)
    db.commit()
    return new_id


def _load_session_intent(db: Session, session_id: str) -> dict:
    """Load short-term purchase intent saved on the conversation session."""
    sess = db.query(ConversationSession).filter(
        ConversationSession.session_id == session_id
    ).first()
    if not sess or not sess.summary:
        return {}
    try:
        summary = json.loads(sess.summary)
    except json.JSONDecodeError:
        return {}
    if isinstance(summary, dict):
        intent = summary.get("purchase_intent", {})
        return intent if isinstance(intent, dict) else {}
    return {}


def _save_session_intent(db: Session, session_id: str, purchase_intent: dict):
    """Persist short-term purchase intent for the next turn in the same session."""
    if not purchase_intent:
        return
    sess = db.query(ConversationSession).filter(
        ConversationSession.session_id == session_id
    ).first()
    if not sess:
        return
    sess.summary = json.dumps({"purchase_intent": purchase_intent}, ensure_ascii=False)
    db.commit()


def _save_user_message(db: Session, session_id: str, content: str):
    """Persist a user message."""
    from backend.models.models import ConversationMessage

    msg = ConversationMessage(
        session_id=session_id,
        role="user",
        content=content,
    )
    db.add(msg)
    db.commit()


def _save_agent_message(db: Session, session_id: str, content: str, tool_trace: list):
    """Persist an assistant message."""
    from backend.models.models import ConversationMessage

    msg = ConversationMessage(
        session_id=session_id,
        role="assistant",
        content=content,
        tool_trace=tool_trace,
    )
    db.add(msg)
    db.commit()


def _save_run_metric(
    db: Session,
    session_id: str,
    customer_id: str,
    question: str,
    intent: str,
    tool_trace: list,
    response_time_ms: int,
    error_type: str = "",
):
    """Persist lightweight runtime data for the operations dashboard."""
    tool_names = []
    failed_tool_names = []
    rag_no_result = False
    for item in tool_trace or []:
        name = item.get("tool_name", "")
        if name and name not in tool_names:
            tool_names.append(name)
        output = item.get("output") or {}
        if name and isinstance(output, dict) and output.get("error") and name not in failed_tool_names:
            failed_tool_names.append(name)
        if name == "rag_search_tool" and isinstance(output, dict) and output.get("docs_count") == 0:
            rag_no_result = True

    resolved_error_type = error_type or ("tool_fallback" if failed_tool_names else "rag_no_result" if rag_no_result else "")
    metric = AgentRunMetric(
        session_id=session_id,
        customer_id=customer_id,
        question=question,
        intent=intent,
        success=not resolved_error_type,
        response_time_ms=max(response_time_ms, 0),
        tool_names=tool_names,
        failed_tool_names=failed_tool_names,
        error_type=resolved_error_type,
    )
    db.add(metric)
    db.commit()


def _polish_reply(reply: str) -> str:
    """Remove repetitive sales-script openings from LLM output."""
    cleaned = (reply or "").strip()
    repetitive_patterns = [
        r"^您好[！!，,。\s]*感谢您的(?:咨询|关注)[！!，,。\s]*",
        r"^作为您的(?:汽车)?销售顾问[，,。\s]*",
        r"^我是(?:您的)?(?:汽车)?销售顾问[，,。\s]*",
        r"^很高兴为您服务[！!，,。\s]*",
        r"^非常乐意为您(?:推荐|服务)[^。！？!?]*[。！？!?]\s*",
    ]

    previous = None
    while previous != cleaned:
        previous = cleaned
        for pattern in repetitive_patterns:
            cleaned = re.sub(pattern, "", cleaned).strip()

    return cleaned or reply
