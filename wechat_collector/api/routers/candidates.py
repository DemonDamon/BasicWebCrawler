from fastapi import APIRouter, HTTPException, status

from wechat_collector.api.deps import AuthRequired, DbSession
from wechat_collector.api.schemas import (
    CandidateCreateBody,
    CandidateImportBody,
    CandidateImportResponse,
    CandidateResponse,
)
from wechat_collector.services import candidate_service

router = APIRouter(tags=["candidates"])


@router.post("/candidates", response_model=CandidateResponse)
def create_candidate(
    _auth: AuthRequired,
    body: CandidateCreateBody,
    db: DbSession,
) -> CandidateResponse:
    try:
        candidate, created = candidate_service.enqueue_candidate(
            db,
            url=body.url,
            org_id=body.org_id,
            account_id=body.account_id,
            title=body.title,
            source=body.source,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return CandidateResponse(
        id=candidate.id,
        url=candidate.url,
        normalized_url=candidate.normalized_url,
        status=candidate.status,
        created=created,
        sources=candidate.sources,
    )


@router.post("/candidates/import", response_model=CandidateImportResponse)
def import_candidates(
    _auth: AuthRequired,
    body: CandidateImportBody,
    db: DbSession,
) -> CandidateImportResponse:
    created = 0
    merged = 0
    skipped = 0

    for url in body.urls:
        stripped = url.strip()
        if not stripped:
            skipped += 1
            continue
        try:
            _, was_created = candidate_service.enqueue_candidate(
                db,
                url=stripped,
                org_id=body.org_id,
                account_id=body.account_id,
                source=body.source,
            )
        except ValueError:
            skipped += 1
            continue
        if was_created:
            created += 1
        else:
            merged += 1

    return CandidateImportResponse(created=created, merged=merged, skipped=skipped)
