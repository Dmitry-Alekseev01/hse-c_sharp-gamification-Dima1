from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import selectinload

from app.models.ai_gamification_job import AIGamificationJob
from app.schemas.ai_gamification import AIGamifyDraft, AIGamifyRequest


def _to_request_payload(job: AIGamificationJob) -> dict:
    return {
        "source_type": job.source_type,
        "source_id": job.source_id,
        "raw_text": job.raw_text,
        "target_level": job.target_level,
        "language": job.language,
        "style": job.style,
        "tone": job.tone,
        "constraints": list(job.constraints_json or []),
    }


def _safe_error_text(error: str | None) -> str | None:
    if not error:
        return None
    return str(error)[:4000]


async def create_job(
    session,
    *,
    created_by_user_id: int,
    payload: AIGamifyRequest,
    source_snapshot: str | None = None,
) -> AIGamificationJob:
    job = AIGamificationJob(
        created_by_user_id=created_by_user_id,
        status="pending",
        source_type=payload.source_type.value,
        source_id=payload.source_id,
        raw_text=payload.raw_text,
        source_snapshot=source_snapshot,
        target_level=payload.target_level.value if payload.target_level else None,
        language=payload.language or "ru",
        style=payload.style.value if payload.style else None,
        tone=payload.tone.value if payload.tone else None,
        constraints_json=list(payload.constraints or []),
    )
    session.add(job)
    await session.flush()
    await session.refresh(job)
    return job


async def get_job(session, job_id: int) -> AIGamificationJob | None:
    stmt = (
        select(AIGamificationJob)
        .options(selectinload(AIGamificationJob.creator))
        .where(AIGamificationJob.id == job_id)
    )
    return (await session.execute(stmt)).scalars().first()


async def list_jobs_for_user(
    session,
    *,
    current_user_id: int,
    is_admin: bool,
    status_filter: str | None = None,
    source_type_filter: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[AIGamificationJob]:
    stmt = select(AIGamificationJob).order_by(desc(AIGamificationJob.id)).offset(max(offset, 0)).limit(max(limit, 1))
    if not is_admin:
        stmt = stmt.where(AIGamificationJob.created_by_user_id == current_user_id)
    if status_filter:
        stmt = stmt.where(AIGamificationJob.status == status_filter)
    if source_type_filter:
        stmt = stmt.where(AIGamificationJob.source_type == source_type_filter)
    return list((await session.execute(stmt)).scalars().all())


async def set_job_running(session, job: AIGamificationJob) -> AIGamificationJob:
    job.status = "running"
    job.started_at = datetime.now(UTC).replace(tzinfo=None)
    job.error_text = None
    await session.flush()
    await session.refresh(job)
    return job


async def set_job_completed(
    session,
    job: AIGamificationJob,
    *,
    draft: AIGamifyDraft,
    model: str | None,
    provider: str | None,
    usage: dict | None,
    latency_ms: int | None,
) -> AIGamificationJob:
    job.status = "completed"
    job.draft_json = draft.model_dump(mode="json")
    job.model = model
    job.provider = provider
    job.usage_json = usage
    job.latency_ms = latency_ms
    job.error_text = None
    job.completed_at = datetime.now(UTC).replace(tzinfo=None)
    await session.flush()
    await session.refresh(job)
    return job


async def set_job_failed(session, job: AIGamificationJob, *, error_text: str | None) -> AIGamificationJob:
    job.status = "failed"
    job.error_text = _safe_error_text(error_text)
    job.completed_at = datetime.now(UTC).replace(tzinfo=None)
    await session.flush()
    await session.refresh(job)
    return job


async def set_job_applied(
    session,
    job: AIGamificationJob,
    *,
    target_type: str,
    target_id: int,
) -> AIGamificationJob:
    job.status = "applied"
    job.applied_target_type = target_type
    job.applied_target_id = target_id
    job.applied_at = datetime.now(UTC).replace(tzinfo=None)
    await session.flush()
    await session.refresh(job)
    return job


async def reset_job_for_retry(session, job: AIGamificationJob) -> AIGamificationJob:
    job.status = "pending"
    job.error_text = None
    job.started_at = None
    job.completed_at = None
    await session.flush()
    await session.refresh(job)
    return job


def to_job_read_payload(job: AIGamificationJob) -> dict:
    return {
        "job_id": job.id,
        "status": job.status,
        "input": _to_request_payload(job),
        "draft": job.draft_json,
        "error": job.error_text,
        "model": job.model,
        "provider": job.provider,
        "usage": job.usage_json,
        "latency_ms": job.latency_ms,
    }
