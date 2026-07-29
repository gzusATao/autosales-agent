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


def test_inventory_songplus_alias_queries_real_model():
    from backend.database import init_db
    from backend.seed_data import seed_all
    from backend.agent.nodes import tool_executor

    init_db()
    seed_all()
    state = {
        "user_message": "广州有宋PLUS现车吗",
        "current_intent": "inventory_query",
        "next_action": "inventory_query_action",
        "purchase_intent": {},
        "tool_results": {},
        "tool_trace": [],
    }

    result = tool_executor(state)
    inventory = result["tool_results"]["inventory"]
    trace_input = result["tool_trace"][-1]["input"]

    assert trace_input["model"] == "宋PLUS DM-i"
    assert trace_input["city"] == "广州"
    assert inventory
    assert all(item["model"] == "宋PLUS DM-i" for item in inventory)


def test_impossible_tesla_budget_reply_explains_mismatch():
    state = {
        "user_message": "给我推荐一辆5万以内的特斯拉",
        "current_intent": "car_recommendation",
        "purchase_intent": {
            "budget": "5万以内",
            "car_type": "SUV",
            "energy_type": "纯电",
            "intent_models": ["Model Y"],
        },
        "tool_results": {"search_cars": []},
        "tool_trace": [],
    }

    reply = response_node(state)["final_response"]

    assert "5万" in reply
    assert "特斯拉" in reply or "Model Y" in reply
    assert "不太现实" in reply
    assert "提高预算" in reply or "替代" in reply


def test_bare_model_alias_introduces_model_not_purchase_slots():
    from backend.agent.nodes import intent_node

    result = intent_node({
        "user_message": "modely",
        "purchase_intent": {},
    })

    assert result["current_intent"] == "general_question"
    assert result["next_action"] == "general_response"
    assert result["missing_slots"] == []
    assert result["purchase_intent"]["intent_models"] == ["Model Y"]
    assert "Model Y" in result["final_response"]
    assert "指导价" in result["final_response"]
    assert "分期月供" in result["final_response"]
    assert "销售话术" in result["final_response"]
    assert "轿车还是SUV" not in result["final_response"]


def test_named_model_recommendation_does_not_ask_car_type():
    from backend.agent.nodes import slot_fill_node

    result = slot_fill_node({
        "current_intent": "car_recommendation",
        "next_action": "ask_question",
        "customer_profile": {},
        "purchase_intent": {"intent_models": ["Model Y"]},
    })

    assert "car_type" not in result["missing_slots"]
    assert "energy_type" not in result["missing_slots"]
    assert "budget" in result["missing_slots"]


def test_new_sedan_recommendation_clears_stale_model_context():
    from backend.agent.nodes import intent_node, slot_fill_node

    state = {
        "user_message": "推荐30w左右的轿车",
        "purchase_intent": {"intent_models": ["Model Y"], "energy_type": "纯电"},
    }

    intent = intent_node(state)
    filled = slot_fill_node(state | intent | {"customer_profile": {}})

    assert "intent_models" not in filled["purchase_intent"]
    assert "energy_type" not in filled["purchase_intent"]
    assert filled["purchase_intent"]["budget"] == "30万以内"
    assert filled["purchase_intent"]["car_type"] == "轿车"
    assert "car_type" not in filled["missing_slots"]


def test_new_suv_recommendation_does_not_inherit_stale_profile_preferences():
    from backend.agent.nodes import intent_node, slot_fill_node

    state = {
        "user_message": "推荐几款20万以内的SUV",
        "purchase_intent": {"intent_models": ["Model Y"], "energy_type": "纯电", "usage": "轿车"},
        "customer_profile": {
            "intent_models": ["Model Y"],
            "energy_type": "纯电",
            "usage": "轿车",
            "purchase_time": "1个月内",
        },
    }

    intent = intent_node(state)
    filled = slot_fill_node(state | intent)
    purchase_intent = filled["purchase_intent"]

    assert "intent_models" not in purchase_intent
    assert purchase_intent["budget"] == "20万以内"
    assert purchase_intent["car_type"] == "SUV"
    assert purchase_intent.get("energy_type", "") != "纯电"
    assert purchase_intent.get("usage", "") != "轿车"
    assert purchase_intent.get("purchase_time", "") != "1个月内"
    assert filled["missing_slots"] == ["energy_type", "purchase_time"]


