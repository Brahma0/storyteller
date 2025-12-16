from __future__ import annotations

"""Hacker News 热门列表爬取，用作知乎不可用时的备用数据源。

目的：
- MVP 只要求“至少一个外部数据源”，不强制必须是中文站点；
- HN 页面结构简单、反爬较少，适合作为开发阶段的稳定备选。
"""

from dataclasses import dataclass
from typing import List

import httpx
import structlog
from bs4 import BeautifulSoup  # type: ignore[import-untyped]

from core.database import Database


HN_TOP_URL = "https://news.ycombinator.com/"


@dataclass
class HNTopic:
    title: str
    url: str
    score_ai: float


def _parse_hn_topics(html: str, limit: int = 20) -> List[HNTopic]:
    soup = BeautifulSoup(html, "html.parser")
    result: List[HNTopic] = []

    for a in soup.select("span.titleline > a")[:limit]:
        title = (a.get_text(strip=True) or "").strip()
        href = a.get("href") or ""
        if not title or not href:
            continue
        # HN 内部链接补全
        if href.startswith("item?id="):
            href = f"https://news.ycombinator.com/{href}"
        result.append(HNTopic(title=title, url=href, score_ai=5.0))

    return result


def fetch_hn_topics(db: Database, limit: int = 20) -> int:
    """抓取 HN 热门列表并落库，返回新增条数。"""
    logger = structlog.get_logger("cyber_pingshu.spider.hn")
    try:
        resp = httpx.get(
            HN_TOP_URL,
            timeout=15.0,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36"
                )
            },
        )
        resp.raise_for_status()
    except httpx.RequestError as exc:  # pragma: no cover
        logger.warning("hn_fetch_failed", error=str(exc))
        return 0

    topics = _parse_hn_topics(resp.text, limit=limit)
    if not topics:
        logger.warning("hn_parse_empty")
        return 0

    inserted = 0
    for t in topics:
        exists = list(
            db.query(
                "SELECT id FROM topics WHERE source_url = ? LIMIT 1",
                (t.url,),
            )
        )
        if exists:
            continue

        db.execute(
            """
            INSERT INTO topics (source_url, title, score_ai, status)
            VALUES (?, ?, ?, 'pending')
            """,
            (t.url, t.title, t.score_ai),
        )
        inserted += 1

    logger.info("hn_fetch_done", inserted=inserted, total=len(topics))
    return inserted


