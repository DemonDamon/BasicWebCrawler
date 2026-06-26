"""搜狗微信搜索 Playwright 发现层：真实浏览器跟随跳转，解析 mp.weixin.qq.com 直链。"""

from __future__ import annotations

import logging
import random
import time
from typing import TYPE_CHECKING, Any, Protocol
from urllib.parse import quote

from wechat_collector.config import Settings, get_settings
from wechat_collector.discovery.base import (
    CandidateLink,
    DiscoveryProvider,
    DiscoveryResult,
    extract_wechat_links,
)
from wechat_collector.services import org_service
from wechat_collector.utils.url_normalize import normalize_wechat_url

if TYPE_CHECKING:
    from wechat_collector.db.models import Organization

logger = logging.getLogger(__name__)

ANTISPIDER_MARKERS = (
    "antispider",
    "验证码",
    "请输入验证码",
    "此验证码用于确认",
    "异常访问",
)

SEARCH_RESULT_SELECTORS = (
    ".news-list h3 a",
    ".news-box h3 a",
    "ul.news-list li h3 a",
    ".txt-box h3 a",
)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


class PlaywrightPage(Protocol):
    url: str

    def goto(self, url: str, *, wait_until: str = ..., timeout: int = ...) -> Any: ...

    def go_back(self, *, wait_until: str = ..., timeout: int = ...) -> Any: ...

    def content(self) -> str: ...

    def eval_on_selector_all(self, selector: str, expression: str) -> Any: ...


def build_sogou_search_url(query: str) -> str:
    encoded = quote(query.strip())
    return f"https://weixin.sogou.com/weixin?type=2&query={encoded}&ie=utf8"


def is_antispider_page(url: str, content: str) -> bool:
    haystack = f"{url}\n{content}".lower()
    return any(marker.lower() in haystack for marker in ANTISPIDER_MARKERS)


def is_wechat_article_url(url: str) -> bool:
    return "mp.weixin.qq.com/s" in (url or "")


def extract_redirect_links_from_html(html: str) -> list[str]:
    """从页面 HTML 中提取搜狗跳转链接（用于单测 / 兜底）。"""
    links = extract_wechat_links(html)
    # 搜狗结果页也可能直接嵌入 mp 链接（少见）
    import re

    sogou_links = re.findall(
        r'https?://weixin\.sogou\.com/link[^\s"\'<>]*',
        html,
        flags=re.IGNORECASE,
    )
    seen: set[str] = set()
    out: list[str] = []
    for href in sogou_links + links:
        if href not in seen:
            seen.add(href)
            out.append(href)
    return out


def _collect_redirect_hrefs(page: PlaywrightPage) -> list[str]:
    for selector in SEARCH_RESULT_SELECTORS:
        try:
            hrefs = page.eval_on_selector_all(selector, "els => els.map(e => e.href)")
            if hrefs:
                return [h for h in hrefs if h]
        except Exception:  # noqa: BLE001
            continue
    return extract_redirect_links_from_html(page.content())


def _sleep_random(min_seconds: float, max_seconds: float) -> None:
    if max_seconds <= 0:
        return
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)


def follow_redirect_links(
    page: PlaywrightPage,
    redirect_links: list[str],
    *,
    max_articles: int,
    source: str,
    query: str,
    page_timeout_ms: int,
    article_delay_min: float,
    article_delay_max: float,
) -> tuple[list[CandidateLink], str | None]:
    """跟随搜狗跳转链接，收集真实微信文章 URL。"""
    collected: list[CandidateLink] = []
    seen_normalized: set[str] = set()

    for link in redirect_links[: max(max_articles * 2, max_articles)]:
        if len(collected) >= max_articles:
            break
        if not link:
            continue

        search_url = page.url
        try:
            page.goto(link, wait_until="domcontentloaded", timeout=page_timeout_ms)
        except Exception as exc:  # noqa: BLE001
            logger.debug("跳转失败 link=%s err=%s", link[:80], exc)
            continue

        content = ""
        try:
            content = page.content()
        except Exception:  # noqa: BLE001
            content = ""

        if is_antispider_page(page.url, content):
            return collected, "antispider"

        final_url = page.url
        if is_wechat_article_url(final_url):
            normalized = normalize_wechat_url(final_url)
            if normalized and normalized not in seen_normalized:
                seen_normalized.add(normalized)
                collected.append(
                    CandidateLink(url=final_url, source=source, query=query)
                )

        try:
            page.goto(search_url, wait_until="domcontentloaded", timeout=page_timeout_ms)
        except Exception:
            try:
                page.go_back(wait_until="domcontentloaded", timeout=page_timeout_ms)
            except Exception:  # noqa: BLE001
                logger.warning("无法返回搜索结果页，中止当前 query=%s", query)
                break

        _sleep_random(article_delay_min, article_delay_max)

    return collected, None


