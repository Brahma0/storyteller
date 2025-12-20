from __future__ import annotations
"""
Render 节点：使用 FFmpeg 将音频与背景素材合成为竖屏视频（MVP 极简实现）。

行为：
- 优先使用 `assets/carousel/` 下的第一个视频素材并循环（-stream_loop）。
- 将音频与视频合成，输出到 `output/{task_id}/final.mp4`。
- 在失败时设置 `state.error_message` 并将 `state.status='failed'`。
"""

from pathlib import Path
import shutil
import subprocess
from datetime import datetime
from typing import Optional

import structlog

from core.graph import AgentState
from core.config import AppConfig

logger = structlog.get_logger("cyber_pingshu.nodes.render")


def _choose_background_asset(assets_dir: Path) -> Optional[Path]:
    if not assets_dir.exists():
        return None
    # Prefer mp4 files
    for ext in ("*.mp4", "*.mov", "*.mkv"):
        for p in assets_dir.glob(ext):
            return p
    # fallback any file
    for p in assets_dir.iterdir():
        if p.is_file():
            return p
    return None


def render_node(state: AgentState, config: AppConfig) -> AgentState:
    """Combine state.audio_path with a background asset to produce a final video.

    Expects:
    - state.audio_path to be a valid file path (string).
    - config.paths.assets to point to assets directory.
    - config.paths.output to point to output base directory.
    """
    ffmpeg_path = shutil.which("ffmpeg") or "ffmpeg"

    audio_path = Path(state.audio_path) if state.audio_path else None
    if not audio_path or not audio_path.exists():
        state.error_message = "audio_missing"
        state.status = "failed"
        logger.error("render_failed_no_audio", audio=str(audio_path))
        return state

    assets_carousel = config.paths.assets / "carousel"
    bg = _choose_background_asset(assets_carousel)
    if not bg:
        state.error_message = "no_background_asset"
        state.status = "failed"
        logger.error("render_failed_no_bg", assets_dir=str(assets_carousel))
        return state

    # Prepare output directory
    task_id = state.task_id or datetime.utcnow().strftime("%Y%m%d%H%M%S")
    out_dir = config.paths.output / f"{task_id}"
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / "final.mp4"

    # parse resolution
    try:
        res = config.video.resolution.split("x")
        width = int(res[0])
        height = int(res[1])
    except Exception:
        width, height = 1080, 1920

    bitrate = getattr(config.video, "bitrate", "8M") or "8M"

    cmd = [
        ffmpeg_path,
        "-y",
        "-stream_loop",
        "-1",
        "-i",
        str(bg),
        "-i",
        str(audio_path),
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-c:a",
        "aac",
        "-b:v",
        bitrate,
        "-vf",
        f"scale={width}:{height},format=yuv420p",
        "-shortest",
        str(output_path),
    ]

    logger.info("render_start", cmd=" ".join(cmd[:6]) + " ...", output=str(output_path))
    try:
        res = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=600)
    except Exception as exc:  # pragma: no cover - external runtime
        state.error_message = f"ffmpeg_exception:{exc}"
        state.status = "failed"
        logger.error("render_ffmpeg_exception", error=str(exc))
        return state

    if res.returncode != 0:
        state.error_message = f"ffmpeg_failed:{res.returncode}"
        state.status = "failed"
        logger.error("render_ffmpeg_failed", returncode=res.returncode, stderr=res.stderr)
        return state

    # Success
    state.video_path = str(output_path)
    state.current_node = "render"
    state.progress = 95.0
    state.status = "completed"
    logger.info("render_done", path=str(output_path))
    return state


