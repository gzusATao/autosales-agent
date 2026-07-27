"""
LLM 调用封装
支持 DeepSeek（通过兼容 OpenAI SDK）、mock 模式
"""

import json
import re
from typing import Optional

from openai import OpenAI
from backend.config import settings


# DeepSeek 客户端
_client: Optional[OpenAI] = None


def get_llm_client() -> OpenAI:
    """获取 LLM 客户端（单例）"""
    global _client
    if _client is not None:
        return _client

    if settings.LLM_PROVIDER == "deepseek":
        _client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL or "https://api.deepseek.com",
        )
    elif settings.LLM_PROVIDER == "openai":
        _client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL or "https://api.openai.com/v1",
        )
    else:
        _client = None  # mock 模式
    return _client


def chat_completion(
    system_prompt: str,
    user_message: str,
    response_format: Optional[dict] = None,
    temperature: float = 0.1,
) -> str:
    """
    调用 LLM 获取回复
    支持 deepseek / openai / mock 三种模式
    """
    if settings.LLM_PROVIDER in ("deepseek", "openai"):
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
        except Exception as e:
            print(f"[LLM Error] {e}")
            return _mock_llm_response(system_prompt, user_message)

    # Mock 模式
    return _mock_llm_response(system_prompt, user_message)


def extract_json(text: str) -> dict:
    """从 LLM 回复中提取 JSON"""
    # 尝试直接解析
    text = text.strip()
    # 移除 markdown 代码块标记
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    # 查找最外层的 { }
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
        text = text[brace_start : brace_end + 1]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 清理不可见字符后重试
        cleaned = re.sub(r"[\x00-\x1f]", "", text)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {}


def _mock_llm_response(system_prompt: str, user_message: str) -> str:
    """
    Mock LLM 响应 — 基于关键词规则返回结构化结果
    用于无 API key 时的演示
    """
    msg = user_message.lower()

    # 意图识别 mock
    if "意图识别" in system_prompt or "intent" in system_prompt.lower():
        return _mock_intent(msg)

    # 回复生成 mock
    if "回复生成" in system_prompt or "销售回复" in system_prompt:
        return _mock_reply(msg)

    # 记忆更新 mock
    if "记忆更新" in system_prompt or "跟进摘要" in system_prompt:
        return _mock_memory_update(msg)

    return json.dumps({"reply": f"收到您的消息：{user_message}，请问还有什么可以帮您？"})


def _mock_intent(msg: str) -> str:
    """模拟意图识别"""
    intent = "general_question"
    slots = {"budget": "", "car_type": "", "energy_type": "", "usage": "", "purchase_time": ""}
    missing = ["budget", "car_type", "energy_type", "usage"]

    # 预算
    budget_match = re.search(r"(\d+)\s*万", msg)
    if budget_match:
        slots["budget"] = f"{budget_match.group(1)}万以内"
        missing = [s for s in missing if s != "budget"]

    # 车型
    if re.search(r"suv|越野|城市越野", msg):
        slots["car_type"] = "SUV"
        missing = [s for s in missing if s != "car_type"]
    elif re.search(r"轿车|小轿车|三厢", msg):
        slots["car_type"] = "轿车"
        missing = [s for s in missing if s != "car_type"]

    # 能源
    if re.search(r"混动|油电混合|插混|双擎", msg):
        slots["energy_type"] = "混动"
        missing = [s for s in missing if s != "energy_type"]
    elif re.search(r"纯电|电动|电车", msg):
        slots["energy_type"] = "纯电"
        missing = [s for s in missing if s != "energy_type"]
    elif re.search(r"燃油|汽油|油车", msg):
        slots["energy_type"] = "燃油"
        missing = [s for s in missing if s != "energy_type"]

    # 用途
    if re.search(r"家用|家庭|代步|接送|孩子|小孩|老人", msg):
        slots["usage"] = "家用"
        missing = [s for s in missing if s != "usage"]
    elif re.search(r"商务|办公|公司|接待", msg):
        slots["usage"] = "商务"
        missing = [s for s in missing if s != "usage"]

    # 购车时间
    if re.search(r"一个月|本月|这个月|尽快|最近|这个月", msg):
        slots["purchase_time"] = "1个月内"
    elif re.search(r"三个月|半年|不急|看看|了解", msg):
        slots["purchase_time"] = "3个月内"

    # intent 判断
    if re.search(r"对比|哪个好|怎么选|区别|vs|和.*比", msg):
        intent = "car_compare"
    elif re.search(r"首付|月供|贷款|分期|按揭|利息", msg):
        intent = "loan_calculation"
    elif re.search(r"现车|库存|有车吗|什么时候能提", msg):
        intent = "inventory_query"
    elif re.search(r"试驾|试车|体验|开一开", msg):
        intent = "test_drive"
    elif re.search(r"预算|推荐|买.*车|推荐.*车|什么车|选择", msg) or slots["budget"]:
        intent = "car_recommendation"

    return json.dumps({
        "intent": intent,
        "slots": slots,
        "missing_slots": missing,
        "confidence": 0.85,
    })


