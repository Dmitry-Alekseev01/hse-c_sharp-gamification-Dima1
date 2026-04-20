from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import add_post_commit_task
from app.api.v1.access import can_manage_material, can_manage_test
from app.cache.redis_cache import (
    NS_MATERIALS,
    NS_QUESTIONS,
    NS_TEST_CONTENT,
    NS_TESTS,
    bump_cache_namespace,
    get_redis_client,
)
from app.db.session import AsyncSessionLocal
from app.models.material_block import MaterialBlock
from app.models.user import User
from app.core.config import settings
from app.repositories import ai_gamification_repo, material_repo, question_repo, test_repo
from app.schemas.ai_gamification import (
    AIGamifyApplyRequest,
    AIGamifyDraft,
    AIGamifyRequest,
    AIGamifyTargetType,
)
from app.services.ai_service import (
    AIGamificationConfigError,
    AIGamificationDisabledError,
    ensure_ai_gamification_ready,
    generate_gamification_draft,
)


logger = logging.getLogger(__name__)

AI_GAMIFY_QUEUE = "ai:gamify"
AI_GAMIFY_DLQ = "ai:gamify:dlq"
AI_GAMIFY_RETRY_KEY_PREFIX = "ai:gamify:retry"
AI_GAMIFY_METRICS_KEY = "ai:gamify:metrics"


class AIGamificationDraftValidationError(ValueError):
    pass


def _utc_day_key(now: datetime | None = None) -> str:
    effective_now = now or datetime.now(UTC)
    return effective_now.strftime("%Y%m%d")


def _seconds_until_next_utc_day(now: datetime | None = None) -> int:
    effective_now = now or datetime.now(UTC)
    next_day = datetime.combine((effective_now + timedelta(days=1)).date(), datetime.min.time(), tzinfo=UTC)
    return max(int((next_day - effective_now).total_seconds()), 1)


def _trim_source_text(source_text: str) -> str:
    limit = max(int(settings.ai_gamification_max_source_chars), 1000)
    if len(source_text) <= limit:
        return source_text
    marker = "\n\n[truncated]"
    cut = max(limit - len(marker), 1)
    return source_text[:cut] + marker


async def enforce_ai_daily_quota(current_user: User) -> None:
    daily_quota = int(settings.ai_gamification_daily_quota_per_user)
    if daily_quota <= 0:
        return

    day_key = _utc_day_key()
    redis_key = f"ai:quota:gamify:create:user:{current_user.id}:{day_key}"
    ttl_seconds = _seconds_until_next_utc_day()

    try:
        redis = get_redis_client()
        current = await redis.incr(redis_key)
        if current == 1:
            await redis.expire(redis_key, ttl_seconds)
    except Exception:
        logger.exception("AI quota check failed for user_id=%s", current_user.id)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI quota backend unavailable")

    if current > daily_quota:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily AI quota exceeded",
        )


async def _bump_ai_metric(metric_name: str, increment: int = 1) -> None:
    try:
        redis = get_redis_client()
        await redis.hincrby(AI_GAMIFY_METRICS_KEY, metric_name, int(increment))
    except Exception:
        logger.exception("Failed to bump AI metric '%s'", metric_name)


async def enqueue_ai_job(job_id: int) -> None:
    redis = get_redis_client()
    await redis.rpush(AI_GAMIFY_QUEUE, json.dumps({"job_id": int(job_id)}))


def _render_draft_text(draft: AIGamifyDraft) -> str:
    lines: list[str] = [f"Title: {draft.draft_title}", "", f"Story: {draft.story_frame}", ""]
    lines.append(f"Task goal: {draft.task_goal}")
    if draft.game_rules:
        lines.append("")
        lines.append("Game rules:")
        lines.extend([f"- {rule}" for rule in draft.game_rules])
    if draft.hints:
        lines.append("")
        lines.append("Hints:")
        lines.extend([f"- {hint}" for hint in draft.hints])
    if draft.acceptance_criteria:
        lines.append("")
        lines.append("Acceptance criteria:")
        lines.extend([f"- {criterion}" for criterion in draft.acceptance_criteria])
    if draft.rewards and (draft.rewards.xp or draft.rewards.badges):
        lines.append("")
        lines.append(f"XP reward: {draft.rewards.xp}")
        if draft.rewards.badges:
            lines.append(f"Badges: {', '.join(draft.rewards.badges)}")
    if draft.teacher_notes:
        lines.append("")
        lines.append(f"Teacher notes: {draft.teacher_notes}")
    return "\n".join(lines).strip()


