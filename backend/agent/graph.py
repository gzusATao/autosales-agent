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


NODE_FALLBACK_REPLIES = {
    "intent": "我暂时没能准确理解您的需求，请稍后再试，或换一种说法重新发送。",
    "memory_load": "我暂时没能读取到历史偏好，但可以先按您这次提供的信息继续服务。",
    "slot_fill": "我暂时没能整理完整需求信息，请直接告诉我预算、车型偏好或用途，我继续帮您分析。",
    "route": "我暂时没能判断下一步处理方式，请稍后再试，或把问题说得更具体一点。",
    "ask_question": "我暂时没能生成追问问题。您可以直接补充预算、车型偏好、能源类型或用途。",
    "tool_executor": "相关业务工具暂时不可用，我先不编造结果。请稍后再试，或换个问题继续咨询。",
    "response": "我已经收到您的问题，但暂时没能生成完整回复，请稍后再试。",
    "memory_write": "",
}


def _safe_node(node_name, node_func):
    """Catch node failures and convert them into node-specific fallbacks."""
    def wrapped(state):
        try:
            return node_func(state)
        except Exception as exc:
            print(f"[Agent Node Error] {node_name}: {exc}")
            if node_name == "memory_write":
                return {}
            return {
                "current_intent": "system_error",
                "next_action": "node_error",
                "missing_slots": [],
                "tool_trace": [
                    *state.get("tool_trace", []),
                    {
                        "tool_name": f"{node_name}_node",
                        "input": {"node": node_name},
                        "output": {"error": "fallback"},
                        "timestamp": "",
                    },
                ],
                "final_response": NODE_FALLBACK_REPLIES.get(
                    node_name,
                    "抱歉，我这边遇到了一点技术问题，请稍后再试。",
                ),
            }

    return wrapped


def build_agent_graph() -> StateGraph:
    """构建 Agent 状态图"""
    builder = StateGraph(SalesAgentState)

    # 注册节点
    builder.add_node("intent", _safe_node("intent", intent_node))
    builder.add_node("memory_load", _safe_node("memory_load", memory_load_node))
    builder.add_node("slot_fill", _safe_node("slot_fill", slot_fill_node))
    builder.add_node("route", _safe_node("route", route_node))
    builder.add_node("ask_question", _safe_node("ask_question", ask_question_node))
    builder.add_node("tool_executor", _safe_node("tool_executor", tool_executor))
    builder.add_node("response", _safe_node("response", response_node))
    builder.add_node("memory_write", _safe_node("memory_write", memory_write_node))

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
            "general_response": "response",
            "rag_search": "tool_executor",
            "search_car": "tool_executor",
            "compare_car": "tool_executor",
            "loan_calculator": "tool_executor",
            "inventory_query_action": "tool_executor",
            "test_drive_action": "tool_executor",
            "lead_save": "tool_executor",
            "node_error": "response",
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
