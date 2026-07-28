"""
Feedback API for closing the Agent optimization loop.
"""

from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.models import AgentFeedback
from backend.schemas.schemas import (
    FeedbackCreate,
    FeedbackCreateResponse,
    FeedbackStatsResponse,
)

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackCreateResponse)
def create_feedback(req: FeedbackCreate, db: Session = Depends(get_db)):
    """Persist one user rating with the full Agent turn context."""
    tool_trace = [item.model_dump() for item in req.tool_trace]
    feedback = AgentFeedback(
        session_id=req.session_id,
        customer_id=req.customer_id,
        question=req.question,
        answer=req.answer,
        intent=req.intent,
        rating=req.rating,
        reason=req.reason if req.rating == "bad" else "",
        tool_names=_extract_tool_names(tool_trace),
        tool_trace=tool_trace,
        rag_chunks=_extract_rag_chunks(tool_trace),
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return FeedbackCreateResponse(id=feedback.id)


@router.get("/stats", response_model=FeedbackStatsResponse)
def feedback_stats(db: Session = Depends(get_db)):
    """Summarize feedback signals for prompt/tool/RAG iteration."""
    rows = db.query(AgentFeedback).order_by(AgentFeedback.created_at.desc()).all()
    bad_rows = [row for row in rows if row.rating == "bad"]

    reason_counts = Counter(row.reason for row in bad_rows if row.reason)
    intent_counts = Counter(row.intent for row in rows if row.intent)
    tool_counts = Counter()
    for row in rows:
        for name in row.tool_names or []:
            tool_counts[name] += 1

    recent_bad = [
        {
            "id": row.id,
            "question": row.question,
            "answer": row.answer,
            "intent": row.intent,
            "reason": row.reason,
            "tool_names": row.tool_names or [],
            "rag_chunks": row.rag_chunks or [],
            "created_at": row.created_at.isoformat() if row.created_at else "",
        }
        for row in bad_rows[:10]
    ]

    return FeedbackStatsResponse(
        total=len(rows),
        good=sum(1 for row in rows if row.rating == "good"),
        bad=len(bad_rows),
        reason_counts=dict(reason_counts),
        intent_counts=dict(intent_counts),
        tool_counts=dict(tool_counts),
        recent_bad=recent_bad,
        suggestions=_build_suggestions(reason_counts, intent_counts, tool_counts),
    )


def _extract_tool_names(tool_trace: list[dict]) -> list[str]:
    names = []
    for item in tool_trace:
        name = item.get("tool_name")
        if name and name not in names:
            names.append(name)
    return names


def _extract_rag_chunks(tool_trace: list[dict]) -> list[dict]:
    chunks = []
    for item in tool_trace:
        name = item.get("tool_name", "")
        if "rag" not in name.lower():
            continue
        output = item.get("output") or {}
        docs = output.get("docs") or output.get("results") or []
        if isinstance(docs, dict):
            docs = [docs]
        for doc in docs[:5]:
            if not isinstance(doc, dict):
                continue
            content = doc.get("content") or doc.get("chunk_text") or doc.get("text") or ""
            chunks.append({
                "title": doc.get("title", ""),
                "content": content[:500],
                "score": doc.get("score", 0),
                "doc_type": doc.get("doc_type", ""),
            })
    return chunks[:10]


def _build_suggestions(
    reason_counts: Counter,
    intent_counts: Counter,
    tool_counts: Counter,
) -> dict:
    prompt = []
    tools = []
    knowledge_base = []

    if reason_counts.get("答非所问", 0):
        prompt.append("收紧 Response Prompt：回答前先复述识别到的用户意图，避免跳到上一轮任务。")
    if reason_counts.get("追问太多", 0):
        prompt.append("优化 SlotFill Prompt：缺失槽位合并一次追问，简单咨询不要强制采集购车信息。")
    if reason_counts.get("信息不准", 0):
        tools.append("检查高频工具入参映射，特别是价格、首付、车型名等数字和实体字段。")
    if reason_counts.get("工具调用错误", 0):
        tools.append("补充工具描述和参数校验，失败时记录 error 并走业务兜底回复。")
    if reason_counts.get("资料不足", 0):
        knowledge_base.append("补充高频失败问题对应车型、优惠政策、配置对比和销售话术资料。")
    if tool_counts.get("rag_search_tool", 0) and intent_counts.get("rag_answer", 0):
        knowledge_base.append("复盘 RAG 命中片段，清理低相关 chunk，补充车型别名和政策关键词。")

    if not prompt:
        prompt.append("持续观察不满意样本，优先处理同一意图下重复出现的失败原因。")
    if not tools:
        tools.append("保持工具轨迹可追踪，后续按失败样本补充参数边界测试。")
    if not knowledge_base:
        knowledge_base.append("定期查看不满意问题，将真实问法沉淀为销售资料和检索测试用例。")

    return {
        "prompt": prompt,
        "tools": tools,
        "knowledge_base": knowledge_base,
    }
