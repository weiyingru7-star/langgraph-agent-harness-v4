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


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek API Provider，调用 DeepSeek Chat Completions 润色回复。"""

    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", _DEFAULT_BASE_URL).rstrip("/")
        self.model = os.getenv("DEEPSEEK_MODEL", _DEFAULT_MODEL)
        self.timeout = int(os.getenv("LLM_TIMEOUT_SECONDS", _DEFAULT_TIMEOUT))

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
