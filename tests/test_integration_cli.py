import pytest
from unittest.mock import patch, ANY
import sys
from main import main

@pytest.mark.asyncio
@patch("main.Spine")
async def test_main_default_mock(mock_spine_class):
    """Test main() runs mock loop by default."""
    mock_spine = mock_spine_class.return_value
    # Ensure call to async method returns a coroutine (awaitable)
    async def async_mock(*args, **kwargs):
        class Result:
            message = "Success"
        return Result()
    mock_spine.run_mock_loop.side_effect = async_mock
    
    with patch.object(sys, 'argv', ['main.py']):
        await main()
        
    mock_spine.run_mock_loop.assert_called_once()
    mock_spine.run_autonomous_loop.assert_not_called()

@pytest.mark.asyncio
@patch("main.Spine")
async def test_main_autonomous(mock_spine_class):
    """Test main() runs autonomous loop with --autonomous flag."""
    mock_spine = mock_spine_class.return_value
    # Ensure call to async method returns a coroutine (awaitable)
    async def async_mock(*args, **kwargs):
        class Result:
            message = "Success"
        return Result()
    mock_spine.run_autonomous_loop.side_effect = async_mock
    
    with patch.object(sys, 'argv', ['main.py', '--autonomous', 'Write code']):
        await main()
        
    # main.py now generates a task_id and passes it as existing_task_id
    # We use ANY for the task_id since it's random
    mock_spine.run_autonomous_loop.assert_called_once_with('Write code', existing_task_id=ANY)
    mock_spine.run_mock_loop.assert_not_called()

@pytest.mark.asyncio
@patch("main.Spine")
@patch("builtins.input", side_effect=["exit"])
async def test_main_interactive(mock_input, mock_spine_class):
    """Test main() with -i flag enters interactive loop."""
    mock_spine = mock_spine_class.return_value
    
    with patch.object(sys, 'argv', ['main.py', '-i']):
        await main()
    
    # It should have called print or input at least, but to verify it entered the block
    # we can check if it mocked input was called
    mock_input.assert_called_once()
