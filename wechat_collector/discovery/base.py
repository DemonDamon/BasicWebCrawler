"""发现层基础类型与工具。"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from urllib.parse import unquote

from wechat_collector.utils.url_normalize import normalize_wechat_url

if TYPE_CHECKING:
    from wechat_collector.db.models import Organization

WECHAT_LINK_PATTERN = re.compile(
    r"https?://mp\.weixin\.qq\.com/s[^\s\"'<>]*",
    re.IGNORECASE,
)


@dataclass
class CandidateLink:
    url: str
    title: str | None = None
    source: str = "unknown"
    query: str | None = None


@dataclass
class DiscoveryResult:
    source: str
    links: list[CandidateLink] = field(default_factory=list)
    queries: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def hit_count(self) -> int:
        return len(self.links)


class DiscoveryProvider(ABC):
    name: str

    @abstractmethod
    def discover(self, org: Organization, queries: list[str]) -> DiscoveryResult:
        raise NotImplementedError


def extract_wechat_links(text: str) -> list[str]:
    seen: set[str] = set()
    links: list[str] = []
    for match in WECHAT_LINK_PATTERN.findall(text):
        decoded = unquote(match.rstrip(".,;)"))
        normalized = normalize_wechat_url(decoded)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        links.append(decoded)
    return links


def build_search_queries(org: Organization, *, extra_keywords: list[str] | None = None) -> list[str]:
    from wechat_collector.services import org_service

    names = org_service.get_search_names(org)
    keywords = extra_keywords or ["通知", "发布", "2025", "2026"]
    queries: list[str] = []
    seen: set[str] = set()

    for name in names[:5]:
        base = f'site:mp.weixin.qq.com/s "{name}"'
        if base not in seen:
            seen.add(base)
            queries.append(base)
        for keyword in keywords[:2]:
            q = f'site:mp.weixin.qq.com/s "{name}" {keyword}'
            if q not in seen:
                seen.add(q)
                queries.append(q)

    for account in org.wechat_accounts[:3]:
        q = f'site:mp.weixin.qq.com/s "{account.account_name}"'
        if q not in seen:
            seen.add(q)
            queries.append(q)

    return queries


def is_relevant_link(link: CandidateLink, org: Organization) -> bool:
    from wechat_collector.services import org_service

    haystack = " ".join(
        filter(
            None,
            [link.title or "", link.url, link.query or ""],
        )
    ).lower()
    for name in org_service.get_search_names(org):
        token = name.lower()
        if len(token) >= 2 and token in haystack:
            return True
    return False