def _mock_reply(msg: str) -> str:
    """模拟销售回复"""
    if "对比" in msg or "哪个好" in msg:
        return json.dumps({
            "reply": "根据对比结果，宋PLUS DM-i 在空间和油耗方面更有优势，适合家用；锋兰达双擎在品牌保值率方面更胜一筹。建议您根据侧重点选择，如果注重空间和省油，宋PLUS DM-i 性价比更高。需要帮您算算分期月供吗？",
        })
    if "月供" in msg or "首付" in msg or "分期" in msg:
        return json.dumps({
            "reply": "以宋PLUS DM-i 16.98万为例，首付30%即5.09万，贷款3年，年利率4.5%，月供约3,748元。您看这个预算合适吗？需要帮您查一下附近门店的现车情况吗？",
        })
    if "现车" in msg or "库存" in msg:
        return json.dumps({
            "reply": "广州天河体验店目前有白色宋PLUS DM-i 现车，3天内可提车。如果您想要其他颜色，也可以帮您查询调货时间。要预约试驾感受一下吗？",
        })
    if "试驾" in msg:
        return json.dumps({
            "reply": "好的，已为您预约周六下午3点广州天河体验店的宋PLUS DM-i 试驾。预约编号：TD202607270001。届时会有专业顾问接待您，请问还有其他需要吗？",
        })
    if re.search(r"20万.*SUV|SUV.*20万|家用.*SUV", msg):
        return json.dumps({
            "reply": "根据您的预算和需求，我重点推荐以下三款混动SUV：\n\n1. **比亚迪宋PLUS DM-i** — 16.98万，插电混动，油耗低至4.4L/100km，空间宽敞，非常适合家用。\n2. **丰田锋兰达双擎** — 17.98万起，油电混动，丰田品质，油耗4.5L/100km。\n3. **哈弗枭龙MAX** — 18.98万，插电混动四驱，配置丰富。\n\n这三款您对哪款比较感兴趣？我可以帮您详细对比一下。",
        })
    return json.dumps({
        "reply": f"好的，已收到您的需求。请问您对车型有什么具体要求，比如预算范围、车型级别（SUV/轿车）和能源类型（燃油/混动/纯电）？我可以为您做精准推荐。",
    })


def _mock_memory_update(msg: str) -> str:
    """模拟记忆更新"""
    concerns = []
    if "省油" in msg:
        concerns.append("油耗")
    if "空间" in msg or "后排" in msg:
        concerns.append("空间")
    if "安全" in msg:
        concerns.append("安全性")
    if "配置" in msg:
        concerns.append("配置")
    if "品牌" in msg:
        concerns.append("品牌")

    return json.dumps({
        "budget": "",
        "usage": "",
        "energy_type": "",
        "concerns": concerns if concerns else ["油耗"],
        "intent_models": [],
        "purchase_time": "",
        "follow_up_summary": f"客户咨询：{msg[:50]}..." if len(msg) > 50 else f"客户咨询：{msg}",
        "lead_level": "中意向",
    })
