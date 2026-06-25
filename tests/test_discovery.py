from wechat_collector.discovery.base import CandidateLink, extract_wechat_links, is_relevant_link
from wechat_collector.discovery.providers.baidu import BaiduDiscoveryProvider
from wechat_collector.discovery.providers.bing import BingDiscoveryProvider
from wechat_collector.discovery.providers.official_site import OfficialSiteDiscoveryProvider
from wechat_collector.discovery.service import discover_for_organization
from wechat_collector.services import org_service


SAMPLE_HTML = """
<html><body>
<a href="https://mp.weixin.qq.com/s?__biz=abc&mid=1&idx=1&sn=1">示例市发展和改革委员会通知</a>
<a href="https://mp.weixin.qq.com/s?__biz=def&mid=1&idx=1&sn=2">无关文章</a>
</body></html>
"""


def mock_fetch(_url: str) -> str:
    return SAMPLE_HTML


def test_extract_wechat_links_deduplicates() -> None:
    links = extract_wechat_links(
        "https://mp.weixin.qq.com/s?__biz=abc&mid=1&idx=1&sn=1 "
        "https://mp.weixin.qq.com/s?__biz=abc&mid=1&idx=1&sn=9"
    )
    assert len(links) == 1


def test_discover_from_multiple_sources(db_session) -> None:
    org = org_service.create_organization(
        db_session,
        org_code="org_disc",
        org_name="示例市发展和改革委员会",
        aliases='["市发改委"]',
    )
    org.official_website = "https://example.gov.cn"
    db_session.commit()

    providers = [
        BingDiscoveryProvider(fetch_html=mock_fetch),
        BaiduDiscoveryProvider(fetch_html=mock_fetch),
        OfficialSiteDiscoveryProvider(fetch_html=mock_fetch),
    ]
    summary = discover_for_organization(db_session, org, providers=providers)

    assert summary.created >= 1
    assert "bing_search" in summary.by_source
    assert "baidu_search" in summary.by_source
    assert summary.by_source["bing_search"] >= 1
    assert summary.by_source["baidu_search"] >= 1


def test_discovery_source_empty_warning(db_session, monkeypatch) -> None:
    monkeypatch.setenv("SCHEDULER_EMPTY_SOURCE_THRESHOLD", "2")
    from wechat_collector.config import get_settings

    get_settings.cache_clear()

    org = org_service.create_organization(db_session, org_code="org_empty", org_name="空结果组织")

    def empty_fetch(_url: str) -> str:
        return "<html><body>no links</body></html>"

    providers = [BingDiscoveryProvider(fetch_html=empty_fetch)]
    discover_for_organization(db_session, org, providers=providers)
    discover_for_organization(db_session, org, providers=providers)

    summary = discover_for_organization(db_session, org, providers=providers)
    assert "bing_search" in summary.disabled_sources

    get_settings.cache_clear()


def test_is_relevant_link_filters_noise(db_session) -> None:
    org = org_service.create_organization(db_session, org_code="org_rel", org_name="示例教育局")
    assert is_relevant_link(
        CandidateLink(url="https://mp.weixin.qq.com/s?__biz=x&mid=1&idx=1", title="示例教育局通知"),
        org,
    )
    assert not is_relevant_link(
        CandidateLink(url="https://mp.weixin.qq.com/s?__biz=x&mid=1&idx=1", title="完全无关"),
        org,
    )
