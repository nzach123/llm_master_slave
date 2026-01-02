import pytest
from core.parsing import TagParser
from core.specs import ToolCall

def test_parse_write_file_simple():
    parser = TagParser()
    text = """
    Here is the code:
    <write_file path="main.py">
    print("Hello World")
    </write_file>
    """
    calls = parser.parse_tool_calls(text)
    assert len(calls) == 1
    assert calls[0].action == "write_file"
    assert calls[0].path == "main.py"
    assert calls[0].content == 'print("Hello World")'

def test_parse_write_file_with_nested_xml_syntax():
    parser = TagParser()
    text = """
    <write_file path="parser.py">
    code_with_tags = "<div>content</div>"
    if x < 5:
        pass
    </write_file>
    """
    calls = parser.parse_tool_calls(text)
    assert len(calls) == 1
    assert calls[0].path == "parser.py"
    assert '<div>content</div>' in calls[0].content
    assert 'if x < 5:' in calls[0].content

def test_parse_apply_patch_simple():
    parser = TagParser()
    text = """
    <apply_patch path="main.py">
    <old>
    old_code
    </old>
    <new>
    new_code
    </new>
    </apply_patch>
    """
    calls = parser.parse_tool_calls(text)
    assert len(calls) == 1
    assert calls[0].action == "apply_patch"
    assert calls[0].path == "main.py"
    assert "old_code" in calls[0].old_content
    assert "new_code" in calls[0].content

def test_parse_multiple_mixed():
    parser = TagParser()
    text = """
    First file:
    <write_file path="a.py">A</write_file>

    Then patch:
    <apply_patch path="b.py">
        <old>B1</old>
        <new>B2</new>
    </apply_patch>

    Last file:
    <write_file path="c.py">C</write_file>
    """
    calls = parser.parse_tool_calls(text)
    assert len(calls) == 3
    assert calls[0].path == "a.py"
    assert calls[1].path == "b.py"
    assert calls[2].path == "c.py"

def test_parse_malformed_ignored():
    parser = TagParser()
    text = """
    <write_file path="broken.py">
    Missing closing tag
    <write_file path="valid.py">valid</write_file>
    """
    # Depending on logic, it might skip the broken one and find the nested valid one
    # OR it might consider the broken one starts until the end of string (and thus fail to find closing).
    # Current logic: looks for closing tag. If not found, skips the start tag and advances cursor.
    # So it should skip broken.py start tag, then find valid.py.

    calls = parser.parse_tool_calls(text)
    # Actually, my logic advances cursor to start_content_idx if no closing tag found.
    # start_content_idx of "broken.py" is after the opening tag.
    # So it will scan from "Missing closing tag..."
    # It should find valid.py opening tag.

    assert len(calls) == 1
    assert calls[0].path == "valid.py"

def test_parse_apply_patch_messy_content():
    parser = TagParser()
    text = """
    <apply_patch path="complex.py">
    <old>
    def foo(x):
        return x < 10
    </old>
    <new>
    def foo(x):
        return x > 20
    </new>
    </apply_patch>
    """
    calls = parser.parse_tool_calls(text)
    assert len(calls) == 1
    assert "return x < 10" in calls[0].old_content
    assert "return x > 20" in calls[0].content
