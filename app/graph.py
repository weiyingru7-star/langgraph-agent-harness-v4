"""
graph.py — LangGraph 图定义

构建完整的 LangGraph StateGraph，包含 7 个线性节点：
  START → parse_input → decide_modality → analyze_text
       → classify_intent → classify_emotion → classify_stage
       → save_log → END

提供 build_graph() 和 run_graph() 两个入口函数。
"""

from langgraph.graph import END, StateGraph

from app.nodes.analyze_text import analyze_text
from app.nodes.classify_emotion import classify_emotion
from app.nodes.classify_intent import classify_intent
from app.nodes.classify_stage import classify_stage
from app.nodes.decide_modality import decide_modality
from app.nodes.parse_input import parse_input
from app.nodes.save_log import save_log
from app.state.customer_state import CustomerServiceState


def build_graph():
    """
    构建并编译 LangGraph StateGraph。

    流程：
        START → parse_input → decide_modality → analyze_text
             → classify_intent → classify_emotion → classify_stage
             → save_log → END

    Returns:
        编译好的 Graph 对象
    """
    graph = StateGraph(CustomerServiceState)

    # 注册 7 个节点
    graph.add_node("parse_input", parse_input)
    graph.add_node("decide_modality", decide_modality)
    graph.add_node("analyze_text", analyze_text)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("classify_emotion", classify_emotion)
    graph.add_node("classify_stage", classify_stage)
    graph.add_node("save_log", save_log)

    # 入口点
    graph.set_entry_point("parse_input")

    # 线性边（Phase 4 不做条件路由）
    graph.add_edge("parse_input", "decide_modality")
    graph.add_edge("decide_modality", "analyze_text")
    graph.add_edge("analyze_text", "classify_intent")
    graph.add_edge("classify_intent", "classify_emotion")
    graph.add_edge("classify_emotion", "classify_stage")
    graph.add_edge("classify_stage", "save_log")
    graph.add_edge("save_log", END)

    return graph.compile()


def run_graph(initial_state: CustomerServiceState) -> CustomerServiceState:
    """
    运行图流程，返回最终 state。

    Args:
        initial_state: 通过 create_initial_state() 创建的初始 state

    Returns:
        经过所有节点处理后的最终 state
    """
    graph = build_graph()
    result = graph.invoke(initial_state)
    return result
