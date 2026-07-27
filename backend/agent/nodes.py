"""
Agent 节点定义
包含完整的 LangGraph 状态节点
"""

import json
from datetime import datetime

from backend.agent.state import SalesAgentState
from backend.agent.tools import TOOL_REGISTRY, search_car_tool, compare_car_tool, \
    loan_calculator_tool, inventory_tool, test_drive_tool, lead_save_tool, rag_search_tool
from backend.llm import chat_completion, extract_json
from backend.database import SessionLocal
from backend.models.models import Customer, CustomerProfile, ConversationMessage


INTENT_SYSTEM_PROMPT = """你是一个汽车销售Agent的意图识别模块。
请分析用户的输入，识别其购车意图，并抽取需求字段。
输出JSON格式：{
  "intent": "car_recommendation | car_compare | loan_calculation | inventory_query | test_drive | general_question | lead_save",
  "slots": {"budget": "", "car_type": "", "energy_type": "", "usage": "", "purchase_time": ""},
  "missing_slots": []
}"""

REPLY_SYSTEM_PROMPT = """你是一个专业的汽车销售顾问。根据客户需求和工具调用结果生成回复。
要求：
- 语气专业、热情、可信
- 不夸大车型能力，不承诺不存在的优惠
- 涉及价格和库存时必须基于工具结果
- 回复自然简洁，引导客户继续沟通
- 如果需要更多信息，礼貌追问"""

MEMORY_SYSTEM_PROMPT = """你是一个客户记忆更新模块。
根据对话内容，提取并更新客户画像信息。
输出JSON格式：{
  "budget": "",
  "usage": "",
  "energy_type": "",
  "concerns": [],
  "intent_models": [],
  "purchase_time": "",
  "follow_up_summary": "",
  "lead_level": "低意向|中意向|高意向"
}"""


def intent_node(state: SalesAgentState) -> dict:
    """意图识别节点"""
    msg = state.get("user_message", "")

    # 用 LLM 识别意图，有 key 走真实调用，无 key 走 mock
    result_text = chat_completion(INTENT_SYSTEM_PROMPT, msg)
    result = extract_json(result_text)

    intent = result.get("intent", "general_question")
    slots = result.get("slots", {})
    missing = result.get("missing_slots", [])

    # 补充默认字段
    purchase_intent = state.get("purchase_intent", {})
    for key, val in slots.items():
        if val and not purchase_intent.get(key):
            purchase_intent[key] = val

    # 根据 intent 和字段完整性决定下一步
    has_critical_info = bool(
        slots.get("budget") and slots.get("car_type")
    )

    if intent == "car_recommendation":
        if has_critical_info:
            next_action = "rag_search"
        else:
            next_action = "ask_question"
    elif intent == "general_question":
        if has_critical_info:
            next_action = "rag_search"
        else:
            next_action = "ask_question"
    elif intent == "car_compare":
        next_action = "compare_car"
    elif intent == "loan_calculation":
        next_action = "loan_calculator"
    elif intent == "inventory_query":
        next_action = "inventory_query_action"
    elif intent == "test_drive":
        next_action = "test_drive_action"
    elif intent == "lead_save":
        next_action = "lead_save"
    else:
        next_action = "rag_search"

    return {
        "current_intent": intent,
        "purchase_intent": purchase_intent,
        "missing_slots": missing,
        "next_action": next_action,
    }


def memory_load_node(state: SalesAgentState) -> dict:
    """加载客户长期记忆"""
    customer_id = state.get("customer_id", "")
    if not customer_id:
        return {"customer_profile": {}}

    db = SessionLocal()
    try:
        customer = db.query(Customer).filter(Customer.id == int(customer_id)).first()
        if not customer:
            return {"customer_profile": {}}

        profile = db.query(CustomerProfile).filter(
            CustomerProfile.customer_id == customer.id
        ).first()

        if profile:
            return {
                "customer_profile": {
                    "budget": profile.budget or "",
                    "car_type": profile.car_type or "",
                    "energy_type": profile.energy_type or "",
                    "usage": profile.usage or "",
                    "concerns": profile.concerns or [],
                    "intent_models": profile.intent_models or [],
                    "purchase_time": profile.purchase_time or "",
                    "lead_level": profile.lead_level or "低意向",
                    "follow_up_summary": profile.follow_up_summary or "",
                }
            }
        return {"customer_profile": {}}
    finally:
        db.close()


