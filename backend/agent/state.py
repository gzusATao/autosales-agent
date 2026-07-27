"""
Agent 状态定义
基于 LangGraph 的销售顾问 Agent 状态
"""

from typing import Any

from langgraph.graph import MessagesState


class SalesAgentState(MessagesState):
    """销售顾问 Agent 状态"""

    # 会话标识
    session_id: str = ""
    customer_id: str = ""

    # 当前输入
    user_message: str = ""

    # 对话历史
    conversation_history: list[dict] = []

    # 客户画像（长期记忆）
    customer_profile: dict = {}

    # 购车意图（短期记忆）
    purchase_intent: dict = {}

    # 当前意图
    current_intent: str = ""
    missing_slots: list[str] = []

    # 下一步动作
    next_action: str = ""

    # RAG 检索结果
    retrieved_docs: list[dict] = []

    # 工具调用记录
    tool_results: dict[str, Any] = {}
    tool_trace: list[dict] = []

    # Agent 最终回复
    final_response: str = ""
    # 是否需要更新长期记忆
    needs_memory_update: bool = False
