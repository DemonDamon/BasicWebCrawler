from __future__ import annotations

from wechat_collector.db.models import Organization
from wechat_collector.discovery.base import (
    CandidateLink,
    DiscoveryProvider,
    DiscoveryResult,
    extract_wechat_links,
)
from wechat_collector.discovery.search_html import FetchHtmlFn, default_fetch_html


class OfficialSiteDiscoveryProvider(DiscoveryProvider):
    name = "official_site"

    def __init__(self, fetch_html: FetchHtmlFn | None = None) -> None:
        self.fetch_html = fetch_html or default_fetch_html

    def discover(self, org: Organization, queries: list[str]) -> DiscoveryResult:
        if not org.official_website:
            return DiscoveryResult(source=self.name, links=[], queries=[])

        try:
            html = self.fetch_html(org.official_website)
        except Exception as exc:  # noqa: BLE001
            return DiscoveryResult(source=self.name, links=[], queries=[], error=str(exc))

        links = [
            CandidateLink(url=url, source=self.name, query=org.official_website)
            for url in extract_wechat_links(html)
        ]
        return DiscoveryResult(source=self.name, links=links, queries=[org.official_website])