def slot_fill_node(state: SalesAgentState) -> dict:
    """需求补全节点 — 合并现有信息，判断缺失"""
    profile = state.get("customer_profile", {})
    intent = state.get("purchase_intent", {})

    # 从画像补充缺失字段
    for key in ("budget", "car_type", "energy_type", "usage", "purchase_time"):
        if not intent.get(key) and profile.get(key):
            intent[key] = profile[key]

    # 重新计算缺失字段
    required = ["budget", "car_type", "energy_type"]
    missing = [k for k in required if not intent.get(k)]

    return {
        "purchase_intent": intent,
        "missing_slots": missing,
    }


def route_node(state: SalesAgentState) -> dict:
    """路由节点 — 判断下一步该调用哪个工具"""
    action = state.get("next_action", "rag_search")
    missing = state.get("missing_slots", [])

    # 仅当意图不明且完全缺失关键信息时转为追问
    intent = state.get("current_intent", "")
    if action == "rag_search" and intent in ("general_question",) and len(missing) >= 3:
        return {"next_action": "ask_question"}

    return {"next_action": action}


def ask_question_node(state: SalesAgentState) -> dict:
    """追问节点 — 生成追问问题"""
    missing = state.get("missing_slots", [])
    intent = state.get("purchase_intent", {})

    questions = []
    slot_labels = {
        "budget": "您的购车预算大概是多少？",
        "car_type": "您想买轿车还是SUV？",
        "energy_type": "您倾向燃油、混动还是纯电？",
        "usage": "主要用途是家用还是商务？",
        "purchase_time": "您计划什么时候购车？",
    }

    for slot in missing:
        if slot in slot_labels:
            questions.append(slot_labels[slot])

    if not questions:
        questions.append("请问您对车型还有哪些具体要求？我可以帮您做精准推荐。")

    reply = "要推荐得更准，我还需要确认这几项：\n" + "\n".join(f"- {q}" for q in questions[:3])

    return {"final_response": reply}


