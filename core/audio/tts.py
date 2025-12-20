from __future__ import annotations
"""
TTS 封装（云优先实现）。

提供简单的 TTSClient，统一入口为 `synthesize(text, output_path)`，
当前实现优先支持 ElevenLabs（若配置可用），否则尝试 EdgeTTS via api 参数（占位）。
"""
from pathlib import Path
from typing import Optional
import os

import httpx
import structlog

from core.config import AppConfig
from core.exceptions import APIError, NetworkError


logger = structlog.get_logger("cyber_pingshu.audio.tts")


class TTSClient:
    def __init__(self, config: AppConfig) -> None:
        self._cfg = config.api.tts or {}
        self._provider = self._cfg.get("provider", "") or os.getenv("TTS_PROVIDER", "")
        self._client = httpx.Client(timeout=60.0)

    def synthesize(self, text: str, output_path: Path, voice: Optional[str] = None) -> Path:
        """Synthesize `text` into an audio file at `output_path`.

        - Returns the Path to the written audio file on success.
        - Raises NetworkError / APIError on failures.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Provider resolution: prefer explicit provider config
        provider = (self._provider or "").lower()

        if provider in ("elevenlabs", "eleven_lab", "eleven"):
            return self._synthesize_elevenlabs(text, output_path, voice)

        # Future providers can be added here (openai-tts, edge-tts, local)
        raise APIError(f"No supported TTS provider configured: {provider}")

    def _synthesize_elevenlabs(self, text: str, output_path: Path, voice: Optional[str]) -> Path:
        """Call ElevenLabs text-to-speech API and save MP3/WAV to output_path.

        Expects API key to be available in one of:
        - self._cfg.get('elevenlabs', {}).get('api_key')
        - self._cfg.get('api_key')
        - environment variable ELEVENLABS_API_KEY
        """
        cfg_nested = self._cfg.get("elevenlabs", {}) if isinstance(self._cfg.get("elevenlabs", {}), dict) else {}
        api_key = cfg_nested.get("api_key") or self._cfg.get("api_key") or os.getenv("ELEVENLABS_API_KEY")
        voice_id = voice or cfg_nested.get("voice_id") or self._cfg.get("voice_id") or "default"

        if not api_key:
            raise APIError("ElevenLabs API key not configured for TTS")

        # ElevenLabs v1 TTS endpoint
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": api_key,
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
        }
        payload = {"text": text}

        try:
            resp = self._client.post(url, headers=headers, json=payload, timeout=120.0)
        except httpx.RequestError as exc:
            logger.error("elevenlabs_request_error", error=str(exc))
            raise NetworkError(str(exc)) from exc

        if resp.status_code >= 400:
            logger.error("elevenlabs_api_error", status_code=resp.status_code, text=resp.text)
            raise APIError(f"ElevenLabs error {resp.status_code}: {resp.text}")

        # Response body is audio bytes
        try:
            with output_path.open("wb") as f:
                f.write(resp.content)
        except Exception as exc:  # pragma: no cover - IO errors
            logger.error("tts_write_failed", path=str(output_path), error=str(exc))
            raise APIError(f"Failed to write audio to {output_path}: {exc}") from exc

        logger.info("tts_succeeded", path=str(output_path), provider="elevenlabs")
        return output_path