def _validate_draft_quality(draft: AIGamifyDraft) -> None:
    def _is_blank(value: str | None) -> bool:
        return value is None or len(value.strip()) < 3

    if _is_blank(draft.draft_title):
        raise AIGamificationDraftValidationError("AI draft is semantically empty: draft_title")
    if _is_blank(draft.story_frame):
        raise AIGamificationDraftValidationError("AI draft is semantically empty: story_frame")
    if _is_blank(draft.task_goal):
        raise AIGamificationDraftValidationError("AI draft is semantically empty: task_goal")


def _with_semantic_fallback_constraints(payload: AIGamifyRequest) -> AIGamifyRequest:
    extra_constraint = (
        "Mandatory: draft_title, story_frame and task_goal must be non-empty, concrete, "
        "and each at least one full sentence."
    )
    constraints = [*(payload.constraints or [])]
    if extra_constraint not in constraints:
        constraints.append(extra_constraint)
    return payload.model_copy(update={"constraints": constraints})


async def _generate_draft_with_semantic_fallback(
    *,
    payload: AIGamifyRequest,
    source_text: str,
):
    primary_result = await generate_gamification_draft(payload=payload, source_text=source_text)
    try:
        _validate_draft_quality(primary_result.draft)
        return primary_result
    except AIGamificationDraftValidationError as exc:
        logger.warning("AI semantic fallback for source_type=%s: %s", payload.source_type.value, exc)
        await _bump_ai_metric("jobs_semantic_fallback_used")

    fallback_payload = _with_semantic_fallback_constraints(payload)
    fallback_result = await generate_gamification_draft(payload=fallback_payload, source_text=source_text)
    _validate_draft_quality(fallback_result.draft)
    return fallback_result


def _validate_apply_target_for_bound_job(job, payload: AIGamifyApplyRequest) -> None:
    if job.source_type not in {"material", "question"}:
        return
    if job.source_id is None:
        return
    if payload.target_type.value != job.source_type or payload.target_id != job.source_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Draft is bound to its source entity and cannot be applied to another target",
        )


async def _apply_draft_to_material(
    db: AsyncSession,
    *,
    target_id: int,
    draft: AIGamifyDraft,
    apply_mode: str,
    current_user: User,
) -> int:
    material = await material_repo.get_material(db, target_id)
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
    if current_user.role == "teacher" and not can_manage_material(current_user, material):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    draft_text = _render_draft_text(draft)
    if apply_mode == "replace":
        material.blocks = [
            MaterialBlock(
                block_type="text",
                title=draft.draft_title,
                body=draft_text,
                url=None,
                order_index=0,
            )
        ]
    else:
        next_order = max((int(block.order_index or 0) for block in material.blocks), default=-1) + 1
        material.blocks.append(
            MaterialBlock(
                block_type="text",
                title=draft.draft_title,
                body=draft_text,
                url=None,
                order_index=next_order,
            )
        )

    await db.flush()
    await db.refresh(material)
    return material.id


async def _apply_draft_to_question(
    db: AsyncSession,
    *,
    target_id: int,
    draft: AIGamifyDraft,
    apply_mode: str,
    current_user: User,
) -> int:
    question = await question_repo.get_question_with_choices(db, target_id)
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    test = await test_repo.get_test(db, question.test_id)
    if test is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found")
    if current_user.role == "teacher" and not can_manage_test(current_user, test):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    draft_text = _render_draft_text(draft)
    if apply_mode == "replace":
        question.text = draft_text
    else:
        base_text = (question.text or "").strip()
        append_text = f"[AI Gamification Draft]\n{draft_text}"
        question.text = f"{base_text}\n\n{append_text}" if base_text else append_text

    await db.flush()
    await db.refresh(question)
    return question.id


