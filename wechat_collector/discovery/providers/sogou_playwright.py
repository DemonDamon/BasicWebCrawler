"""搜狗微信搜索 Playwright 发现层：真实浏览器跟随跳转，解析 mp.weixin.qq.com 直链。"""

from __future__ import annotations

import logging
import random
import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol
from urllib.parse import quote, urljoin

from wechat_collector.config import Settings, get_settings
from wechat_collector.discovery.base import (
    CandidateLink,
    DiscoveryProvider,
    DiscoveryResult,
    extract_wechat_links,
)
from wechat_collector.services import org_service
from wechat_collector.utils.article_age import (
    extract_publish_time_from_html,
    is_publish_time_too_old,
)
from wechat_collector.utils.url_normalize import normalize_wechat_url

if TYPE_CHECKING:
    from wechat_collector.db.models import Organization

logger = logging.getLogger(__name__)

SOGOU_WEIXIN_ORIGIN = "https://weixin.sogou.com"

ANTISPIDER_MARKERS = (
    "antispider",
    "验证码",
    "请输入验证码",
    "此验证码用于确认",
    "异常访问",
)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

SERP_ITEM_JS = """
() => [...document.querySelectorAll('ul.news-list li')].map(li => {
  const anchor = li.querySelector('h3 a');
  if (!anchor) return null;
  const account = li.querySelector('.s-p .all-time-y2')?.innerText?.trim() || '';
  const scriptText = li.querySelector('.s-p script')?.innerText || '';
  let timestamp = null;
  const match = scriptText.match(/timeConvert\\('(\\d+)'\\)/);
  if (match) timestamp = parseInt(match[1], 10);
  return {
    title: anchor.innerText.trim(),
    href: anchor.href,
    account,
    timestamp,
  };
}).filter(Boolean)
"""


@dataclass(frozen=True)
class SerpItem:
    title: str
    href: str
    account: str
    timestamp: int | None = None


@dataclass(frozen=True)
class SerpFilterResult:
    """SERP 过滤统计（便于区分「发错号」与「文章过旧」）。"""

    items: list[SerpItem]
    publisher_mismatch: int
    too_old: int
    newest_matching: datetime | None = None


class PlaywrightPage(Protocol):
    url: str

    def goto(self, url: str, *, wait_until: str = ..., timeout: int = ...) -> Any: ...

    def go_back(self, *, wait_until: str = ..., timeout: int = ...) -> Any: ...

    def content(self) -> str: ...

    def eval_on_selector_all(self, selector: str, expression: str) -> Any: ...

    def evaluate(self, expression: str) -> Any: ...

    def wait_for_url(self, url: str | re.Pattern[str], *, timeout: float = ...) -> Any: ...


def build_sogou_search_url(query: str, *, tsn: int | None = None) -> str:
    """构建搜狗微信搜索 URL（按发布时间倒序）。

    搜狗 type=1「搜公众号」仅展示少量认证号，绝大多数试点号不可用。
    因此采用 type=2 搜索 + 结果页 ``.all-time-y2`` 发布者过滤，等效「只取该号发的文章」。
    """
    encoded = quote(query.strip())
    _ = tsn  # 兼容旧配置；tsn 参数已失效
    return (
        f"{SOGOU_WEIXIN_ORIGIN}/weixin?type=2&query={encoded}&ie=utf8&sort=1"
    )


def build_sogou_account_search_url(account_name: str) -> str:
    """按公众号名搜索该号文章（type=2 + sort=1）。"""
    return build_sogou_search_url(account_name)


def build_sogou_org_queries(
    search_names: list[str],
    *,
    max_queries: int = 4,
    now: datetime | None = None,
) -> list[str]:
    """为单个 org 生成多角度搜狗搜索词。

    仅搜公众号名时，搜狗常把「他人提及该号」的旧文排在前面（如「X 加入 OMAHA」）。
    需补搜「号 + 当前年月 / 年份」才能 surfaced 该号自己发的近期文章。
    """
    reference = now or datetime.now()
    year, month = reference.year, reference.month
    queries: list[str] = []
    seen: set[str] = set()

    def add(query: str) -> None:
        normalized = query.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            queries.append(normalized)

    for name in search_names[:2]:
        if not name:
            continue
        add(name)
        add(f"{name} {year}年{month}月")
        add(f"{name} {year}")
        if month > 1:
            add(f"{name} {year}年{month - 1}月")

    return queries[: max(max_queries, 1)]