def tool_executor(state: SalesAgentState) -> dict:
    """通用工具执行器节点"""
    action = state.get("next_action", "")
    trace = state.get("tool_trace", [])
    results = state.get("tool_results", {})

    intent = state.get("purchase_intent", {})

    tool_map = {
        "rag_search": ("rag_search_tool", rag_search_tool, {
            "query": state.get("user_message", ""),
            "top_k": 5,
        }),
        "compare_car": ("compare_car_tool", compare_car_tool, {
            "models": [],  # 从消息中提取
        }),
        "loan_calculator": ("loan_calculator_tool", loan_calculator_tool, {
            "car_price": 169800,
            "down_payment_rate": 0.3,
            "years": 3,
            "annual_rate": 0.045,
        }),
        "inventory_query_action": ("inventory_tool", inventory_tool, {
            "model": "",
            "city": "",
        }),
        "test_drive_action": ("test_drive_tool", test_drive_tool, {
            "customer_name": "",
            "phone": "",
            "model": "",
            "store": "",
            "appointment_time": "",
        }),
        "lead_save": ("lead_save_tool", lead_save_tool, {
            "budget": intent.get("budget", ""),
            "intent_models": intent.get("intent_models", []),
            "concerns": intent.get("concerns", []),
            "purchase_time": intent.get("purchase_time", ""),
            "follow_up_summary": f"客户咨询：{state.get('user_message', '')[:100]}",
        }),
    }

    if action not in tool_map:
        return {"tool_results": results, "tool_trace": trace}

    tool_name, tool_func, default_params = tool_map[action]

    # 根据消息内容动态填充参数
    msg = state.get("user_message", "").lower()
    purchase_intent = state.get("purchase_intent", {})

    if action == "search_car" or action == "rag_search":
        # 尝试提取预算
        budget_max = 0
        import re
        budget_match = re.search(r"(\d+)\s*万", msg)
        if budget_match:
            budget_max = int(budget_match.group(1)) * 10000
        elif purchase_intent.get("budget"):
            b = purchase_intent["budget"]
            bm = re.search(r"(\d+)", b)
            if bm:
                budget_max = int(bm.group(1)) * 10000

        # 构建搜索参数（去掉RAG专用的query和top_k）
        valid_energy_types = ["燃油", "混动", "纯电", "插电混动", "油电混动", "插混", "双擎"]
        raw_energy = purchase_intent.get("energy_type", "")

        # 从消息中重新提取能源类型（避免 LLM 把"省油"等关注点填入 energy_type）
        energy_type = ""
        for et in valid_energy_types:
            if et in msg:
                energy_type = et
                break
        if not energy_type:
            # 从 purchase_intent 取，但必须是有效值
            for et in valid_energy_types:
                if et in raw_energy:
                    energy_type = et
                    break

        search_params = {
            "budget_max": budget_max,
            "car_type": purchase_intent.get("car_type", ""),
            "energy_type": energy_type,
        }

        # 先调RAG再调车型搜索
        rag_result = rag_search_tool(msg)
        if rag_result.get("docs"):
            results["rag_docs"] = rag_result["docs"]
            trace.append({
                "tool_name": "rag_search_tool",
                "input": {"query": msg, "top_k": 5},
                "output": {"docs_count": len(rag_result["docs"])},
                "timestamp": datetime.now().isoformat(),
            })

        car_result = search_car_tool(**search_params)
        results["search_cars"] = car_result.get("cars", [])
        trace.append({
            "tool_name": "search_car_tool",
            "input": search_params,
            "output": {"cars_count": len(car_result.get("cars", []))},
            "timestamp": datetime.now().isoformat(),
        })

    elif action == "compare_car":
        # 从消息中提取车型名
        import re
        # 匹配消息中的车型关键词
        known_models = ["宋PLUS DM-i", "锋兰达双擎", "哈弗枭龙MAX", "秦PLUS DM-i",
                        "CR-V e:HEV", "星越L", "Model Y", "小鹏G6"]
        found = [m for m in known_models if m.lower() in msg]
        if not found:
            found = ["宋PLUS DM-i", "锋兰达双擎"]

        compare_result = compare_car_tool(found)
        results["compare"] = compare_result.get("cars", [])
        trace.append({
            "tool_name": "compare_car_tool",
            "input": {"models": found},
            "output": {"cars_count": len(compare_result.get("cars", []))},
            "timestamp": datetime.now().isoformat(),
        })

    elif action == "loan_calculator":
        # 从消息中提取车价
        import re
        price = 169800  # 默认宋PLUS
        price_match = re.search(r"(\d+)\s*万", msg)
        if price_match:
            price = int(price_match.group(1)) * 10000

        default_params["car_price"] = price
        loan_result = loan_calculator_tool(**default_params)
        results["loan"] = loan_result
        trace.append({
            "tool_name": "loan_calculator_tool",
            "input": default_params,
            "output": loan_result,
            "timestamp": datetime.now().isoformat(),
        })

    elif action == "inventory_query_action":
        # 提取车型和城市
        import re
        car_model = purchase_intent.get("intent_models", [""])[0] if purchase_intent.get("intent_models") else ""
        city = ""

        if not car_model:
            known_models = ["宋PLUS DM-i", "锋兰达双擎", "哈弗枭龙MAX", "秦PLUS DM-i"]
            for m in known_models:
                if m.lower() in msg:
                    car_model = m
                    break

        city_match = re.search(r"(广州|深圳|上海|北京|成都|杭州|武汉)", msg)
        if city_match:
            city = city_match.group(1)

        default_params["model"] = car_model
        default_params["city"] = city
        inv_result = inventory_tool(**default_params)
        results["inventory"] = inv_result.get("results", [])
        trace.append({
            "tool_name": "inventory_tool",
            "input": default_params,
            "output": {"results_count": len(inv_result.get("results", []))},
            "timestamp": datetime.now().isoformat(),
        })

    elif action == "test_drive_action":
        # 提取试驾信息
        import re
        car_model = ""
        known_models = ["宋PLUS DM-i", "锋兰达双擎", "哈弗枭龙MAX", "秦PLUS DM-i"]
        for m in known_models:
            if m.lower() in msg:
                car_model = m
                break

        store_match = re.search(r"(广州天河体验店|广州白云店|深圳南山店)", msg)
        store = store_match.group(1) if store_match else "广州天河体验店"
        time_match = re.search(r"(周六|周日|下周一|明天|今天)(.*?)(点|半)", msg)
        time_str = time_match.group(0) + "试驾" if time_match else "周六下午3点"

        default_params["model"] = car_model or "宋PLUS DM-i"
        default_params["store"] = store
        default_params["appointment_time"] = time_str

        # 尝试从客户画像获取姓名和电话
        customer_id = state.get("customer_id", "")
        if customer_id:
            db = SessionLocal()
            try:
                customer = db.query(Customer).filter(Customer.id == int(customer_id)).first()
                if customer:
                    default_params["customer_name"] = customer.name or ""
                    default_params["phone"] = customer.phone or ""
            finally:
                db.close()

        if not default_params.get("customer_name"):
            default_params["customer_name"] = "张先生"
            default_params["phone"] = "13800000000"

        drive_result = test_drive_tool(**default_params)
        results["test_drive"] = drive_result
        trace.append({
            "tool_name": "test_drive_tool",
            "input": {k: v for k, v in default_params.items()},
            "output": drive_result,
            "timestamp": datetime.now().isoformat(),
        })

        # 试驾后自动保存线索
        lead_params = {
            "customer_id": drive_result.get("customer_id", 0),
            "budget": purchase_intent.get("budget", ""),
            "intent_models": purchase_intent.get("intent_models", [car_model]),
            "concerns": purchase_intent.get("concerns", []),
            "purchase_time": purchase_intent.get("purchase_time", ""),
            "follow_up_summary": f"已预约试驾 {car_model}，时间：{time_str}",
        }
        lead_result = lead_save_tool(**lead_params)
        results["lead_save"] = lead_result
        trace.append({
            "tool_name": "lead_save_tool",
            "input": lead_params,
            "output": lead_result,
            "timestamp": datetime.now().isoformat(),
        })

    return {
        "tool_results": results,
        "tool_trace": trace,
        "needs_memory_update": True,
    }


