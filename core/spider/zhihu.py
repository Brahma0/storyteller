from __future__ import annotations

"""知乎热点基础爬取（MVP 版本，单源雷达）。

说明：
- 为了降低 Playwright 依赖与反爬复杂度，MVP 先使用 httpx + 简单解析实现基础爬取；
  后续可按设计文档升级为 Playwright 版本。
"""

from dataclasses import dataclass
from typing import List

import httpx
import structlog
from bs4 import BeautifulSoup  # type: ignore[import-untyped]

from core.database import Database


ZH_HOT_URL = "https://www.zhihu.com/hot"


@dataclass
class ZhihuTopic:
    title: str
    url: str
    score_ai: float


def _parse_hot_topics(html: str, limit: int = 20) -> List[ZhihuTopic]:
    """从知乎热点页面 HTML 中提取若干条标题与链接。

    解析规则基于当前页面结构做了尽量宽松的选择器，若结构变更将返回空列表。
    """
    soup = BeautifulSoup(html, "html.parser")
    result: List[ZhihuTopic] = []

    for item in soup.select("div.HotItem-content a.HotItem-title")[:limit]:
        title = (item.get_text(strip=True) or "").strip()
        href = item.get("href") or ""
        if not title or not href:
            continue
        if href.startswith("/"):
            href = "https://www.zhihu.com" + href

        # 暂用固定分数占位，后续可接入多 Agent 打分
        result.append(ZhihuTopic(title=title, url=href, score_ai=5.0))

    return result


def fetch_zhihu_hot_topics(db: Database, limit: int = 20) -> int:
    """抓取知乎热点并落库到 topics 表，返回新增条数。

    - 若请求或解析失败，不抛出异常，仅记录日志并返回 0。
    - 已存在相同 source_url 的记录不会重复插入。
    """
    logger = structlog.get_logger("cyber_pingshu.spider.zhihu")
    try:
        resp = httpx.get(
            ZH_HOT_URL,
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
        logger.warning("zhihu_fetch_failed", error=str(exc))
        return 0

    if resp.status_code == 403:
        # 本地未登录或触发反爬时常见，作为正常情况记录并交由其他数据源兜底
        logger.info("zhihu_forbidden", status_code=resp.status_code)
        return 0

    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:  # pragma: no cover
        logger.warning("zhihu_http_error", status_code=resp.status_code, error=str(exc))
        return 0

    topics = _parse_hot_topics(resp.text, limit=limit)
    if not topics:
        logger.warning("zhihu_parse_empty")
        return 0

    inserted = 0
    for t in topics:
        # 去重：按 source_url 唯一
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

    logger.info("zhihu_fetch_done", inserted=inserted, total=len(topics))
    return inserted


