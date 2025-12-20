from __future__ import annotations
"""
Selector 节点：负责触发爬虫抓取（今日头条）并从 DB 返回待处理的候选选题列表。

设计要点：
- 无副作用（除写入 topics 表以外），便于测试。
- 返回值为候选列表，供后续 Writer 节点选择或自动发起任务。
"""

from typing import List, Dict

import structlog

from core.database import Database
from core.graph import AgentState
from core.spider.toutiao import fetch_toutiao_hot_topics


logger = structlog.get_logger("cyber_pingshu.nodes.selector")


def run_selector(db: Database, limit: int = 20) -> List[Dict]:
    """触发今日头条抓取、写库并返回最新的 pending 选题列表。

    - 调用 spider 的抓取函数填充 `topics` 表（已去重）。
    - 读取 `topics` 表中 status='pending' 的最新 N 条并返回。
    """
    inserted = fetch_toutiao_hot_topics(db, limit=limit)
    logger.info("fetch_invoked", inserted=inserted)

    rows = list(
        db.query(
            "SELECT id, source_url, title, score_ai, created_at FROM topics WHERE status = 'pending' ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
    )

    candidates: List[Dict] = []
    for r in rows:
        candidates.append(
            {
                "id": r["id"],
                "source_url": r["source_url"],
                "title": r["title"],
                "score_ai": r["score_ai"],
                "created_at": r["created_at"],
            }
        )

    logger.info("selector_done", candidates_count=len(candidates))
    return candidates


def selector_node(state: AgentState, db: Database, limit: int = 5) -> AgentState:
    """LangGraph 兼容的简易 Selector 节点实现。

    - 在状态中不直接改变 task_id 等持久化字段，仅在需要时将第一个候选写入 state.topic。
    """
    candidates = run_selector(db, limit=limit)
    if not candidates:
        state.current_node = "selector"
        state.progress = 0.0
        state.error_message = None
        return state

    # 默认选择排名第一的候选作为当前 topic（UI 可允许用户复选覆盖）
    first = candidates[0]
    state.topic = first["title"]
    state.metadata.setdefault("candidates", candidates)
    state.current_node = "selector"
    state.progress = 5.0
    return state


