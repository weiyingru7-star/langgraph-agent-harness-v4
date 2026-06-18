"""
LangGraph 电商客服 Agent Harness V4-lite

项目入口：构建并运行 LangGraph 状态流转流程。
Phase 4.2：意图/情绪/客户阶段分类演示。
"""

import json

from app.graph import run_graph
from app.state.customer_state import create_initial_state

# 8 个 demo 用例，覆盖 8 种意图、5 种情绪、4 种客户阶段
_DEMOS = [
    {"id": "demo-01", "msg": "我的快递怎么还没到"},
    {"id": "demo-02", "msg": "质量太差了我要退款"},
    {"id": "demo-03", "msg": "这个衣服是什么材质"},
    {"id": "demo-04", "msg": "适合夏天骑车穿吗"},
    {"id": "demo-05", "msg": "气死了，我要人工"},
    {"id": "demo-06", "msg": "我要换个尺码"},
    {"id": "demo-07", "msg": "你们这个太垃圾了，我要投诉"},
    {"id": "demo-08", "msg": "你好，在吗"},
]


def _show_summary(state):
    """打印关键分类字段，便于快速查看。"""
    print(f"  intent={state['intent']} | "
          f"emotion={state['emotion']}({state['emotion_score']}) | "
          f"stage={state['customer_stage']} | "
          f"logs={len(state['logs'])}条")


def main():
    print("=" * 60)
    print("LangGraph Customer Service Agent")
    print("版本: V4-lite | Phase 4.2")
    print("=" * 60)

    for demo in _DEMOS:
        print(f"\n--- {demo['id']}: {demo['msg']} ---")
        state = run_graph(create_initial_state(
            session_id=demo['id'],
            user_message=demo['msg'],
        ))
        _show_summary(state)
        print(json.dumps(state, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
