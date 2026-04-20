import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.user import User
from app.repositories import ai_gamification_repo
from app.schemas.ai_gamification import AIGamifyDraft, AIGamifyRequest
from app.services.ai_gamification_service import AI_GAMIFY_QUEUE, process_ai_gamification_job
from app.services.ai_service import AIGamifyGenerationResult

pytestmark = pytest.mark.asyncio


class _FakeRedis:
    def __init__(self):
        self._counters: dict[str, int] = {}
        self._lists: dict[str, list[str]] = {}
        self._hashes: dict[str, dict[str, int]] = {}

    async def incr(self, key: str) -> int:
        next_value = int(self._counters.get(key, 0)) + 1
        self._counters[key] = next_value
        return next_value

    async def expire(self, *_args, **_kwargs):
        return True

    async def rpush(self, key: str, value: str):
        items = self._lists.setdefault(key, [])
        items.append(value)
        return len(items)

    async def hincrby(self, key: str, field: str, amount: int):
        bucket = self._hashes.setdefault(key, {})
        bucket[field] = int(bucket.get(field, 0)) + int(amount)
        return bucket[field]

    async def delete(self, key: str):
        self._counters.pop(key, None)
        self._lists.pop(key, None)
        self._hashes.pop(key, None)
        return 1


async def test_process_ai_gamification_job_completes_with_draft(db, monkeypatch):
    user = User(username="ai_worker_user", password_hash="x", role="teacher")
    db.add(user)
    await db.flush()

    payload = AIGamifyRequest(source_type="raw_text", raw_text="Explain inheritance in C#")
    job = await ai_gamification_repo.create_job(db, created_by_user_id=user.id, payload=payload, source_snapshot=payload.raw_text)
    await db.commit()

    async def fake_generate(**_kwargs):
        return AIGamifyGenerationResult(
            draft=AIGamifyDraft(
                draft_title="C# Hero Mission",
                story_frame="You are onboarding a junior dev.",
                task_goal="Explain inheritance with an example.",
                game_rules=["Use one class hierarchy", "Keep code short"],
                hints=["Think about base/derived classes"],
                rewards={"xp": 20, "badges": ["inheritance-starter"]},
                acceptance_criteria=["Mentions base class", "Mentions override"],
                teacher_notes="Good for first lecture",
            ),
            model="openrouter/auto",
            provider="openrouter",
            usage={"total_tokens": 42},
            latency_ms=120,
            raw_response={},
        )

    monkeypatch.setattr("app.services.ai_gamification_service.generate_gamification_draft", fake_generate)

    session_factory = async_sessionmaker(bind=db.bind, expire_on_commit=False)
    await process_ai_gamification_job(job.id, session_factory=session_factory)

    async with session_factory() as verify_session:
        refreshed = await ai_gamification_repo.get_job(verify_session, job.id)
    assert refreshed is not None
    assert refreshed.status == "completed"
    assert refreshed.draft_json is not None
    assert refreshed.draft_json["draft_title"] == "C# Hero Mission"
    assert refreshed.model == "openrouter/auto"
    assert refreshed.provider == "openrouter"
    assert refreshed.latency_ms == 120


async def test_process_ai_gamification_job_marks_failed_when_provider_errors(db, monkeypatch):
    user = User(username="ai_worker_error_user", password_hash="x", role="teacher")
    db.add(user)
    await db.flush()

    payload = AIGamifyRequest(source_type="raw_text", raw_text="Explain interfaces")
    job = await ai_gamification_repo.create_job(db, created_by_user_id=user.id, payload=payload, source_snapshot=payload.raw_text)
    await db.commit()

    async def fake_generate(**_kwargs):
        raise RuntimeError("provider timeout")

    monkeypatch.setattr("app.services.ai_gamification_service.generate_gamification_draft", fake_generate)

    session_factory = async_sessionmaker(bind=db.bind, expire_on_commit=False)
    await process_ai_gamification_job(job.id, session_factory=session_factory)

    async with session_factory() as verify_session:
        refreshed = await ai_gamification_repo.get_job(verify_session, job.id)
    assert refreshed is not None
    assert refreshed.status == "failed"
    assert refreshed.error_text is not None
    assert "provider timeout" in refreshed.error_text


async def test_process_ai_gamification_job_retries_before_failed(db, monkeypatch):
    from app.services import ai_gamification_service
    from app.core.config import settings

    fake_redis = _FakeRedis()
    monkeypatch.setattr(ai_gamification_service, "get_redis_client", lambda: fake_redis)
    monkeypatch.setattr(settings, "ai_gamification_job_max_retries", 1)

    user = User(username="ai_worker_retry_user", password_hash="x", role="teacher")
    db.add(user)
    await db.flush()

    payload = AIGamifyRequest(source_type="raw_text", raw_text="Explain polymorphism")
    job = await ai_gamification_repo.create_job(db, created_by_user_id=user.id, payload=payload, source_snapshot=payload.raw_text)
    await db.commit()

    async def always_fail(**_kwargs):
        raise RuntimeError("provider temporary timeout")

    monkeypatch.setattr("app.services.ai_gamification_service.generate_gamification_draft", always_fail)

    session_factory = async_sessionmaker(bind=db.bind, expire_on_commit=False)

    await process_ai_gamification_job(job.id, session_factory=session_factory)
    async with session_factory() as verify_session:
        refreshed = await ai_gamification_repo.get_job(verify_session, job.id)
    assert refreshed is not None
    assert refreshed.status == "running"
    assert len(fake_redis._lists.get(AI_GAMIFY_QUEUE, [])) == 1

    await process_ai_gamification_job(job.id, session_factory=session_factory)
    async with session_factory() as verify_session:
        refreshed = await ai_gamification_repo.get_job(verify_session, job.id)
    assert refreshed is not None
    assert refreshed.status == "failed"


