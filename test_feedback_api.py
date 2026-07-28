from fastapi.testclient import TestClient

from backend.database import SessionLocal, init_db
from backend.main import app


def test_feedback_api_saves_turn_context_and_rag_chunks():
    from backend.models.models import AgentFeedback

    init_db()
    client = TestClient(app)
    payload = {
        "session_id": "SFEEDBACK01",
        "customer_id": "101",
        "question": "宋PLUS现在优惠多少？",
        "answer": "根据资料，当前优惠以门店政策为准。",
        "intent": "rag_answer",
        "rating": "bad",
        "reason": "资料不足",
        "tool_trace": [
            {
                "tool_name": "rag_search_tool",
                "input": {"query": "宋PLUS优惠"},
                "output": {
                    "docs": [
                        {
                            "title": "宋PLUS DM-i 优惠政策",
                            "content": "置换补贴和金融政策以门店为准。",
                            "score": 1.8,
                        }
                    ]
                },
                "timestamp": "2026-07-29T01:00:00",
            }
        ],
    }

    response = client.post("/api/feedback", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "saved"
    assert body["id"] > 0

    db = SessionLocal()
    try:
        saved = db.query(AgentFeedback).filter(AgentFeedback.id == body["id"]).one()
        assert saved.question == "宋PLUS现在优惠多少？"
        assert saved.answer.startswith("根据资料")
        assert saved.intent == "rag_answer"
        assert saved.rating == "bad"
        assert saved.reason == "资料不足"
        assert saved.tool_names == ["rag_search_tool"]
        assert saved.rag_chunks[0]["title"] == "宋PLUS DM-i 优惠政策"
        assert "置换补贴" in saved.rag_chunks[0]["content"]
    finally:
        db.delete(saved)
        db.commit()
        db.close()


def test_feedback_stats_reports_common_failure_patterns():
    from backend.models.models import AgentFeedback

    init_db()
    db = SessionLocal()
    created = []
    try:
        rows = [
            AgentFeedback(
                session_id="SSTAT01",
                customer_id="1",
                question="优惠多少",
                answer="资料不足",
                intent="rag_answer",
                rating="bad",
                reason="资料不足",
                tool_names=["rag_search_tool"],
                tool_trace=[],
                rag_chunks=[],
            ),
            AgentFeedback(
                session_id="SSTAT02",
                customer_id="2",
                question="月供多少",
                answer="算错了",
                intent="loan_calculation",
                rating="bad",
                reason="信息不准",
                tool_names=["loan_calculator_tool"],
                tool_trace=[],
                rag_chunks=[],
            ),
            AgentFeedback(
                session_id="SSTAT03",
                customer_id="3",
                question="推荐SUV",
                answer="好的",
                intent="car_recommendation",
                rating="good",
                reason="",
                tool_names=["search_car_tool"],
                tool_trace=[],
                rag_chunks=[],
            ),
        ]
        db.add_all(rows)
        db.commit()
        created = rows

        client = TestClient(app)
        response = client.get("/api/feedback/stats")

        assert response.status_code == 200
        stats = response.json()
        assert stats["total"] >= 3
        assert stats["bad"] >= 2
        assert stats["reason_counts"]["资料不足"] >= 1
        assert stats["intent_counts"]["loan_calculation"] >= 1
        assert stats["tool_counts"]["rag_search_tool"] >= 1
        assert any(item["question"] == "月供多少" for item in stats["recent_bad"])
        assert any("补充高频失败问题" in item for item in stats["suggestions"]["knowledge_base"])
    finally:
        for row in created:
            db.delete(row)
        db.commit()
        db.close()


if __name__ == "__main__":
    test_feedback_api_saves_turn_context_and_rag_chunks()
    test_feedback_stats_reports_common_failure_patterns()
    print("feedback api checks passed")
