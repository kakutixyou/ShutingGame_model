import pytest

from to_model.reasoning.persona_and_flow import FriendlyResolutionFirstEngine


def test_greeting_is_not_treated_as_task():
    engine = FriendlyResolutionFirstEngine()
    result = engine.process_user_wishes("今日はいい天気ですね。")
    assert result["message_type"] == "greeting"
    assert result["execution_state"] == "idle"
    assert result["resolved_items"] == []


def test_task_extraction_handles_action_request():
    engine = FriendlyResolutionFirstEngine()
    result = engine.process_user_wishes("マルウェアの挙動を解析して、あと自己紹介もして")
    wishes = [item["user_wish"] for item in result["resolved_items"]]
    assert any("マルウェアの挙動を解析して" in wish for wish in wishes)
    assert any("自己紹介もして" in wish for wish in wishes)


def test_execution_error_marks_resolution_false():
    engine = FriendlyResolutionFirstEngine()
    result = engine.process_user_wishes(
        "マルウェアの挙動を調べて",
        execution_results=[{"error": "failed"}],
    )
    assert result["resolved_items"][0]["resolved"] is False
    assert result["execution_state"] == "needs_clarification"


def test_self_intro_returns_intro_and_state():
    engine = FriendlyResolutionFirstEngine()
    result = engine.process_user_wishes("自己紹介して")
    assert result["message_type"] == "self_intro"
    assert result["execution_state"] == "introducing"
    assert "自作AI" in result["friendly_response_text"]


def test_teacher_template_is_applied_for_role_specific_response():
    engine = FriendlyResolutionFirstEngine()
    result = engine.process_user_wishes("先生、自己紹介して", interaction_role="teacher")
    assert result["interaction_role"] == "teacher"
    assert "指導" in result["friendly_response_text"] or "ご相談" in result["friendly_response_text"]


def test_malware_context_proposal_is_contextual():
    engine = FriendlyResolutionFirstEngine()
    result = engine.process_user_wishes(
        "マルウェアの挙動を調べて",
        execution_results=[{"success": True}],
    )
    assert "サンプル確認" in result["follow_up_proposal"]
    assert result["task_history"][0]["status"] == "resolved"