async def test_process_ai_gamification_job_marks_failed_when_draft_semantically_empty(db, monkeypatch):
    from app.services import ai_gamification_service
    from app.core.config import settings

    fake_redis = _FakeRedis()
    monkeypatch.setattr(ai_gamification_service, "get_redis_client", lambda: fake_redis)
    monkeypatch.setattr(settings, "ai_gamification_job_max_retries", 0)

    user = User(username="ai_worker_empty_draft_user", password_hash="x", role="teacher")
    db.add(user)
    await db.flush()

    payload = AIGamifyRequest(source_type="raw_text", raw_text="Explain abstraction")
    job = await ai_gamification_repo.create_job(db, created_by_user_id=user.id, payload=payload, source_snapshot=payload.raw_text)
    await db.commit()

    async def fake_generate(**_kwargs):
        return AIGamifyGenerationResult(
            draft=AIGamifyDraft(
                draft_title="",
                story_frame="",
                task_goal="",
                game_rules=[],
                hints=[],
                rewards={"xp": 0, "badges": []},
                acceptance_criteria=[],
                teacher_notes=None,
            ),
            model="openrouter/free",
            provider="openrouter",
            usage={"total_tokens": 10},
            latency_ms=10,
            raw_response={},
        )

    monkeypatch.setattr("app.services.ai_gamification_service.generate_gamification_draft", fake_generate)

    session_factory = async_sessionmaker(bind=db.bind, expire_on_commit=False)
    await process_ai_gamification_job(job.id, session_factory=session_factory)

    async with session_factory() as verify_session:
        refreshed = await ai_gamification_repo.get_job(verify_session, job.id)
    assert refreshed is not None
    assert refreshed.status == "failed"
    assert refreshed.error_text is not None
    assert "semantically empty" in refreshed.error_text


async def test_process_ai_gamification_job_recovers_with_semantic_fallback(db, monkeypatch):
    from app.services import ai_gamification_service

    fake_redis = _FakeRedis()
    monkeypatch.setattr(ai_gamification_service, "get_redis_client", lambda: fake_redis)

    user = User(username="ai_worker_semantic_fallback_user", password_hash="x", role="teacher")
    db.add(user)
    await db.flush()

    payload = AIGamifyRequest(source_type="raw_text", raw_text="Explain interfaces in C#")
    job = await ai_gamification_repo.create_job(db, created_by_user_id=user.id, payload=payload, source_snapshot=payload.raw_text)
    await db.commit()

    calls = {"count": 0}

    async def fake_generate(**_kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return AIGamifyGenerationResult(
                draft=AIGamifyDraft(
                    draft_title="",
                    story_frame="",
                    task_goal="",
                    game_rules=[],
                    hints=[],
                    rewards={"xp": 0, "badges": []},
                    acceptance_criteria=[],
                    teacher_notes=None,
                ),
                model="openrouter/free",
                provider="openrouter",
                usage={"total_tokens": 10},
                latency_ms=10,
                raw_response={},
            )
        return AIGamifyGenerationResult(
            draft=AIGamifyDraft(
                draft_title="Mission: Interface Contract",
                story_frame="Your team needs a common contract for coding guild members.",
                task_goal="Define and implement a C# interface with one practical example.",
                game_rules=["Keep implementation short"],
                hints=["Describe what must be implemented by every class"],
                rewards={"xp": 20, "badges": ["interface-starter"]},
                acceptance_criteria=["Contains interface definition", "Contains implementation example"],
                teacher_notes=None,
            ),
            model="openrouter/free",
            provider="openrouter",
            usage={"total_tokens": 20},
            latency_ms=20,
            raw_response={},
        )

    monkeypatch.setattr("app.services.ai_gamification_service.generate_gamification_draft", fake_generate)

    session_factory = async_sessionmaker(bind=db.bind, expire_on_commit=False)
    await process_ai_gamification_job(job.id, session_factory=session_factory)

    async with session_factory() as verify_session:
        refreshed = await ai_gamification_repo.get_job(verify_session, job.id)
    assert refreshed is not None
    assert refreshed.status == "completed"
    assert refreshed.draft_json is not None
    assert refreshed.draft_json["draft_title"] == "Mission: Interface Contract"
    assert calls["count"] == 2
    assert fake_redis._hashes.get("ai:gamify:metrics", {}).get("jobs_semantic_fallback_used") == 1
