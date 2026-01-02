import pytest
from core.hub import Spine

def test_parse_multiple_tool_calls():
    spine = Spine()
    text = """
    I will create two files.
    <write_file path="file1.py">
    print("file1")
    </write_file>
    And another one.
    <write_file path="file2.py">
    print("file2")
    </write_file>
    """
    calls = spine._parse_tool_calls(text)
    assert len(calls) == 2
    assert calls[0].path == "file1.py"
    assert calls[1].path == "file2.py"

def test_parse_apply_patch():
    spine = Spine()
    text = """
    <apply_patch path="utils.py">
    <old>
    old code
    </old>
    <new>
    new code
    </new>
    </apply_patch>
    """
    calls = spine._parse_tool_calls(text)
    assert len(calls) == 1
    assert calls[0].action == "apply_patch"
    assert calls[0].path == "utils.py"
    assert calls[0].old_content.strip() == "old code"
    assert calls[0].content.strip() == "new code"

def test_parse_unescaped_special_chars():
    spine = Spine()
    # XML fails on unescaped & unless handled
    text = """
    <write_file path="logic.py">
    if a > 0 and b < 0:
        print("match")
    </write_file>
    """
    # This might fail with the current implementation if it uses ET.fromstring directly
    calls = spine._parse_tool_calls(text)
    # If it fails, len(calls) will be 0 because of the try-except block in _parse_tool_calls
    assert len(calls) == 1, "Should handle unescaped characters in content"
    assert "if a > 0 and b < 0:" in calls[0].content

def test_parse_malformed_xml():
    spine = Spine()
    text = """
    <write_file path="broken.py">
    missing closing tag...
    """
    calls = spine._parse_tool_calls(text)
    assert len(calls) == 0

def test_parse_with_comments_inside():
    spine = Spine()
    text = """
    <write_file path="code.py">
    def foo():
        pass
    <!-- LLM comment -->
    def bar():
        pass
    </write_file>
    """
    calls = spine._parse_tool_calls(text)
    assert len(calls) == 1
    content = calls[0].content
    assert "def foo():" in content
    assert "def bar():" in content
