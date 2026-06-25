from __future__ import annotations

from wechat_collector.db.models import Organization
from wechat_collector.discovery.base import DiscoveryProvider, DiscoveryResult
from wechat_collector.discovery.search_html import FetchHtmlFn, search_and_extract


class SogouWechatDiscoveryProvider(DiscoveryProvider):
    name = "sogou_wechat"

    def __init__(self, fetch_html: FetchHtmlFn | None = None) -> None:
        self.fetch_html = fetch_html

    def discover(self, org: Organization, queries: list[str]) -> DiscoveryResult:
        sogou_queries = [query.replace("site:mp.weixin.qq.com/s", "").strip() for query in queries]
        return search_and_extract(
            source=self.name,
            search_url_template="https://weixin.sogou.com/weixin?type=2&query={query}",
            queries=sogou_queries[:3],
            fetch_html=self.fetch_html,
        )
