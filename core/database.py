from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterator


class Database:
    """SQLite 简单封装，负责连接与初始化表结构。"""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._path)
        self._conn.row_factory = sqlite3.Row

    @property
    def conn(self) -> sqlite3.Connection:
        return self._conn

    def init_schema(self) -> None:
        cur = self._conn.cursor()
        # 这里只初始化关键表，字段结构与设计文档保持一致，可后续扩展
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_url TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT,
                score_ai REAL,
                tags TEXT,
                status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS productions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER,
                task_id TEXT UNIQUE,
                script_content TEXT NOT NULL,
                video_path TEXT,
                audio_path TEXT,
                cover_path TEXT,
                duration INTEGER,
                file_size INTEGER,
                status TEXT DEFAULT 'draft',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(topic_id) REFERENCES topics(id)
            );

            CREATE TABLE IF NOT EXISTS feedbacks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                production_id INTEGER,
                platform TEXT NOT NULL,
                platform_video_id TEXT,
                views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0,
                comments_sentiment REAL,
                extracted_keywords TEXT,
                collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(production_id) REFERENCES productions(id)
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT UNIQUE NOT NULL,
                state_json TEXT,
                current_node TEXT,
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                progress REAL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME
            );

            CREATE TABLE IF NOT EXISTS platform_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                username TEXT,
                api_key TEXT,
                profile_path TEXT,
                last_login_at DATETIME,
                status TEXT DEFAULT 'active',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sensitive_words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT UNIQUE NOT NULL,
                level INTEGER DEFAULT 1,
                category TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        self._conn.commit()

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        cur = self._conn.cursor()
        cur.execute(sql, params)
        self._conn.commit()
        return cur

    def query(self, sql: str, params: tuple = ()) -> Iterator[sqlite3.Row]:
        cur = self._conn.cursor()
        cur.execute(sql, params)
        yield from cur.fetchall()

    def close(self) -> None:
        self._conn.close()
