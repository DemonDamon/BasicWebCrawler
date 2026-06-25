from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from wechat_collector.api.deps import AuthRequired, DbSession
from wechat_collector.api.schemas import DiscoveryRunRequest, DiscoveryRunResponse
from wechat_collector.db.models import Organization
from wechat_collector.discovery.service import discover_for_active_organizations, discover_for_organization

router = APIRouter(prefix="/discovery", tags=["discovery"])


@router.post("/run", response_model=DiscoveryRunResponse)
def run_discovery(
    body: DiscoveryRunRequest,
    _auth: AuthRequired,
    db: DbSession,
) -> DiscoveryRunResponse:
    if body.org_id is not None:
        org = db.scalar(
            select(Organization)
            .options(joinedload(Organization.wechat_accounts))
            .where(Organization.id == body.org_id)
        )
        if org is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
        summaries = [discover_for_organization(db, org)]
    else:
        summaries = discover_for_active_organizations(db, limit=body.limit)

    details = [
        {
            "org_id": item.org_id,
            "org_name": item.org_name,
            "created": item.created,
            "merged": item.merged,
            "skipped": item.skipped,
            "by_source": item.by_source,
            "disabled_sources": item.disabled_sources,
            "errors": item.errors,
        }
        for item in summaries
    ]
    return DiscoveryRunResponse(
        organizations_scanned=len(summaries),
        created=sum(item.created for item in summaries),
        merged=sum(item.merged for item in summaries),
        skipped=sum(item.skipped for item in summaries),
        details=details,
    )
