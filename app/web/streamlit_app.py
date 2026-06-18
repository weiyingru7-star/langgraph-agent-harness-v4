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
    page_title="LangGraph 客服 Agent Demo",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

FASTAPI_URL = "http://127.0.0.1:8003"
API_TIMEOUT = 30

# ── 自定义 CSS ──
st.markdown("""
<style>
    .stApp { background: #FAFBFC; }
    .app-header {
        background: linear-gradient(135deg, #1E88E5 0%, #1565C0 100%);
        padding: 1.2rem 2rem; border-radius: 12px; margin-bottom: 1.5rem; color: white;
    }
    .app-header h1 { margin: 0; font-size: 1.5rem; font-weight: 600; }
    .app-header p { margin: 0.2rem 0 0 0; font-size: 0.85rem; opacity: 0.85; }
    .status-badge { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 20px; font-size: 0.75rem; font-weight: 500; }
    .status-connected { background: #E8F5E9; color: #2E7D32; }
    .status-disconnected { background: #FFEBEE; color: #C62828; }
    .card { background: white; border: 1px solid #E8EAED; border-radius: 12px; padding: 1.2rem; margin-bottom: 1rem; }
    .card-title { font-size: 0.75rem; font-weight: 600; color: #5F6368; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.8rem; }
    .analysis-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; }
    .analysis-item { background: #F8F9FA; border-radius: 8px; padding: 0.5rem 0.7rem; }
    .analysis-label { font-size: 0.65rem; color: #5F6368; margin-bottom: 0.15rem; }
    .analysis-value { font-size: 0.85rem; font-weight: 600; color: #1A1A2E; }
    .trace-node { display: flex; align-items: center; gap: 0.5rem; padding: 0.3rem 0; font-size: 0.8rem; border-bottom: 1px solid #F0F0F0; }
    .trace-dot { width: 8px; height: 8px; border-radius: 50%; background: #43A047; flex-shrink: 0; }
    .trace-node-name { font-weight: 500; color: #1A1A2E; min-width: 8rem; }
    .trace-summary { color: #5F6368; font-size: 0.75rem; }
    .welcome-card { text-align: center; padding: 3rem 1rem; color: #5F6368; }
    .welcome-card h3 { color: #1A1A2E; font-size: 1.1rem; margin-bottom: 0.5rem; }
    .error-box { background: #FFF3E0; border: 1px solid #FFE0B2; border-radius: 8px; padding: 1rem; margin: 1rem 0; }
    .error-title { font-weight: 600; color: #E65100; margin-bottom: 0.3rem; }
    .error-code { background: #FFF8E1; padding: 0.5rem; border-radius: 4px; font-family: monospace; font-size: 0.8rem; margin-top: 0.5rem; }
    /* 输入区固定底部 */
    .input-area {
        position: sticky; bottom: 0; background: white; padding: 0.8rem 0 0 0;
        border-top: 1px solid #E8EAED; margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ── Session 状态初始化 ──
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_response" not in st.session_state:
    st.session_state.last_response = None
if "last_payload" not in st.session_state:
    st.session_state.last_payload = None
if "fastapi_ok" not in st.session_state:
    st.session_state.fastapi_ok = None
if "processing" not in st.session_state:
    st.session_state.processing = False

# ── 辅助函数 ──

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

    # 保存请求体用于调试
    payload = {
        "session_id": st.session_state.session_id,
        "user_message": user_message,
        "image_url": image_url or None,
        "image_base64": None,
        "return_full_state": return_full_state,
    }
    st.session_state.last_payload = payload

    # 显示用户消息
    display_text = user_message if user_message else "(图片)"
    st.session_state.messages.append({
        "role": "user", "content": display_text,
        "image": image_url or None, "time": now,
    })
    data = call_api(user_message, image_url, return_full_state)
    if data is None:
        st.session_state.messages.append({
            "role": "assistant", "content": "⛔ 无法连接到 FastAPI 服务。请确认 FastAPI 已启动。",
            "time": now, "error": True,
        })
    elif "error" in data:
        st.session_state.messages.append({
            "role": "assistant", "content": f"⚠️ 请求异常: {data['error']}",
            "time": now, "error": True,
        })
    else:
        reply = data.get("reply")
        if not reply:
            reply = "后端未返回 reply，请检查 API response 或 generate_reply 节点。"
        st.session_state.messages.append({
            "role": "assistant", "content": reply,
            "time": now,
        })
        st.session_state.last_response = data
    st.session_state.processing = False


# ══════════════════════════════════════════════════════════
#  页面渲染
# ══════════════════════════════════════════════════════════

# ── Header ──
check_fastapi()
status_class = "status-connected" if st.session_state.fastapi_ok else "status-disconnected"
status_text = "● Connected" if st.session_state.fastapi_ok else "● Disconnected"

st.markdown(f"""
<div class="app-header">
    <div style="display:flex;justify-content:space-between;align-items:center;">
        <div>
            <h1>🤖 LangGraph 电商客服 Agent Harness</h1>
            <p>支持文本 / 图片 / 图文输入的电商客服 Agent 演示 · V4-lite Portfolio Demo</p>
        </div>
        <div><span class="status-badge {status_class}">{status_text}</span></div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── 三列布局 ──
left_col, center_col, right_col = st.columns([1, 1.4, 1], gap="medium")

# ════════════════════════════════════════════════
#  左列：Demo 按钮 + 高级设置
# ════════════════════════════════════════════════
with left_col:
    # Demo 按钮
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">⚡ 快速体验</div>', unsafe_allow_html=True)
    st.caption("点击后自动发送，无需手动输入")

    demo_scenarios = [
        ("📦", "物流查询", "我的快递怎么还没到", ""),
        ("💰", "退款请求", "质量太差了我要退款", ""),
        ("👕", "商品咨询", "这个衣服是什么材质", ""),
        ("🫵", "转人工", "我要人工，太生气了", ""),
        ("⚠️", "投诉", "你们这个太垃圾了，我要投诉", ""),
        ("👋", "闲聊", "你好，在吗", ""),
        ("🖼️", "纯图片", "", "https://example.com/test.jpg"),
        ("🔍", "图文测试", "这个破了能退吗", "https://example.com/broken.jpg"),
    ]

    disabled = st.session_state.processing
    for i in range(0, len(demo_scenarios), 2):
        cols = st.columns(2)
        for j in range(2):
            if i + j < len(demo_scenarios):
                emoji, label, msg, img = demo_scenarios[i + j]
                with cols[j]:
                    if st.button(f"{emoji} {label}", use_container_width=True, key=f"demo_{i+j}", disabled=disabled):
                        send_message(msg, img, True)
    st.markdown('</div>', unsafe_allow_html=True)

    # 高级设置
    with st.expander("⚙️ 高级设置", expanded=False):
        st.text_input("会话 ID", value=st.session_state.session_id, key="sid_input",
                      placeholder="自动生成", label_visibility="collapsed")
        if st.button("🔄 新会话", use_container_width=True, disabled=st.session_state.processing):
            st.session_state.session_id = str(uuid.uuid4())[:8]
            st.session_state.messages = []
            st.session_state.last_response = None
            st.rerun()

        st.text_input("图片 URL（可选）", key="img_input",
                      placeholder="https://example.com/image.jpg", label_visibility="collapsed")

        with st.container():
            return_full = st.checkbox("返回完整 State 调试信息", value=True)

        st.caption(f"API: {FASTAPI_URL}")

# ════════════════════════════════════════════════
#  中列：聊天区 + 输入框
# ════════════════════════════════════════════════
with center_col:
    st.markdown("#### 💬 对话")

    # 聊天展示（用户消息 + AI 回复）
    if not st.session_state.messages:
        st.markdown("""
        <div class="welcome-card">
            <h3>👋 欢迎使用 LangGraph 电商客服 Agent</h3>
            <p style="font-size:0.9rem;">
                点击左侧场景按钮或直接在下方输入问题体验。
            </p>
            <p style="font-size:0.8rem;margin-top:1rem;color:#9E9E9E;">
                支持文本、图片、图文混合输入
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # 聊天展示 — 使用必定可见的 Streamlit 原生组件
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.info(f"🧑 **你**: {msg['content']}", icon="🧑")
            else:
                content = msg["content"]
                if content:
                    st.success(f"🤖 **Agent**: {content}", icon="🤖")
                else:
                    st.warning("🤖 Agent 回复为空", icon="⚠️")

    # 清空按钮
    if st.session_state.messages:
        if st.button("🗑️ 清空对话"):
            st.session_state.messages = []
            st.session_state.last_response = None
            st.rerun()

    st.divider()

    # ── 输入区（在聊天区底部） ──
    with st.container():
        st.markdown("##### ✏️ 输入消息")
        user_msg_col, send_col = st.columns([4, 1])
        with user_msg_col:
            user_msg = st.text_input(
                "消息内容", key="msg_input",
                placeholder="请输入您的问题…", label_visibility="collapsed",
            )
        with send_col:
            btn_disabled = st.session_state.processing
            if st.button("📨 发送", type="primary", use_container_width=True, disabled=btn_disabled):
                img_url = st.session_state.get("img_input", "")
                send_message(user_msg, img_url, return_full)

        if st.session_state.processing:
            st.info("⏳ Agent 处理中…")
        elif st.session_state.last_response:
            st.success("✅ 请求成功")
            # 调试区
            with st.expander("📦 原始 API 响应", expanded=False):
                st.json(st.session_state.last_response)
            with st.expander("📤 本次请求体", expanded=False):
                if st.session_state.last_payload:
                    st.json(st.session_state.last_payload)

# ════════════════════════════════════════════════
#  右列：Agent 分析面板 + Trace
# ════════════════════════════════════════════════
with right_col:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">🔍 Agent 分析</div>', unsafe_allow_html=True)

    data = st.session_state.last_response
    if data:
        intent = data.get("intent") or "—"
        emotion = data.get("emotion") or "—"
        emotion_score = data.get("emotion_score", 0)
        stage = data.get("customer_stage") or "—"
        skill = data.get("selected_skill") or "—"
        policy = data.get("policy_decision") or "—"
        need_human = data.get("need_human", False)
        human_reason = data.get("human_reason")

        st.markdown(f"""
        <div class="analysis-grid">
            <div class="analysis-item"><div class="analysis-label">🎯 意图</div><div class="analysis-value">{intent}</div></div>
            <div class="analysis-item"><div class="analysis-label">😊 情绪</div><div class="analysis-value">{emotion} ({emotion_score})</div></div>
            <div class="analysis-item"><div class="analysis-label">📌 客户阶段</div><div class="analysis-value">{stage}</div></div>
            <div class="analysis-item"><div class="analysis-label">⚙️ 路由技能</div><div class="analysis-value">{skill}</div></div>
        </div>
        """, unsafe_allow_html=True)

        if policy != "—":
            st.markdown(f"""
            <div class="analysis-item" style="margin-top:0.5rem;">
                <div class="analysis-label">📋 策略决策</div><div class="analysis-value">{policy}</div>
            </div>
            """, unsafe_allow_html=True)

        human_label = "🟢 否" if not need_human else "🔴 是"
        st.markdown(f"""
        <div class="analysis-item" style="margin-top:0.5rem;">
            <div class="analysis-label">👤 转人工</div>
            <div class="analysis-value" style="color:{'#C62828' if need_human else '#2E7D32'}">{human_label}</div>
        </div>
        """, unsafe_allow_html=True)

        if human_reason:
            st.markdown(f"""
            <div style="font-size:0.75rem;color:#5F6368;margin-top:0.3rem;">原因：{human_reason}</div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="text-align:center;padding:2rem 0;color:#9E9E9E;font-size:0.85rem;">
            发送一条消息后<br>分析结果将在此显示
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # Logs Trace
    with st.expander("📋 执行日志 Trace", expanded=False):
        if data and data.get("logs"):
            for log in data["logs"]:
                summary = log.get("summary", "")
                node = log.get("node", "")
                st.markdown(f"""
                <div class="trace-node"><div class="trace-dot"></div><div class="trace-node-name">{node}</div><div class="trace-summary">{summary}</div></div>
                """, unsafe_allow_html=True)
        else:
            st.text("暂无日志")

    # Full State
    with st.expander("📄 完整 State JSON", expanded=False):
        if data and return_full:
            st.json(data.get("state", data))
        elif data:
            st.json(data)
        else:
            st.text("暂无数据")

    # FastAPI 连接提示
    if st.session_state.fastapi_ok is False:
        st.markdown(f"""
        <div class="error-box">
            <div class="error-title">⛔ FastAPI 未启动</div>
            <div style="font-size:0.85rem;color:#BF360C;">请在终端启动 FastAPI 服务：</div>
            <div class="error-code">.venv/bin/python -m uvicorn app.server:app --reload --port 8003</div>
        </div>
        """, unsafe_allow_html=True)
