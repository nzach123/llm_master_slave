"""
Integration test for the Tool Binder (XML parser).
Tests that the system can parse XML tool calls and execute them safely.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.hub import Spine
from core.specs import ToolCall


def test_xml_parser():
    """Test XML parsing functionality."""
    print("=== Testing XML Parser ===\n")
    
    spine = Spine()
    
    # Sample LLM output with XML tags
    sample_output = """
I'll help you create that file.

<write_file path="test_output.txt">
Hello from the autonomous system!
This is a test file.
</write_file>

The file has been created.
"""
    
    # Parse the output
    tool_calls = spine._parse_tool_calls(sample_output)
    
    print(f"Parsed {len(tool_calls)} tool calls:")
    for i, call in enumerate(tool_calls, 1):
        print(f"  {i}. {call.action} -> {call.path}")
    
    # Test execution (should create file)
    if tool_calls:
        print("\nExecuting tool calls...")
        results = spine._execute_tool_calls(tool_calls)
        
        print(f"\nResults:")
        print(f"  Success: {results['success']}")
        print(f"  Failed: {results['failed']}")
        
        # Verify file was created
        if os.path.exists("test_output.txt"):
            print("\n✓ File was successfully created!")
            with open("test_output.txt") as f:
                content = f.read()
                print(f"  Content: {content[:50]}...")
            
            # Cleanup
            os.remove("test_output.txt")
            print("✓ Cleanup complete")
        else:
            print("\n✗ File was NOT created")


def test_path_security():
    """Test path whitelisting security."""
    print("\n\n=== Testing Path Security ===\n")
    
    spine = Spine()
    
    # Malicious attempt to write outside project
    malicious_output = """
<write_file path="/etc/passwd">
HACKED
</write_file>
"""
    
    tool_calls = spine._parse_tool_calls(malicious_output)
    
    if tool_calls:
        print(f"Parsed malicious call: {tool_calls[0].path}")
        print("Attempting execution (should fail)...")
        
        results = spine._execute_tool_calls(tool_calls)
        
        if results['failed']:
            print(f"\n✓ Security check worked!")
            print(f"  Error: {results['failed'][0]}")
        else:
            print(f"\n✗ SECURITY BREACH! File was written outside project!")


def test_patch_operation():
    """Test apply_patch XML parsing."""
    print("\n\n=== Testing Patch Operation ===\n")
    
    spine = Spine()
    
    # Create a test file first
    test_file = "patch_test.py"
    with open(test_file, "w") as f:
        f.write("def old_function():\n    pass\n")
    
    print(f"Created {test_file} with old content")
    
    # LLM output with patch
    patch_output = """
<apply_patch path="patch_test.py">
<old>def old_function():</old>
<new>def new_function():</new>
</apply_patch>
"""
    
    tool_calls = spine._parse_tool_calls(patch_output)
    
    if tool_calls:
        print(f"\nParsed patch: {tool_calls[0].action}")
        results = spine._execute_tool_calls(tool_calls)
        
        if results['success']:
            print("✓ Patch applied successfully")
            
            # Verify patch
            with open(test_file) as f:
                content = f.read()
                if "new_function" in content:
                    print("✓ Content was correctly updated")
                else:
                    print("✗ Content was NOT updated")
        
        # Cleanup
        os.remove(test_file)
        print("✓ Cleanup complete")


if __name__ == "__main__":
    print("INTEGRATION TESTS: Tool Binder\n")
    print("=" * 50)
    
    try:
        test_xml_parser()
        test_path_security()
        test_patch_operation()
        
        print("\n" + "=" * 50)
        print("ALL TESTS COMPLETED")
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
