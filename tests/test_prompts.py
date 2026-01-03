from core.prompts import SYSTEM_PROMPT, get_system_prompt

def test_system_prompt_contains_guidelines():
    assert "Comprehensiveness" in SYSTEM_PROMPT
    assert "Strict JSON" in SYSTEM_PROMPT

def test_get_system_prompt_includes_schema():
    prompt = get_system_prompt()
    assert "DispatchStep" in prompt
    assert "agent_name" in prompt
    assert "task_description" in prompt
    assert "context" in prompt
