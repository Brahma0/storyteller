from __future__ import annotations
"""
今日头条（Toutiao）热点抓取（MVP 版本，单源雷达）。

说明：
- 为了降低 Playwright 依赖与反爬复杂度，MVP 先使用 httpx + 简单解析实现基础爬取；
  如需更稳定的抓取再替换为 Playwright 版本或使用官方 API。
"""

from dataclasses import dataclass
from typing import List

import structlog

from core.database import Database

# Use Playwright for robust JS-rendered scraping
TOUTIAO_BASE_URL = "https://www.toutiao.com/"


@dataclass
class ToutiaoTopic:
    title: str
    url: str
    score_ai: float


def _contains_chinese(text: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in (text or ""))


def fetch_toutiao_hot_topics(db: Database, limit: int = 20) -> int:
    """Use Playwright to fetch Toutiao hot topics (JS-rendered) and persist to DB.

    Requires Playwright browsers installed: `python -m playwright install`.
    """
    logger = structlog.get_logger("cyber_pingshu.spider.toutiao")

    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]
    except Exception as exc:
        logger.warning("playwright_not_available", error=str(exc))
        return 0

    inserted = 0
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36")
            # Request Chinese content
            page.set_extra_http_headers({"Accept-Language": "zh-CN,zh;q=0.9"})
            page.goto(TOUTIAO_BASE_URL, timeout=30000)
            # wait for network to be mostly idle and for potential hot list to render
            page.wait_for_load_state("networkidle", timeout=30000)

            # Try several selectors that commonly contain headlines
            candidates = []
            selectors = [
                "a",  # fallback to anchors
                "div.title a",  # generic
                "h3 a",
                "div.feed-card a",
                "a[href*='/item/']",
            ]
            for sel in selectors:
                try:
                    elements = page.query_selector_all(sel)
                except Exception:
                    elements = []
                for el in elements:
                    try:
                        title = (el.inner_text() or "").strip()
                        href = el.get_attribute("href") or ""
                        if not title or not href:
                            continue
                        # Normalize href
                        if href.startswith("/"):
                            href = "https://www.toutiao.com" + href
                        # Keep only Chinese titles preferentially
                        if _contains_chinese(title):
                            candidates.append((title, href))
                    except Exception:
                        continue
                if len(candidates) >= limit:
                    break

            browser.close()

            # dedupe preserving order
            seen = set()
            topics = []
            for t, u in candidates:
                if u in seen:
                    continue
                seen.add(u)
                topics.append(ToutiaoTopic(title=t, url=u, score_ai=5.0))
                if len(topics) >= limit:
                    break

            if not topics:
                logger.warning("toutiao_parse_empty_playwright")
                return 0

            for t in topics:
                exists = list(db.query("SELECT id FROM topics WHERE source_url = ? LIMIT 1", (t.url,)))
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

    except Exception as exc:
        logger.warning("toutiao_fetch_failed_playwright", error=str(exc))
        return 0