def test_two_named_models_with_choice_phrase_routes_to_compare():
    from backend.agent.nodes import intent_node

    result = intent_node({
        "user_message": "宋PLUS和锋兰达怎么选",
        "purchase_intent": {},
    })

    assert result["current_intent"] == "car_compare"
    assert result["next_action"] == "compare_car"
    assert result["purchase_intent"]["intent_models"] == ["宋PLUS DM-i", "锋兰达双擎"]


def test_explicit_compare_routes_to_compare_tool_not_rag():
    from backend.agent.nodes import intent_node

    result = intent_node({
        "user_message": "对比宋PLUS和锋兰达",
        "purchase_intent": {"budget": "20万以内", "car_type": "SUV"},
    })

    assert result["current_intent"] == "car_compare"
    assert result["next_action"] == "compare_car"
    assert result["missing_slots"] == []


def test_follow_up_budget_update_overrides_previous_budget():
    from backend.agent.nodes import intent_node

    result = intent_node({
        "user_message": "30w呢",
        "purchase_intent": {"budget": "20万以内", "car_type": "SUV"},
    })

    assert result["purchase_intent"]["budget"] == "30万以内"
    assert result["next_action"] == "rag_search"


def test_down_payment_follow_up_keeps_loan_intent_not_budget_update():
    from backend.agent.nodes import intent_node

    result = intent_node({
        "user_message": "首付10万分3年",
        "purchase_intent": {"budget": "20万以内", "car_type": "SUV", "intent_models": ["宋PLUS DM-i"]},
    })

    assert result["current_intent"] == "loan_calculation"
    assert result["next_action"] == "loan_calculator"
    assert result["purchase_intent"]["budget"] == "20万以内"


def test_loan_tool_uses_down_payment_amount_not_as_car_price():
    from backend.agent.nodes import response_node, tool_executor

    result = tool_executor({
        "user_message": "首付10万分3年",
        "current_intent": "loan_calculation",
        "next_action": "loan_calculator",
        "purchase_intent": {"budget": "20万以内", "car_type": "SUV", "intent_models": ["宋PLUS DM-i"]},
        "tool_results": {},
        "tool_trace": [],
    })

    loan = result["tool_results"]["loan"]
    trace_input = result["tool_trace"][-1]["input"]

    assert trace_input["car_price"] == 169800
    assert abs(trace_input["down_payment_rate"] - (100000 / 169800)) < 0.000001
    assert loan["down_payment"] == 100000
    assert loan["loan_amount"] == 69800

    reply = response_node({
        "user_message": "首付10万呢",
        "current_intent": "loan_calculation",
        "purchase_intent": {"budget": "20万以内", "car_type": "SUV"},
        "tool_results": result["tool_results"],
        "tool_trace": result["tool_trace"],
    })["final_response"]

    assert "首付" in reply and "¥100,000" in reply
    assert "贷款金额" in reply and "¥69,800" in reply
    assert "首付 30%" not in reply


def test_loan_with_down_payment_missing_term_asks_before_calculating():
    from backend.agent.nodes import ask_question_node, response_node, route_node, slot_fill_node

    state = {
        "user_message": "宋PLUS首付10w",
        "current_intent": "loan_calculation",
        "next_action": "loan_calculator",
        "customer_profile": {},
        "purchase_intent": {"intent_models": ["宋PLUS DM-i"]},
    }

    filled = slot_fill_node(state)
    assert filled["missing_slots"] == ["loan_term"]

    routed = route_node(state | filled)
    assert routed["next_action"] == "ask_question"

    asked = ask_question_node(state | filled | routed)
    reply = response_node(state | filled | routed | asked)["final_response"]
    assert "贷款期限" in reply
    assert "月供" not in reply


def test_loan_tool_uses_named_model_price_for_monthly_payment():
    from backend.agent.nodes import intent_node, tool_executor

    intent = intent_node({
        "user_message": "瑞虎8首付3万分3年月供多少",
        "purchase_intent": {},
    })
    assert intent["current_intent"] == "loan_calculation"
    assert intent["purchase_intent"]["intent_models"] == ["瑞虎8"]

    result = tool_executor({
        "user_message": "瑞虎8首付3万分3年月供多少",
        "current_intent": "loan_calculation",
        "next_action": "loan_calculator",
        "purchase_intent": intent["purchase_intent"],
        "tool_results": {},
        "tool_trace": [],
    })

    trace_input = result["tool_trace"][-1]["input"]
    loan = result["tool_results"]["loan"]

    assert trace_input["car_price"] == 109900
    assert trace_input["model"] == "瑞虎8"
    assert loan["model"] == "瑞虎8"
    assert loan["down_payment"] == 30000
    assert loan["loan_amount"] == 79900


