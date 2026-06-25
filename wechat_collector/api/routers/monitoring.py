from fastapi import APIRouter

from wechat_collector.api.deps import AuthRequired, DbSession
from wechat_collector.api.schemas import AlertItem, MonitoringRefreshResponse
from wechat_collector.monitoring.alerts import evaluate_alerts
from wechat_collector.monitoring.metrics import refresh_account_health

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.post("/refresh", response_model=MonitoringRefreshResponse)
def refresh_monitoring(_auth: AuthRequired, db: DbSession) -> MonitoringRefreshResponse:
    updated = refresh_account_health(db)
    alerts = evaluate_alerts(db)
    return MonitoringRefreshResponse(
        accounts_updated=updated,
        alerts=[
            AlertItem(
                code=alert.code,
                severity=alert.severity,
                message=alert.message,
                account_id=alert.account_id,
                source=alert.source,
            )
            for alert in alerts
        ],
    )


@router.get("/alerts", response_model=list[AlertItem])
def list_alerts(_auth: AuthRequired, db: DbSession) -> list[AlertItem]:
    alerts = evaluate_alerts(db)
    return [
        AlertItem(
            code=alert.code,
            severity=alert.severity,
            message=alert.message,
            account_id=alert.account_id,
            source=alert.source,
        )
        for alert in alerts
    ]
