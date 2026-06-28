"""Sogou Playwright 发现层单测（mock page，无需安装 Chromium）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

import pytest

from wechat_collector.discovery.providers.sogou_playwright import (
    SerpItem,
    SogouPlaywrightDiscoveryProvider,
    account_name_matches,
    build_sogou_org_queries,
    build_sogou_search_url,
    discover_from_search_page,
    filter_serp_items_for_account,
    follow_redirect_links,
    is_antispider_page,
    is_wechat_article_url,
    merge_serp_items,
)
from wechat_collector.services import org_service


@dataclass
class MockPage:
    url: str = ""
    _html: str = ""
    _serp_items: list[dict] = field(default_factory=list)
    goto_calls: list[str] = field(default_factory=list)
    go_back_calls: int = 0

    def goto(self, url: str, *, wait_until: str = "domcontentloaded", timeout: int = 30000):
        self.goto_calls.append(url)
        if "weixin.sogou.com/weixin" in url:
            self.url = url
            self._html = "<html><body><ul class='news-list'></ul></body></html>"
            return None
        if "weixin.sogou.com/link" in url:
            self.url = "https://mp.weixin.qq.com/s/ABC123xyz"
            self._html = (
                '<html><head><meta property="og:title" content="测试文章"/>'
                '<span id="publish_time">2026-06-27 10:00</span></head><body></body></html>'
            )
            return None
        self.url = url
        return None

    def go_back(self, *, wait_until: str = "domcontentloaded", timeout: int = 30000):
        self.go_back_calls += 1
        self.url = "https://weixin.sogou.com/weixin?type=2&query=test"
        return None

    def content(self) -> str:
        return self._html

    def evaluate(self, expression: str):
        if "news-list li" in expression:
            return list(self._serp_items)
        if "sg_data" in expression:
            return None
        return None

    def eval_on_selector_all(self, selector: str, expression: str):
        return []

    def wait_for_url(self, url: str | object, *, timeout: float = 30000):
        return None


def test_build_sogou_org_queries_includes_month_and_year() -> None:
    queries = build_sogou_org_queries(
        ["OMAHA联盟"],
        max_queries=4,
        now=datetime(2026, 6, 28),
    )
    assert queries[0] == "OMAHA联盟"
    assert "OMAHA联盟 2026年6月" in queries
    assert "OMAHA联盟 2026" in queries


def test_merge_serp_items_keeps_newer_timestamp() -> None:
    merged: dict[str, SerpItem] = {}
    merge_serp_items(
        merged,
        [
            SerpItem("a", "https://weixin.sogou.com/link?url=x", "OMAHA联盟", 100),
        ],
    )
    merge_serp_items(
        merged,
        [
            SerpItem("a-new", "https://weixin.sogou.com/link?url=x", "OMAHA联盟", 200),
        ],
    )
    assert merged["https://weixin.sogou.com/link?url=x"].title == "a-new"


def test_build_sogou_search_url_encodes_query_and_sorts_by_time() -> None:
    url = build_sogou_search_url("机器之心")
    assert "weixin.sogou.com/weixin" in url
    assert "type=2" in url
    assert "sort=1" in url
    assert "query=" in url


def test_build_sogou_search_url_omits_tsn() -> None:
    url = build_sogou_search_url("机器之心", tsn=2)
    assert "tsn=" not in url


def test_account_name_matches_aliases() -> None:
    assert account_name_matches("机器之心", ["机器之心"])
    assert account_name_matches("InfoQ", ["InfoQ"])
    assert account_name_matches("智猩猩 AI", ["智猩猩AI"])
    assert not account_name_matches("DaillyAI速递", ["机器之心"])


def test_filter_serp_items_for_account_skips_other_publishers() -> None:
    now = int(datetime.now().timestamp())
    old = int((datetime.now() - timedelta(days=30)).timestamp())
    items = [
        SerpItem("新文", "https://weixin.sogou.com/link?url=a", "机器之心", now),
        SerpItem("旧文", "https://weixin.sogou.com/link?url=b", "机器之心", old),
        SerpItem("别的号", "https://weixin.sogou.com/link?url=c", "DaillyAI速递", now),
    ]
    result = filter_serp_items_for_account(
        items, ["机器之心"], max_age_days=14
    )
    assert result.publisher_mismatch == 1
    assert result.too_old == 1
    assert len(result.items) == 1
    assert result.items[0].title == "新文"


def test_filter_serp_items_tracks_newest_when_all_too_old() -> None:
    old_ts = int((datetime.now() - timedelta(days=100)).timestamp())
    items = [
        SerpItem("旧文1", "https://weixin.sogou.com/link?url=a", "OMAHA联盟", old_ts),
        SerpItem("旧文2", "https://weixin.sogou.com/link?url=b", "OMAHA联盟", old_ts - 86400),
    ]
    result = filter_serp_items_for_account(items, ["OMAHA联盟"], max_age_days=14)
    assert not result.items
    assert result.too_old == 2
    assert result.newest_matching is not None


def test_is_antispider_page_detects_captcha() -> None:
    assert is_antispider_page("https://weixin.sogou.com/antispider", "")
    assert is_antispider_page("https://weixin.sogou.com/", "请输入验证码")
    assert not is_antispider_page("https://weixin.sogou.com/weixin?type=2", "正常列表")


def test_is_wechat_article_url() -> None:
    assert is_wechat_article_url("https://mp.weixin.qq.com/s/ABC")
    assert not is_wechat_article_url("https://weixin.sogou.com/link?url=xxx")


def test_follow_redirect_links_collects_wechat_urls() -> None:
    page = MockPage(url="https://weixin.sogou.com/weixin?type=2&query=test")
    serp = [SerpItem("测试", "https://weixin.sogou.com/link?url=encoded", "机器之心")]
    links, error = follow_redirect_links(
        page,
        serp,
        search_url="https://weixin.sogou.com/weixin?type=2&query=test",
        max_articles=3,
        source="sogou_playwright",
        query="机器之心",
        page_timeout_ms=5000,
        article_delay_min=0,
        article_delay_max=0,
    )
    assert error is None
    assert len(links) == 1
    assert "mp.weixin.qq.com/s/ABC123xyz" in links[0].url


def test_follow_redirect_links_stops_on_antispider() -> None:
    page = MockPage()

    def goto_antispider(url: str, *, wait_until: str = "domcontentloaded", timeout: int = 30000):
        page.url = "https://weixin.sogou.com/antispider"
        page._html = "验证码"
        page.goto_calls.append(url)

    page.goto = goto_antispider  # type: ignore[method-assign]

    links, error = follow_redirect_links(
        page,
        [SerpItem("x", "https://weixin.sogou.com/link?url=1", "机器之心")],
        search_url="https://weixin.sogou.com/weixin?type=2&query=test",
        max_articles=5,
        source="sogou_playwright",
        query="test",
        page_timeout_ms=5000,
        article_delay_min=0,
        article_delay_max=0,
    )
    assert error == "antispider"


def test_discover_from_search_page_with_mock_serp(monkeypatch) -> None:
    page = MockPage(
        _serp_items=[
            {
                "title": "最新文章",
                "href": "https://weixin.sogou.com/link?url=a",
                "account": "机器之心",
                "timestamp": int(datetime.now().timestamp()),
            }
        ]
    )
    monkeypatch.setenv("SOGOU_MAX_ARTICLES_PER_ACCOUNT", "2")
    from wechat_collector.config import get_settings

    get_settings.cache_clear()

    result = discover_from_search_page(
        page, "机器之心", account_names=["机器之心"]
    )
    get_settings.cache_clear()

    assert result.error is None
    assert len(result.links) >= 1
    assert all("mp.weixin.qq.com/s" in link.url for link in result.links)


def test_provider_discover_for_org(db_session, monkeypatch) -> None:
    org = org_service.create_organization(
        db_session,
        org_code="org_sogou_pw",
        org_name="机器之心",
    )
    org_service.bind_wechat_account(db_session, org.id, account_name="机器之心")

    page = MockPage(
        _serp_items=[
            {
                "title": "only",
                "href": "https://weixin.sogou.com/link?url=only",
                "account": "机器之心",
                "timestamp": int(datetime.now().timestamp()),
            }
        ]
    )
    monkeypatch.setenv("SOGOU_MAX_ARTICLES_PER_ACCOUNT", "3")
    monkeypatch.setenv("SOGOU_MAX_QUERIES_PER_ORG", "1")
    from wechat_collector.config import get_settings

    get_settings.cache_clear()

    provider = SogouPlaywrightDiscoveryProvider(page)
    result = provider.discover(org, [])

    get_settings.cache_clear()

    assert result.error is None
    assert result.hit_count >= 1
    assert result.links[0].source == "sogou_playwright"
