from backend.agent.nodes import response_node


def test_response_node_preserves_follow_up_question():
    state = {
        "user_message": "好的",
        "current_intent": "general_question",
        "final_response": "要推荐得更准，我还需要确认这几项：\n- 您想买轿车还是SUV？\n- 您倾向燃油、混动还是纯电？",
        "tool_results": {},
        "tool_trace": [],
    }

    reply = response_node(state)["final_response"]

    assert "您想买轿车还是SUV" in reply
    assert "您倾向燃油、混动还是纯电" in reply
    assert "补充预算、车型偏好和主要用途" not in reply


def test_recommendation_response_uses_search_results_not_compare_script():
    state = {
        "user_message": "推荐几款20万以内的SUV",
        "current_intent": "car_recommendation",
        "purchase_intent": {"budget": "20万以内", "car_type": "SUV"},
        "tool_results": {
            "search_cars": [
                {
                    "brand": "比亚迪",
                    "model": "宋PLUS DM-i",
                    "price": 169800,
                    "energy_type": "插电混动",
                    "fuel_consumption": "4.4 L/100km",
                    "highlights": ["空间大", "油耗低"],
                },
                {
                    "brand": "丰田",
                    "model": "锋兰达双擎",
                    "price": 179800,
                    "energy_type": "混动",
                    "fuel_consumption": "4.5 L/100km",
                    "highlights": ["丰田品质", "油耗低"],
                },
                {
                    "brand": "哈弗",
                    "model": "枭龙MAX",
                    "price": 189800,
                    "energy_type": "插电混动",
                    "fuel_consumption": "5.5 L/100km",
                    "highlights": ["四驱", "配置丰富"],
                },
            ]
        },
        "tool_trace": [],
    }

    reply = response_node(state)["final_response"]

    assert "这几款" in reply
    assert "宋PLUS DM-i" in reply
    assert "锋兰达双擎" in reply
    assert "枭龙MAX" in reply
    assert "这两款定位不太一样" not in reply
    assert "如果你更看重空间和用车成本" not in reply


def test_compare_tesla_alias_uses_model_y():
    from backend.database import init_db
    from backend.seed_data import seed_all
    from backend.agent.nodes import tool_executor

    init_db()
    seed_all()
    state = {
        "user_message": "对比特斯拉",
        "current_intent": "car_compare",
        "next_action": "compare_car",
        "purchase_intent": {"budget": "20万以内", "car_type": "SUV"},
        "tool_results": {},
        "tool_trace": [],
    }

    result = tool_executor(state)
    models = [car["model"] for car in result["tool_results"]["compare"]]
    trace_models = result["tool_trace"][-1]["input"]["models"]

    assert "Model Y" in models
    assert "Model Y" in trace_models
    assert trace_models != ["宋PLUS DM-i", "锋兰达双擎"]
    assert len(models) >= 2


if __name__ == "__main__":
    test_response_node_preserves_follow_up_question()
    test_recommendation_response_uses_search_results_not_compare_script()
    test_compare_tesla_alias_uses_model_y()
    print("agent response checks passed")
