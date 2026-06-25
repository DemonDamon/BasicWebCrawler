from __future__ import annotations

from wechat_collector.db.models import Organization
from wechat_collector.discovery.base import DiscoveryProvider, DiscoveryResult
from wechat_collector.discovery.search_html import FetchHtmlFn, search_and_extract


class BingDiscoveryProvider(DiscoveryProvider):
    name = "bing_search"

    def __init__(self, fetch_html: FetchHtmlFn | None = None) -> None:
        self.fetch_html = fetch_html

    def discover(self, org: Organization, queries: list[str]) -> DiscoveryResult:
        return search_and_extract(
            source=self.name,
            search_url_template="https://www.bing.com/search?q={query}",
            queries=queries,
            fetch_html=self.fetch_html,
        )
