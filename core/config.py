from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import os

import yaml


@dataclass
class OpenRouterModels:
    text_primary: str
    text_cost_saver: Optional[str] = None
    text_alt: Optional[str] = None
    text_backup: Optional[str] = None
    moderation: Optional[str] = None
    embedding: Optional[str] = None


@dataclass
class OpenRouterConfig:
    api_key: str
    base_url: str
    models: OpenRouterModels


@dataclass
class APIConfig:
    openrouter: OpenRouterConfig
    images: Dict[str, Any]
    tts: Dict[str, Any]
    asr: Dict[str, Any]


@dataclass
class PathsConfig:
    assets: Path
    output: Path
    db: Path
    logs: Path
    checkpoints: Path
    models: Path


@dataclass
class VideoConfig:
    resolution: str
    fps: int
    codec: str
    bitrate: str


@dataclass
class LoggingConfig:
    level: str
    format: str


@dataclass
class AppConfig:
    api: APIConfig
    paths: PathsConfig
    video: VideoConfig
    logging: LoggingConfig


def _expand_env(value: Any) -> Any:
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        key = value[2:-1]
        return os.getenv(key, "")
    return value


def load_config(path: Path) -> AppConfig:
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    # 展开环境变量占位符
    api_cfg = raw.get("api", {})
    or_cfg = api_cfg.get("openrouter", {})
    or_models = or_cfg.get("models", {})

    openrouter = OpenRouterConfig(
        api_key=_expand_env(or_cfg.get("api_key")),
        base_url=str(or_cfg.get("base_url")),
        models=OpenRouterModels(
            text_primary=str(or_models.get("text_primary")),
            text_cost_saver=or_models.get("text_cost_saver"),
            text_alt=or_models.get("text_alt"),
            text_backup=or_models.get("text_backup"),
            moderation=or_models.get("moderation"),
            embedding=or_models.get("embedding"),
        ),
    )

    api = APIConfig(
        openrouter=openrouter,
        images=api_cfg.get("images", {}),
        tts=api_cfg.get("tts", {}),
        asr=api_cfg.get("asr", {}),
    )

    paths_cfg = raw.get("paths", {})
    paths = PathsConfig(
        assets=Path(paths_cfg.get("assets", "./assets")),
        output=Path(paths_cfg.get("output", "./output")),
        db=Path(paths_cfg.get("db", "./db/studio.db")),
        logs=Path(paths_cfg.get("logs", "./logs")),
        checkpoints=Path(paths_cfg.get("checkpoints", "./checkpoints")),
        models=Path(paths_cfg.get("models", "./models")),
    )

    video_cfg = raw.get("video", {})
    video = VideoConfig(
        resolution=str(video_cfg.get("resolution", "1080x1920")),
        fps=int(video_cfg.get("fps", 60)),
        codec=str(video_cfg.get("codec", "h264")),
        bitrate=str(video_cfg.get("bitrate", "8M")),
    )

    log_cfg = raw.get("logging", {})
    logging_cfg = LoggingConfig(
        level=str(log_cfg.get("level", "INFO")),
        format=str(log_cfg.get("format", "json")),
    )

    return AppConfig(api=api, paths=paths, video=video, logging=logging_cfg)
