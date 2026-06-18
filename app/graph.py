"""
graph.py — LangGraph 图定义

构建完整的 LangGraph StateGraph，包含 11 个线性节点：
  START → parse_input → decide_modality
       → analyze_text → analyze_multimodal
       → classify_intent → classify_emotion → classify_stage
       → route_to_skill → escalation_check
       → generate_reply → save_log → END

analyze_multimodal 在内部检查 modality，非图文场景直接跳过。
"""

from langgraph.graph import END, StateGraph

from app.nodes.analyze_multimodal import analyze_multimodal
from app.nodes.analyze_text import analyze_text
from app.nodes.classify_emotion import classify_emotion
from app.nodes.classify_intent import classify_intent
from app.nodes.classify_stage import classify_stage
from app.nodes.decide_modality import decide_modality
from app.nodes.escalation_check import escalation_check
from app.nodes.generate_reply import generate_reply
from app.nodes.parse_input import parse_input
from app.nodes.route_to_skill import route_to_skill
from app.nodes.save_log import save_log
from app.state.customer_state import CustomerServiceState


def build_graph():
    graph = StateGraph(CustomerServiceState)

    # 注册 11 个节点
    graph.add_node("parse_input", parse_input)
    graph.add_node("decide_modality", decide_modality)
    graph.add_node("analyze_text", analyze_text)
    graph.add_node("analyze_multimodal", analyze_multimodal)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("classify_emotion", classify_emotion)
    graph.add_node("classify_stage", classify_stage)
    graph.add_node("route_to_skill", route_to_skill)
    graph.add_node("escalation_check", escalation_check)
    graph.add_node("generate_reply", generate_reply)
    graph.add_node("save_log", save_log)

    graph.set_entry_point("parse_input")

    graph.add_edge("parse_input", "decide_modality")
    graph.add_edge("decide_modality", "analyze_text")
    graph.add_edge("analyze_text", "analyze_multimodal")
    graph.add_edge("analyze_multimodal", "classify_intent")
    graph.add_edge("classify_intent", "classify_emotion")
    graph.add_edge("classify_emotion", "classify_stage")
    graph.add_edge("classify_stage", "route_to_skill")
    graph.add_edge("route_to_skill", "escalation_check")
    graph.add_edge("escalation_check", "generate_reply")
    graph.add_edge("generate_reply", "save_log")
    graph.add_edge("save_log", END)

    return graph.compile()


def run_graph(initial_state: CustomerServiceState) -> CustomerServiceState:
    """运行图流程，返回最终 state。"""
    graph = build_graph()
    return graph.invoke(initial_state)
