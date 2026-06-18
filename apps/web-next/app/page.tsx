"use client";

import { useCallback, useEffect, useRef, useState } from "react";

// ── Types ──

type Message = {
  role: "user" | "assistant";
  content: string;
  time: string;
};

type AgentResponse = {
  reply: string;
  intent: string | null;
  emotion: string;
  emotion_score: number;
  customer_stage: string;
  selected_skill: string | null;
  policy_decision: string | null;
  need_human: boolean;
  human_reason: string | null;
  logs: { node: string; summary: string }[];
  state?: Record<string, unknown>;
};

type Status = "idle" | "loading" | "success" | "error";

const API_URL = "http://127.0.0.1:8003";

const DEMOS: { emoji: string; label: string; msg: string; img: string }[] = [
  { emoji: "👕", label: "商品材质", msg: "这个衣服是什么材质", img: "" },
  { emoji: "📏", label: "尺码追问", msg: "有什么码数", img: "" },
  { emoji: "🎯", label: "售前推荐", msg: "有没有推荐", img: "" },
  { emoji: "💰", label: "退款请求", msg: "质量太差了我要退款", img: "" },
  { emoji: "⚠️", label: "投诉转人工", msg: "你们这个太垃圾了，我要投诉", img: "" },
  { emoji: "🖼️", label: "纯图片", msg: "", img: "https://example.com/test.jpg" },
  { emoji: "🔄", label: "图文测试", msg: "这个破了能退吗", img: "https://example.com/test.jpg" },
  { emoji: "👋", label: "闲聊", msg: "你好，在吗", img: "" },
];

// ── Helpers ──

function generateId(): string {
  return Math.random().toString(36).substring(2, 10);
}

function getSessionId(): string {
  if (typeof window === "undefined") return "ssr";
  let sid = localStorage.getItem("session_id");
  if (!sid) {
    sid = generateId();
    localStorage.setItem("session_id", sid);
  }
  return sid;
}

function resetSessionId(): string {
  const sid = generateId();
  localStorage.setItem("session_id", sid);
  return sid;
}

function now(): string {
  return new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
}

