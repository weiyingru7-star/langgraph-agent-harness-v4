"""
deepseek_provider.py — DeepSeek API LLM Provider。

调用 DeepSeek Chat Completions API 润色客服回复。
默认不启用，需要设置 LLM_PROVIDER=deepseek 和 DEEPSEEK_API_KEY。
"""

import json
import os
import re

import httpx

from app.llm.base import BaseLLMProvider

_DEFAULT_BASE_URL = "https://api.deepseek.com"
_DEFAULT_MODEL = "deepseek-chat"
_DEFAULT_TIMEOUT = 15

SYSTEM_PROMPT = """你是一个电商客服回复润色助手。你的职责：

1. 只能基于 template_reply / skill_result 润色语言表达，让回复更自然。
2. 可以根据 emotion 调整语气（anger 更温和，neutral 保持正常）。
3. 可以引用 conversation_history 来承接上下文。
4. 不得编造商品信息（材质、尺码、价格等）。
5. 不得承诺退款成功、不得承诺补发/发货/赔偿。
6. 不得修改业务决策。
7. 如果 need_human=true，回复中必须包含"转人工"/"人工客服"等表达。
8. 回复要简洁自然，像真人客服的语气。
9. 输出必须是 JSON 格式：{"reply": "润色后的回复文本"}。
10. 只输出 JSON，不要额外说明。"""


RAG_SYSTEM_PROMPT = """你是一个客服知识库问答助手。你的职责：

1. 只能基于下方提供的「参考资料」（retrieved_chunks）回答用户问题。
2. 不得使用外部知识或编造内容。
3. 如果参考资料不足以回答，回复「当前资料不足，建议转人工确认」。
4. 不得承诺「已退款」「已补发」「已发货」「已赔偿」「已处理完成」。
5. 不得修改业务决策（退款、转人工、订单操作等）。
6. 在回答末尾注明资料来源，例如：依据：refund_policy.md。
7. 输出必须是 JSON 格式：{"reply": "你的回答", "sources": ["来源文件1.md", "来源文件2.md"]}
8. 只输出 JSON，不要额外说明。"""


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek API Provider，调用 DeepSeek Chat Completions 润色回复。"""

    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", _DEFAULT_BASE_URL).rstrip("/")
        self.model = os.getenv("DEEPSEEK_MODEL", _DEFAULT_MODEL)
        self.timeout = int(os.getenv("LLM_TIMEOUT_SECONDS", _DEFAULT_TIMEOUT))

    # ... [keep existing generate_reply, _build_prompt, _parse_reply unchanged] ...

    def generate_reply(self, payload: dict) -> dict:
        # 没有 API Key 直接返回
        if not self.api_key:
            return {
                "reply": payload.get("template_reply", ""),
                "provider": "deepseek",
                "success": False,
                "error": "missing_api_key",
            }

        prompt = self._build_prompt(payload)

        try:
            response = httpx.post(
                f"{self.base_url}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                                 {"role": "user", "content": prompt}],
                    "temperature": 0.5,
                    "max_tokens": 1024,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            if not content:
                return {
                    "reply": payload.get("template_reply", ""),
                    "provider": "deepseek",
                    "success": False,
                    "error": "empty_response",
                }

            # 尝试解析 JSON
            reply = self._parse_reply(content)
            if reply:
                return {
                    "reply": reply,
                    "provider": "deepseek",
                    "success": True,
                }

            # 不是 JSON 但有文本，直接作为 reply
            return {
                "reply": content,
                "provider": "deepseek",
                "success": True,
            }

        except httpx.TimeoutException:
            return {
                "reply": payload.get("template_reply", ""),
                "provider": "deepseek",
                "success": False,
                "error": "timeout",
            }
        except Exception as e:
            return {
                "reply": payload.get("template_reply", ""),
                "provider": "deepseek",
                "success": False,
                "error": str(e),
            }

    def generate_rag_answer(self, payload: dict) -> dict:
        """基于 RAG retrieved_chunks 生成回答。"""
        chunks = payload.get("retrieved_chunks", [])
        if not chunks:
            return {"reply": "", "sources": [], "provider": "deepseek", "success": False, "error": "no_evidence"}
        if not self.api_key:
            return {"reply": "", "sources": [], "provider": "deepseek", "success": False, "error": "missing_api_key"}

        prompt = self._build_rag_prompt(payload)
        try:
            response = httpx.post(
                f"{self.base_url}/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "model": self.model,
                    "messages": [{"role": "system", "content": RAG_SYSTEM_PROMPT},
                                 {"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 1024,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            if not content:
                return {"reply": "", "sources": [], "provider": "deepseek", "success": False, "error": "empty_response"}
            result = self._parse_rag_reply(content, chunks)
            if result:
                return result
            return {"reply": content, "sources": list(set(c["source_file"] for c in chunks)), "provider": "deepseek", "success": True}
        except httpx.TimeoutException:
            return {"reply": "", "sources": [], "provider": "deepseek", "success": False, "error": "timeout"}
        except Exception as e:
            return {"reply": "", "sources": [], "provider": "deepseek", "success": False, "error": str(e)}

    def _build_rag_prompt(self, payload: dict) -> str:
        """构建 RAG 问答 prompt。"""
        parts = [f"## 用户问题\n{payload.get('user_message', '')}"]
        parts.append("\n## 参考资料")
        for c in payload.get("retrieved_chunks", []):
            parts.append(f"--- {c['source_file']} ---\n{c['text']}")
        return "\n".join(parts)

    def parse_semantic(self, payload: dict) -> dict:
        """语义解析。"""
        if not self.api_key:
            return {"intent": "unknown", "explicit_product": None, "query_type": "unknown", "use_history": False, "confidence": 0.0, "provider": "deepseek", "success": False, "error": "missing_api_key"}

        tools_list = []
        for p in payload.get("available_products", []):
            tools_list.append(f"  - {p.get('name', '')}")
            for a in p.get("aliases", []):
                tools_list.append(f"    alias: {a}")

        prompt = f"""## 用户输入
{payload.get('user_message', '')}

