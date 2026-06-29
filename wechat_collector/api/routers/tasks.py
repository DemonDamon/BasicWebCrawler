from fastapi import APIRouter, HTTPException, status

from wechat_collector.api.deps import AuthRequired, DbSession
from wechat_collector.api.schemas import TaskActionResponse, TaskFailedBody, TaskResponse
from wechat_collector.services import candidate_service
from wechat_collector.services.candidate_service import InvalidCandidateTransitionError

router = APIRouter(prefix="/crawl/tasks", tags=["tasks"])


@router.get("/next", response_model=TaskResponse | None)
def get_next_task(
    _auth: AuthRequired,
    db: DbSession,
    priority: str | None = None,
) -> TaskResponse | None:
    task = candidate_service.get_next_task(db, priority=priority)
    if task is None:
        return None
    return TaskResponse(
        id=task.id,
        url=task.url,
        normalized_url=task.normalized_url,
        title=task.title,
        org_id=task.org_id,
        account_id=task.account_id,
        status=task.status,
    )


@router.post("/{task_id}/success", response_model=TaskActionResponse)
def mark_task_success(
    task_id: int,
    _auth: AuthRequired,
    db: DbSession,
) -> TaskActionResponse:
    try:
        task = candidate_service.mark_success(db, task_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidCandidateTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return TaskActionResponse(id=task.id, status=task.status)


@router.post("/{task_id}/failed", response_model=TaskActionResponse)
def mark_task_failed(
    task_id: int,
    body: TaskFailedBody,
    _auth: AuthRequired,
    db: DbSession,
) -> TaskActionResponse:
    try:
        task = candidate_service.mark_failed(db, task_id, fail_reason=body.fail_reason)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidCandidateTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return TaskActionResponse(id=task.id, status=task.status)
