import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "LangGraph 客服 Agent",
  description: "多轮上下文 + 本地知识库 + SQLite 持久化 + LLM Provider",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body style={{ margin: 0, fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif" }}>
        {children}
      </body>
    </html>
  );
}