def test_loan_current_message_model_overrides_previous_model_context():
    from backend.agent.nodes import intent_node, tool_executor

    message = "modely\u9996\u4ed810w \u520612\u671f"
    intent = intent_node({
        "user_message": message,
        "purchase_intent": {"intent_models": ["\u5b8bPLUS DM-i"], "budget": "20\u4e07\u4ee5\u5185"},
    })

    assert intent["current_intent"] == "loan_calculation"
    assert intent["purchase_intent"]["intent_models"][0] == "Model Y"

    result = tool_executor({
        "user_message": message,
        "current_intent": "loan_calculation",
        "next_action": "loan_calculator",
        "purchase_intent": intent["purchase_intent"],
        "tool_results": {},
        "tool_trace": [],
    })

    trace_input = result["tool_trace"][-1]["input"]
    loan = result["tool_results"]["loan"]

    assert trace_input["model"] == "Model Y"
    assert trace_input["car_price"] == 249900
    assert trace_input["years"] == 1
    assert loan["model"] == "Model Y"
    assert loan["down_payment"] == 100000
    assert loan["loan_amount"] == 149900


def test_loan_tool_accepts_down_payment_percentage_and_term():
    from backend.agent.nodes import slot_fill_node, tool_executor

    state = {
        "user_message": "宋PLUS首付30%分36期",
        "current_intent": "loan_calculation",
        "next_action": "loan_calculator",
        "customer_profile": {},
        "purchase_intent": {"intent_models": ["宋PLUS DM-i"]},
        "tool_results": {},
        "tool_trace": [],
    }

    filled = slot_fill_node(state)
    assert filled["missing_slots"] == []

    result = tool_executor(state | filled)
    trace_input = result["tool_trace"][-1]["input"]
    loan = result["tool_results"]["loan"]

    assert trace_input["down_payment_rate"] == 0.3
    assert trace_input["years"] == 3
    assert loan["months"] == 36


def test_follow_up_question_mentions_known_budget_and_car_type():
    from backend.agent.nodes import ask_question_node

    reply = ask_question_node({
        "purchase_intent": {"budget": "20万以内", "car_type": "SUV"},
        "missing_slots": ["energy_type"],
    })["final_response"]

    assert "20万以内" in reply
    assert "SUV" in reply
    assert "能源" in reply or "燃油" in reply


def test_recommendation_asks_purchase_time_after_core_slots():
    from backend.agent.nodes import route_node, slot_fill_node, ask_question_node

    state = {
        "user_message": "我想买20万以内SUV，要混动",
        "current_intent": "car_recommendation",
        "next_action": "rag_search",
        "customer_profile": {},
        "purchase_intent": {
            "budget": "20万以内",
            "car_type": "SUV",
            "energy_type": "混动",
        },
    }

    filled = slot_fill_node(state)
    assert filled["missing_slots"] == ["purchase_time"]

    routed = route_node(state | filled)
    assert routed["next_action"] == "ask_question"

    reply = ask_question_node(filled)["final_response"]
    assert "什么时候购车" in reply


def test_purchase_time_follow_up_updates_existing_intent():
    from backend.agent.nodes import intent_node

    result = intent_node({
        "user_message": "这个月内",
        "purchase_intent": {
            "budget": "20万以内",
            "car_type": "SUV",
            "energy_type": "混动",
        },
    })

    assert result["current_intent"] == "car_recommendation"
    assert result["purchase_intent"]["purchase_time"] == "这个月内"


def test_general_question_does_not_force_purchase_slots():
    from backend.agent.nodes import intent_node

    result = intent_node({
        "user_message": "你们这个系统能做什么",
        "purchase_intent": {},
    })

    assert result["current_intent"] == "general_question"
    assert result["next_action"] == "general_response"
    assert result["missing_slots"] == []


def test_sales_material_question_routes_to_rag_not_slot_fill():
    from backend.agent.nodes import intent_node

    result = intent_node({
        "user_message": "价格贵怎么说服客户",
        "purchase_intent": {},
    })

    assert result["current_intent"] == "general_question"
    assert result["next_action"] == "rag_search"
    assert result["missing_slots"] == []


