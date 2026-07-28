"""
Operations metrics API for the Agent demo dashboard.
"""

from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.models import AgentRunMetric
from backend.schemas.schemas import AgentMetricsResponse

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/agent", response_model=AgentMetricsResponse)
def agent_metrics(db: Session = Depends(get_db)):
    """Summarize reliability, feedback, RAG and tool-call health."""
    runs = db.query(AgentRunMetric).order_by(AgentRunMetric.created_at.desc()).all()

    total_runs = len(runs)
    failed_runs = sum(1 for row in runs if not row.success)
    successful_runs = total_runs - failed_runs
    avg_ms = int(sum(row.response_time_ms or 0 for row in runs) / total_runs) if total_runs else 0

    tool_counts = Counter()
    failed_tool_counts = Counter()
    for row in runs:
        for name in row.tool_names or []:
            tool_counts[name] += 1
        for name in row.failed_tool_names or []:
            failed_tool_counts[name] += 1

    tool_call_total = sum(tool_counts.values())
    tool_failure_total = sum(failed_tool_counts.values())

    feedback_rows = [row for row in runs if row.feedback_rating]
    bad_feedbacks = [row for row in feedback_rows if row.feedback_rating == "bad"]
    good_feedbacks = [row for row in feedback_rows if row.feedback_rating == "good"]
    reason_counts = Counter(row.feedback_reason for row in bad_feedbacks if row.feedback_reason)
    rag_negative_count = sum(
        1 for row in bad_feedbacks
        if row.error_type == "rag_no_result" or any("rag" in name.lower() for name in (row.tool_names or []))
    )

    return AgentMetricsResponse(
        total_runs=total_runs,
        successful_runs=successful_runs,
        failed_runs=failed_runs,
        success_rate=_percent(successful_runs, total_runs),
        failure_rate=_percent(failed_runs, total_runs),
        average_response_time_ms=avg_ms,
        feedback_total=len(feedback_rows),
        satisfied=len(good_feedbacks),
        unsatisfied=len(bad_feedbacks),
        satisfaction_rate=_percent(len(good_feedbacks), len(feedback_rows)),
        dissatisfaction_rate=_percent(len(bad_feedbacks), len(feedback_rows)),
        rag_negative_count=rag_negative_count,
        tool_success_rate=_percent(tool_call_total - tool_failure_total, tool_call_total),
        tool_call_total=tool_call_total,
        tool_failure_total=tool_failure_total,
        tool_counts=dict(tool_counts),
        failed_tool_counts=dict(failed_tool_counts),
        reason_counts=dict(reason_counts),
        recent_failures=[
            {
                "id": row.id,
                "question": row.question,
                "intent": row.intent,
                "error_type": row.error_type,
                "failed_tool_names": row.failed_tool_names or [],
                "response_time_ms": row.response_time_ms or 0,
                "created_at": row.created_at.isoformat() if row.created_at else "",
            }
            for row in runs
            if not row.success
        ][:8],
        recent_bad_feedback=[
            {
                "id": row.id,
                "question": row.question,
                "intent": row.intent,
                "reason": row.feedback_reason,
                "tool_names": row.tool_names or [],
                "rag_chunks": [],
                "created_at": row.created_at.isoformat() if row.created_at else "",
            }
            for row in bad_feedbacks[:8]
        ],
    )


def _percent(part: int, total: int) -> float:
    if not total:
        return 0.0
    return round(part * 100 / total, 1)
