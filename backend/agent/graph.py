"""
AutoLead Agent LangGraph 图定义
编排完整的销售顾问 Agent 流程
"""

from langgraph.graph import StateGraph, START, END

from backend.agent.state import SalesAgentState
from backend.agent.nodes import (
    intent_node,
    memory_load_node,
    slot_fill_node,
    route_node,
    ask_question_node,
    tool_executor,
    response_node,
    memory_write_node,
)


def build_agent_graph() -> StateGraph:
    """构建 Agent 状态图"""
    builder = StateGraph(SalesAgentState)

    # 注册节点
    builder.add_node("intent", intent_node)
    builder.add_node("memory_load", memory_load_node)
    builder.add_node("slot_fill", slot_fill_node)
    builder.add_node("route", route_node)
    builder.add_node("ask_question", ask_question_node)
    builder.add_node("tool_executor", tool_executor)
    builder.add_node("response", response_node)
    builder.add_node("memory_write", memory_write_node)

    # 设置入口
    builder.add_edge(START, "intent")
    builder.add_edge("intent", "memory_load")
    builder.add_edge("memory_load", "slot_fill")
    builder.add_edge("slot_fill", "route")

    # 路由节点 → 各执行节点
    builder.add_conditional_edges(
        "route",
        lambda state: state["next_action"],
        {
            "ask_question": "ask_question",
            "rag_search": "tool_executor",
            "search_car": "tool_executor",
            "compare_car": "tool_executor",
            "loan_calculator": "tool_executor",
            "inventory_query_action": "tool_executor",
            "test_drive_action": "tool_executor",
            "lead_save": "tool_executor",
        },
    )

    # 追问 → 直接回复，不需要工具结果
    builder.add_edge("ask_question", "response")

    # 工具执行 → 回复
    builder.add_edge("tool_executor", "response")

    # 回复 → 记忆更新 → 结束
    builder.add_edge("response", "memory_write")
    builder.add_edge("memory_write", END)

    return builder.compile()


# 图实例（单例）
_agent_graph = None


def get_agent_graph():
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = build_agent_graph()
    return _agent_graph


def run_agent(state: SalesAgentState) -> SalesAgentState:
    """
    运行 Agent 并返回最终状态
    """
    graph = get_agent_graph()
    result = graph.invoke(state)
    return result
