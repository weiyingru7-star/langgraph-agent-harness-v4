"use client";

import { useCallback, useEffect, useRef, useState } from "react";

// ── Types ──

type Message = {
  role: "user" | "assistant";
  content: string;
  time: string;
  evidence?: Evidence[];
};

type Evidence = {
  source_file: string;
  score: number;
  text?: string;
};

type SkillResult = {
  action?: string;
  source?: string;
  knowledge_source?: string;
  matched?: boolean;
  evidence?: Evidence[];
  retrieved_chunks?: Evidence[];
  sources?: string[];
  message?: string;
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
  state?: { skill_result?: SkillResult; [key: string]: unknown };
};

// ── Helpers ──

function getRagInfo(d: AgentResponse | null): { skill?: SkillResult; src?: string; ev?: Evidence[] } {
  if (!d) return {};
  const sr = d.state?.skill_result;
  if (!sr) return {};
  const isRag = sr.source === "rag" || sr.source === "rag_llm";
  return { skill: sr, src: sr.source || "", ev: (sr.evidence || sr.retrieved_chunks || []).slice(0, 3) };
}

function generateId() {
  return Math.random().toString(36).substring(2, 10);
}
function getSessionId(): string {
  let sid = "";
  try { sid = localStorage.getItem("session_id") || ""; } catch {}
  if (!sid) { sid = generateId(); try { localStorage.setItem("session_id", sid); } catch {} }
  return sid;
}
function resetSessionId(): string {
  const sid = generateId();
  try { localStorage.setItem("session_id", sid); } catch {}
  return sid;
}
function now() { return new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }); }

const API_URL = "http://127.0.0.1:8003";
const DEMOS = [
  { emoji: "👕", label: "商品材质", msg: "这个衣服是什么材质", img: "" },
  { emoji: "📏", label: "尺码追问", msg: "有什么码数", img: "" },
  { emoji: "🎯", label: "售前推荐", msg: "有没有推荐", img: "" },
  { emoji: "💰", label: "退款请求", msg: "质量太差了我要退款", img: "" },
  { emoji: "⚠️", label: "投诉转人工", msg: "你们这个太垃圾了，我要投诉", img: "" },
  { emoji: "🖼️", label: "纯图片", msg: "", img: "https://example.com/test.jpg" },
  { emoji: "🔄", label: "图文测试", msg: "这个破了能退吗", img: "https://example.com/test.jpg" },
  { emoji: "👋", label: "闲聊", msg: "你好，在吗", img: "" },
];