def merge_serp_items(into: dict[str, SerpItem], items: list[SerpItem]) -> None:
    """按 href 合并 SERP，同一链接保留较新的 timestamp。"""
    for item in items:
        if not item.href:
            continue
        existing = into.get(item.href)
        if existing is None:
            into[item.href] = item
            continue
        old_ts = existing.timestamp or 0
        new_ts = item.timestamp or 0
        if new_ts >= old_ts:
            into[item.href] = item


def normalize_account_name(name: str) -> str:
    return re.sub(r"[\s\u3000]+", "", name).casefold()


def account_name_matches(serp_account: str, allowed_names: list[str]) -> bool:
    """结果页发布者是否属于目标公众号（允许别名/大小写/空格差异）。"""
    serp = normalize_account_name(serp_account)
    if not serp:
        return False
    for name in allowed_names:
        target = normalize_account_name(name)
        if not target:
            continue
        if serp == target or serp in target or target in serp:
            return True
    return False


def timestamp_to_datetime(timestamp: int | None) -> datetime | None:
    if timestamp is None:
        return None
    try:
        return datetime.fromtimestamp(timestamp)
    except (OSError, OverflowError, ValueError):
        return None


def parse_serp_items(raw_items: list[dict[str, Any]]) -> list[SerpItem]:
    items: list[SerpItem] = []
    for raw in raw_items:
        href = str(raw.get("href") or "").strip()
        if not href:
            continue
        if href.startswith("/"):
            href = urljoin(SOGOU_WEIXIN_ORIGIN, href)
        title = str(raw.get("title") or "").strip()
        account = str(raw.get("account") or "").strip()
        ts_raw = raw.get("timestamp")
        timestamp = int(ts_raw) if ts_raw is not None else None
        items.append(SerpItem(title=title, href=href, account=account, timestamp=timestamp))
    return items


def filter_serp_items_for_account(
    items: list[SerpItem],
    allowed_names: list[str],
    *,
    max_age_days: int = 0,
) -> SerpFilterResult:
    """只保留发布者匹配且（可选）在新鲜度窗口内的搜狗结果。"""
    matched: list[SerpItem] = []
    publisher_mismatch = 0
    too_old = 0
    newest_matching: datetime | None = None
    for item in items:
        if allowed_names and not account_name_matches(item.account, allowed_names):
            publisher_mismatch += 1
            continue
        publish_time = timestamp_to_datetime(item.timestamp)
        if publish_time and (
            newest_matching is None or publish_time > newest_matching
        ):
            newest_matching = publish_time
        if is_publish_time_too_old(publish_time, max_age_days=max_age_days):
            too_old += 1
            continue
        matched.append(item)
    matched.sort(key=lambda x: x.timestamp or 0, reverse=True)
    return SerpFilterResult(
        items=matched,
        publisher_mismatch=publisher_mismatch,
        too_old=too_old,
        newest_matching=newest_matching,
    )


