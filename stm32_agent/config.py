from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_BASE_URL = "https://newapi.sansun.eu.cc/v1"
DEFAULT_MODEL = "gpt-5.3-codex"


@dataclass(slots=True)
class AppConfig:
    api_key: str
    base_url: str
    model: str
    output_root: Path
    timeout_seconds: int = 120

    @classmethod
    def from_env(
        cls,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        output_root: str | None = None,
        timeout_seconds: int | None = None,
    ) -> "AppConfig":
        resolved_api_key = api_key or os.getenv("STM32_AGENT_API_KEY") or os.getenv("OPENAI_API_KEY")
        resolved_base_url = base_url or os.getenv("STM32_AGENT_BASE_URL") or os.getenv("OPENAI_BASE_URL") or DEFAULT_BASE_URL
        resolved_model = model or os.getenv("STM32_AGENT_MODEL") or DEFAULT_MODEL
        resolved_output_root = Path(output_root or os.getenv("STM32_AGENT_OUTPUT_DIR", "generated"))
        resolved_timeout = timeout_seconds or int(os.getenv("STM32_AGENT_TIMEOUT", "120"))

        if not resolved_api_key:
            raise ValueError("缺少 API Key，请通过 --api-key 或环境变量 STM32_AGENT_API_KEY 提供。")
        if not resolved_base_url:
            raise ValueError("缺少 Base URL，请通过 --base-url 或环境变量 STM32_AGENT_BASE_URL 提供。")

        return cls(
            api_key=resolved_api_key,
            base_url=resolved_base_url,
            model=resolved_model,
            output_root=resolved_output_root,
            timeout_seconds=resolved_timeout,
        )
