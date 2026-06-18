"""
LangGraph 电商客服 Agent Harness V4-lite

项目入口：构建并运行 LangGraph 状态流转流程。
Phase 7.2：多模态路由演示。
"""

import json

from app.graph import run_graph
from app.state.customer_state import create_initial_state

# 常规 demo
_DEMOS = [
    {"id": "demo-01", "msg": "我的快递怎么还没到", "img": None},
    {"id": "demo-02", "msg": "", "img": "https://example.com/broken.jpg"},
    {"id": "demo-03", "msg": "这个破了能退吗", "img": "https://example.com/broken.jpg"},
]

# 先文字后图片需要两轮
_INSTALL_DEMO_1 = {"id": "demo-install", "msg": "这个怎么安装", "img": None}
_INSTALL_DEMO_2 = {"id": "demo-install", "msg": "", "img": "https://example.com/install.jpg"}


def _show_summary(state):
    """打印关键执行结果，便于快速查看。"""
    print(f"  intent={state['intent']} | "
          f"skill={state['selected_skill']} | "
          f"need_human={state['need_human']} | "
          f"logs={len(state['logs'])}条")


def _show_highlights(state):
    """打印本阶段关注的关键字段变化。"""
    print(f"  → modality       = {state['modality']}")
    print(f"  → selected_skill = {state['selected_skill']}")
    print(f"  → skill_result   = {json.dumps(state['skill_result'], ensure_ascii=False)}")
    if state["multimodal_analysis"]:
        ma = state["multimodal_analysis"]
        print(f"  → multimodal_analysis = visible={ma.get('visible_issue','')}, is_mock={ma.get('is_mock')}")
    print(f"  → need_human     = {state['need_human']}")
    reply = state["reply"]
    print(f"  → reply (前60字) = {reply[:60] + '…' if reply and len(reply) > 60 else reply}")


def main():
    """主入口：运行多模态路由 demo。"""
    print("=" * 60)
    print("LangGraph Customer Service Agent")
    print("版本: V4-lite | Phase 7.2")
    print("=" * 60)

    for demo in _DEMOS:
        label = f"{demo['id']}: {demo['msg'] or '(图片)'}"
        print(f"\n--- {label} ---")
        state = run_graph(create_initial_state(
            session_id=demo['id'],
            user_message=demo['msg'],
            image_url=demo['img'],
        ))
        _show_summary(state)
        _show_highlights(state)
        print(json.dumps(state, ensure_ascii=False, indent=2))

    # 先文字后图片 demo
    print(f"\n--- {_INSTALL_DEMO_1['id']} 第一轮: {_INSTALL_DEMO_1['msg']} ---")
    state1 = run_graph(create_initial_state(
        session_id=_INSTALL_DEMO_1['id'],
        user_message=_INSTALL_DEMO_1['msg'],
        image_url=_INSTALL_DEMO_1['img'],
    ))
    print(json.dumps(state1, ensure_ascii=False, indent=2))

    print(f"\n--- {_INSTALL_DEMO_2['id']} 第二轮: (图片) ---")
    state2 = run_graph(create_initial_state(
        session_id=_INSTALL_DEMO_2['id'],
        user_message=_INSTALL_DEMO_2['msg'],
        image_url=_INSTALL_DEMO_2['img'],
    ))
    _show_summary(state2)
    _show_highlights(state2)
    print(json.dumps(state2, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