def _request_from_job(job) -> AIGamifyRequest:
    return AIGamifyRequest.model_validate(
        {
            "source_type": job.source_type,
            "source_id": job.source_id,
            "raw_text": job.raw_text,
            "target_level": job.target_level,
            "language": job.language,
            "style": job.style,
            "tone": job.tone,
            "constraints": list(job.constraints_json or []),
        }
    )


async def _material_source_snapshot(db: AsyncSession, source_id: int, current_user: User) -> str:
    material = await material_repo.get_material(db, source_id)
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
    if current_user.role == "teacher" and not can_manage_material(current_user, material):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    parts: list[str] = [
        f"Material title: {material.title}",
        f"Material type: {material.material_type}",
    ]
    if material.description:
        parts.append(f"Description: {material.description}")
    for block in sorted(material.blocks, key=lambda item: item.order_index):
        block_line = f"Block[{block.order_index}] type={block.block_type}"
        if block.title:
            block_line += f" title={block.title}"
        parts.append(block_line)
        if block.body:
            parts.append(block.body)
        if block.url:
            parts.append(f"URL: {block.url}")
    for attachment in sorted(material.attachments, key=lambda item: item.order_index):
        parts.append(
            f"Attachment[{attachment.order_index}] {attachment.file_kind}: {attachment.title} ({attachment.file_url})"
        )
    return "\n".join(parts)


async def _question_source_snapshot(db: AsyncSession, source_id: int, current_user: User) -> str:
    question = await question_repo.get_question_with_choices(db, source_id)
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    test = await test_repo.get_test(db, question.test_id)
    if test is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found")
    if current_user.role == "teacher" and not can_manage_test(current_user, test):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    parts: list[str] = [
        f"Question text: {question.text}",
        f"Points: {float(question.points)}",
        f"Is open answer: {bool(question.is_open_answer)}",
    ]
    if question.material_urls:
        parts.append(f"Material URLs: {', '.join(question.material_urls)}")
    for choice in sorted(question.choices, key=lambda item: int(item.ordinal or 0)):
        parts.append(f"Choice[{choice.ordinal}]: {choice.value}")
    return "\n".join(parts)


async def build_source_snapshot(db: AsyncSession, payload: AIGamifyRequest, current_user: User) -> str | None:
    if payload.source_type.value == "raw_text":
        raw_text = (payload.raw_text or "").strip()
        if not raw_text:
            return raw_text
        return _trim_source_text(raw_text)
    if payload.source_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="source_id is required")

    if payload.source_type.value == "material":
        snapshot = await _material_source_snapshot(db, payload.source_id, current_user)
        return _trim_source_text(snapshot)
    if payload.source_type.value == "question":
        snapshot = await _question_source_snapshot(db, payload.source_id, current_user)
        return _trim_source_text(snapshot)

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported source_type")


async def create_ai_gamification_job(db: AsyncSession, payload: AIGamifyRequest, current_user: User):
    try:
        ensure_ai_gamification_ready()
    except AIGamificationDisabledError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except AIGamificationConfigError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

    await enforce_ai_daily_quota(current_user)

    source_snapshot = await build_source_snapshot(db, payload, current_user)
    job = await ai_gamification_repo.create_job(
        db,
        created_by_user_id=current_user.id,
        payload=payload,
        source_snapshot=source_snapshot,
    )

    async def enqueue_after_commit() -> None:
        try:
            await enqueue_ai_job(job.id)
        except Exception as exc:
            logger.exception("Failed to enqueue AI gamification job_id=%s", job.id)
            async with AsyncSessionLocal() as fail_session:
                failed_job = await ai_gamification_repo.get_job(fail_session, job.id)
                if failed_job is not None and failed_job.status == "pending":
                    await ai_gamification_repo.set_job_failed(
                        fail_session,
                        failed_job,
                        error_text=f"Queue unavailable: {exc}",
                    )
                    await fail_session.commit()

    add_post_commit_task(db, enqueue_after_commit)
    return job


