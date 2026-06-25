from fastapi import APIRouter

from wechat_collector.api.deps import AuthRequired, DbSession
from wechat_collector.api.schemas import CoverageReportResponse
from wechat_collector.services import report_service

router = APIRouter(prefix="/coverage", tags=["coverage"])


@router.get("/report", response_model=CoverageReportResponse)
def get_coverage_report(_auth: AuthRequired, db: DbSession) -> CoverageReportResponse:
    report = report_service.build_coverage_report(db)
    return CoverageReportResponse(
        organization_total=report.organization_total,
        organization_active=report.organization_active,
        wechat_account_total=report.wechat_account_total,
        wechat_account_with_org=report.wechat_account_with_org,
        candidate_total=report.candidate_total,
        candidate_pending=report.candidate_pending,
        candidate_success=report.candidate_success,
        candidate_failed=report.candidate_failed,
        article_total=report.article_total,
        crawl_success_rate=report.crawl_success_rate,
        account_coverage_rate=report.account_coverage_rate,
        manual_queue_count=report.manual_queue_count,
        retry_queue_count=report.retry_queue_count,
        avg_collect_delay_hours=report.avg_collect_delay_hours,
        discovery_sources_warning=report.discovery_sources_warning,
    )