def _log_serp_filter_summary(
    query: str,
    *,
    total: int,
    result: SerpFilterResult,
    max_age_days: int,
    allowed_names: list[str] | None = None,
) -> None:
    """记录 SERP 过滤原因，避免把「过旧」误读成「发错号」。"""
    kept = len(result.items)
    if kept:
        if result.publisher_mismatch or result.too_old:
            logger.info(
                "query=%s SERP 共 %d 条：保留 %d | 发布者不符 %d | 过旧 %d（max_age_days=%d）",
                query,
                total,
                kept,
                result.publisher_mismatch,
                result.too_old,
                max_age_days,
            )
        return

    if result.newest_matching is not None:
        age_days = (datetime.now() - result.newest_matching).days
        logger.info(
            "query=%s 无 %d 天内目标号文章 | SERP=%d 发布者不符=%d 过旧=%d | "
            "目标号最近=%s（约 %d 天前）。低频更新号可调大 SOGOU_MAX_ARTICLE_AGE_DAYS",
            query,
            max_age_days,
            total,
            result.publisher_mismatch,
            result.too_old,
            result.newest_matching.strftime("%Y-%m-%d"),
            age_days,
        )
        return

    logger.info(
        "query=%s SERP=%d 条均无目标号发布者（allowed=%s）",
        query,
        total,
        ",".join(allowed_names[:3]) if allowed_names else query,
    )


def is_antispider_page(url: str, content: str) -> bool:
    haystack = f"{url}\n{content}".lower()
    return any(marker.lower() in haystack for marker in ANTISPIDER_MARKERS)


def is_wechat_article_url(url: str) -> bool:
    return "mp.weixin.qq.com/s" in (url or "")


def extract_redirect_links_from_html(html: str) -> list[str]:
    """从页面 HTML 中提取搜狗跳转链接（用于单测 / 兜底）。"""
    links = extract_wechat_links(html)
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


def _collect_serp_items(page: PlaywrightPage) -> list[SerpItem]:
    try:
        raw = page.evaluate(SERP_ITEM_JS)
    except Exception:  # noqa: BLE001
        raw = []
    items = parse_serp_items(raw or [])
    if items:
        return items
    # 兜底：旧逻辑仅拿 href，无发布者信息时不做账号过滤
    hrefs = extract_redirect_links_from_html(page.content())
    return [SerpItem(title="", href=href, account="") for href in hrefs]


def _build_mp_url_from_sg_data(page: PlaywrightPage) -> str | None:
    try:
        sg_data = page.evaluate(
            "() => window.sg_data && typeof window.sg_data === 'object' ? window.sg_data : null"
        )
    except Exception:  # noqa: BLE001
        return None
    if not sg_data:
        return None
    src = sg_data.get("src")
    ver = sg_data.get("ver")
    timestamp = sg_data.get("timestamp")
    signature = sg_data.get("signature")
    if not all([src, ver, timestamp, signature]):
        return None
    return (
        f"https://mp.weixin.qq.com/s?src={src}&timestamp={timestamp}"
        f"&ver={ver}&signature={signature}"
    )


def _resolve_wechat_article_url(page: PlaywrightPage, *, page_timeout_ms: int) -> str:
    """等待搜狗中转页跳转到 mp.weixin.qq.com，必要时从 sg_data 构造 URL。"""
    if is_wechat_article_url(page.url):
        return page.url
    try:
        page.wait_for_url(re.compile(r"mp\.weixin\.qq\.com/s"), timeout=min(page_timeout_ms, 20000))
    except Exception:  # noqa: BLE001
        pass
    if is_wechat_article_url(page.url):
        return page.url
    built = _build_mp_url_from_sg_data(page)
    return built or page.url


def _sleep_random(min_seconds: float, max_seconds: float) -> None:
    if max_seconds <= 0:
        return
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)