def test_slot_fill_does_not_add_purchase_slots_for_general_response():
    from backend.agent.nodes import slot_fill_node

    result = slot_fill_node({
        "current_intent": "general_question",
        "next_action": "general_response",
        "customer_profile": {},
        "purchase_intent": {},
    })

    assert result["missing_slots"] == []


def test_inventory_query_does_not_force_purchase_slots_or_appointment():
    from backend.agent.nodes import response_node, slot_fill_node

    filled = slot_fill_node({
        "current_intent": "inventory_query",
        "next_action": "inventory_query_action",
        "customer_profile": {},
        "purchase_intent": {},
    })

    assert filled["missing_slots"] == []

    reply = response_node({
        "user_message": "广州有现车吗？",
        "current_intent": "inventory_query",
        "purchase_intent": {"intent_models": ["宋PLUS DM-i"]},
        "tool_results": {
            "inventory": [
                {
                    "model": "宋PLUS DM-i",
                    "city": "广州",
                    "store_name": "广州天河体验店",
                    "color": "白色",
                    "stock_count": 2,
                    "delivery_time": "最快2-3天可提车",
                }
            ]
        },
        "tool_trace": [],
    })["final_response"]

    assert "宋PLUS DM-i" in reply
    assert "广州天河体验店" in reply
    assert "白色" in reply
    assert "预算" not in reply
    assert "试驾" not in reply
    assert "预约" not in reply


def test_inventory_query_without_model_asks_for_target_model():
    from backend.agent.nodes import intent_node, response_node

    result = intent_node({
        "user_message": "有现车吗",
        "purchase_intent": {"budget": "20万以内", "car_type": "SUV"},
    })

    assert result["current_intent"] == "general_question"
    assert result["next_action"] == "general_response"
    assert result["missing_slots"] == []
    assert result["final_response"]
    assert "哪款车" in result["final_response"] or "具体车型" in result["final_response"]

    reply = response_node(result | {"user_message": "有现车吗", "tool_results": {}})["final_response"]
    assert "哪款车" in reply or "具体车型" in reply
    assert "广州白云店" not in reply


def test_short_what_car_question_does_not_trigger_rag_recommendation():
    from backend.agent.nodes import intent_node, response_node

    result = intent_node({
        "user_message": "什么车",
        "purchase_intent": {"budget": "20万以内", "car_type": "SUV"},
    })

    assert result["current_intent"] == "general_question"
    assert result["next_action"] == "general_response"
    assert result["missing_slots"] == []
    assert result["final_response"]

    reply = response_node(result | {"user_message": "什么车", "tool_results": {}})["final_response"]
    assert "你是想问" in reply or "具体车型" in reply
    assert "销售资料" not in reply
    assert "竞品对比" not in reply


def test_acknowledgement_with_existing_purchase_intent_continues_slot_fill():
    from backend.agent.nodes import intent_node

    result = intent_node({
        "user_message": "好的",
        "purchase_intent": {"budget": "20万以内", "car_type": "SUV"},
    })

    assert result["current_intent"] == "car_recommendation"
    assert result["next_action"] == "rag_search"


def test_acknowledgement_with_complete_intent_routes_to_recommendation():
    from backend.agent.nodes import intent_node

    result = intent_node({
        "user_message": "好的",
        "purchase_intent": {
            "budget": "20万以内",
            "car_type": "SUV",
            "energy_type": "混动",
        },
    })

    assert result["current_intent"] == "car_recommendation"
    assert result["next_action"] == "rag_search"


def test_test_drive_missing_contact_does_not_create_fake_appointment():
    from backend.agent.nodes import response_node, tool_executor

    result = tool_executor({
        "user_message": "帮我预约周六下午试驾宋PLUS",
        "current_intent": "test_drive",
        "next_action": "test_drive_action",
        "customer_id": "",
        "purchase_intent": {"intent_models": ["宋PLUS DM-i"]},
        "tool_results": {},
        "tool_trace": [],
    })

    assert result["tool_results"] == {}
    assert result["tool_trace"] == []
    assert "手机号" in result["final_response"]
    assert "姓名" in result["final_response"]
    assert "13800000000" not in result["final_response"]

    reply = response_node(result)["final_response"]
    assert "手机号" in reply


