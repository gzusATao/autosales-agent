from fastapi.testclient import TestClient

from backend.database import SessionLocal, init_db
from backend.main import app


def test_agent_metrics_reports_runtime_feedback_rag_and_tool_health():
    from backend.models.models import AgentFeedback, AgentRunMetric

    init_db()
    db = SessionLocal()
    created_runs = []
    created_feedbacks = []
    try:
        created_runs = [
            AgentRunMetric(
                session_id="SMETRIC01",
                customer_id="1",
                question="recommend suv",
                intent="car_recommendation",
                success=True,
                response_time_ms=1200,
                tool_names=["search_car_tool"],
                failed_tool_names=[],
                error_type="",
                feedback_rating="good",
            ),
            AgentRunMetric(
                session_id="SMETRIC02",
                customer_id="2",
                question="song plus discount",
                intent="rag_answer",
                success=False,
                response_time_ms=1800,
                tool_names=["rag_search_tool"],
                failed_tool_names=["rag_search_tool"],
                error_type="tool_fallback",
                feedback_rating="bad",
                feedback_reason="material_missing",
            ),
        ]
        created_feedbacks = [
            AgentFeedback(
                session_id="SMETRIC01",
                customer_id="1",
                question="recommend suv",
                answer="ok",
                intent="car_recommendation",
                rating="good",
                reason="",
                tool_names=["search_car_tool"],
                tool_trace=[],
                rag_chunks=[],
            ),
            AgentFeedback(
                session_id="SMETRIC02",
                customer_id="2",
                question="song plus discount",
                answer="no material",
                intent="rag_answer",
                rating="bad",
                reason="material_missing",
                tool_names=["rag_search_tool"],
                tool_trace=[],
                rag_chunks=[{"title": "empty", "content": "", "score": 0}],
            ),
        ]
        db.add_all(created_runs + created_feedbacks)
        db.commit()

        client = TestClient(app)
        response = client.get("/api/metrics/agent")

        assert response.status_code == 200
        body = response.json()
        assert body["total_runs"] >= 2
        assert body["successful_runs"] >= 1
        assert body["failed_runs"] >= 1
        assert body["average_response_time_ms"] > 0
        assert body["satisfied"] >= 1
        assert body["unsatisfied"] >= 1
        assert body["rag_negative_count"] >= 1
        assert body["tool_counts"]["rag_search_tool"] >= 1
        assert body["failed_tool_counts"]["rag_search_tool"] >= 1
        assert body["reason_counts"]["material_missing"] >= 1
        assert any(item["error_type"] == "tool_fallback" for item in body["recent_failures"])
    finally:
        for row in created_feedbacks:
            db.delete(row)
        for row in created_runs:
            db.delete(row)
        db.commit()
        db.close()


def test_feedback_submission_updates_agent_run_metric():
    from backend.models.models import AgentFeedback, AgentRunMetric

    init_db()
    db = SessionLocal()
    metric = AgentRunMetric(
        session_id="SFEEDBACK01",
        customer_id="88",
        question="瑞虎8多少钱",
        intent="rag_answer",
        success=True,
        response_time_ms=900,
        tool_names=["rag_search_tool"],
        failed_tool_names=[],
    )
    db.add(metric)
    db.commit()
    feedback_id = None
    try:
        client = TestClient(app)
        response = client.post(
            "/api/feedback",
            json={
                "session_id": "SFEEDBACK01",
                "customer_id": "88",
                "question": "瑞虎8多少钱",
                "answer": "目前没有“瑞虎8”相关资料。",
                "intent": "rag_answer",
                "rating": "bad",
                "reason": "资料不足",
                "tool_trace": [
                    {
                        "tool_name": "rag_search_tool",
                        "input": {"query": "瑞虎8多少钱"},
                        "output": {"docs_count": 0},
                        "timestamp": "",
                    }
                ],
            },
        )

        assert response.status_code == 200
        feedback_id = response.json()["id"]
        db.refresh(metric)
        assert metric.feedback_id == feedback_id
        assert metric.feedback_rating == "bad"
        assert metric.feedback_reason == "资料不足"
    finally:
        if feedback_id:
            feedback = db.query(AgentFeedback).filter(AgentFeedback.id == feedback_id).first()
            if feedback:
                db.delete(feedback)
        db.delete(metric)
        db.commit()
        db.close()


if __name__ == "__main__":
    test_agent_metrics_reports_runtime_feedback_rag_and_tool_health()
    test_feedback_submission_updates_agent_run_metric()
    print("metrics api checks passed")
