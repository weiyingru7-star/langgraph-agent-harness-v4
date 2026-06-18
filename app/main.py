"""
LangGraph 电商客服 Agent Harness V4-lite

项目入口：构建并运行 LangGraph 状态流转流程。
Phase 5.2：Skill / Tool / Policy 集成演示。
"""

import json

from app.graph import run_graph
from app.state.customer_state import create_initial_state

# 7 个 demo 用例，覆盖业务 skill 路由 + 闲聊兜底
_DEMOS = [
    {"id": "demo-01", "msg": "我的快递怎么还没到"},
    {"id": "demo-02", "msg": "质量太差了我要退款"},
    {"id": "demo-03", "msg": "这个衣服是什么材质"},
    {"id": "demo-04", "msg": "气死了，我要人工"},
    {"id": "demo-05", "msg": "你们这个太垃圾了，我要投诉"},
    {"id": "demo-06", "msg": "我要换个尺码"},
    {"id": "demo-07", "msg": "你好，在吗"},
]


def _show_summary(state):
    """打印关键执行结果，便于快速查看。"""
    print(f"  intent={state['intent']} | "
          f"skill={state['selected_skill']} | "
          f"need_human={state['need_human']} | "
          f"logs={len(state['logs'])}条")


def _show_highlights(state):
    """打印本阶段关注的关键字段变化。"""
    print(f"  → selected_skill = {state['selected_skill']}")
    print(f"  → skill_result   = {json.dumps(state['skill_result'], ensure_ascii=False)}")
    if state["policy_decision"]:
        print(f"  → policy_decision = {state['policy_decision']}")
    print(f"  → need_human     = {state['need_human']}")
    if state["human_reason"]:
        print(f"  → human_reason   = {state['human_reason']}")


def main():
    """主入口：循环运行 7 个 demo 并输出完整 JSON state。"""
    print("=" * 60)
    print("LangGraph Customer Service Agent")
    print("版本: V4-lite | Phase 5.2")
    print("=" * 60)

    for demo in _DEMOS:
        print(f"\n--- {demo['id']}: {demo['msg']} ---")
        state = run_graph(create_initial_state(
            session_id=demo['id'],
            user_message=demo['msg'],
        ))
        _show_summary(state)
        _show_highlights(state)
        print(json.dumps(state, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
