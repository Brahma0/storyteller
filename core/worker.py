from __future__ import annotations
"""
Simple synchronous task runner for MVP.

Responsibilities:
- Create a task record in `tasks` table.
- Execute steps: load topic -> generate script -> persist production -> TTS -> render -> finalize.
- Update `tasks` and `productions` records with progress and error info.
"""

import json
import uuid
import threading
from pathlib import Path
from typing import Callable

import structlog

from core.database import Database
from core.config import AppConfig
from core.graph import AgentState
from core.api.llm import OpenRouterLLMClient, generate_ping_shu_script
from core.audio.tts import TTSClient
from core.nodes.render import render_node

logger = structlog.get_logger("cyber_pingshu.worker")

LogCallback = Callable[[str], None]


def _write_task_row(db: Database, task_id: str, status: str, progress: float = 0.0, error: str | None = None) -> None:
    db.execute(
        """
        INSERT INTO tasks (task_id, status, progress, error_message)
        VALUES (?, ?, ?, ?)
        """,
        (task_id, status, progress, error),
    )


def _update_task_row(db: Database, task_id: str, **kwargs) -> None:
    fields = []
    params = []
    for k, v in kwargs.items():
        fields.append(f"{k} = ?")
        params.append(v)
    params.append(task_id)
    sql = f"UPDATE tasks SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP WHERE task_id = ?"
    db.execute(sql, tuple(params))


def run_task(topic_id: int, db: Database, config: AppConfig, log_cb: LogCallback | None = None) -> None:
    """Run a full production task for the given topic_id."""
    task_id = str(uuid.uuid4())
    if log_cb:
        log_cb(f"创建任务 {task_id}，开始处理 topic_id={topic_id}")
    # create task row
    _write_task_row(db, task_id, "running", 0.0, None)

    state = AgentState()
    state.task_id = task_id

    try:
        # load topic
        rows = list(db.query("SELECT id, title, source_url FROM topics WHERE id = ? LIMIT 1", (topic_id,)))
        if not rows:
            raise RuntimeError("topic_not_found")
        topic_row = rows[0]
        state.topic = topic_row["title"]
        if log_cb:
            log_cb(f"已加载选题：{state.topic}")
        _update_task_row(db, task_id, current_node="selector", progress=5.0)

        # LLM: generate script
        llm_client = OpenRouterLLMClient(config)
        script = generate_ping_shu_script(llm_client, state.topic)
        state.script = script
        if log_cb:
            log_cb("脚本生成完成，正在保存到 productions 表。")
            # Log a short preview of the script for UI visibility
            preview = script[:1000].replace("\n", " ")
            log_cb(f"--- script preview start ---\n{preview}\n--- script preview end ---")
        # persist production draft
        cur = db.execute(
            """
            INSERT INTO productions (topic_id, task_id, script_content, status)
            VALUES (?, ?, ?, 'draft')
            """,
            (topic_id, task_id, script),
        )
        production_id = cur.lastrowid
        if log_cb:
            log_cb(f"已创建 production id={production_id}")
        _update_task_row(db, task_id, current_node="writer", progress=30.0)

        # TTS
        tts = TTSClient(config)
        out_dir = config.paths.output / f"{task_id}"
        out_dir.mkdir(parents=True, exist_ok=True)
        audio_path = out_dir / "audio.wav"
        if log_cb:
            log_cb("开始 TTS 合成...")
        tts.synthesize(script, audio_path)
        # update production audio_path
        db.execute("UPDATE productions SET audio_path = ? WHERE id = ?", (str(audio_path), production_id))
        state.audio_path = str(audio_path)
        if log_cb:
            log_cb(f"TTS 完成，生成音频：{audio_path}")
        _update_task_row(db, task_id, current_node="tts", progress=60.0)
        if log_cb:
            log_cb(f"TTS 完成：{audio_path}")

        # Render
        if log_cb:
            log_cb("开始视频合成（FFmpeg）...")
        state = render_node(state, config)
        if state.status == "failed":
            raise RuntimeError(state.error_message or "render_failed")
        # update production video_path and mark completed
        db.execute("UPDATE productions SET video_path = ?, status = 'completed' WHERE id = ?", (state.video_path, production_id))
        if log_cb:
            log_cb(f"渲染完成，视频路径：{state.video_path}")
        _update_task_row(db, task_id, current_node="render", progress=95.0)
        if log_cb:
            log_cb(f"渲染完成：{state.video_path}")

        # finalize task
        _update_task_row(db, task_id, status="completed", progress=100.0)
        if log_cb:
            log_cb("任务已完成。")

    except Exception as exc:
        err = str(exc)
        logger.error("task_failed", task_id=task_id, error=err)
        _update_task_row(db, task_id, status="failed", error_message=err)
        if log_cb:
            log_cb(f"任务失败：{err}")


def run_task_in_thread(topic_id: int, db: Database, config: AppConfig, log_cb: LogCallback | None = None) -> threading.Thread:
    t = threading.Thread(target=run_task, args=(topic_id, db, config, log_cb), daemon=True)
    t.start()
    return t


