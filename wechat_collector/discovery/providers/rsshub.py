"""RSSHub 发现提供者：通过本地 RSSHub 实例拉取公众号 RSS，提取新文章链接。

支持的 RSSHub 路由：
  /wechat/wechat2rss/:id     无反爬，需要 wechat2rss 订阅 ID
  /freewechat/profile/:id    使用 __biz，有一定反爬限制
  /wechat/mp/homepage/:biz   需 __biz（仅适用有首页模板的号）

账号配置示例（WechatAccount.rsshub_routes）：
  [
    {"provider": "wechat2rss", "route": "/wechat/wechat2rss/abc123"},
    {"provider": "freewechat",  "route": "/freewechat/profile/MzA3MDM3NjE5NQ=="}
  ]
"""

from __future__ import annotations

import logging
import random
import time
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING

import requests

from wechat_collector.config import get_settings
from wechat_collector.db.models import WechatAccount
from wechat_collector.discovery.base import CandidateLink, DiscoveryProvider, DiscoveryResult
from wechat_collector.utils.url_normalize import normalize_wechat_url

if TYPE_CHECKING:
    from wechat_collector.db.models import Organization

logger = logging.getLogger(__name__)

RSS_NS = {
    "atom": "http://www.w3.org/2005/Atom",
}


def parse_rss_links(xml_text: str, source: str) -> list[CandidateLink]:
    """解析 RSS 2.0 / Atom feed，返回微信文章候选链接。"""
    links: list[CandidateLink] = []
    seen_normalized: set[str] = set()

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.warning("RSS XML 解析失败: %s", exc)
        return links

    # RSS 2.0: <channel><item><link>
    items = root.findall(".//item")
    # Atom: <entry><link href="...">
    if not items:
        items = root.findall(".//{http://www.w3.org/2005/Atom}entry")

    for item in items:
        # RSS 2.0
        link_el = item.find("link")
        title_el = item.find("title")

        # Atom
        if link_el is None:
            link_el = item.find("{http://www.w3.org/2005/Atom}link")
            title_el = item.find("{http://www.w3.org/2005/Atom}title")

        url: str | None = None
        if link_el is not None:
            url = (link_el.text or link_el.get("href") or "").strip()

        if not url or "mp.weixin.qq.com" not in url:
            continue

        normalized = normalize_wechat_url(url)
        if not normalized or normalized in seen_normalized:
            continue
        seen_normalized.add(normalized)

        title = (title_el.text or "").strip() if title_el is not None else None
        links.append(CandidateLink(url=url, title=title or None, source=source))

    return links


class RSSHubDiscoveryProvider(DiscoveryProvider):
    """通过本地 RSSHub 实例发现微信公众号新文章。"""

    name = "rsshub"

    def __init__(
        self,
        rsshub_base_url: str | None = None,
        request_timeout: int | None = None,
        delay_min: float | None = None,
        delay_max: float | None = None,
    ) -> None:
        cfg = get_settings()
        self._base = (rsshub_base_url or cfg.rsshub_base_url).rstrip("/")
        self._timeout = request_timeout or cfg.rss_request_timeout_seconds
        self._delay_min = delay_min if delay_min is not None else cfg.rss_request_delay_min_seconds
        self._delay_max = delay_max if delay_max is not None else cfg.rss_request_delay_max_seconds

    def _fetch_route(self, route: str) -> str | None:
        """拉取单条 RSSHub 路由，返回 XML 文本，失败返回 None。"""
        url = f"{self._base}{route}"
        try:
            resp = requests.get(url, timeout=self._timeout, headers={"Accept": "application/rss+xml, application/xml, text/xml"})
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as exc:
            logger.warning("RSSHub 请求失败 %s: %s", url, exc)
            return None

    def _is_rsshub_reachable(self) -> bool:
        """快速检测 RSSHub 是否可达（避免大量失败请求）。"""
        try:
            requests.get(self._base, timeout=3)
            return True
        except requests.RequestException:
            return False

    def discover(self, org: "Organization", queries: list[str]) -> DiscoveryResult:
        result = DiscoveryResult(source=self.name)

        accounts: list[WechatAccount] = [
            a for a in (org.wechat_accounts or []) if a.rsshub_routes
        ]
        if not accounts:
            return result

        if not self._is_rsshub_reachable():
            result.error = f"RSSHub 不可达：{self._base}"
            logger.warning("RSSHub 不可达，跳过 org=%s", org.org_name)
            return result

        for account in accounts:
            routes: list[dict] = account.rsshub_routes or []
            for route_cfg in routes:
                route = route_cfg.get("route", "")
                provider_tag = route_cfg.get("provider", "rsshub")
                if not route:
                    continue

                xml_text = self._fetch_route(route)
                if xml_text:
                    source_tag = f"rsshub_{provider_tag}"
                    links = parse_rss_links(xml_text, source=source_tag)
                    result.links.extend(links)
                    logger.debug(
                        "RSSHub route=%s account=%s 发现 %d 条链接",
                        route, account.account_name, len(links),
                    )

                delay = random.uniform(self._delay_min, self._delay_max)
                time.sleep(delay)

        return result
