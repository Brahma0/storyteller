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
        # Determine provider in order:
        # 1. explicit provider field in config.api.tts.provider
        # 2. config.api.tts.primary (recommended in config.yaml)
        # 3. environment variable TTS_PROVIDER
        # 4. if ELEVENLABS_API_KEY present, default to elevenlabs
        provider_candidate = (
            (self._cfg.get("provider") or "")
            or (self._cfg.get("primary") or "")
            or os.getenv("TTS_PROVIDER", "")  # type: ignore[arg-type]
        )
        if not provider_candidate and os.getenv("ELEVENLABS_API_KEY"):
            provider_candidate = "elevenlabs"
        self._provider = (provider_candidate or "").lower()
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
        raise APIError(f"No supported TTS provider configured: '{provider}'. "
                       "Please set config.api.tts.provider or config.api.tts.primary or the env TTS_PROVIDER, "
                       "or ensure ELEVENLABS_API_KEY is set.")

    def _synthesize_elevenlabs(self, text: str, output_path: Path, voice: Optional[str]) -> Path:
        """Call ElevenLabs text-to-speech API and save MP3/WAV to output_path.

        Expects API key to be available in one of:
        - self._cfg.get('elevenlabs', {}).get('api_key')
        - self._cfg.get('api_key')
        - environment variable ELEVENLABS_API_KEY
        """
        cfg_nested = self._cfg.get("elevenlabs", {}) if isinstance(self._cfg.get("elevenlabs", {}), dict) else {}
        api_key = cfg_nested.get("api_key") or self._cfg.get("api_key") or os.getenv("ELEVENLABS_API_KEY")
        voice_id = voice or cfg_nested.get("voice_id") or self._cfg.get("voice_id") or ""

        if not api_key:
            raise APIError("ElevenLabs API key not configured for TTS")

        # If no voice_id specified, query ElevenLabs voices endpoint and pick the first available voice.
        if not voice_id:
            try:
                voices_url = "https://api.elevenlabs.io/v1/voices"
                vresp = self._client.get(voices_url, headers={"xi-api-key": api_key}, timeout=30.0)
            except httpx.RequestError as exc:
                logger.error("elevenlabs_get_voices_error", error=str(exc))
                raise NetworkError(str(exc)) from exc

            if vresp.status_code >= 400:
                logger.error("elevenlabs_get_voices_failed", status_code=vresp.status_code, text=vresp.text)
                raise APIError(f"ElevenLabs voices request failed {vresp.status_code}: {vresp.text}")

            try:
                voices_data = vresp.json()
                voices_list = voices_data.get("voices", []) if isinstance(voices_data, dict) else []
                if not voices_list:
                    raise APIError("No voices available in ElevenLabs account.")
                # pick the first voice_id
                voice_id = voices_list[0].get("voice_id") or voices_list[0].get("id")
                logger.info("elevenlabs_chosen_voice", voice_id=voice_id)
            except Exception as exc:
                logger.error("elevenlabs_parse_voices_failed", error=str(exc), text=vresp.text if 'vresp' in locals() else "")
                raise APIError(f"Failed to select ElevenLabs voice: {exc}") from exc

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


