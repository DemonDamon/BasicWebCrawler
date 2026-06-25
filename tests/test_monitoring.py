from datetime import timedelta

from wechat_collector.db.models import AccountHealth, Article, ArticleCandidate
from wechat_collector.monitoring.alerts import evaluate_alerts
from wechat_collector.monitoring.metrics import refresh_account_health
from wechat_collector.scheduler.retry import utcnow
from wechat_collector.services import candidate_service, org_service
from wechat_collector.services import report_service


def test_refresh_account_health_and_coverage(db_session) -> None:
    org = org_service.create_organization(db_session, org_code="org_mon", org_name="监控组织")
    account = org_service.bind_wechat_account(db_session, org.id, account_name="监控号")

    db_session.add(
        Article(
            org_id=org.id,
            account_id=account.id,
            title="监控文章",
            url="https://mp.weixin.qq.com/s?__biz=mon&mid=1&idx=1",
            publish_time=utcnow() - timedelta(hours=2),
            collected_at=utcnow(),
            content_text="正文",
        )
    )
    db_session.commit()

    updated = refresh_account_health(db_session)
    assert updated >= 1

    report = report_service.build_coverage_report(db_session)
    assert report.article_total >= 1
    assert report.account_coverage_rate == 1.0


def test_alerts_for_manual_queue_and_source_empty(db_session, monkeypatch) -> None:
    monkeypatch.setenv("SCHEDULER_EMPTY_SOURCE_THRESHOLD", "1")
    from wechat_collector.config import get_settings

    get_settings.cache_clear()

    org = org_service.create_organization(db_session, org_code="org_alert", org_name="告警组织")
    candidate, _ = candidate_service.enqueue_candidate(
        db_session,
        url="https://mp.weixin.qq.com/s?__biz=alert&mid=1&idx=1",
        org_id=org.id,
        source="manual",
    )
    task = candidate_service.get_next_task(db_session)
    assert task is not None
    for _ in range(4):
        candidate_service.mark_failed(db_session, task.id, fail_reason="parse_error")
        refreshed = db_session.get(ArticleCandidate, task.id)
        assert refreshed is not None
        if refreshed.status == "manual":
            break
        refreshed.next_retry_at = utcnow() - timedelta(minutes=1)
        db_session.commit()
        task = candidate_service.get_next_task(db_session)
        assert task is not None

    report = report_service.build_coverage_report(db_session)
    assert report.manual_queue_count >= 1

    from wechat_collector.discovery.providers.bing import BingDiscoveryProvider
    from wechat_collector.discovery.service import discover_for_organization

    discover_for_organization(
        db_session,
        org,
        providers=[BingDiscoveryProvider(fetch_html=lambda _u: "<html></html>")],
    )
    alerts = evaluate_alerts(db_session)
    assert any(alert.code == "discovery_source_empty" for alert in alerts)

    get_settings.cache_clear()