const RAG_DEMOS = [0, 1, 2, 3, 4, 5, 6, 7].map(i => DEMOS[i]);

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [lastResponse, setLastResponse] = useState<AgentResponse | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => { setSessionId(getSessionId()); }, []);
  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);
  useEffect(() => { fetch(`${API_URL}/api/health`).then(r => setApiOk(r.status === 200)).catch(() => setApiOk(false)); }, []);

  const send = useCallback(async (userMessage: string, imageUrl = "") => {
    if (!userMessage && !imageUrl) return;
    if (status === "loading") return;
    const time = now();
    setMessages(p => [...p, { role: "user", content: userMessage || "(图片)", time }]);
    setStatus("loading");
    try {
      const res = await fetch(`${API_URL}/api/chat`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, user_message: userMessage, image_url: imageUrl || null, image_base64: null, return_full_state: true }),
      });
      if (!res.ok) { setMessages(p => [...p, { role: "assistant", content: `⚠️ 请求失败 (${res.status})`, time: now() }]); setStatus("error"); return; }
      const data: AgentResponse = await res.json();
      setLastResponse(data);
      const sr = data.state?.skill_result;
      const ev = sr?.evidence || sr?.retrieved_chunks || [];
      setMessages(p => [...p, { role: "assistant", content: data.reply || "(无回复)", time: now(), evidence: ev.length > 0 ? ev.slice(0, 3) : undefined }]);
      setStatus("success");
    } catch {
      setApiOk(false);
      setMessages(p => [...p, { role: "assistant", content: "⛔ FastAPI 服务未连接", time: now() }]);
      setStatus("error");
    }
  }, [sessionId, status]);

  const d = lastResponse;
  const { skill: ragSkill, src: ragSrc, ev: ragEv } = getRagInfo(d);

  return (
    <div style={styles.wrapper}>
      <header style={styles.topbar}>
        <div>
          <h1 style={styles.title}>🤖 LangGraph 电商客服 Agent</h1>
          <p style={styles.subtitle}>多轮上下文 · 本地知识库 · SQLite · RAG · DeepSeek</p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ width: 8, height: 8, borderRadius: "50%", background: apiOk ? "#34C759" : "#FF3B30", display: "inline-block" }} />
          <span style={{ fontSize: 12, fontWeight: 500, color: "#5F6B7A" }}>{apiOk ? "Connected" : "Disconnected"}</span>
        </div>
      </header>
      <div style={styles.main}>
        {/* Left */}
        <aside style={styles.leftPanel}>
          <div style={styles.card}>
            <h3 style={styles.cardTitle}>⚡ 快速体验</h3>
            <div style={styles.demoGrid}>
              {DEMOS.map((d, i) => (
                <button key={i} style={styles.demoBtn} disabled={status === "loading"} onClick={() => send(d.msg, d.img)}>{d.emoji} {d.label}</button>
              ))}
            </div>
          </div>
          <div style={styles.card}>
            <h3 style={styles.cardTitle}>⚙️ 会话</h3>
            <button style={styles.secondaryBtn} onClick={() => { setMessages([]); setLastResponse(null); setStatus("idle"); }}>🗑️ 清空对话</button>
            <button style={{ ...styles.secondaryBtn, marginTop: 4 }} onClick={() => { const s = resetSessionId(); setSessionId(s); setMessages([]); setLastResponse(null); setStatus("idle"); }}>🔄 新会话</button>
            <p style={{ fontSize: 11, color: "#8896A6", marginTop: 6 }}>Session: {sessionId}</p>
          </div>
        </aside>
        {/* Center */}
        <main style={styles.centerPanel}>
          <div style={styles.chatArea}>
            {messages.length === 0 && (
              <div style={styles.welcome}><div style={{ fontSize: 40, marginBottom: 8 }}>💬</div><h3 style={{ color: "#1A2332", margin: 0 }}>欢迎使用 LangGraph 电商客服 Agent</h3><p style={{ color: "#8896A6", fontSize: 14 }}>左侧点击场景或输入文字开始体验</p></div>
            )}
            {messages.map((m, i) => (
              <div key={i}>
                <div style={{ display: "flex", marginBottom: 4, justifyContent: m.role === "user" ? "flex-end" : "flex-start" }}>
                  <div style={{
                    maxWidth: "75%", padding: "10px 16px",
                    borderRadius: m.role === "user" ? "18px 18px 4px 18px" : "18px 18px 18px 4px",
                    background: m.role === "user" ? "#1A73E8" : "white",
                    color: m.role === "user" ? "white" : "#1A2332",
                    border: m.role === "assistant" ? "1px solid #E8ECF0" : "none",
                    fontSize: 14, lineHeight: 1.5, whiteSpace: "pre-wrap",
                  }}>{m.content}</div>
                </div>
                {/* Evidence card for RAG responses */}
                {m.evidence && m.evidence.length > 0 && (
                  <div style={{ marginBottom: 12, marginLeft: 4 }}>
                    <div style={{ padding: "6px 10px", background: "#FFF8E1", border: "1px solid #FFE0B2", borderRadius: 8, fontSize: 12, display: "inline-block" }}>
                      📚 <strong>知识库依据</strong>
                    </div>
                    {m.evidence.map((ev, ei) => (
                      <div key={ei} style={{ marginTop: 4, padding: "6px 10px", background: "#FFFDE7", border: "1px solid #F0E68C", borderRadius: 8 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "#5F6B7A" }}>
                          <code style={{ fontSize: 11, background: "#F0F0F0", padding: "1px 4px", borderRadius: 3 }}>{ev.source_file}</code>
                          <span>score: {ev.score?.toFixed(2)}</span>
                        </div>
                        {ev.text && <div style={{ fontSize: 12, color: "#1A2332", marginTop: 2, lineHeight: 1.4 }}>{ev.text.length > 120 ? ev.text.slice(0, 120) + "…" : ev.text}</div>}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {status === "loading" && <div style={{ textAlign: "center", padding: 12, color: "#1A73E8", fontSize: 13 }}>⏳ Agent 正在分析…</div>}
            <div ref={chatEndRef} />
          </div>
          {/* Input */}
          <div style={styles.inputArea}>
            <textarea style={styles.textarea} value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); const msg = input.trim(); if (msg) { setInput(""); send(msg); } } }} placeholder="请输入您的问题… (Enter)" rows={1} />
            <button style={styles.sendBtn} disabled={status === "loading" || !input.trim()} onClick={() => { const msg = input.trim(); if (msg) { setInput(""); send(msg); } }}>发送</button>
          </div>
        </main>
        {/* Right: Trace */}
        <aside style={styles.rightPanel}>
          <div style={styles.card}>
            <h3 style={styles.cardTitle}>🔍 Agent 分析</h3>
            {d ? (
              <>
                <div style={styles.grid}>
                  <div style={styles.item}><div style={styles.label}>🎯 意图</div><div style={styles.value}>{d.intent || "—"}</div></div>
                  <div style={styles.item}><div style={styles.label}>😊 情绪</div><div style={styles.value}>{d.emotion} ({d.emotion_score})</div></div>
                  <div style={styles.item}><div style={styles.label}>📌 阶段</div><div style={styles.value}>{d.customer_stage || "—"}</div></div>
                  <div style={styles.item}><div style={styles.label}>⚙️ 技能</div><div style={styles.value}>{d.selected_skill || "—"}</div></div>
                  {/* RAG source row */}
                  {ragSrc && (
                    <div style={styles.item}><div style={styles.label}>📚 知识源</div><div style={{ fontSize: 12, fontWeight: 600, color: "#1A2332" }}>{ragSrc === "rag_llm" ? "rag + llm" : ragSrc}</div></div>
                  )}
                  {ragSrc && ragEv && ragEv.length > 0 && (
                    <div style={styles.item}><div style={styles.label}>📄 依据数</div><div style={{ fontSize: 12, fontWeight: 600, color: "#1A2332" }}>{ragEv.length} chunks</div></div>
                  )}
                </div>
                {ragSrc && ragEv && ragEv.length > 0 && (
                  <div style={{ marginTop: 6 }}>
                    <div style={styles.label}>📎 来源</div>
                    {ragEv.map((e, i) => <div key={i} style={{ fontSize: 11, color: "#5F6B7A", marginTop: 1, fontFamily: "monospace" }}>• {e.source_file} ({e.score?.toFixed(2)})</div>)}
                  </div>
                )}
                {d.policy_decision && <div style={{ ...styles.item, marginTop: 6 }}><div style={styles.label}>📋 策略</div><div style={styles.value}>{d.policy_decision}</div></div>}
                <div style={{ ...styles.item, marginTop: 6 }}><div style={styles.label}>👤 转人工</div><div style={{ ...styles.value, color: d.need_human ? "#C62828" : "#2E7D32" }}>{d.need_human ? "是" : "否"}</div></div>
                {d.human_reason && <p style={{ fontSize: 12, color: "#8896A6", marginTop: 2 }}>{d.human_reason}</p>}
              </>
            ) : (
              <p style={{ color: "#B0BCC9", fontSize: 13, textAlign: "center", padding: "24px 0" }}>发送消息后<br />分析结果在此显示</p>
            )}
          </div>
          <details style={{ marginBottom: 8 }}>
            <summary style={styles.summary}>📋 执行日志 ({d?.logs?.length || 0})</summary>
            <div style={{ marginTop: 6 }}>
              {d?.logs?.map((log, i) => (
                <div key={i} style={styles.logLine}>
                  <span style={styles.logDot} /><span style={styles.logName}>{log.node}</span><span style={styles.logSum}>{log.summary}</span>
                </div>
              ))}
              {(!d || !d.logs?.length) && <p style={{ fontSize: 12, color: "#8896A6" }}>暂无日志</p>}
            </div>
          </details>
          <details>
            <summary style={styles.summary}>📄 原始 API 响应</summary>
            <pre style={styles.code}>{JSON.stringify(d, null, 2) || "暂无数据"}</pre>
          </details>
        </aside>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: { minHeight: "100vh", background: "#F5F7FA", display: "flex", flexDirection: "column" },
  topbar: { background: "white", borderBottom: "1px solid #E8ECF0", padding: "12px 24px", display: "flex", alignItems: "center", justifyContent: "space-between" },
  title: { margin: 0, fontSize: 16, fontWeight: 700, color: "#1A2332" },
  subtitle: { margin: 0, fontSize: 12, color: "#8896A6", marginTop: 2 },
  main: { flex: 1, display: "flex", gap: 12, padding: 12, overflow: "hidden" },
  leftPanel: { width: 200, flexShrink: 0, display: "flex", flexDirection: "column", gap: 12 },
  centerPanel: { flex: 1, display: "flex", flexDirection: "column", minWidth: 0 },
  rightPanel: { width: 280, flexShrink: 0, display: "flex", flexDirection: "column", gap: 8 },
  card: { background: "white", border: "1px solid #E8ECF0", borderRadius: 12, padding: 12 },
  cardTitle: { margin: 0, fontSize: 11, fontWeight: 600, color: "#8896A6", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 8 },
  demoGrid: { display: "flex", flexDirection: "column", gap: 4 },
  demoBtn: { padding: "8px 12px", fontSize: 13, fontWeight: 500, color: "#1A2332", background: "#F5F7FA", border: "1px solid #E8ECF0", borderRadius: 8, cursor: "pointer", textAlign: "left" as const },
  secondaryBtn: { width: "100%", padding: "6px 12px", fontSize: 12, fontWeight: 500, background: "white", border: "1px solid #E8ECF0", borderRadius: 8, cursor: "pointer", color: "#5F6B7A" },
  chatArea: { flex: 1, overflowY: "auto", padding: "0 4px" },
  welcome: { textAlign: "center" as const, padding: "60px 0" },
  inputArea: { display: "flex", gap: 8, padding: "8px 0", background: "white", borderTop: "1px solid #E8ECF0" },
  textarea: { flex: 1, padding: 8, fontSize: 14, border: "1px solid #E8ECF0", borderRadius: 8, resize: "none", outline: "none", fontFamily: "inherit" },
  sendBtn: { padding: "8px 20px", fontSize: 14, fontWeight: 600, color: "white", background: "#1A73E8", border: "none", borderRadius: 8, cursor: "pointer" },
  grid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4 },
  item: { background: "#F8F9FB", borderRadius: 8, padding: "6px 10px" },
  label: { fontSize: 10, color: "#8896A6", marginBottom: 1 },
  value: { fontSize: 13, fontWeight: 600, color: "#1A2332" },
  summary: { fontSize: 12, fontWeight: 500, color: "#5F6B7A", cursor: "pointer" },
  logLine: { display: "flex", alignItems: "center", gap: 6, padding: "3px 0", fontSize: 12, borderBottom: "1px solid #F0F2F5" },
  logDot: { width: 6, height: 6, borderRadius: "50%", background: "#34C759", flexShrink: 0 },
  logName: { fontWeight: 500, color: "#1A2332", minWidth: 100, fontSize: 12 },
  logSum: { color: "#8896A6", fontSize: 11 },
  code: { fontSize: 11, background: "#F8F9FB", padding: 8, borderRadius: 8, overflow: "auto", maxHeight: 300, whiteSpace: "pre" as const },
};
