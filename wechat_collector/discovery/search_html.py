"""HTML 搜索页抓取辅助。"""

from __future__ import annotations

import time
from typing import Callable

import requests

from wechat_collector.config import get_settings
from wechat_collector.discovery.base import CandidateLink, DiscoveryResult, extract_wechat_links

FetchHtmlFn = Callable[[str], str]

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.8",
}


def default_fetch_html(url: str, *, timeout: int = 15) -> str:
    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    response.raise_for_status()
    settings = get_settings()
    time.sleep(settings.discovery_request_delay_seconds)
    return response.text


def search_and_extract(
    *,
    source: str,
    search_url_template: str,
    queries: list[str],
    fetch_html: FetchHtmlFn | None = None,
) -> DiscoveryResult:
    fetcher = fetch_html or default_fetch_html
    links: list[CandidateLink] = []
    last_error: str | None = None

    for query in queries:
        url = search_url_template.format(query=requests.utils.quote(query))
        try:
            html = fetcher(url)
            for article_url in extract_wechat_links(html):
                links.append(CandidateLink(url=article_url, source=source, query=query))
        except Exception as exc:  # noqa: BLE001 - provider boundary
            last_error = str(exc)
            continue

    deduped: dict[str, CandidateLink] = {}
    for link in links:
        normalized = link.url
        deduped.setdefault(normalized, link)

    return DiscoveryResult(
        source=source,
        links=list(deduped.values()),
        queries=queries,
        error=last_error,
    )