## 可识别商品
{chr(10).join(tools_list) if tools_list else '  暂无'}

## 规则 intent
{payload.get('rule_intent', 'unknown')}

## 对话历史
"""
        history = payload.get("conversation_history", [])
        for msg in history[-4:]:
            prompt += f"{msg.get('role', '?')}: {msg.get('content', '')}\n"

        try:
            response = httpx.post(
                f"{self.base_url}/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "你是一个电商客服语义理解助手。你只能基于用户输入和对话历史做语义分析。输出必须是以下 JSON 格式：{\"intent\": \"...\", \"explicit_product\": \"...\" or null, \"query_type\": \"...\", \"use_history\": true/false, \"user_signal\": \"...\", \"confidence\": 0.0, \"reason\": \"...\"}。不得编造。不得将退款/投诉/转人工请求降级为闲聊。"},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 512,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            if not content:
                return {"intent": "unknown", "explicit_product": None, "query_type": "unknown", "use_history": False, "confidence": 0.0, "provider": "deepseek", "success": False, "error": "empty"}
            parsed = self._parse_rag_reply(content, [])
            if parsed and "reply" in parsed:
                try:
                    import json as _j
                    d2 = _j.loads(content)
                    return {
                        "intent": d2.get("intent", "unknown"),
                        "explicit_product": d2.get("explicit_product"),
                        "query_type": d2.get("query_type", "unknown"),
                        "use_history": d2.get("use_history", False),
                        "user_signal": d2.get("user_signal", "unknown"),
                        "confidence": d2.get("confidence", 0.0),
                        "reason": d2.get("reason", ""),
                        "provider": "deepseek",
                        "success": True,
                    }
                except Exception:
                    pass
            return {"intent": "unknown", "explicit_product": None, "query_type": "unknown", "use_history": False, "confidence": 0.0, "provider": "deepseek", "success": False, "error": "parse_failed"}
        except httpx.TimeoutException:
            return {"intent": "unknown", "explicit_product": None, "query_type": "unknown", "use_history": False, "confidence": 0.0, "provider": "deepseek", "success": False, "error": "timeout"}
        except Exception as e:
            return {"intent": "unknown", "explicit_product": None, "query_type": "unknown", "use_history": False, "confidence": 0.0, "provider": "deepseek", "success": False, "error": str(e)}

    def _parse_rag_reply(self, content: str, chunks: list) -> dict | None:
        """解析 RAG 回答 JSON。"""
        try:
            data = json.loads(content)
            if isinstance(data, dict) and "reply" in data:
                sources = data.get("sources", list(set(c["source_file"] for c in chunks)))
                return {"reply": data["reply"].strip(), "sources": sources, "provider": "deepseek", "success": True}
        except json.JSONDecodeError:
            pass
        match = re.search(r'\{[^}]*"reply"[^}]*\}', content, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                if "reply" in data:
                    sources = data.get("sources", list(set(c["source_file"] for c in chunks)))
                    return {"reply": data["reply"].strip(), "sources": sources, "provider": "deepseek", "success": True}
            except (json.JSONDecodeError, AttributeError):
                pass
        return None

    def _build_prompt(self, payload: dict) -> str:
        """构建用户 prompt。"""
        parts = []

        parts.append(f"## 用户输入\n{payload.get('user_message', '')}")
        parts.append(f"\n## 客服模板回复\n{payload.get('template_reply', '')}")

        intent = payload.get("intent")
        if intent:
            parts.append(f"\n## 意图\n{intent}")

        emotion = payload.get("emotion")
        score = payload.get("emotion_score", 0)
        if emotion:
            parts.append(f"\n## 用户情绪\n{emotion}({score})")

        skill = payload.get("selected_skill")
        if skill:
            parts.append(f"\n## 选中技能\n{skill}")

        policy = payload.get("policy_decision")
        if policy:
            parts.append(f"\n## 策略决策\n{policy}")

        need_human = payload.get("need_human", False)
        if need_human:
            parts.append(f"\n## 需要转人工\n{payload.get('human_reason', '')}")

        history = payload.get("conversation_history", [])
        if history:
            parts.append("\n## 对话历史\n")
            for msg in history[-4:]:
                parts.append(f"{msg.get('role', '?')}: {msg.get('content', '')}")

        return "\n".join(parts)

    def _parse_reply(self, content: str) -> str | None:
        """从 LLM 返回内容中解析 JSON reply。"""
        # 尝试完整 JSON 解析
        try:
            data = json.loads(content)
            if isinstance(data, dict) and "reply" in data:
                return data["reply"].strip()
        except json.JSONDecodeError:
            pass

        # 尝试从文本中提取 JSON 块
        match = re.search(r'\{[^}]*"reply"[^}]*\}', content, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                if "reply" in data:
                    return data["reply"].strip()
            except (json.JSONDecodeError, AttributeError):
                pass

        return None
