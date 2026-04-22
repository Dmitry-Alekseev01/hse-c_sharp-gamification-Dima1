from app.schemas.ai_gamification import AIGamifyRequest
from app.services.ai_service import _build_system_prompt, _build_user_prompt


def test_system_prompt_requires_semantic_equivalence():
    prompt = _build_system_prompt()
    assert "without changing the assignment semantics" in prompt
    assert "keep all original logic" in prompt
    assert "every numeric value unchanged" in prompt


def test_user_prompt_resolves_anime_universe_and_preserves_numbers_rule():
    payload = AIGamifyRequest(
        source_type="raw_text",
        raw_text="Solve 3 tasks. Time limit is 45 minutes. Maximum score is 100.",
        constraints=["anime: Naruto", "keep all tests"],
        style="mission",
        tone="friendly",
    )
    prompt = _build_user_prompt(payload, payload.raw_text or "")
    assert "Preferred anime universe: Naruto" in prompt
    assert "Preserve every numeric value exactly as in source" in prompt
    assert "3 tasks" in prompt
    assert "45 minutes" in prompt
    assert "Maximum score is 100" in prompt