def test_rag_only_response_uses_sales_materials_not_slot_question():
    state = {
        "user_message": "价格贵怎么说服客户",
        "current_intent": "general_question",
        "purchase_intent": {},
        "tool_results": {
            "rag_docs": [
                {
                    "title": "价格异议处理话术",
                    "content": "客户觉得贵时，应先认可客户对价格的关注，再结合配置、油耗和金融方案解释综合价值。",
                }
            ]
        },
        "tool_trace": [],
    }

    reply = response_node(state)["final_response"]

    assert "价格" in reply
    assert "配置" in reply
    assert "预算" not in reply


def test_model_question_with_rag_docs_uses_sales_materials_before_car_search():
    from backend.agent.nodes import response_node

    state = {
        "user_message": "宋PLUS有什么优惠",
        "current_intent": "car_recommendation",
        "purchase_intent": {"intent_models": ["宋PLUS DM-i"]},
        "tool_results": {
            "rag_docs": [
                {
                    "title": "比亚迪宋PLUS DM-i 优惠政策",
                    "content": "当前优惠政策包括置换补贴、2年0息金融方案、免费赠送家用充电桩。",
                }
            ],
            "search_cars": [
                {
                    "brand": "比亚迪",
                    "model": "宋PLUS DM-i",
                    "price": 169800,
                    "energy_type": "插电混动",
                    "fuel_consumption": "4.4 L/100km",
                    "highlights": ["油耗低", "空间大"],
                }
            ],
        },
        "tool_trace": [],
    }

    reply = response_node(state)["final_response"]

    assert "优惠政策" in reply
    assert "置换补贴" in reply
    assert "我会先看这几款" not in reply


def test_model_question_without_rag_docs_uses_grounding_fallback():
    from backend.agent.nodes import response_node

    state = {
        "user_message": "宋PLUS隐藏功能有哪些",
        "current_intent": "car_recommendation",
        "purchase_intent": {"intent_models": ["宋PLUS DM-i"]},
        "tool_results": {"rag_docs": []},
        "tool_trace": [],
    }

    reply = response_node(state)["final_response"]

    assert "目前没有" in reply
    assert "宋PLUS" in reply
    assert "不能直接编" in reply


def test_rag_query_expansion_adds_business_terms():
    from backend.agent.nodes import _expand_rag_query

    expanded = _expand_rag_query("客户嫌宋PLUS价格贵怎么办", ["宋PLUS DM-i"])

    assert "宋PLUS DM-i" in expanded
    assert "价格异议" in expanded
    assert "金融方案" in expanded


def test_tool_executor_handles_rag_exception_with_fallback(monkeypatch=None):
    from backend.agent import nodes

    original = nodes.rag_search_tool

    def broken_rag_search(query, top_k=5):
        raise RuntimeError("boom")

    try:
        nodes.rag_search_tool = broken_rag_search
        result = nodes.tool_executor({
            "user_message": "宋PLUS有什么优惠",
            "current_intent": "car_recommendation",
            "next_action": "rag_search",
            "purchase_intent": {"intent_models": ["宋PLUS DM-i"]},
            "tool_results": {},
            "tool_trace": [],
        })
    finally:
        nodes.rag_search_tool = original

    assert result["tool_results"]["rag_docs"] == []
    assert result["tool_trace"][-1]["tool_name"] == "rag_search_tool"
    assert result["tool_trace"][-1]["output"]["error"] == "fallback"


def test_memory_write_persists_purchase_intent_fields():
    from backend.database import init_db, SessionLocal
    from backend.models.models import Customer, CustomerProfile
    from backend.agent.nodes import memory_write_node

    init_db()
    db = SessionLocal()
    try:
        customer = Customer(name="", phone="")
        db.add(customer)
        db.commit()
        customer_id = customer.id
    finally:
        db.close()

    memory_write_node({
        "customer_id": str(customer_id),
        "user_message": "我想买20万以内SUV",
        "purchase_intent": {
            "budget": "20万以内",
            "car_type": "SUV",
            "energy_type": "混动",
            "intent_models": ["宋PLUS DM-i"],
        },
    })

    db = SessionLocal()
    try:
        profile = db.query(CustomerProfile).filter(
            CustomerProfile.customer_id == customer_id
        ).first()
        assert profile is not None
        assert profile.budget == "20万以内"
        assert profile.car_type == "SUV"
        assert profile.energy_type == "混动"
        assert "宋PLUS DM-i" in (profile.intent_models or [])
    finally:
        db.close()


