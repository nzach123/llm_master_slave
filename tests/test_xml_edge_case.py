"""
Test to verify XML content parsing with child elements (edge case).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.hub import Spine


def test_xml_with_child_elements():
    """Test that XML parser handles content with child elements correctly."""
    print("=== Testing XML Parser with Child Elements ===\n")
    
    spine = Spine()
    
    # LLM output with XML comment (creates child element)
    sample_output = """
<write_file path="test_edge_case.py">
def function():
    pass
<!-- this is a comment -->
def another_function():
    pass
</write_file>
"""
    
    tool_calls = spine._parse_tool_calls(sample_output)
    
    if tool_calls:
        content = tool_calls[0].content
        print(f"Parsed content:\n{content}\n")
        
        # Verify both functions are present (content after comment)
        if "another_function" in content:
            print("✅ SUCCESS: Content after child element was preserved!")
        else:
            print("❌ FAILURE: Content after child element was lost!")
            return False
    else:
        print("❌ FAILURE: No tool calls parsed!")
        return False
    
    return True


if __name__ == "__main__":
    try:
        success = test_xml_with_child_elements()
        exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
