"""sogou_poller 反爬跳过逻辑单测。"""

from __future__ import annotations

from wechat_collector.discovery.base import CandidateLink, DiscoveryResult
from wechat_collector.discovery.providers.sogou_playwright import (
    SogouPlaywrightDiscoveryProvider,
)
from wechat_collector.services import org_service
from wechat_collector.worker import sogou_poller


class _SessionFactory:
    def __init__(self, session) -> None:  # noqa: ANN001
        self._session = session

    def __call__(self):
        return self

    def __enter__(self):
        return self._session

    def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
        return False


class _SequenceProvider(SogouPlaywrightDiscoveryProvider):
    """按 org 顺序返回预设 DiscoveryResult。"""

    def __init__(self, results: list[DiscoveryResult]) -> None:
        self._results = list(results)
        self._index = 0

    def discover(self, org, queries):  # noqa: ANN001
        if self._index >= len(self._results):
            return DiscoveryResult(source="sogou_playwright")
        result = self._results[self._index]
        self._index += 1
        return result


def test_poll_round_continues_after_antispider(db_session, monkeypatch) -> None:
    org_a = org_service.create_organization(db_session, org_code="org_a", org_name="OrgA")
    org_service.bind_wechat_account(db_session, org_a.id, account_name="OrgA")
    org_b = org_service.create_organization(db_session, org_code="org_b", org_name="OrgB")
    org_service.bind_wechat_account(db_session, org_b.id, account_name="OrgB")

    provider = _SequenceProvider(
        [
            DiscoveryResult(source="sogou_playwright", error="antispider"),
            DiscoveryResult(
                source="sogou_playwright",
                links=[
                    CandidateLink(
                        url="https://mp.weixin.qq.com/s/after_antispider",
                        source="sogou_playwright",
                        query="OrgB",
                    )
                ],
            ),
        ]
    )

    monkeypatch.setattr(sogou_poller, "_sleep_between_accounts", lambda: None)
    monkeypatch.setattr(sogou_poller, "SessionLocal", _SessionFactory(db_session))
    monkeypatch.setattr(
        sogou_poller,
        "_get_active_organizations",
        lambda _db: [org_a, org_b],
    )

    stats = sogou_poller.run_poll_round(provider)

    assert stats["orgs"] == 2
    assert stats["errors"] == 1
    assert stats["created"] == 1
    assert provider._index == 2