def test_graph_node_exception_uses_node_specific_fallback():
    from backend.agent import graph

    original_intent_node = graph.intent_node
    graph._agent_graph = None

    def broken_intent_node(state):
        raise RuntimeError("intent down")

    try:
        graph.intent_node = broken_intent_node
        result = graph.run_agent({
            "session_id": "T-NODE-FALLBACK",
            "customer_id": "",
            "user_message": "帮我推荐一款SUV",
            "purchase_intent": {},
        })
    finally:
        graph.intent_node = original_intent_node
        graph._agent_graph = None

    assert "理解您的需求" in result["final_response"]
    assert "稍后再试" in result["final_response"]
    assert result["current_intent"] == "system_error"


def test_inventory_tool_exception_uses_inventory_fallback():
    from backend.agent import nodes

    original_inventory_tool = nodes.inventory_tool

    def broken_inventory_tool(**kwargs):
        raise RuntimeError("inventory down")

    try:
        nodes.inventory_tool = broken_inventory_tool
        result = nodes.tool_executor({
            "user_message": "广州有现车吗",
            "current_intent": "inventory_query",
            "next_action": "inventory_query_action",
            "purchase_intent": {},
            "tool_results": {},
            "tool_trace": [],
        })
    finally:
        nodes.inventory_tool = original_inventory_tool

    reply = response_node(result)["final_response"]
    assert "库存查询暂时不可用" in reply
    assert "实时库存" in reply
    assert result["tool_trace"][-1]["tool_name"] == "inventory_tool"
    assert result["tool_trace"][-1]["output"]["error"] == "fallback"


def test_market_hot_cars_are_seeded_with_aliases():
    from backend.agent.nodes import _extract_known_models
    from backend.seed_data import SEED_CARS

    models = {car["model"] for car in SEED_CARS}

    assert 20 <= len(models) <= 30
    for model in ["理想L6", "问界M7", "小米SU7", "海鸥", "元PLUS", "腾势D9 DM-i"]:
        assert model in models

    found = _extract_known_models("想看看理想L6、问界M7和小米SU7")

    assert "理想L6" in found
    assert "问界M7" in found
    assert "小米SU7" in found


def test_demo_recommendation_flow_calls_car_search_after_complete_slots():
    from backend.agent.nodes import intent_node, route_node, slot_fill_node, tool_executor

    message = "\u63a8\u835020\u4e07\u4ee5\u5185\u6df7\u52a8SUV\uff0c\u8fd9\u4e2a\u6708\u4e70\u8f66"
    state = {
        "user_message": message,
        "purchase_intent": {},
        "customer_profile": {},
        "tool_results": {},
        "tool_trace": [],
    }

    intent = intent_node(state)
    filled = slot_fill_node(state | intent)
    routed = route_node(state | intent | filled)
    result = tool_executor(state | intent | filled | routed)

    tool_names = [item["tool_name"] for item in result["tool_trace"]]
    assert intent["current_intent"] == "car_recommendation"
    assert filled["missing_slots"] == []
    assert routed["next_action"] == "rag_search"
    assert "rag_search_tool" in tool_names
    assert "search_car_tool" in tool_names
    assert result["tool_results"]["search_cars"]


def test_demo_compare_flow_calls_compare_tool():
    from backend.agent.nodes import intent_node, route_node, slot_fill_node, tool_executor

    message = "\u5bf9\u6bd4\u5b8bPLUS\u548c\u950b\u5170\u8fbe"
    state = {
        "user_message": message,
        "purchase_intent": {},
        "customer_profile": {},
        "tool_results": {},
        "tool_trace": [],
    }

    intent = intent_node(state)
    filled = slot_fill_node(state | intent)
    routed = route_node(state | intent | filled)
    result = tool_executor(state | intent | filled | routed)

    assert intent["current_intent"] == "car_compare"
    assert routed["next_action"] == "compare_car"
    assert result["tool_trace"][-1]["tool_name"] == "compare_car_tool"
    assert len(result["tool_results"]["compare"]) >= 2