def response_node(state: SalesAgentState) -> dict:
    """回复生成节点"""
    trace = state.get("tool_trace", [])
    results = state.get("tool_results", {})
    msg = state.get("user_message", "")
    purchase_intent = state.get("purchase_intent", {})

    # 构建回复上下文
    context_parts = [f"客户消息：{msg}"]

    if results.get("search_cars"):
        cars = results["search_cars"]
        context_parts.append(f"推荐车型 ({len(cars)}款)：")
        for c in cars[:5]:
            highlights = "、".join(c.get("highlights", [])[:3])
            context_parts.append(f"- {c['brand']} {c['model']} ¥{c['price']:.0f} {c['energy_type']} {highlights}")

    if results.get("compare"):
        context_parts.append("对比结果：")
        for c in results["compare"]:
            context_parts.append(f"- {c['brand']} {c['model']}: ¥{c['price']:.0f}, {c['energy_type']}, {c.get('recommendation', '')}")

    if results.get("loan"):
        l = results["loan"]
        context_parts.append(
            f"分期试算结果：首付¥{l['down_payment']:.0f}，贷款¥{l['loan_amount']:.0f}，"
            f"月供¥{l['monthly_payment']:.0f}，总利息¥{l['total_interest']:.0f}"
        )

    if results.get("inventory"):
        for inv in results["inventory"]:
            context_parts.append(f"库存：{inv['city']} {inv['store_name']} {inv['color']} "
                                 f"{'有现车' if inv['stock_count'] > 0 else '暂无库存'} {inv['delivery_time']}")

    if results.get("test_drive"):
        td = results["test_drive"]
        context_parts.append(f"试驾预约：{td.get('status', '')} 编号{td.get('appointment_id', '')}")

    if results.get("rag_docs"):
        context_parts.append("知识库参考信息：")
        for d in results["rag_docs"][:3]:
            context_parts.append(f"- {d.get('title', '')}: {d.get('content', '')[:100]}")

    context = "\n".join(context_parts)

    # 用 LLM 生成回复
    reply_text = chat_completion(REPLY_SYSTEM_PROMPT, context)

    # 如果 LLM 返回 JSON 格式，提取 reply 字段
    try:
        parsed = json.loads(reply_text)
        if isinstance(parsed, dict) and "reply" in parsed:
            reply_text = parsed["reply"]
    except (json.JSONDecodeError, TypeError):
        pass

    return {"final_response": reply_text}


def memory_write_node(state: SalesAgentState) -> dict:
    """记忆更新节点 — 写入长期记忆"""
    customer_id = state.get("customer_id", "")
    if not customer_id:
        return {}

    # 用 LLM 提取记忆信息
    msg = state.get("user_message", "")
    result_text = chat_completion(MEMORY_SYSTEM_PROMPT, msg)
    memory_update = extract_json(result_text)

    db = SessionLocal()
    try:
        customer = db.query(Customer).filter(Customer.id == int(customer_id)).first()
        if not customer:
            return {}

        profile = db.query(CustomerProfile).filter(
            CustomerProfile.customer_id == customer.id
        ).first()
        if not profile:
            profile = CustomerProfile(customer_id=customer.id)
            db.add(profile)

        # 更新字段
        for field in ("budget", "usage", "energy_type", "purchase_time", "follow_up_summary", "lead_level"):
            if memory_update.get(field):
                setattr(profile, field, memory_update[field])

        if memory_update.get("concerns"):
            existing = set(profile.concerns or [])
            existing.update(memory_update["concerns"])
            profile.concerns = list(existing)

        if memory_update.get("intent_models"):
            existing = set(profile.intent_models or [])
            existing.update(memory_update["intent_models"])
            profile.intent_models = list(existing)

        db.commit()
        return {}
    finally:
        db.close()
