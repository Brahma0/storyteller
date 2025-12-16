from __future__ import annotations

"""LLM 客户端封装：统一通过 OpenRouter 调用不同大模型。"""

from typing import Any, Dict

import httpx

from core.config import AppConfig
from core.exceptions import APIError, NetworkError


class OpenRouterLLMClient:
    def __init__(self, config: AppConfig) -> None:
        self._cfg = config.api.openrouter
        self._client = httpx.Client(base_url=self._cfg.base_url, timeout=60.0)

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._cfg.api_key}",
            "Content-Type": "application/json",
        }

    def chat(self, prompt: str, model: str | None = None, **kwargs: Any) -> str:
        if not self._cfg.api_key:
            raise APIError("OpenRouter API key is not configured")

        model_name = model or self._cfg.models.text_primary
        payload: Dict[str, Any] = {
            "model": model_name,
            "messages": [
                {"role": "user", "content": prompt},
            ],
        }
        payload.update(kwargs)

        try:
            resp = self._client.post("/chat/completions", headers=self._headers(), json=payload)
        except httpx.RequestError as exc:  # 网络异常
            raise NetworkError(str(exc)) from exc

        if resp.status_code >= 400:
            raise APIError(f"OpenRouter error {resp.status_code}: {resp.text}")

        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise APIError("Unexpected OpenRouter response format") from exc