def follow_redirect_links(
    page: PlaywrightPage,
    serp_items: list[SerpItem],
    *,
    search_url: str,
    max_articles: int,
    source: str,
    query: str,
    page_timeout_ms: int,
    article_delay_min: float,
    article_delay_max: float,
    max_article_age_days: int = 0,
) -> tuple[list[CandidateLink], str | None]:
    """跟随搜狗跳转链接，收集真实微信文章 URL。"""
    collected: list[CandidateLink] = []
    seen_normalized: set[str] = set()
    skipped_old = 0

    for item in serp_items[: max(max_articles * 3, max_articles)]:
        if len(collected) >= max_articles:
            break
        link = item.href
        if not link:
            continue

        try:
            page.goto(link, wait_until="networkidle", timeout=page_timeout_ms)
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

        final_url = _resolve_wechat_article_url(page, page_timeout_ms=page_timeout_ms)
        if not is_wechat_article_url(final_url):
            logger.debug("未能解析微信直链 query=%s title=%s url=%s", query, item.title[:40], final_url[:80])
            try:
                page.goto(search_url, wait_until="load", timeout=page_timeout_ms)
            except Exception:  # noqa: BLE001
                pass
            continue

        if not content and is_wechat_article_url(page.url):
            try:
                content = page.content()
            except Exception:  # noqa: BLE001
                content = ""

        publish_time = extract_publish_time_from_html(content, url=final_url)
        if publish_time is None:
            publish_time = timestamp_to_datetime(item.timestamp)

        if is_publish_time_too_old(publish_time, max_age_days=max_article_age_days):
            skipped_old += 1
            logger.debug(
                "跳过旧文 query=%s publish_time=%s title=%s",
                query,
                publish_time,
                item.title[:40],
            )
        else:
            normalized = normalize_wechat_url(final_url)
            if normalized and normalized not in seen_normalized:
                seen_normalized.add(normalized)
                collected.append(
                    CandidateLink(
                        url=final_url,
                        source=source,
                        query=query,
                        title=item.title or None,
                    )
                )

        try:
            page.goto(search_url, wait_until="load", timeout=page_timeout_ms)
        except Exception:
            try:
                page.go_back(wait_until="load", timeout=page_timeout_ms)
            except Exception:  # noqa: BLE001
                logger.warning(
                    "无法返回搜索结果页，尝试重新打开 search_url query=%s", query
                )
                try:
                    page.goto(
                        search_url,
                        wait_until="load",
                        timeout=page_timeout_ms,
                    )
                except Exception:  # noqa: BLE001
                    logger.warning("重新打开搜索结果页失败，中止当前 query=%s", query)
                    break

        _sleep_random(article_delay_min, article_delay_max)

    if skipped_old:
        logger.info(
            "query=%s 跳过 %d 篇过旧文章（max_age_days=%d）",
            query,
            skipped_old,
            max_article_age_days,
        )

    return collected, None


def _fetch_serp_for_query(
    page: PlaywrightPage,
    query: str,
    *,
    page_timeout_ms: int,
) -> tuple[list[SerpItem], str | None]:
    """打开搜狗搜索页并解析 SERP；返回 (items, error)。"""
    search_url = build_sogou_search_url(query)
    try:
        page.goto(search_url, wait_until="load", timeout=page_timeout_ms)
    except Exception as exc:  # noqa: BLE001
        return [], str(exc)

    content = ""
    try:
        content = page.content()
    except Exception:  # noqa: BLE001
        content = ""

    if is_antispider_page(page.url, content):
        return [], "antispider"

    return _collect_serp_items(page), None


