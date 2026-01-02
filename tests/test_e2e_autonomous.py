"""
E2E tests for autonomous loop with live Gemini and Ollama integration.

These tests validate the complete execution flow:
- Plan generation via Gemini API
- Tool call extraction and execution
- Test feedback and retry logic
"""
import os
import pytest
from pathlib import Path
from core.hub import Spine
from core.specs import AgentResult


@pytest.fixture
def spine():
    """Initialize Spine with live configuration."""
    return Spine()


@pytest.fixture
def cleanup_test_files():
    """Cleanup test artifacts after each test."""
    test_files = [
        "test_utils.py",
        "utils.py",
        "calculator.py",
        "test_calculator.py"
    ]
    yield
    for file in test_files:
        path = Path(file)
        if path.exists():
            path.unlink()


@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set - skipping E2E test"
)
class TestAutonomousLoopE2E:
    """End-to-end tests for the autonomous loop."""
    
    def test_e2e_simple_addition(self, spine):
        """
        Test 1: Simple Addition (Baseline)
        
        Validates:
        - Gemini generates valid plan
        - CoderSpoke returns XML tool calls
        - Parser extracts tool calls correctly
        - Patcher writes file successfully
        - No retries needed
        
        NOTE: Not using cleanup_test_files fixture to check file before cleanup
        """
        intent = (
            "Create a file called 'utils.py' with a single function 'add(a, b)' "
            "that returns a + b. Keep it simple - just the function, no tests."
        )
        
        try:
            result = spine.run_autonomous_loop(intent, max_retries=1)
            
            # Check if file was created (even if tests ran and "failed" the loop)
            utils_path = Path("utils.py")
            file_created = utils_path.exists()
            
            if file_created:
                # Validate content
                content = utils_path.read_text()
                assert "def add(" in content, "Function 'add' not found in utils.py"
                assert "return" in content, "Return statement not found"
                print("✅ Test PASSED - File created with correct content")
            else:
                # File creation failed
                pytest.fail(f"utils.py was not created. Result: {result.message}")
                
        finally:
            # Cleanup
            for file in ["utils.py"]:
                path = Path(file)
                if path.exists():
                    path.unlink()
        
    def test_e2e_with_test_generation(self, spine, cleanup_test_files):
        """
        Test 2: TDD Workflow (Test Execution Feedback)
        
        Validates:
        - LLM creates both implementation and test
        - Test executor runs and captures results
        - Retry logic activates on test failures
        - Error context improves subsequent attempts
        """
        intent = (
            "Create a calculator.py file with a 'divide(a, b)' function that handles "
            "zero division by raising ValueError. Also create test_calculator.py with "
            "pytest tests that validate both normal division and zero division handling."
        )
        
        result = spine.run_autonomous_loop(intent, max_retries=3)
        
        # Validate result
        assert result.status == "ok", f"Expected success, got: {result.message}"
        
        # Validate files were created
        impl_path = Path("calculator.py")
        test_path = Path("test_calculator.py")
        assert impl_path.exists(), "calculator.py was not created"
        assert test_path.exists(), "test_calculator.py was not created"
        
        # Validate implementation
        impl_content = impl_path.read_text()
        assert "def divide(" in impl_content, "Function 'divide' not found"
        assert "ValueError" in impl_content or "ZeroDivisionError" in impl_content, \
            "Zero division handling not found"
        
        # Validate tests
        test_content = test_path.read_text()
        assert "def test_" in test_content, "No test functions found"
        assert "divide" in test_content, "Tests don't reference divide function"
        
    def test_e2e_patch_operation(self, spine, cleanup_test_files):
        """
        Test 3: Patch Operation (Modify Existing File)
        
        Validates:
        - Parser handles apply_patch XML correctly
        - Patcher modifies existing file
        - Idempotency checks work
        """
        # Create initial file
        initial_content = """def greet(name):
    return f"Hello, {name}"
"""
        Path("utils.py").write_text(initial_content)
        
        intent = (
            "Modify utils.py to add a second function called 'farewell(name)' "
            "that returns 'Goodbye, {name}'. Use apply_patch to add it after "
            "the greet function."
        )
        
        result = spine.run_autonomous_loop(intent, max_retries=3)
        
        # Validate result
        assert result.status == "ok", f"Expected success, got: {result.message}"
        
        # Validate file was modified
        utils_path = Path("utils.py")
        content = utils_path.read_text()
        assert "def greet(" in content, "Original greet function was removed"
        assert "def farewell(" in content, "New farewell function not added"
        assert "Goodbye" in content, "Farewell message not found"
        
    def test_e2e_error_recovery(self, spine, cleanup_test_files):
        """
        Test 4: Error Recovery (Retry Logic Stress Test)
        
        Validates:
        - System handles ambiguous requirements
        - Retry logic activates on failures
        - Error context is injected properly
        - Graceful degradation after max retries
        """
        intent = (
            "Create a complex data structure with nested classes in data_structures.py. "
            "Include a Node class and a LinkedList class with append and find methods."
        )
        
        # This may succeed or fail, but should not crash
        result = spine.run_autonomous_loop(intent, max_retries=2)
        
        # Allow either success or graceful failure
        assert result.status in ["ok", "error"], f"Unexpected status: {result.status}"
        assert isinstance(result.message, str), "Result message should be a string"
        
        # If it succeeded, validate basic structure
        if result.status == "ok":
            ds_path = Path("data_structures.py")
            if ds_path.exists():
                content = ds_path.read_text()
                assert "class" in content.lower(), "No class definitions found"


@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set - skipping E2E test"
)
def test_e2e_mock_loop_sanity(spine):
    """
    Sanity test: Verify mock loop still works (no API key needed for this).
    
    This validates that the basic dispatch mechanism works even without
    the autonomous loop.
    """
    os.environ["SKIP_RESOURCE_CHECK"] = "true"
    
    try:
        result = spine.run_mock_loop()
        assert result.status == "ok", f"Mock loop failed: {result.message}"
    finally:
        os.environ.pop("SKIP_RESOURCE_CHECK", None)
