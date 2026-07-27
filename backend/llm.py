"""
LLM client wrapper with a deterministic mock fallback.
"""

import json
import re
from typing import Optional

from openai import OpenAI

from backend.config import settings

_client: Optional[OpenAI] = None


def get_llm_client() -> Optional[OpenAI]:
    """Return an OpenAI-compatible client, or None when credentials are absent."""
    global _client
    if _client is not None:
        return _client

    if settings.LLM_PROVIDER not in ("deepseek", "openai") or not settings.OPENAI_API_KEY:
        return None

    _client = OpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL or "https://api.deepseek.com",
    )
    return _client


def chat_completion(
    system_prompt: str,
    user_message: str,
    response_format: Optional[dict] = None,
    temperature: float = 0.1,
) -> str:
    """Call the configured model, falling back to mock output for local demos."""
    client = get_llm_client()
    if client is None:
        return _mock_llm_response(system_prompt, user_message)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    kwargs = {
        "model": settings.OPENAI_MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    if response_format:
        kwargs["response_format"] = response_format

    try:
        resp = client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""
    except Exception as exc:
        print(f"[LLM Error] {exc}")
        return _mock_llm_response(system_prompt, user_message)


def extract_json(text: str) -> dict:
    """Extract the outer JSON object from an LLM response."""
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
        text = text[brace_start:brace_end + 1]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        cleaned = re.sub(r"[\x00-\x1f]", "", text)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {}


def _mock_llm_response(system_prompt: str, user_message: str) -> str:
    prompt = system_prompt.lower()
    msg = user_message.lower()

    if "intent" in prompt or "意图" in system_prompt:
        return _mock_intent(msg)
    if "记忆" in system_prompt or "memory" in prompt:
        return _mock_memory_update(msg)
    return _mock_reply(msg)


def _mock_intent(msg: str) -> str:
    intent = "general_question"
    slots = {"budget": "", "car_type": "", "energy_type": "", "usage": "", "purchase_time": ""}
    missing = ["budget", "car_type", "energy_type", "usage"]

    budget_match = re.search(r"(\d+)\s*万", msg)
    if budget_match:
        slots["budget"] = f"{budget_match.group(1)}万以内"
        missing.remove("budget")

    if re.search(r"suv|越野|家用车", msg):
        slots["car_type"] = "SUV"
        missing.remove("car_type")
    elif re.search(r"轿车|小车", msg):
        slots["car_type"] = "轿车"
        missing.remove("car_type")

    if re.search(r"混动|插混|省油", msg):
        slots["energy_type"] = "混动"
        missing.remove("energy_type")
    elif re.search(r"纯电|电车", msg):
        slots["energy_type"] = "纯电"
        missing.remove("energy_type")
    elif re.search(r"燃油|油车", msg):
        slots["energy_type"] = "燃油"
        missing.remove("energy_type")

    if re.search(r"家用|家庭|通勤|接送", msg):
        slots["usage"] = "家用"
        missing.remove("usage")
    elif re.search(r"商务|接待|公司", msg):
        slots["usage"] = "商务"
        missing.remove("usage")

    if re.search(r"对比|区别|哪个好|vs", msg):
        intent = "car_compare"
    elif re.search(r"月供|首付|贷款|分期", msg):
        intent = "loan_calculation"
    elif re.search(r"现车|库存|有车", msg):
        intent = "inventory_query"
    elif re.search(r"试驾|试车|预约", msg):
        intent = "test_drive"
    elif re.search(r"推荐|预算|买.*车|什么车", msg) or slots["budget"]:
        intent = "car_recommendation"

    return json.dumps({
        "intent": intent,
        "slots": slots,
        "missing_slots": missing,
        "confidence": 0.86,
    }, ensure_ascii=False)


def _mock_reply(msg: str) -> str:
    if "对比" in msg or "哪个好" in msg:
        reply = (
            "这两款定位不太一样：\n\n"
            "**宋PLUS DM-i** 更适合家用和通勤，空间宽，油耗低，配置给得比较足。\n"
            "**锋兰达双擎** 更偏稳定省心，品牌口碑和长期可靠性更好。\n\n"
            "如果你更看重空间和用车成本，我会优先推荐宋PLUS DM-i；如果更看重品牌稳定性，锋兰达更稳。"
        )
    elif "月供" in msg or "首付" in msg or "分期" in msg:
        reply = (
            "按 16.98 万车型估算，首付 30% 约 5.09 万，贷款 3 年，月供大概 3700 元左右。\n\n"
            "这个只是演示试算，实际月供要看裸车价、保险、购置税、金融利率和门店政策。"
        )
    elif "现车" in msg or "库存" in msg:
        reply = (
            "广州天河体验店当前有宋PLUS DM-i 白色现车，正常 3 天内可提。\n\n"
            "如果你想看其他颜色，我可以继续按门店库存帮你查。"
        )
    elif "试驾" in msg:
        reply = (
            "已按演示流程生成试驾预约：周六下午 3 点，广州天河体验店，车型宋PLUS DM-i。\n\n"
            "到店前可以再确认一次手机号和具体门店。"
        )
    elif "20万" in msg and "suv" in msg:
        reply = (
            "20 万以内家用 SUV，我会先看这三款：\n\n"
            "1. **宋PLUS DM-i**：空间大、油耗低，适合家用通勤。\n"
            "2. **锋兰达双擎**：可靠性和品牌口碑更稳。\n"
            "3. **哈弗枭龙MAX**：配置丰富，适合想要四驱和科技配置的用户。\n\n"
            "你更在意省油、空间，还是品牌可靠性？我可以按这个方向继续缩小范围。"
        )
    else:
        reply = (
            "可以，我先帮你把需求拆一下。你补充预算、车型偏好和主要用途后，"
            "我就能结合车型库给出更具体的推荐。"
        )

    return json.dumps({"reply": reply}, ensure_ascii=False)


def _mock_memory_update(msg: str) -> str:
    concerns = []
    if "省油" in msg:
        concerns.append("油耗")
    if "空间" in msg or "家用" in msg:
        concerns.append("空间")
    if "品牌" in msg or "可靠" in msg:
        concerns.append("品牌可靠性")

    return json.dumps({
        "budget": "",
        "usage": "家用" if "家用" in msg else "",
        "energy_type": "混动" if "混动" in msg or "省油" in msg else "",
        "concerns": concerns,
        "intent_models": [],
        "purchase_time": "",
        "follow_up_summary": f"客户咨询：{msg[:50]}",
        "lead_level": "中意向",
    }, ensure_ascii=False)
