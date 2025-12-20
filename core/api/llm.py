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


def generate_ping_shu_script(client: OpenRouterLLMClient, topic: str, word_count: int = 900, mvp_shorten: bool = True) -> str:
    """Generate a ping-shu (评书) style script for the given topic using the provided LLM client.

    - `client` is an instance of `OpenRouterLLMClient`.
    - `topic` is the selected headline/title to transform into a ping-shu script.
    - `word_count` is a soft target for script length (default ~900 words).
    """
    # Role & style framing
    role_description = (
        "你是赛博说书人·零号先生（Master Zero），来自2077年的数据考古学家，"
        "用赛博朋克风格的评书技法讲述现代科技与社会热点。请遵循以下结构并使用中文："
    )

    structure_instructions = (
        "结构要求：\n"
        "1. 定场诗（短句，建立场景与语气）\n"
        "2. 开场白（引入主题、抛出问题）\n"
        "3. 正文（分三段，采用'三翻四抖'的评书节奏，每段有小高潮，穿插术语转译表的比喻）\n"
        "4. 结尾（留扣子，引导下回期待）\n"
    )

    translation_table = (
        "术语转译表（示例）：服务器→藏经阁；Bug→走火入魔；程序员→符文师；数据库→天书库；算法→心法；代码→符咒；调试→调息；部署→出关。\n"
    )

    # For MVP we shorten the output to speed up verification.
    target_words = word_count
    if mvp_shorten:
        target_words = max(200, word_count // 2)

    constraints = (
        f"字数目标：约 {target_words} 字（MVP 缩短），语言风格：赛博水墨风 + 霓虹点缀，避免使用具体真实个人或声纹模仿，注意合规与去敏感化。"
    )

    prompt = (
        f"{role_description}\n\n"
        f"主题（topic）：{topic}\n\n"
        f"{structure_instructions}\n\n"
        f"{translation_table}\n\n"
        f"{constraints}\n\n"
        "请输出完整的评书脚本，分段清晰，用中文标明各部分（定场诗 / 开场白 / 正文段落 / 结尾）。"
    )

    # Use the client's chat endpoint
    # Set model to default; allow temperature and max_tokens to be tuned if needed
    # Convert target words to a loose token limit for max_tokens (approx factor 1.5)
    approx_max_tokens = min(4000, int(target_words * 1.5))
    response = client.chat(prompt, model=None, temperature=0.7, max_tokens=approx_max_tokens)
    return response
