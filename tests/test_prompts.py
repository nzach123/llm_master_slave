from core.prompts import SYSTEM_PROMPT

def test_system_prompt_contains_guidelines():
    assert "Technical Minimalism" in SYSTEM_PROMPT
    assert "Strict JSON" in SYSTEM_PROMPT
