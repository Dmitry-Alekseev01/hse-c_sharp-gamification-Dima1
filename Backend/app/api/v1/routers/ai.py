from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.security import require_roles
from app.models.user import User
from app.repositories import ai_gamification_repo
from app.schemas.ai_gamification import (
    AIGamifyApplyRequest,
    AIGamifyApplyResponse,
    AIGamifyCreateResponse,
    AIGamifyJobRead,
    AIGamifyJobListRead,
    AIGamifyOpsMetricsRead,
    AIGamifyRequest,
)
from app.services.ai_gamification_service import (
    apply_job_draft,
    create_ai_gamification_job,
    get_ai_ops_metrics,
    get_job_for_user,
    list_ai_jobs_for_user,
    retry_ai_gamification_job,
)


router = APIRouter()


@router.post("/gamify", response_model=AIGamifyCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_ai_gamification(
    payload: AIGamifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("teacher", "admin")),
):
    job = await create_ai_gamification_job(db, payload, current_user)
    return {"job_id": job.id, "status": job.status}


@router.get("/gamify", response_model=AIGamifyJobListRead, status_code=status.HTTP_200_OK)
async def list_ai_gamification_jobs(
    status_filter: str | None = Query(default=None, alias="status"),
    source_type: str | None = Query(default=None, alias="source_type"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("teacher", "admin")),
):
    items = await list_ai_jobs_for_user(
        db,
        current_user=current_user,
        limit=limit,
        offset=offset,
        status_filter=status_filter,
        source_type_filter=source_type,
    )
    payload = {"items": [AIGamifyJobRead.model_validate(item) for item in items], "limit": limit, "offset": offset}
    return AIGamifyJobListRead.model_validate(payload)


@router.get("/gamify/{job_id}", response_model=AIGamifyJobRead, status_code=status.HTTP_200_OK)
async def get_ai_gamification_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("teacher", "admin")),
):
    job = await get_job_for_user(db, job_id, current_user)
    payload = ai_gamification_repo.to_job_read_payload(job)
    return AIGamifyJobRead.model_validate(payload)


@router.post("/gamify/{job_id}/apply", response_model=AIGamifyApplyResponse, status_code=status.HTTP_200_OK)
async def apply_ai_gamification_job(
    job_id: int,
    payload: AIGamifyApplyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("teacher", "admin")),
):
    applied = await apply_job_draft(db, job_id=job_id, payload=payload, current_user=current_user)
    return AIGamifyApplyResponse.model_validate(applied)


@router.post("/gamify/{job_id}/retry", response_model=AIGamifyCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def retry_ai_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("teacher", "admin")),
):
    retried = await retry_ai_gamification_job(db, job_id=job_id, current_user=current_user)
    return AIGamifyCreateResponse.model_validate(retried)


@router.get("/ops/metrics", response_model=AIGamifyOpsMetricsRead, status_code=status.HTTP_200_OK)
async def get_ai_metrics(
    current_user: User = Depends(require_roles("admin")),
):
    metrics = await get_ai_ops_metrics()
    return AIGamifyOpsMetricsRead.model_validate(metrics)