def discover_org_with_queries(
    page: PlaywrightPage,
    search_names: list[str],
    *,
    settings: Settings | None = None,
    max_queries: int | None = None,
) -> DiscoveryResult:
    """对单个 org 用多组搜索词合并 SERP，再发布者过滤 + 跳转。"""
    cfg = settings or get_settings()
    source = "sogou_playwright"
    allowed = list(search_names)
    if not allowed:
        return DiscoveryResult(source=source, error="no_search_names")

    org_queries = build_sogou_org_queries(
        allowed,
        max_queries=max_queries or cfg.sogou_max_queries_per_org,
    )
    primary = allowed[0]
    return_url = build_sogou_account_search_url(primary)

    merged: dict[str, SerpItem] = {}
    used_queries: list[str] = []
    last_error: str | None = None

    for query in org_queries:
        items, fetch_error = _fetch_serp_for_query(
            page,
            query,
            page_timeout_ms=cfg.sogou_page_timeout_ms,
        )
        used_queries.append(query)
        if fetch_error:
            last_error = fetch_error
            if fetch_error == "antispider":
                logger.warning(
                    "query=%s 触发搜狗验证码，中止 org=%s 剩余搜索词",
                    query,
                    primary,
                )
                break
            continue
        merge_serp_items(merged, items)

    serp_items = list(merged.values())
    if not serp_items and last_error:
        return DiscoveryResult(
            source=source,
            queries=used_queries,
            error=last_error,
        )
    if not serp_items:
        return DiscoveryResult(source=source, queries=used_queries)

    filtered = filter_serp_items_for_account(
        serp_items,
        allowed,
        max_age_days=cfg.sogou_max_article_age_days,
    )
    _log_serp_filter_summary(
        f"{primary}({len(used_queries)}组搜索词)",
        total=len(serp_items),
        result=filtered,
        max_age_days=cfg.sogou_max_article_age_days,
        allowed_names=allowed,
    )
    if not filtered.items:
        return DiscoveryResult(source=source, queries=used_queries, error=last_error)

    links, follow_error = follow_redirect_links(
        page,
        filtered.items,
        search_url=return_url,
        max_articles=cfg.sogou_max_articles_per_account,
        source=source,
        query=primary,
        page_timeout_ms=cfg.sogou_page_timeout_ms,
        article_delay_min=cfg.sogou_article_delay_min_seconds,
        article_delay_max=cfg.sogou_article_delay_max_seconds,
        max_article_age_days=cfg.sogou_max_article_age_days,
    )
    return DiscoveryResult(
        source=source,
        links=links,
        queries=used_queries,
        error=follow_error or last_error,
    )


def discover_from_search_page(
    page: PlaywrightPage,
    query: str,
    *,
    account_names: list[str] | None = None,
    settings: Settings | None = None,
) -> DiscoveryResult:
    """对单个公众号名执行搜狗发现（type=2 + 发布者过滤 + 按时间排序）。"""
    cfg = settings or get_settings()
    source = "sogou_playwright"
    allowed = account_names or [query]
    search_url = build_sogou_account_search_url(query)

    try:
        page.goto(search_url, wait_until="load", timeout=cfg.sogou_page_timeout_ms)
    except Exception as exc:  # noqa: BLE001
        return DiscoveryResult(source=source, queries=[query], error=str(exc))

    content = ""
    try:
        content = page.content()
    except Exception:  # noqa: BLE001
        content = ""

    if is_antispider_page(page.url, content):
        return DiscoveryResult(source=source, queries=[query], error="antispider")

    serp_items = _collect_serp_items(page)
    if not serp_items:
        return DiscoveryResult(source=source, queries=[query])

    filtered = filter_serp_items_for_account(
        serp_items,
        allowed,
        max_age_days=cfg.sogou_max_article_age_days,
    )
    _log_serp_filter_summary(
        query,
        total=len(serp_items),
        result=filtered,
        max_age_days=cfg.sogou_max_article_age_days,
        allowed_names=allowed,
    )
    if not filtered.items:
        return DiscoveryResult(source=source, queries=[query])

    links, follow_error = follow_redirect_links(
        page,
        filtered.items,
        search_url=search_url,
        max_articles=cfg.sogou_max_articles_per_account,
        source=source,
        query=query,
        page_timeout_ms=cfg.sogou_page_timeout_ms,
        article_delay_min=cfg.sogou_article_delay_min_seconds,
        article_delay_max=cfg.sogou_article_delay_max_seconds,
        max_article_age_days=cfg.sogou_max_article_age_days,
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
        max_queries_per_org: int | None = None,
    ) -> None:
        self.page = page
        self.settings = settings or get_settings()
        self.max_queries_per_org = (
            max_queries_per_org
            if max_queries_per_org is not None
            else self.settings.sogou_max_queries_per_org
        )

    def discover(self, org: Organization, queries: list[str]) -> DiscoveryResult:
        names = org_service.get_search_names(org)
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
                for q in queries[:3]
            ]

        if not search_names:
            return DiscoveryResult(source=self.name, error="no_search_names")

        return discover_org_with_queries(
            self.page,
            search_names,
            settings=self.settings,
            max_queries=self.max_queries_per_org,
        )