def discover_from_search_page(
    page: PlaywrightPage,
    query: str,
    *,
    settings: Settings | None = None,
) -> DiscoveryResult:
    """对单个搜索词执行搜狗发现（供 provider 与单测调用）。"""
    cfg = settings or get_settings()
    source = "sogou_playwright"
    search_url = build_sogou_search_url(query)

    try:
        page.goto(search_url, wait_until="domcontentloaded", timeout=cfg.sogou_page_timeout_ms)
    except Exception as exc:  # noqa: BLE001
        return DiscoveryResult(source=source, queries=[query], error=str(exc))

    content = ""
    try:
        content = page.content()
    except Exception:  # noqa: BLE001
        content = ""

    if is_antispider_page(page.url, content):
        return DiscoveryResult(source=source, queries=[query], error="antispider")

    redirect_links = _collect_redirect_hrefs(page)
    if not redirect_links:
        return DiscoveryResult(source=source, queries=[query])

    links, follow_error = follow_redirect_links(
        page,
        redirect_links,
        max_articles=cfg.sogou_max_articles_per_account,
        source=source,
        query=query,
        page_timeout_ms=cfg.sogou_page_timeout_ms,
        article_delay_min=cfg.sogou_article_delay_min_seconds,
        article_delay_max=cfg.sogou_article_delay_max_seconds,
    )
    return DiscoveryResult(
        source=source,
        links=links,
        queries=[query],
        error=follow_error,
    )


class SogouPlaywrightDiscoveryProvider(DiscoveryProvider):
    """使用 Playwright 页面实例做搜狗微信文章发现。"""

    name = "sogou_playwright"

    def __init__(
        self,
        page: PlaywrightPage,
        *,
        settings: Settings | None = None,
        max_queries_per_org: int = 2,
    ) -> None:
        self.page = page
        self.settings = settings or get_settings()
        self.max_queries_per_org = max_queries_per_org

    def discover(self, org: Organization, queries: list[str]) -> DiscoveryResult:
        names = org_service.get_search_names(org)
        # 优先用公众号账号名，其次 org 名
        search_names: list[str] = []
        seen: set[str] = set()
        for account in org.wechat_accounts[:3]:
            if account.account_name and account.account_name not in seen:
                seen.add(account.account_name)
                search_names.append(account.account_name)
        for name in names[:3]:
            if name not in seen:
                seen.add(name)
                search_names.append(name)

        if not search_names and queries:
            search_names = [
                q.replace("site:mp.weixin.qq.com/s", "").strip().strip('"')
                for q in queries[: self.max_queries_per_org]
            ]

        search_names = search_names[: self.max_queries_per_org]
        if not search_names:
            return DiscoveryResult(source=self.name, error="no_search_names")

        all_links: list[CandidateLink] = []
        used_queries: list[str] = []
        last_error: str | None = None

        for query in search_names:
            result = discover_from_search_page(self.page, query, settings=self.settings)
            used_queries.extend(result.queries)
            if result.error:
                last_error = result.error
                if result.error == "antispider":
                    return DiscoveryResult(
                        source=self.name,
                        links=all_links,
                        queries=used_queries,
                        error="antispider",
                    )
                continue
            all_links.extend(result.links)

        deduped: dict[str, CandidateLink] = {}
        for link in all_links:
            normalized = normalize_wechat_url(link.url)
            if normalized:
                deduped.setdefault(normalized, link)

        return DiscoveryResult(
            source=self.name,
            links=list(deduped.values()),
            queries=used_queries,
            error=last_error if not deduped else None,
        )