// ── Page ──

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [lastResponse, setLastResponse] = useState<AgentResponse | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [statusText, setStatusText] = useState("idle");
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState(getSessionId());
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Check FastAPI health
  useEffect(() => {
    fetch(`${API_URL}/api/health`)
      .then((r) => setApiOk(r.status === 200))
      .catch(() => setApiOk(false));
  }, []);

  const send = useCallback(
    async (userMessage: string, imageUrl = "") => {
      if (!userMessage && !imageUrl) return;
      if (status === "loading") return;

      const time = now();
      setMessages((prev) => [...prev, { role: "user", content: userMessage || "(图片)", time }]);
      setStatus("loading");
      setStatusText("Agent 正在分析…");

      try {
        const res = await fetch(`${API_URL}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: sessionId,
            user_message: userMessage,
            image_url: imageUrl || null,
            image_base64: null,
            return_full_state: true,
          }),
        });

        if (!res.ok) {
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: `⚠️ 请求失败 (${res.status})`, time: now() },
          ]);
          setStatus("error");
          return;
        }

        const data: AgentResponse & { state?: Record<string, unknown> } = await res.json();
        setLastResponse(data);
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: data.reply || "(无回复)", time: now() },
        ]);
        setStatus("success");
        setStatusText("请求成功");
      } catch {
        setApiOk(false);
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: "⛔ FastAPI 服务未连接，请先启动 uvicorn app.server:app --reload --port 8003",
            time: now(),
          },
        ]);
        setStatus("error");
      }
    },
    [sessionId, status]
  );

  const handleSend = () => {
    const msg = input.trim();
    if (!msg) return;
    setInput("");
    send(msg);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const clearChat = () => {
    setMessages([]);
    setLastResponse(null);
    setStatus("idle");
    setStatusText("idle");
  };

  const newSession = () => {
    const sid = resetSessionId();
    setSessionId(sid);
    clearChat();
  };

  const d = lastResponse;

  return (
    <div style={styles.wrapper}>
      {/* Top Bar */}
      <header style={styles.topbar}>
        <div>
          <h1 style={styles.title}>🤖 LangGraph 电商客服 Agent</h1>
          <p style={styles.subtitle}>多轮上下文 · 本地知识库 · SQLite 持久化 · LLM Provider 插槽</p>
        </div>
        <div style={styles.statusRow}>
          <span style={{ ...styles.dot, background: apiOk ? "#34C759" : "#FF3B30" }} />
          <span style={styles.statusLabel}>{apiOk ? "Connected" : "Disconnected"}</span>
        </div>
      </header>

      {/* Main */}
      <div style={styles.main}>
        {/* Left: Demos */}
        <aside style={styles.leftPanel}>
          <div style={styles.card}>
            <h3 style={styles.cardTitle}>⚡ 快速体验</h3>
            <div style={styles.demoGrid}>
              {DEMOS.map((d, i) => (
                <button
                  key={i}
                  style={styles.demoBtn}
                  disabled={status === "loading"}
                  onClick={() => send(d.msg, d.img)}
                >
                  {d.emoji} {d.label}
                </button>
              ))}
            </div>
          </div>

          <div style={styles.card}>
            <h3 style={styles.cardTitle}>⚙️ 会话</h3>
            <button style={styles.secondaryBtn} onClick={clearChat} disabled={status === "loading"}>
              🗑️ 清空对话
            </button>
            <button style={{ ...styles.secondaryBtn, marginTop: 4 }} onClick={newSession} disabled={status === "loading"}>
              🔄 新会话
            </button>
            <p style={{ fontSize: 11, color: "#8896A6", marginTop: 6 }}>Session: {sessionId}</p>
          </div>
        </aside>

        {/* Center: Chat */}
        <main style={styles.centerPanel}>
          <div style={styles.chatArea}>
            {messages.length === 0 && (
              <div style={styles.welcome}>
                <div style={{ fontSize: 40, marginBottom: 8 }}>💬</div>
                <h3 style={{ color: "#1A2332", margin: 0 }}>欢迎使用 LangGraph 电商客服 Agent</h3>
                <p style={{ color: "#8896A6", fontSize: 14 }}>左侧点击场景或输入文字开始体验</p>
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} style={{ display: "flex", marginBottom: 16, justifyContent: m.role === "user" ? "flex-end" : "flex-start" }}>
                <div
                  style={{
                    maxWidth: "75%",
                    padding: "10px 16px",
                    borderRadius: m.role === "user" ? "18px 18px 4px 18px" : "18px 18px 18px 4px",
                    background: m.role === "user" ? "#1A73E8" : "white",
                    color: m.role === "user" ? "white" : "#1A2332",
                    border: m.role === "assistant" ? "1px solid #E8ECF0" : "none",
                    fontSize: 14,
                    lineHeight: 1.5,
                    whiteSpace: "pre-wrap",
                  }}
                >
                  {m.content}
                </div>
              </div>
            ))}
            {status === "loading" && (
              <div style={{ textAlign: "center", padding: 12, color: "#1A73E8", fontSize: 13 }}>
                ⏳ Agent 正在分析…
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Input */}
          <div style={styles.inputArea}>
            <textarea
              ref={textareaRef}
              style={styles.textarea}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="请输入您的问题… (Enter 发送)"
              rows={2}
            />
            <button style={styles.sendBtn} disabled={status === "loading" || !input.trim()} onClick={handleSend}>
              发送
            </button>
          </div>
        </main>

        {/* Right: Trace */}
        <aside style={styles.rightPanel}>
          <div style={styles.card}>
            <h3 style={styles.cardTitle}>🔍 Agent 分析</h3>
            {d ? (
              <>
                <div style={styles.grid}>
                  <div style={styles.item}>
                    <div style={styles.label}>🎯 意图</div>
                    <div style={styles.value}>{d.intent || "—"}</div>
                  </div>
                  <div style={styles.item}>
                    <div style={styles.label}>😊 情绪</div>
                    <div style={styles.value}>{d.emotion} ({d.emotion_score})</div>
                  </div>
                  <div style={styles.item}>
                    <div style={styles.label}>📌 阶段</div>
                    <div style={styles.value}>{d.customer_stage || "—"}</div>
                  </div>
                  <div style={styles.item}>
                    <div style={styles.label}>⚙️ 技能</div>
                    <div style={styles.value}>{d.selected_skill || "—"}</div>
                  </div>
                </div>
                {d.policy_decision && (
                  <div style={{ ...styles.item, marginTop: 6 }}>
                    <div style={styles.label}>📋 策略</div>
                    <div style={styles.value}>{d.policy_decision}</div>
                  </div>
                )}
                <div style={{ ...styles.item, marginTop: 6 }}>
                  <div style={styles.label}>👤 转人工</div>
                  <div style={{ ...styles.value, color: d.need_human ? "#C62828" : "#2E7D32" }}>
                    {d.need_human ? "是" : "否"}
                  </div>
                </div>
                {d.human_reason && <p style={{ fontSize: 12, color: "#8896A6", marginTop: 2 }}>{d.human_reason}</p>}
              </>
            ) : (
              <p style={{ color: "#B0BCC9", fontSize: 13, textAlign: "center", padding: "24px 0" }}>
                发送消息后<br />分析结果在此显示
              </p>
            )}
          </div>

          {/* Logs */}
          <details style={{ marginBottom: 8 }}>
            <summary style={styles.summary}>📋 执行日志 ({d?.logs?.length || 0})</summary>
            <div style={{ marginTop: 6 }}>
              {d?.logs?.map((log, i) => (
                <div key={i} style={styles.logLine}>
                  <span style={styles.logDot} />
                  <span style={styles.logName}>{log.node}</span>
                  <span style={styles.logSum}>{log.summary}</span>
                </div>
              ))}
              {(!d || !d.logs?.length) && <p style={{ fontSize: 12, color: "#8896A6" }}>暂无日志</p>}
            </div>
          </details>

          {/* Raw Response */}
          <details>
            <summary style={styles.summary}>📄 原始 API 响应</summary>
            <pre style={styles.code}>{JSON.stringify(d, null, 2) || "暂无数据"}</pre>
          </details>
        </aside>
      </div>
    </div>
  );
}

// ── Styles ──

const styles: Record<string, React.CSSProperties> = {
  wrapper: { minHeight: "100vh", background: "#F5F7FA", display: "flex", flexDirection: "column" },
  topbar: {
    background: "white", borderBottom: "1px solid #E8ECF0",
    padding: "12px 24px", display: "flex", alignItems: "center", justifyContent: "space-between",
  },
  title: { margin: 0, fontSize: 16, fontWeight: 700, color: "#1A2332" },
  subtitle: { margin: 0, fontSize: 12, color: "#8896A6", marginTop: 2 },
  statusRow: { display: "flex", alignItems: "center", gap: 6 },
  dot: { width: 8, height: 8, borderRadius: "50%", display: "inline-block" },
  statusLabel: { fontSize: 12, fontWeight: 500, color: "#5F6B7A" },

  main: { flex: 1, display: "flex", gap: 12, padding: 12, overflow: "hidden" },
  leftPanel: { width: 200, flexShrink: 0, display: "flex", flexDirection: "column", gap: 12 },
  centerPanel: { flex: 1, display: "flex", flexDirection: "column", minWidth: 0 },
  rightPanel: { width: 280, flexShrink: 0, display: "flex", flexDirection: "column", gap: 8 },

  card: {
    background: "white", border: "1px solid #E8ECF0", borderRadius: 12, padding: 12,
  },
  cardTitle: { margin: 0, fontSize: 11, fontWeight: 600, color: "#8896A6", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 8 },
  demoGrid: { display: "flex", flexDirection: "column", gap: 4 },
  demoBtn: {
    padding: "8px 12px", fontSize: 13, fontWeight: 500, color: "#1A2332",
    background: "#F5F7FA", border: "1px solid #E8ECF0", borderRadius: 8,
    cursor: "pointer", textAlign: "left" as const,
  },
  secondaryBtn: {
    width: "100%", padding: "6px 12px", fontSize: 12, fontWeight: 500,
    background: "white", border: "1px solid #E8ECF0", borderRadius: 8,
    cursor: "pointer", color: "#5F6B7A",
  },

  chatArea: { flex: 1, overflowY: "auto", padding: "0 4px" },
  welcome: { textAlign: "center" as const, padding: "60px 0" },

  inputArea: {
    display: "flex", gap: 8, padding: "8px 0",
    background: "white", borderTop: "1px solid #E8ECF0",
  },
  textarea: {
    flex: 1, padding: 10, fontSize: 14, border: "1px solid #E8ECF0",
    borderRadius: 8, resize: "none", outline: "none", fontFamily: "inherit",
  },
  sendBtn: {
    padding: "10px 20px", fontSize: 14, fontWeight: 600, color: "white",
    background: "#1A73E8", border: "none", borderRadius: 8, cursor: "pointer",
  },

  grid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4 },
  item: { background: "#F8F9FB", borderRadius: 8, padding: "6px 10px" },
  label: { fontSize: 10, color: "#8896A6", marginBottom: 1 },
  value: { fontSize: 13, fontWeight: 600, color: "#1A2332" },

  summary: { fontSize: 12, fontWeight: 500, color: "#5F6B7A", cursor: "pointer" },
  logLine: { display: "flex", alignItems: "center", gap: 6, padding: "3px 0", fontSize: 12, borderBottom: "1px solid #F0F2F5" },
  logDot: { width: 6, height: 6, borderRadius: "50%", background: "#34C759", flexShrink: 0 },
  logName: { fontWeight: 500, color: "#1A2332", minWidth: 100, fontSize: 12 },
  logSum: { color: "#8896A6", fontSize: 11 },
  code: {
    fontSize: 11, background: "#F8F9FB", padding: 8, borderRadius: 8,
    overflow: "auto", maxHeight: 300, whiteSpace: "pre" as const,
  },
};