async def list_ai_jobs_for_user(
    db: AsyncSession,
    *,
    current_user: User,
    limit: int = 20,
    offset: int = 0,
    status_filter: str | None = None,
    source_type_filter: str | None = None,
) -> list[dict]:
    jobs = await ai_gamification_repo.list_jobs_for_user(
        db,
        current_user_id=current_user.id,
        is_admin=current_user.role == "admin",
        status_filter=status_filter,
        source_type_filter=source_type_filter,
        limit=min(max(limit, 1), 100),
        offset=max(offset, 0),
    )
    return [ai_gamification_repo.to_job_read_payload(item) for item in jobs]


async def retry_ai_gamification_job(
    db: AsyncSession,
    *,
    job_id: int,
    current_user: User,
) -> dict:
    job = await get_job_for_user(db, job_id, current_user)
    if job.status != "failed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only failed jobs can be retried",
        )

    await ai_gamification_repo.reset_job_for_retry(db, job)
    try:
        redis = get_redis_client()
        await redis.delete(f"{AI_GAMIFY_RETRY_KEY_PREFIX}:{job.id}")
        await enqueue_ai_job(job.id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to enqueue retry: {exc}",
        )
    return {"job_id": job.id, "status": "pending"}


async def get_ai_ops_metrics() -> dict:
    redis = get_redis_client()
    metrics_raw = await redis.hgetall(AI_GAMIFY_METRICS_KEY)

    def _to_int(value) -> int:
        if value is None:
            return 0
        try:
            return int(value)
        except Exception:
            return 0

    queued_jobs = _to_int(await redis.llen(AI_GAMIFY_QUEUE))
    dead_letter_jobs = _to_int(await redis.llen(AI_GAMIFY_DLQ))
    return {
        "queued_jobs": queued_jobs,
        "dead_letter_jobs": dead_letter_jobs,
        "jobs_processed": _to_int(metrics_raw.get("jobs_processed")),
        "jobs_completed": _to_int(metrics_raw.get("jobs_completed")),
        "jobs_failed": _to_int(metrics_raw.get("jobs_failed")),
        "jobs_retried": _to_int(metrics_raw.get("jobs_retried")),
        "jobs_semantic_fallback_used": _to_int(metrics_raw.get("jobs_semantic_fallback_used")),
    }


async def get_job_for_user(db: AsyncSession, job_id: int, current_user: User):
    job = await ai_gamification_repo.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if current_user.role != "admin" and job.created_by_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return job


async def apply_job_draft(
    db: AsyncSession,
    *,
    job_id: int,
    payload: AIGamifyApplyRequest,
    current_user: User,
) -> dict:
    job = await get_job_for_user(db, job_id, current_user)

    if job.status == "applied":
        if job.applied_target_type == payload.target_type.value and job.applied_target_id == payload.target_id:
            return {
                "job_id": job.id,
                "status": "applied",
                "updated_entity": {"type": payload.target_type.value, "id": payload.target_id},
            }
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job already applied to another target")

    if job.status != "completed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job must be completed before apply")

    if not job.draft_json:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Completed job has no draft payload")

    _validate_apply_target_for_bound_job(job, payload)

    try:
        draft = AIGamifyDraft.model_validate(job.draft_json)
    except Exception:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Stored draft payload is invalid")
    try:
        _validate_draft_quality(draft)
    except AIGamificationDraftValidationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    if payload.target_type == AIGamifyTargetType.MATERIAL:
        target_id = await _apply_draft_to_material(
            db,
            target_id=payload.target_id,
            draft=draft,
            apply_mode=payload.apply_mode.value,
            current_user=current_user,
        )
        try:
            await bump_cache_namespace(NS_MATERIALS, NS_TESTS, NS_TEST_CONTENT)
        except Exception:
            logger.exception("Failed to bump cache namespace for material apply, target_id=%s", payload.target_id)
    else:
        target_id = await _apply_draft_to_question(
            db,
            target_id=payload.target_id,
            draft=draft,
            apply_mode=payload.apply_mode.value,
            current_user=current_user,
        )
        try:
            await bump_cache_namespace(NS_QUESTIONS, NS_TEST_CONTENT)
        except Exception:
            logger.exception("Failed to bump cache namespace for question apply, target_id=%s", payload.target_id)

    await ai_gamification_repo.set_job_applied(
        db,
        job,
        target_type=payload.target_type.value,
        target_id=payload.target_id,
    )

    return {
        "job_id": job.id,
        "status": "applied",
        "updated_entity": {"type": payload.target_type.value, "id": target_id},
    }


