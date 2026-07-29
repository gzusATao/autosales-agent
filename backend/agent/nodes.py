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
from backend.models.models import Car, Customer, CustomerProfile, ConversationMessage


TOOL_FALLBACK_REPLIES = {
    "search_car_tool": "抱歉，当前车型库查询暂时不可用，我不能可靠地推荐车型。你可以稍后再试，或先补充预算、车型偏好和用途。",
    "compare_car_tool": "抱歉，当前车型对比工具暂时不可用，我不能可靠地给出对比结论。你可以稍后再试，或先换成具体车型资料问题。",
    "loan_calculator_tool": "抱歉，当前分期试算暂时不可用，我先不估算月供，避免给你不准确的金额。你可以稍后再试。",
    "inventory_tool": "抱歉，当前库存查询暂时不可用，我不能确认现车情况。你可以稍后再查，或联系门店确认实时库存。",
    "test_drive_tool": "抱歉，当前试驾预约系统暂时不可用，暂时没能创建试驾预约。你可以稍后再试，或先留下姓名和手机号，方便门店跟进确认。",
    "lead_save_tool": "抱歉，当前线索保存暂时不可用，但我已经收到你的需求。请稍后再试，或让销售顾问手动跟进。",
}


INTENT_SYSTEM_PROMPT = """你是一个汽车销售Agent的意图识别模块。
请分析用户的输入，识别其购车意图，并抽取需求字段。
输出JSON格式：{
  "intent": "car_recommendation | car_compare | loan_calculation | inventory_query | test_drive | general_question | lead_save",
  "slots": {"budget": "", "car_type": "", "energy_type": "", "usage": "", "purchase_time": "", "intent_models": []},
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
    msg_lower = msg.lower()

    inferred_models = _extract_known_models(msg_lower)
    inferred_budget = _extract_budget_text(msg_lower)
    inferred_purchase_time = _extract_purchase_time_text(msg_lower)
    finance_like = _is_finance_query(msg_lower)
    compare_like = _is_compare_query(msg_lower)
    prior_purchase_intent = state.get("purchase_intent", {})
    if _is_ambiguous_model_question(msg_lower):
        return {
            "current_intent": "general_question",
            "purchase_intent": prior_purchase_intent,
            "missing_slots": [],
            "next_action": "general_response",
            "final_response": _build_ambiguous_model_reply(),
        }
    if (
        _is_inventory_query(msg_lower)
        and not inferred_models
        and not prior_purchase_intent.get("intent_models")
    ):
        return {
            "current_intent": "general_question",
            "purchase_intent": prior_purchase_intent,
            "missing_slots": [],
            "next_action": "general_response",
            "final_response": "你想查哪款车的现车？请直接告诉我具体车型，比如“宋PLUS DM-i有现车吗”或“瑞虎8广州有现车吗”，我再按门店库存帮你确认。",
        }
    if _is_acknowledgement(msg_lower) and state.get("purchase_intent"):
        intent = "car_recommendation"
        missing = []
    if finance_like:
        intent = "loan_calculation"
        missing = []
        slots["budget"] = ""
    elif inferred_budget:
        slots["budget"] = inferred_budget
        if "budget" in missing:
            missing.remove("budget")
        if state.get("purchase_intent"):
            intent = "car_recommendation"
    if inferred_models and not slots.get("intent_models"):
        slots["intent_models"] = inferred_models
    if inferred_purchase_time:
        slots["purchase_time"] = inferred_purchase_time
        if "purchase_time" in missing:
            missing.remove("purchase_time")
        if prior_purchase_intent:
            intent = "car_recommendation"
    if compare_like and len(inferred_models) >= 2:
        intent = "car_compare"
        missing = []
    elif inferred_models and intent == "general_question":
        intent = "car_recommendation"
    if _is_sales_material_query(msg_lower) and intent == "general_question":
        intent = "general_question"
        missing = []

    # 补充默认字段
    purchase_intent = state.get("purchase_intent", {})
    for key, val in slots.items():
        if key == "intent_models" and val:
            existing = purchase_intent.get(key, [])
            purchase_intent[key] = list(dict.fromkeys([*existing, *val]))
        elif val:
            purchase_intent[key] = val

    # 根据 intent 和字段完整性决定下一步
    has_critical_info = bool(
        (slots.get("budget") or purchase_intent.get("budget"))
        and (slots.get("car_type") or purchase_intent.get("car_type"))
    )

    action_intents = {"inventory_query", "test_drive", "loan_calculation", "lead_save"}
    if intent == "car_compare":
        next_action = "compare_car"
    elif intent not in action_intents and _should_force_rag_grounding(msg_lower, purchase_intent):
        next_action = "rag_search"
        missing = []
    elif intent == "car_recommendation":
        has_named_model = bool(purchase_intent.get("intent_models"))
        has_budget = bool(purchase_intent.get("budget") or slots.get("budget"))
        if has_critical_info or (has_named_model and has_budget):
            next_action = "rag_search"
        else:
            next_action = "ask_question"
    elif intent == "general_question":
        if _is_sales_material_query(msg_lower):
            next_action = "rag_search"
        elif has_critical_info:
            next_action = "rag_search"
        else:
            next_action = "general_response"
            missing = []
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
    current_intent = state.get("current_intent", "")
    next_action = state.get("next_action", "")

    if current_intent == "loan_calculation":
        missing = _missing_loan_slots(state.get("user_message", ""), intent)
        return {
            "purchase_intent": intent,
            "missing_slots": missing,
        }

    transactional_intents = {"inventory_query", "test_drive", "lead_save"}
    if current_intent in transactional_intents:
        return {
            "purchase_intent": intent,
            "missing_slots": [],
        }

    if current_intent == "general_question" and next_action in ("general_response", "rag_search"):
        return {
            "purchase_intent": intent,
            "missing_slots": [],
        }

    # 从画像补充缺失字段
    for key in ("budget", "car_type", "energy_type", "usage", "purchase_time"):
        if not intent.get(key) and profile.get(key):
            intent[key] = profile[key]

    # 重新计算缺失字段。购车周期是体验友好的轻量追问项：
    # 简单咨询不问；识别出购车推荐需求后，和核心槽位一起一次性追问。
    required = ["budget", "car_type", "energy_type"]
    missing = [k for k in required if not intent.get(k)]
    if current_intent == "car_recommendation" and not intent.get("purchase_time"):
        missing.append("purchase_time")

    return {
        "purchase_intent": intent,
        "missing_slots": missing,
    }


def _extract_compare_models(message: str) -> list[str]:
    """Extract supported car models from explicit model names or common brand aliases."""
    return _extract_known_models(message)


def _extract_known_models(message: str) -> list[str]:
    """Extract supported car models from explicit names or common brand aliases."""
    normalized = message.lower()
    alias_map = [
        ("Model Y", ["model y", "特斯拉", "tesla"]),
        ("小鹏G6", ["小鹏g6", "小鹏", "xpeng", "g6"]),
        ("宋PLUS DM-i", ["宋plus dm-i", "宋plus", "比亚迪宋", "比亚迪", "宋"]),
        ("锋兰达双擎", ["锋兰达双擎", "锋兰达", "丰田"]),
        ("哈弗枭龙MAX", ["哈弗枭龙max", "枭龙max", "枭龙", "哈弗"]),
        ("秦PLUS DM-i", ["秦plus dm-i", "秦plus", "比亚迪秦", "秦"]),
        ("CR-V e:HEV", ["cr-v e:hev", "crv", "cr-v", "本田"]),
        ("星越L", ["星越l", "星越", "吉利"]),
        ("海鸥", ["海鸥", "比亚迪海鸥"]),
        ("元PLUS", ["元plus", "元 plus", "比亚迪元plus", "元plus ev"]),
        ("元UP", ["元up", "元 up", "比亚迪元up"]),
        ("宋Pro DM-i", ["宋pro dm-i", "宋pro", "比亚迪宋pro"]),
        ("宋L DM-i", ["宋l dm-i", "宋l", "比亚迪宋l"]),
        ("海豹06 DM-i", ["海豹06", "海豹 06", "海豹06 dm-i", "比亚迪海豹06"]),
        ("银河星愿", ["银河星愿", "星愿", "吉利星愿"]),
        ("银河E5", ["银河e5", "吉利银河e5", "e5"]),
        ("博越L", ["博越l", "博越", "吉利博越"]),
        ("理想L6", ["理想l6", "l6", "理想"]),
        ("问界M7", ["问界m7", "m7", "aito m7"]),
        ("问界M9", ["问界m9", "m9", "aito m9"]),
        ("小米SU7", ["小米su7", "su7", "小米汽车"]),
        ("零跑C10", ["零跑c10", "c10", "零跑"]),
        ("腾势D9 DM-i", ["腾势d9", "d9", "腾势d9 dm-i"]),
        ("瑞虎8", ["瑞虎8", "奇瑞瑞虎8", "tiggo 8"]),
        ("CS75 PLUS", ["cs75 plus", "cs75", "长安cs75"]),
    ]

    found: list[str] = []
    for model, aliases in alias_map:
        if any(alias in normalized for alias in aliases):
            found.append(model)
    return found


def _first_known_model(message: str, purchase_intent: dict | None = None) -> str:
    """Return the best single model name for tool inputs."""
    purchase_intent = purchase_intent or {}
    intent_models = purchase_intent.get("intent_models") or []
    if intent_models:
        return intent_models[0]
    models = _extract_known_models(message)
    return models[0] if models else ""


def _extract_purchase_time_text(message: str) -> str:
    """Extract common purchase-cycle expressions with deterministic rules."""
    normalized = message.lower()
    time_aliases = [
        ("马上/尽快", ["马上", "立刻", "尽快", "急着买", "马上买", "近期就买"]),
        ("本周/周末", ["本周", "这周", "周末", "星期六", "星期天", "礼拜六", "礼拜天"]),
        ("这个月内", ["这个月", "本月", "月内", "一个月内", "1个月内", "月底", "月底前"]),
        ("三个月内", ["三个月内", "3个月内", "两三个月", "2-3个月", "2到3个月"]),
        ("半年内", ["半年内", "6个月内", "六个月内"]),
        ("年底前", ["年底", "年前", "春节前", "过年前"]),
        ("先看看", ["先看看", "不着急", "以后再说", "明年", "暂时不买"]),
    ]
    for label, aliases in time_aliases:
        if any(alias in normalized for alias in aliases):
            return label
    return ""


def _is_sales_material_query(message: str) -> bool:
    """Identify questions better answered from sales materials than slot filling."""
    keywords = [
        "优惠", "政策", "价格贵", "说服", "话术", "怎么解释", "区别",
        "保值", "质保", "金融方案", "置换", "充电桩",
    ]
    return any(keyword in message for keyword in keywords)


def _is_compare_query(message: str) -> bool:
    """Identify comparison or choice wording."""
    keywords = ["对比", "比较", "区别", "哪个好", "怎么选", "选哪个", "vs"]
    return any(keyword in message for keyword in keywords)


def _is_finance_query(message: str) -> bool:
    """Identify loan or down-payment follow-up wording."""
    keywords = ["月供", "首付", "贷款", "分期", "还款", "利息"]
    return any(keyword in message for keyword in keywords)


def _is_inventory_query(message: str) -> bool:
    """Identify inventory questions that need a concrete model."""
    keywords = ["现车", "库存", "有车", "提车", "可提"]
    return any(keyword in message for keyword in keywords)


def _is_ambiguous_model_question(message: str) -> bool:
    """Short model-reference questions should clarify context instead of guessing."""
    normalized = message.strip().lower().replace("？", "").replace("?", "")
    return normalized in {"什么车", "啥车", "哪款车", "哪个车", "什么车型", "哪款车型"}


def _build_ambiguous_model_reply() -> str:
    return (
        "你是想问刚才提到的是哪款车，还是想让我按你的预算重新推荐车型？"
        "如果是查库存或月供，请直接说具体车型，比如“瑞虎8有现车吗”或“宋PLUS月供多少”；"
        "如果是想推荐，我可以继续按预算、用途和能源偏好帮你筛。"
    )


def _is_acknowledgement(message: str) -> bool:
    """Short confirmation phrases should continue the existing buying context."""
    normalized = message.strip().lower()
    return normalized in {"好", "好的", "可以", "行", "嗯", "继续", "还有吗", "再推荐", "再看看"}


def _should_force_rag_grounding(message: str, purchase_intent: dict | None = None) -> bool:
    """Model-specific questions must be grounded in retrieved sales materials."""
    purchase_intent = purchase_intent or {}
    if not _has_model_context(message, purchase_intent):
        return False
    pure_purchase_phrases = ["我想买", "想买", "买一辆", "买个", "入手"]
    if any(phrase in message for phrase in pure_purchase_phrases) and not _has_budget_mention(message):
        return False
    return True


def _has_budget_mention(message: str) -> bool:
    """Return whether the message includes a simple budget expression."""
    return bool(_extract_budget_text(message))


def _extract_budget_text(message: str) -> str:
    """Extract common budget expressions such as 20万, 30w or 30W."""
    import re

    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:万|w)", message.lower())
    if not match:
        return ""

    raw_value = match.group(1)
    value = raw_value.rstrip("0").rstrip(".") if "." in raw_value else raw_value
    return f"{value}万以内"


def _extract_down_payment_amount(message: str) -> int:
    """Extract explicit down-payment amount in yuan from messages like 首付10万."""
    import re

    match = re.search(r"首付\s*(\d+(?:\.\d+)?)\s*(?:万|w)", message.lower())
    if not match:
        return 0
    return int(float(match.group(1)) * 10000)


def _extract_down_payment_rate(message: str) -> float:
    """Extract down-payment percentage from messages like 首付30%."""
    import re

    match = re.search(r"首付\s*(\d+(?:\.\d+)?)\s*%", message.lower())
    if not match:
        return 0.0
    rate = float(match.group(1)) / 100
    return rate if 0 < rate <= 1 else 0.0


def _extract_loan_years(message: str) -> int:
    """Extract explicit loan term from messages like 分3年 or 36期."""
    import re

    normalized = message.lower()
    year_match = re.search(r"(?:分期|贷款|贷|分)?\s*(\d+)\s*年", normalized)
    if year_match:
        years = int(year_match.group(1))
        return years if 1 <= years <= 5 else 0

    month_match = re.search(r"(\d+)\s*(?:期|个月|月)", normalized)
    if month_match:
        months = int(month_match.group(1))
        if months % 12 == 0:
            years = months // 12
            return years if 1 <= years <= 5 else 0

    chinese_years = {
        "一年": 1,
        "两年": 2,
        "二年": 2,
        "三年": 3,
        "四年": 4,
        "五年": 5,
    }
    for text, years in chinese_years.items():
        if text in normalized:
            return years
    return 0


def _has_explicit_car_price(message: str) -> bool:
    """Return whether the message provides a car price for loan calculation."""
    import re

    lowered = message.lower()
    if "首付" in lowered:
        lowered = re.sub(r"首付\s*\d+(?:\.\d+)?\s*(?:万|w)", "", lowered)
    return bool(re.search(r"(?:车价|裸车价|总价|价格)\s*\d+(?:\.\d+)?\s*(?:万|w)", lowered))


def _missing_loan_slots(message: str, purchase_intent: dict | None = None) -> list[str]:
    """Validate required fields before running the loan calculator."""
    purchase_intent = purchase_intent or {}
    missing = []
    if not _first_known_model(message, purchase_intent) and not _has_explicit_car_price(message):
        missing.append("loan_model")
    if not _extract_down_payment_amount(message) and not _extract_down_payment_rate(message):
        missing.append("loan_down_payment")
    if not _extract_loan_years(message):
        missing.append("loan_term")
    return missing


def _lookup_model_price(model: str) -> int:
    """Return the local car library price for an exact model name."""
    if not model:
        return 0
    db = SessionLocal()
    try:
        car = db.query(Car).filter(Car.model == model).first()
        return int(car.price) if car and car.price else 0
    finally:
        db.close()


def _complete_compare_models(models: list[str], purchase_intent: dict) -> list[str]:
    """When the user names only one car, add a sensible competitor for demo comparison."""
    if len(models) >= 2:
        return models[:4]

    car_type = str(purchase_intent.get("car_type", ""))
    budget = str(purchase_intent.get("budget", ""))
    competitor_map = {
        "Model Y": "小鹏G6",
        "小鹏G6": "Model Y",
        "宋PLUS DM-i": "锋兰达双擎",
        "锋兰达双擎": "宋PLUS DM-i",
        "哈弗枭龙MAX": "宋PLUS DM-i",
        "秦PLUS DM-i": "宋PLUS DM-i",
        "CR-V e:HEV": "锋兰达双擎",
        "星越L": "锋兰达双擎",
    }

    if len(models) == 1:
        model = models[0]
        competitor = competitor_map.get(model, "宋PLUS DM-i")
        return [model, competitor] if competitor != model else [model]

    if "SUV" in car_type.upper():
        return ["宋PLUS DM-i", "锋兰达双擎"]
    if "10" in budget or "15" in budget:
        return ["秦PLUS DM-i", "宋PLUS DM-i"]
    return ["宋PLUS DM-i", "锋兰达双擎"]


def route_node(state: SalesAgentState) -> dict:
    """路由节点 — 判断下一步该调用哪个工具"""
    action = state.get("next_action", "rag_search")
    missing = state.get("missing_slots", [])

    # 仅当意图不明且完全缺失关键信息时转为追问
    intent = state.get("current_intent", "")
    if action == "rag_search" and _is_sales_material_query(state.get("user_message", "").lower()):
        return {"next_action": "rag_search"}
    if intent == "loan_calculation" and missing:
        return {"next_action": "ask_question"}
    if action == "rag_search" and intent == "car_recommendation" and missing:
        return {"next_action": "ask_question"}
    if action == "rag_search" and intent in ("general_question",) and len(missing) >= 3:
        return {"next_action": "ask_question"}

    return {"next_action": action}


def ask_question_node(state: SalesAgentState) -> dict:
    """追问节点 — 生成追问问题"""
    missing = state.get("missing_slots", [])
    intent = state.get("purchase_intent", {})

    questions = []
    slot_labels = {
        "loan_model": "请确认要试算哪款车型，或直接告诉我裸车价。",
        "loan_down_payment": "请确认首付金额，比如首付10万。",
        "loan_term": "请确认贷款期限，比如分3年或36期。",
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

    known_parts = []
    if intent.get("budget"):
        known_parts.append(intent["budget"])
    if intent.get("car_type"):
        known_parts.append(intent["car_type"])
    if intent.get("intent_models"):
        known_parts.append("、".join(intent["intent_models"][:2]))

    if state.get("current_intent") == "loan_calculation":
        if known_parts:
            intro = f"目前我先按{'、'.join(known_parts)}这个方案理解。计算分期前，还需要确认："
        else:
            intro = "计算分期前，还需要确认："
    elif known_parts:
        intro = f"目前我先按{'、'.join(known_parts)}这个方向理解。要推荐得更准，我再确认一下："
    else:
        intro = "要推荐得更准，我还需要确认这几项："

    reply = intro + "\n" + "\n".join(f"- {q}" for q in questions[:3])

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

    def tool_fallback(name: str, params: dict, exc: Exception) -> dict:
        print(f"[Tool Error] {name}: {exc}")
        trace.append({
            "tool_name": name,
            "input": dict(params),
            "output": {"error": "fallback"},
            "timestamp": datetime.now().isoformat(),
        })
        return {
            "tool_results": results,
            "tool_trace": trace,
            "final_response": TOOL_FALLBACK_REPLIES.get(
                name,
                "抱歉，相关业务工具暂时不可用，请稍后再试。",
            ),
            "needs_memory_update": True,
        }

    if action == "search_car" or action == "rag_search":
        # 尝试提取预算
        budget_max = 0
        import re
        budget_text = _extract_budget_text(msg)
        if budget_text:
            budget_max = int(float(budget_text.replace("万以内", ""))) * 10000
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

        model_related = _has_model_context(msg, purchase_intent)
        expanded_query = _expand_rag_query(msg, purchase_intent.get("intent_models", []))

        try:
            rag_result = rag_search_tool(expanded_query, top_k=20)
            rag_docs = rag_result.get("docs", [])
        except Exception as exc:
            print(f"[RAG Tool Error] {exc}")
            rag_docs = []
            trace.append({
                "tool_name": "rag_search_tool",
                "input": {"query": expanded_query, "top_k": 20},
                "output": {"docs_count": 0, "error": "fallback"},
                "timestamp": datetime.now().isoformat(),
            })
        else:
            trace.append({
                "tool_name": "rag_search_tool",
                "input": {"query": expanded_query, "top_k": 20},
                "output": {"docs_count": len(rag_docs)},
                "timestamp": datetime.now().isoformat(),
            })

        results["rag_docs"] = rag_docs
        if model_related:
            results["requires_rag_grounding"] = True

        if model_related or _is_sales_material_query(msg):
            return {
                "tool_results": results,
                "tool_trace": trace,
                "needs_memory_update": True,
            }

        try:
            car_result = search_car_tool(**search_params)
        except Exception as exc:
            return tool_fallback("search_car_tool", search_params, exc)
        results["search_cars"] = car_result.get("cars", [])
        trace.append({
            "tool_name": "search_car_tool",
            "input": search_params,
            "output": {"cars_count": len(car_result.get("cars", []))},
            "timestamp": datetime.now().isoformat(),
        })

    elif action == "compare_car":
        found = _complete_compare_models(
            _extract_compare_models(msg),
            purchase_intent,
        )

        compare_params = {"models": found}
        try:
            compare_result = compare_car_tool(found)
        except Exception as exc:
            return tool_fallback("compare_car_tool", compare_params, exc)
        results["compare"] = compare_result.get("cars", [])
        trace.append({
            "tool_name": "compare_car_tool",
            "input": compare_params,
            "output": {"cars_count": len(compare_result.get("cars", []))},
            "timestamp": datetime.now().isoformat(),
        })

    elif action == "loan_calculator":
        # 从消息中提取车价
        import re
        missing_loan_slots = _missing_loan_slots(msg, purchase_intent)
        if missing_loan_slots:
            return {
                "tool_results": results,
                "tool_trace": trace,
                "missing_slots": missing_loan_slots,
                "next_action": "ask_question",
                "needs_memory_update": True,
            }
        price = 169800  # 默认宋PLUS
        car_model = _first_known_model(msg, purchase_intent)
        down_payment_amount = _extract_down_payment_amount(msg)
        down_payment_rate = _extract_down_payment_rate(msg)
        loan_years = _extract_loan_years(msg)
        if not down_payment_amount:
            price_match = re.search(r"(\d+)\s*万", msg)
            if price_match:
                price = int(price_match.group(1)) * 10000

        if car_model:
            price = _lookup_model_price(car_model) or price

        default_params["car_price"] = price
        if car_model:
            default_params["model"] = car_model
        if down_payment_rate:
            default_params["down_payment_rate"] = down_payment_rate
        elif down_payment_amount:
            default_params["down_payment_rate"] = min(down_payment_amount, price) / price
        if loan_years:
            default_params["years"] = loan_years
        try:
            loan_result = loan_calculator_tool(**default_params)
        except Exception as exc:
            return tool_fallback("loan_calculator_tool", default_params, exc)
        if car_model:
            loan_result["model"] = car_model
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
        car_model = _first_known_model(msg, purchase_intent)
        city = ""

        city_match = re.search(r"(广州|深圳|上海|北京|成都|杭州|武汉)", msg)
        if city_match:
            city = city_match.group(1)

        default_params["model"] = car_model
        default_params["city"] = city
        try:
            inv_result = inventory_tool(**default_params)
        except Exception as exc:
            return tool_fallback("inventory_tool", default_params, exc)
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
        car_model = _first_known_model(msg, purchase_intent)

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

        if not default_params.get("customer_name") or not default_params.get("phone"):
            model_text = default_params.get("model") or "这款车"
            time_text = default_params.get("appointment_time") or "你方便的时间"
            return {
                "tool_results": results,
                "tool_trace": trace,
                "final_response": (
                    f"可以先帮你预留 {model_text} 的试驾意向，时间按{time_text}理解。"
                    "正式创建预约前，还需要确认你的姓名和手机号，方便门店联系确认。"
                ),
                "needs_memory_update": True,
            }

        try:
            drive_result = test_drive_tool(**default_params)
        except Exception as exc:
            return tool_fallback("test_drive_tool", default_params, exc)
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
        try:
            lead_result = lead_save_tool(**lead_params)
        except Exception as exc:
            return tool_fallback("lead_save_tool", lead_params, exc)
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

    if state.get("final_response") and not results:
        return {"final_response": state["final_response"]}

    if state.get("current_intent") == "general_question" and state.get("next_action") == "general_response":
        return {"final_response": _build_general_reply(msg)}

    if results.get("requires_rag_grounding"):
        return {"final_response": _build_rag_reply(results.get("rag_docs", []), msg)}

    if "rag_docs" in results and _has_model_context(msg, purchase_intent):
        return {"final_response": _build_rag_reply(results.get("rag_docs", []), msg)}

    if "search_cars" in results:
        return {"final_response": _build_car_recommendation_reply(results["search_cars"], purchase_intent)}

    if results.get("compare"):
        return {"final_response": _build_compare_reply(results["compare"])}

    if results.get("loan"):
        return {"final_response": _build_loan_reply(results["loan"])}

    if results.get("rag_docs"):
        return {"final_response": _build_rag_reply(results["rag_docs"], msg)}

    if "inventory" in results:
        return {"final_response": _build_inventory_reply(results.get("inventory", []), msg)}

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


def _build_inventory_reply(inventories: list[dict], message: str) -> str:
    """Build a factual inventory answer without forcing purchase slot collection."""
    import re

    city_match = re.search(r"(广州|深圳|上海|北京|成都|杭州|武汉)", message)
    city_text = city_match.group(1) if city_match else "当前"
    if not inventories:
        return (
            f"按当前库存工具查询，{city_text}暂时没有匹配到可直接交付的现车。"
            "你可以补充具体车型或颜色，我再按门店库存帮你查一次。"
        )

    model_names = list(dict.fromkeys(
        inv.get("model", "").strip()
        for inv in inventories
        if inv.get("model", "").strip()
    ))
    model_text = "、".join(model_names[:3])

    grouped: dict[str, list[str]] = {}
    for inv in inventories:
        store = inv.get("store_name") or "门店"
        model = inv.get("model", "").strip()
        color = inv.get("color") or "颜色待确认"
        delivery = inv.get("delivery_time") or "交付时间待确认"
        stock_count = inv.get("stock_count", 0)
        status = "有现车" if stock_count > 0 else "暂无现车"
        item_prefix = f"{model} " if model and len(model_names) != 1 else ""
        grouped.setdefault(store, []).append(f"{item_prefix}{color}（{status}，{delivery}）")

    target_text = model_text if model_text else ""
    lines = [f"根据库存工具查询，{city_text}目前{target_text}有这些库存信息：", ""]
    for store, items in grouped.items():
        lines.append(f"- **{store}**：{'、'.join(items)}")
    lines.extend([
        "",
        "如果你已经有目标车型或颜色，可以直接告诉我，我继续按门店帮你缩小范围。",
    ])
    return "\n".join(lines)


def _build_car_recommendation_reply(cars: list[dict], purchase_intent: dict) -> str:
    """根据车型搜索结果生成稳定推荐文案，避免模型脱离工具结果乱答。"""
    if not cars:
        budget = purchase_intent.get("budget", "当前预算")
        models = purchase_intent.get("intent_models") or []
        display_models = ["特斯拉 Model Y" if model == "Model Y" else model for model in models]
        model_text = "、".join(display_models)
        if model_text:
            return (
                f"按{budget}找{model_text}不太现实，当前车型库里没有匹配到这个价位的车型。"
                "更稳的做法是提高预算，或先看10万级通勤车、二手车等替代方向；"
                "如果你愿意，我可以按实际预算重新筛几款更接近的车。"
            )
        return "按当前条件暂时没有匹配到合适车型。可以把预算、车型或能源偏好放宽一点，我再帮你筛。"

    budget = purchase_intent.get("budget", "")
    car_type = purchase_intent.get("car_type", "")
    prefix_parts = [part for part in (budget, car_type) if part]
    prefix = "、".join(prefix_parts)
    title = f"按{prefix}这个方向，我会先看这几款：" if prefix else "我会先看这几款："

    lines = [title, ""]
    for index, car in enumerate(cars[:5], 1):
        highlights = "、".join((car.get("highlights") or [])[:3])
        price = car.get("price", 0)
        price_text = f"{price / 10000:.1f}万" if price else "价格待确认"
        fuel = car.get("fuel_consumption") or ""
        detail_parts = [car.get("energy_type", ""), fuel, highlights]
        detail = "，".join(part for part in detail_parts if part)
        lines.append(f"{index}. **{car.get('model', '')}**：{price_text}，{detail}。")

    lines.extend([
        "",
        "如果你更看重省油、空间、品牌可靠性或智能配置，我可以继续按这个方向帮你缩小到 1-2 款。",
    ])
    return "\n".join(lines)


def _build_compare_reply(cars: list[dict]) -> str:
    """根据对比工具结果生成稳定对比文案。"""
    if not cars:
        return "我还没匹配到要对比的车型。你可以直接说“对比宋PLUS和锋兰达”。"

    lines = ["这几款车可以这样看：", ""]
    for car in cars:
        price = car.get("price", 0)
        price_text = f"{price / 10000:.1f}万" if price else "价格待确认"
        lines.append(
            f"- **{car.get('model', '')}**：{price_text}，{car.get('energy_type', '')}，"
            f"{car.get('recommendation', '')}"
        )
    lines.extend(["", "你更看重空间、用车成本，还是品牌稳定性？我可以按你的侧重点给结论。"])
    return "\n".join(lines)


def _build_loan_reply(loan: dict) -> str:
    """Build a deterministic loan reply from calculator results."""
    def money(value: float) -> str:
        return f"¥{value:,.0f}"

    monthly_payment = loan.get("monthly_payment", 0)
    months = loan.get("months") or (loan.get("years", 3) * 12)
    model = loan.get("model", "")
    intro = f"按{model}当前方案试算，分期结果如下：" if model else "按当前方案试算，分期结果如下："
    lines = [
        intro,
        "",
        f"- **首付**：{money(loan.get('down_payment', 0))}",
        f"- **贷款金额**：{money(loan.get('loan_amount', 0))}",
        f"- **月供**：{money(monthly_payment)}（约{months}期）",
        f"- **总利息**：{money(loan.get('total_interest', 0))}",
        "",
        "这个结果是按当前工具参数估算，实际月供还要以裸车价、金融利率、保险和门店政策为准。",
    ]
    return "\n".join(lines)


def _build_general_reply(message: str) -> str:
    """Answer non-buying general questions without forcing purchase slot filling."""
    if any(word in message for word in ("你好", "您好", "在吗")):
        return "在的。你可以直接问车型推荐、配置对比、分期月供、库存或试驾预约，我会按你的问题往下接。"
    return (
        "可以，这类问题我先直接回答，不急着追问预算和车型。"
        "如果你想看具体购车方案，再告诉我预算、车型偏好或用途，我再帮你筛。"
    )


def _build_rag_reply(docs: list[dict], message: str) -> str:
    """Build a grounded reply from retrieved sales materials."""
    if not docs:
        topic = "、".join(_extract_known_models(message)) or message.strip() or "这个问题"
        return (
            f"目前没有“{topic}”相关资料。"
            "这个问题需要参考车型销售资料来回答，我不能直接编政策、配置或优惠信息；"
            "你可以换个问法，或先到销售资料库补充对应车型资料后再问。"
        )

    lines = ["这个问题可以先按销售资料里的信息来讲：", ""]
    for doc in docs[:3]:
        title = doc.get("title", "销售资料")
        content = (doc.get("content") or "").strip()
        if len(content) > 120:
            content = content[:120].rstrip() + "..."
        lines.append(f"- **{title}**：{content}")

    lines.extend([
        "",
        "实际沟通时建议先认可客户关注点，再结合配置、用车成本、金融方案或门店政策讲清综合价值；具体优惠以门店当期政策为准。",
    ])
    return "\n".join(lines)


def _has_model_context(message: str, purchase_intent: dict | None = None) -> bool:
    """Return whether the user question is tied to a known model or brand."""
    purchase_intent = purchase_intent or {}
    return bool(_extract_known_models(message) or purchase_intent.get("intent_models"))


def _expand_rag_query(query: str, intent_models: list[str] | None = None) -> str:
    """Expand user wording with business synonyms to improve RAG recall."""
    intent_models = intent_models or []
    additions: list[str] = []
    synonym_groups = [
        (["价格贵", "嫌贵", "太贵", "贵"], ["价格异议", "价值解释", "金融方案", "优惠政策", "用车成本"]),
        (["优惠", "补贴", "降价"], ["置换补贴", "金融政策", "免息", "赠品礼包", "门店政策"]),
        (["插混", "dm-i", "phev"], ["插电混动", "可油可电", "亏电油耗", "充电条件"]),
        (["油混", "双擎", "混动"], ["油电混动", "不用充电", "低油耗", "保值率"]),
        (["配置", "功能"], ["核心配置", "安全配置", "智能驾驶", "空间表现"]),
        (["保值", "可靠"], ["保值率", "品牌可靠性", "长期用车成本"]),
    ]

    normalized = query.lower()
    for triggers, expansions in synonym_groups:
        if any(trigger in normalized for trigger in triggers):
            additions.extend(expansions)

    additions.extend(intent_models)
    additions.extend(_extract_known_models(query))

    terms = [query, *additions]
    return " ".join(dict.fromkeys(term for term in terms if term))


def memory_write_node(state: SalesAgentState) -> dict:
    """记忆更新节点 — 写入长期记忆"""
    customer_id = state.get("customer_id", "")
    if not customer_id:
        return {}

    # 用 LLM 提取记忆信息
    msg = state.get("user_message", "")
    purchase_intent = state.get("purchase_intent", {}) or {}
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

        # 更新字段：确定性 purchase_intent 优先，LLM 记忆抽取作为补充
        merged_update = {
            "budget": purchase_intent.get("budget") or memory_update.get("budget", ""),
            "car_type": purchase_intent.get("car_type") or memory_update.get("car_type", ""),
            "usage": purchase_intent.get("usage") or memory_update.get("usage", ""),
            "energy_type": purchase_intent.get("energy_type") or memory_update.get("energy_type", ""),
            "purchase_time": purchase_intent.get("purchase_time") or memory_update.get("purchase_time", ""),
            "follow_up_summary": memory_update.get("follow_up_summary", ""),
            "lead_level": memory_update.get("lead_level", ""),
        }
        for field, value in merged_update.items():
            if value:
                setattr(profile, field, value)

        if purchase_intent.get("concerns") or memory_update.get("concerns"):
            existing = set(profile.concerns or [])
            existing.update(purchase_intent.get("concerns") or [])
            existing.update(memory_update.get("concerns") or [])
            profile.concerns = list(existing)

        if purchase_intent.get("intent_models") or memory_update.get("intent_models"):
            existing = set(profile.intent_models or [])
            existing.update(purchase_intent.get("intent_models") or [])
            existing.update(memory_update.get("intent_models") or [])
            profile.intent_models = list(existing)

        db.commit()
        return {}
    finally:
        db.close()