def test_demo_loan_flow_missing_term_does_not_calculate():
    from backend.agent.nodes import ask_question_node, route_node, slot_fill_node, tool_executor

    state = {
        "user_message": "Model Y\u9996\u4ed810w",
        "current_intent": "loan_calculation",
        "next_action": "loan_calculator",
        "customer_profile": {},
        "purchase_intent": {"intent_models": ["Model Y"]},
        "tool_results": {},
        "tool_trace": [],
    }

    filled = slot_fill_node(state)
    routed = route_node(state | filled)
    asked = ask_question_node(state | filled | routed)
    result = tool_executor(state | filled | routed)

    assert filled["missing_slots"] == ["loan_term"]
    assert routed["next_action"] == "ask_question"
    assert "\u8d37\u6b3e\u671f\u9650" in asked["final_response"]
    assert result["tool_trace"] == []
    assert "loan" not in result["tool_results"]


def test_demo_inventory_follow_up_uses_previous_model_context():
    from backend.agent.nodes import intent_node, route_node, slot_fill_node, tool_executor

    state = {
        "user_message": "\u5e7f\u5dde\u6709\u73b0\u8f66\u5417\uff1f",
        "purchase_intent": {"intent_models": ["\u5b8bPLUS DM-i"]},
        "customer_profile": {},
        "tool_results": {},
        "tool_trace": [],
    }

    intent = intent_node(state)
    filled = slot_fill_node(state | intent)
    routed = route_node(state | intent | filled)
    result = tool_executor(state | intent | filled | routed)

    trace_input = result["tool_trace"][-1]["input"]
    assert intent["current_intent"] == "inventory_query"
    assert routed["next_action"] == "inventory_query_action"
    assert trace_input["model"] == "\u5b8bPLUS DM-i"
    assert trace_input["city"] == "\u5e7f\u5dde"


if __name__ == "__main__":
    test_response_node_preserves_follow_up_question()
    test_recommendation_response_uses_search_results_not_compare_script()
    test_compare_tesla_alias_uses_model_y()
    test_inventory_songplus_alias_queries_real_model()
    test_impossible_tesla_budget_reply_explains_mismatch()
    test_bare_model_alias_introduces_model_not_purchase_slots()
    test_named_model_recommendation_does_not_ask_car_type()
    test_new_sedan_recommendation_clears_stale_model_context()
    test_new_suv_recommendation_does_not_inherit_stale_profile_preferences()
    test_two_named_models_with_choice_phrase_routes_to_compare()
    test_explicit_compare_routes_to_compare_tool_not_rag()
    test_follow_up_budget_update_overrides_previous_budget()
    test_down_payment_follow_up_keeps_loan_intent_not_budget_update()
    test_loan_tool_uses_down_payment_amount_not_as_car_price()
    test_loan_with_down_payment_missing_term_asks_before_calculating()
    test_loan_tool_uses_named_model_price_for_monthly_payment()
    test_loan_current_message_model_overrides_previous_model_context()
    test_loan_tool_accepts_down_payment_percentage_and_term()
    test_follow_up_question_mentions_known_budget_and_car_type()
    test_recommendation_asks_purchase_time_after_core_slots()
    test_purchase_time_follow_up_updates_existing_intent()
    test_general_question_does_not_force_purchase_slots()
    test_sales_material_question_routes_to_rag_not_slot_fill()
    test_slot_fill_does_not_add_purchase_slots_for_general_response()
    test_inventory_query_does_not_force_purchase_slots_or_appointment()
    test_inventory_query_without_model_asks_for_target_model()
    test_short_what_car_question_does_not_trigger_rag_recommendation()
    test_acknowledgement_with_existing_purchase_intent_continues_slot_fill()
    test_acknowledgement_with_complete_intent_routes_to_recommendation()
    test_test_drive_missing_contact_does_not_create_fake_appointment()
    test_rag_only_response_uses_sales_materials_not_slot_question()
    test_model_question_with_rag_docs_uses_sales_materials_before_car_search()
    test_model_question_without_rag_docs_uses_grounding_fallback()
    test_rag_query_expansion_adds_business_terms()
    test_tool_executor_handles_rag_exception_with_fallback()
    test_memory_write_persists_purchase_intent_fields()
    test_graph_node_exception_uses_node_specific_fallback()
    test_inventory_tool_exception_uses_inventory_fallback()
    test_market_hot_cars_are_seeded_with_aliases()
    test_demo_recommendation_flow_calls_car_search_after_complete_slots()
    test_demo_compare_flow_calls_compare_tool()
    test_demo_loan_flow_missing_term_does_not_calculate()
    test_demo_inventory_follow_up_uses_previous_model_context()
    print("agent response checks passed")
