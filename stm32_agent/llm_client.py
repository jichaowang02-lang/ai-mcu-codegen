from __future__ import annotations

import json
from typing import Any
from urllib import error, request


class LlmClient:
    def __init__(self, api_key: str, base_url: str, model: str, timeout_seconds: int = 120) -> None:
        self.api_key = api_key
        self.base_url = _normalize_chat_completions_url(base_url)
        self.model = model
        self.timeout_seconds = timeout_seconds

    def complete_json(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "messages": messages,
        }

        req = request.Request(
            self.base_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"LLM 请求失败: HTTP {exc.code} {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"无法连接到 LLM 服务: {exc}") from exc

        try:
            data = json.loads(raw)
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"无法解析 LLM 响应: {raw}") from exc

        parsed = _extract_json_object(content)
        if not isinstance(parsed, dict):
            raise RuntimeError("模型返回的不是 JSON 对象。")
        return parsed


def _normalize_chat_completions_url(base_url: str) -> str:
    cleaned = base_url.rstrip("/")
    if cleaned.endswith("/chat/completions"):
        return cleaned
    if cleaned.endswith("/v1"):
        return f"{cleaned}/chat/completions"
    return f"{cleaned}/v1/chat/completions"


def _extract_json_object(content: str) -> Any:
    stripped = content.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            stripped = "\n".join(lines[1:-1]).strip()

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(stripped[start:end + 1])
