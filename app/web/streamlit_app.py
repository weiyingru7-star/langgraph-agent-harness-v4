"""
streamlit_app.py — LangGraph 电商客服 Agent 演示页面。

Streamlit 只是展示层，通过 HTTP 调用 FastAPI /api/chat。
不包含业务逻辑。
"""

import uuid
from datetime import datetime

import httpx
import streamlit as st

# ── 页面配置 ──
st.set_page_config(
    page_title="LangGraph 客服 Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

FASTAPI_URL = "http://127.0.0.1:8003"
API_TIMEOUT = 30

# ── CSS 完全重写 ──
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    * { font-family: 'Inter', -apple-system, sans-serif; }
    .stApp { background: #F5F7FA; }

    /* 顶部导航栏 */
    .topbar {
        background: white;
        border-bottom: 1px solid #E8ECF0;
        padding: 0.7rem 1.5rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin: -1rem -1rem 1rem -1rem;
    }
    .topbar-title {
        font-weight: 700; font-size: 1rem; color: #1A2332;
        display: flex; align-items: center; gap: 0.5rem;
    }
    .topbar-sub {
        font-size: 0.75rem; color: #8896A6;
    }
    .status-dot {
        display: inline-block; width: 8px; height: 8px; border-radius: 50%;
        margin-right: 0.3rem;
    }
    .status-dot.on { background: #34C759; }
    .status-dot.off { background: #FF3B30; }
    .status-label { font-size: 0.75rem; font-weight: 500; color: #5F6B7A; }

    /* 侧边卡片 */
    .side-card {
        background: white;
        border: 1px solid #E8ECF0;
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .side-card-title {
        font-size: 0.7rem; font-weight: 600; color: #8896A6;
        text-transform: uppercase; letter-spacing: 0.06em;
        margin-bottom: 0.7rem;
    }

    /* Demo 按钮 */
    .demo-btn {
        display: inline-flex; align-items: center; gap: 0.4rem;
        background: #F5F7FA; border: 1px solid #E8ECF0;
        border-radius: 8px; padding: 0.45rem 0.7rem;
        font-size: 0.8rem; font-weight: 500; color: #1A2332;
        cursor: pointer; transition: all 0.15s; width: 100%;
        justify-content: center;
    }
    .demo-btn:hover { background: #EEF1F5; border-color: #D0D5DD; }

    /* 聊天气泡容器 */
    .chat-area {
        padding: 0.5rem 0;
    }
    .msg-row {
        display: flex; margin-bottom: 1rem;
        align-items: flex-start;
    }
    .msg-row.user { justify-content: flex-end; }
    .msg-row.assistant { justify-content: flex-start; }

    .msg-avatar {
        width: 32px; height: 32px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 0.9rem; flex-shrink: 0;
    }
    .msg-avatar.user {
        background: #E8F0FE; margin-left: 0.5rem; order: 1;
    }
    .msg-avatar.assistant {
        background: #E8F5E9; margin-right: 0.5rem; order: -1;
    }

    .msg-bubble {
        max-width: 80%;
        padding: 0.7rem 1rem;
        font-size: 0.85rem;
        line-height: 1.5;
        white-space: pre-wrap;
    }
    .msg-bubble.user {
        background: #1A73E8;
        color: white;
        border-radius: 18px 18px 4px 18px;
    }
    .msg-bubble.assistant {
        background: white;
        color: #1A2332;
        border: 1px solid #E8ECF0;
        border-radius: 18px 18px 18px 4px;
    }
    .msg-time {
        font-size: 0.6rem; color: #8896A6;
        margin-top: 0.2rem; padding: 0 0.3rem;
    }
    .msg-row.user .msg-time { text-align: right; }

    /* 输入区 */
    .input-area {
        background: white;
        border: 1px solid #E8ECF0;
        border-radius: 12px;
        padding: 0.8rem 1rem;
    }

    /* 分析网格 */
    .analysis-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.4rem;
    }
    .a-item {
        background: #F8F9FB;
        border-radius: 8px;
        padding: 0.5rem 0.7rem;
    }
    .a-label { font-size: 0.6rem; color: #8896A6; margin-bottom: 0.1rem; }
    .a-value { font-size: 0.85rem; font-weight: 600; color: #1A2332; }

    /* 日志 trace */
    .trace-line {
        display: flex; align-items: center; gap: 0.5rem;
        padding: 0.25rem 0; font-size: 0.75rem;
        border-bottom: 1px solid #F0F2F5;
    }
    .trace-dot {
        width: 6px; height: 6px; border-radius: 50%;
        background: #34C759; flex-shrink: 0;
    }
    .trace-name { font-weight: 500; color: #1A2332; min-width: 7rem; }
    .trace-summary { color: #8896A6; }

    /* 欢迎卡片 */
    .welcome {
        text-align: center; padding: 4rem 1rem;
    }
    .welcome h3 { color: #1A2332; font-size: 1.1rem; margin-bottom: 0.5rem; }
    .welcome p { color: #8896A6; font-size: 0.85rem; }

    /* 错误提示 */
    .err-box {
        background: #FFF5F5; border: 1px solid #FFD7D5;
        border-radius: 8px; padding: 0.8rem; margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ── Session 状态 ──
for key in ["session_id", "messages", "last_response", "last_payload",
            "fastapi_ok", "processing", "demo_msg", "demo_img"]:
    if key not in st.session_state:
        if key == "session_id":
            st.session_state[key] = str(uuid.uuid4())[:8]
        elif key in ("messages",):
            st.session_state[key] = []
        elif key in ("last_response", "last_payload"):
            st.session_state[key] = None
        elif key == "fastapi_ok":
            st.session_state[key] = None
        elif key == "processing":
            st.session_state[key] = False
        else:
            st.session_state[key] = ""


def check_fastapi():
    try:
        r = httpx.get(f"{FASTAPI_URL}/api/health", timeout=3)
        st.session_state.fastapi_ok = r.status_code == 200
    except Exception:
        st.session_state.fastapi_ok = False


def call_api(user_message, image_url, return_full_state):
    payload = {
        "session_id": st.session_state.session_id,
        "user_message": user_message,
        "image_url": image_url or None,
        "image_base64": None,
        "return_full_state": return_full_state,
    }
    try:
        resp = httpx.post(f"{FASTAPI_URL}/api/chat", json=payload, timeout=API_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        st.session_state.fastapi_ok = False
        return None
    except Exception as e:
        return {"error": str(e)}


def send_message(user_message, image_url="", return_full_state=True):
    if not user_message and not image_url:
        st.warning("请输入文本或图片 URL")
        return
    st.session_state.processing = True
    now = datetime.now().strftime("%H:%M")

    payload = {
        "session_id": st.session_state.session_id,
        "user_message": user_message,
        "image_url": image_url or None,
        "image_base64": None,
        "return_full_state": return_full_state,
    }
    st.session_state.last_payload = payload

    display_text = user_message if user_message else "(图片)"
    st.session_state.messages.append({
        "role": "user", "content": display_text,
        "image": image_url or None, "time": now,
    })
    data = call_api(user_message, image_url, return_full_state)
    if data is None:
        st.session_state.messages.append({
            "role": "assistant", "content": "⛔ FastAPI 连接失败，请确认服务已启动",
            "time": now, "error": True,
        })
    elif "error" in data:
        st.session_state.messages.append({
            "role": "assistant", "content": f"⚠️ {data['error']}",
            "time": now, "error": True,
        })
    else:
        reply = data.get("reply") or "后端未返回 reply"
        st.session_state.messages.append({
            "role": "assistant", "content": reply, "time": now,
        })
        st.session_state.last_response = data
    st.session_state.processing = False


# ════════════════════════════════════
#  页面渲染
# ════════════════════════════════════

check_fastapi()
status = "on" if st.session_state.fastapi_ok else "off"

st.markdown(f"""
<div class="topbar">
    <div>
        <div class="topbar-title">🤖 LangGraph 电商客服 Agent</div>
        <div class="topbar-sub">文本 / 图片 / 图文 · V4-lite Portfolio Demo</div>
    </div>
    <div style="display:flex;align-items:center;gap:0.5rem;">
        <span class="status-dot {status}"></span>
        <span class="status-label">{"Connected" if st.session_state.fastapi_ok else "Disconnected"}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── 三列布局 ──
cols = st.columns([1, 1.5, 1.1], gap="small")
left_col, center_col, right_col = cols

# ═══════════════════ 左列 ═══════════════════
with left_col:
    st.markdown('<div class="side-card">', unsafe_allow_html=True)
    st.markdown('<div class="side-card-title">⚡ 快速体验</div>', unsafe_allow_html=True)

    demos = [
        ("📦", "物流查询", "我的快递怎么还没到", ""),
        ("💰", "退款请求", "质量太差了我要退款", ""),
        ("👕", "商品咨询", "这个衣服是什么材质", ""),
        ("🫵", "转人工", "我要人工，太生气了", ""),
        ("⚠️", "投诉", "你们这个太垃圾了，我要投诉", ""),
        ("👋", "闲聊", "你好，在吗", ""),
        ("🖼️", "纯图片", "", "https://example.com/test.jpg"),
        ("🔍", "图文", "这个破了能退吗", "https://example.com/broken.jpg"),
    ]
    d = st.session_state.processing
    for i in range(0, len(demos), 2):
        r = st.columns(2)
        for j in range(2):
            if i + j < len(demos):
                emoji, label, msg, img = demos[i + j]
                with r[j]:
                    if st.button(f"{emoji} {label}", key=f"d{i+j}", disabled=d, use_container_width=True):
                        send_message(msg, img, True)
    st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("⚙️ 高级设置", expanded=False):
        st.text_input("会话 ID", value=st.session_state.session_id, key="sid",
                      label_visibility="collapsed", placeholder="session_id")
        if st.button("🔄 新会话", use_container_width=True, disabled=st.session_state.processing):
            st.session_state.session_id = str(uuid.uuid4())[:8]
            st.session_state.messages = []
            st.session_state.last_response = None
            st.rerun()
        st.text_input("图片 URL", key="img_set", placeholder="https://...", label_visibility="collapsed")
        return_full = st.checkbox("返回完整 State 调试数据", value=True)
        st.caption(f"API: {FASTAPI_URL}")

# ═══════════════════ 中列：聊天 ═══════════════════
with center_col:
    if not st.session_state.messages:
        st.markdown("""
        <div class="welcome">
            <div style="font-size:3rem;margin-bottom:1rem;">💬</div>
            <h3>欢迎使用 LangGraph 电商客服 Agent</h3>
            <p>左侧点击场景或下方输入文字开始体验</p>
            <p style="font-size:0.8rem;color:#B0BCC9;">支持文本 · 图片 · 图文混合输入</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        html = '<div class="chat-area">'
        for m in st.session_state.messages:
            avatar = "🧑" if m["role"] == "user" else "🤖"
            html += f'<div class="msg-row {m["role"]}">'
            html += f'<div class="msg-avatar {m["role"]}">{avatar}</div>'
            html += f'<div><div class="msg-bubble {m["role"]}">{m["content"]}</div>'
            html += f'<div class="msg-time">{m.get("time","")}</div></div></div>'
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)

    if st.session_state.messages:
        if st.button("🗑️ 清空对话"):
            st.session_state.messages = []
            st.session_state.last_response = None
            st.rerun()

    st.divider()

    # 输入区
    st.markdown("<div class='input-area'>", unsafe_allow_html=True)
    cc = st.columns([4, 1])
    with cc[0]:
        user_msg = st.text_input("msg", key="msg_in", placeholder="输入您的问题…",
                                 label_visibility="collapsed")
    with cc[1]:
        bd = st.session_state.processing
        if st.button("发送", type="primary", use_container_width=True, disabled=bd):
            img = st.session_state.get("img_set", "")
            send_message(user_msg, img, return_full)
    if st.session_state.processing:
        st.caption("⏳ 处理中…")
    st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.last_response:
        with st.expander("📦 调试数据", expanded=False):
            tab1, tab2 = st.tabs(["API 响应", "请求体"])
            with tab1: st.json(st.session_state.last_response)
            with tab2:
                if st.session_state.last_payload:
                    st.json(st.session_state.last_payload)

# ═══════════════════ 右列：分析面板 ═══════════════════
with right_col:
    st.markdown('<div class="side-card">', unsafe_allow_html=True)
    st.markdown('<div class="side-card-title">🔍 Agent 分析</div>', unsafe_allow_html=True)

    d = st.session_state.last_response
    if d:
        st.markdown(f"""
        <div class="analysis-grid">
            <div class="a-item"><div class="a-label">🎯 意图</div><div class="a-value">{d.get("intent") or "—"}</div></div>
            <div class="a-item"><div class="a-label">😊 情绪</div><div class="a-value">{d.get("emotion") or "—"} ({d.get("emotion_score",0)})</div></div>
            <div class="a-item"><div class="a-label">📌 阶段</div><div class="a-value">{d.get("customer_stage") or "—"}</div></div>
            <div class="a-item"><div class="a-label">⚙️ 技能</div><div class="a-value">{d.get("selected_skill") or "—"}</div></div>
        </div>
        """, unsafe_allow_html=True)

        if d.get("policy_decision"):
            st.markdown(f'<div class="a-item" style="margin-top:0.4rem;"><div class="a-label">📋 策略</div><div class="a-value">{d["policy_decision"]}</div></div>', unsafe_allow_html=True)

        h = d.get("need_human", False)
        c = "#C62828" if h else "#2E7D32"
        st.markdown(f'<div class="a-item" style="margin-top:0.4rem;"><div class="a-label">👤 转人工</div><div class="a-value" style="color:{c}">{"是" if h else "否"}</div></div>', unsafe_allow_html=True)
        if d.get("human_reason"):
            st.caption(d["human_reason"])
    else:
        st.markdown("<div style='text-align:center;padding:2rem 0;color:#B0BCC9;font-size:0.8rem;'>发送消息后<br>分析结果在此显示</div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Logs
    with st.expander("📋 执行日志", expanded=False):
        if d and d.get("logs"):
            for log in d["logs"]:
                st.markdown(f'<div class="trace-line"><div class="trace-dot"></div><div class="trace-name">{log.get("node","")}</div><div class="trace-summary">{log.get("summary","")}</div></div>', unsafe_allow_html=True)
        else:
            st.text("暂无日志")

    # Full State
    with st.expander("📄 完整 State", expanded=False):
        if d and return_full:
            st.json(d.get("state", d))
        elif d:
            st.json(d)
        else:
            st.text("暂无数据")

    if st.session_state.fastapi_ok is False:
        st.markdown(f"""
        <div class="err-box">
            <strong>⛔ FastAPI 未连接</strong><br>
            <code style="font-size:0.7rem;">.venv/bin/python -m uvicorn app.server:app --reload --port 8003</code>
        </div>
        """, unsafe_allow_html=True)
