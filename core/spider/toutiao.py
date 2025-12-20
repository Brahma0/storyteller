from __future__ import annotations
"""
今日头条（Toutiao）热点抓取（MVP 版本，单源雷达）。

说明：
- 为了降低 Playwright 依赖与反爬复杂度，MVP 先使用 httpx + 简单解析实现基础爬取；
  如需更稳定的抓取再替换为 Playwright 版本或使用官方 API。
"""

from dataclasses import dataclass
from typing import List

import httpx
import structlog
from bs4 import BeautifulSoup  # type: ignore[import-untyped]

from core.database import Database


TOUTIAO_HOT_URL = "https://www.toutiao.com/hot-event/"


@dataclass
class ToutiaoTopic:
    title: str
    url: str
    score_ai: float


def _parse_hot_topics(html: str, limit: int = 20) -> List[ToutiaoTopic]:
    """从今日头条热点页面 HTML 中提取若干条标题与链接。

    解析规则尽量宽松，若页面结构发生较大变化则可能返回空列表。
    """
    soup = BeautifulSoup(html, "html.parser")
    result: List[ToutiaoTopic] = []

    # 宽松选择器：优先匹配常见的标题链接元素，降级为任意带 href 的 a 标签
    candidates = soup.select("a[href]")
    for item in candidates:
        if len(result) >= limit:
            break
        title = (item.get_text(strip=True) or "").strip()
        href = item.get("href") or ""
        if not title or not href:
            continue
        if href.startswith("/"):
            href = "https://www.toutiao.com" + href
        # 过滤明显的外链，优先保留 toutiao 自身链接
        if "toutiao.com" not in href:
            continue

        # 暂用固定分数占位，后续可接入打分 Agent
        result.append(ToutiaoTopic(title=title, url=href, score_ai=5.0))

    return result[:limit]


def fetch_toutiao_hot_topics(db: Database, limit: int = 20) -> int:
    """抓取今日头条热点并落库到 topics 表，返回新增条数。

    - 若请求或解析失败，不抛出异常，仅记录日志并返回 0。
    - 已存在相同 source_url 的记录不会重复插入。
    """
    logger = structlog.get_logger("cyber_pingshu.spider.toutiao")
    try:
        resp = httpx.get(
            TOUTIAO_HOT_URL,
            timeout=15.0,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36"
                )
            },
        )
    except httpx.RequestError as exc:  # pragma: no cover - 外部网络
        logger.warning("toutiao_fetch_failed", error=str(exc))
        return 0

    if resp.status_code == 403:
        # 反爬或访问受限的常见返回，记录后由其他数据源兜底
        logger.info("toutiao_forbidden", status_code=resp.status_code)
        return 0

    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:  # pragma: no cover
        logger.warning("toutiao_http_error", status_code=resp.status_code, error=str(exc))
        return 0

    topics = _parse_hot_topics(resp.text, limit=limit)
    if not topics:
        logger.warning("toutiao_parse_empty")
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

    logger.info("toutiao_fetch_done", inserted=inserted, total=len(topics))
    return inserted