async def process_ai_gamification_job(job_id: int, session_factory=AsyncSessionLocal) -> None:
    # Step 1: mark running and take snapshot of payload fields.
    async with session_factory() as session:
        job = await ai_gamification_repo.get_job(session, job_id)
        if job is None:
            logger.warning("AI job not found: id=%s", job_id)
            return
        if job.status in {"completed", "failed", "applied"}:
            return
        await ai_gamification_repo.set_job_running(session, job)
        await session.commit()

        payload = _request_from_job(job)
        source_text = (job.raw_text or "") if payload.source_type.value == "raw_text" else (job.source_snapshot or "")

    # Step 2: call provider.
    try:
        result = await _generate_draft_with_semantic_fallback(payload=payload, source_text=source_text)
    except Exception as exc:
        retry_key = f"{AI_GAMIFY_RETRY_KEY_PREFIX}:{job_id}"
        max_retries = max(int(settings.ai_gamification_job_max_retries), 0)
        try:
            redis = get_redis_client()
            attempts = await redis.incr(retry_key)
            if attempts == 1:
                await redis.expire(retry_key, 7 * 24 * 3600)
            if attempts <= max_retries:
                await redis.rpush(AI_GAMIFY_QUEUE, json.dumps({"job_id": job_id}))
                await _bump_ai_metric("jobs_retried")
                logger.warning("AI job %s requeued after failure (attempt %s/%s): %s", job_id, attempts, max_retries, exc)
                return
        except Exception:
            logger.exception("AI retry bookkeeping failed for job_id=%s", job_id)

        async with session_factory() as session:
            job = await ai_gamification_repo.get_job(session, job_id)
            if job is None:
                return
            if job.status in {"completed", "applied"}:
                return
            await ai_gamification_repo.set_job_failed(session, job, error_text=str(exc))
            await session.commit()
        await _bump_ai_metric("jobs_failed")
        await _bump_ai_metric("jobs_processed")
        try:
            redis = get_redis_client()
            await redis.rpush(
                AI_GAMIFY_DLQ,
                json.dumps(
                    {
                        "job_id": job_id,
                        "error": str(exc)[:500],
                    }
                ),
            )
        except Exception:
            logger.exception("Failed to push AI job into DLQ job_id=%s", job_id)
        return

    # Step 3: persist completed state.
    async with session_factory() as session:
        job = await ai_gamification_repo.get_job(session, job_id)
        if job is None:
            return
        if job.status in {"applied"}:
            return
        await ai_gamification_repo.set_job_completed(
            session,
            job,
            draft=result.draft,
            model=result.model,
            provider=result.provider,
            usage=result.usage,
            latency_ms=result.latency_ms,
        )
        await session.commit()
    try:
        redis = get_redis_client()
        await redis.delete(f"{AI_GAMIFY_RETRY_KEY_PREFIX}:{job_id}")
    except Exception:
        logger.exception("Failed to cleanup AI retry key for job_id=%s", job_id)
    await _bump_ai_metric("jobs_completed")
    await _bump_ai_metric("jobs_processed")
