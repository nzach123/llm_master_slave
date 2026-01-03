import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from core.hub import Spine
from core.specs import DispatchStep, AgentResult, SpokeResponse, ToolCall
import core.hub

@pytest.mark.asyncio
@patch("core.hub.create_checkpoint")
@patch("tools.git_tools.get_current_branch")
@patch("core.hub.GeminiClient")
@patch("core.hub.run_pytest")
async def test_autonomous_loop_includes_verification_steps(mock_run_pytest, mock_client_class, mock_get_branch, mock_checkpoint):
    """Test that manual verification steps are appended to the result message."""
    mock_get_branch.return_value = "main"
    mock_checkpoint.return_value = "task/abc"
    
    # Mock successful test run
    mock_test_result = MagicMock()
    mock_test_result.success = True
    mock_run_pytest.return_value = mock_test_result
    
    # Mock Spine dependencies
    with patch('core.hub.load_config', return_value={}), \
         patch('core.hub.setup_logging'):
        
        spine = Spine()
        mock_client = mock_client_class.return_value
        mock_client.generate_plan.return_value = DispatchStep(
            agent="coder",
            task="Implement add function",
            context_files=[]
        )
        mock_client.generate_verification_steps.return_value = "**Manual Verification Steps:**\n1. Run it."
        
        # Mock negotiation to skip it or return success
        with patch.object(spine, "_negotiate_plan", new_callable=AsyncMock) as mock_neg:
            mock_neg.return_value = mock_client.generate_plan.return_value
            
            with patch.object(spine, "dispatch_to_agent", new_callable=AsyncMock) as mock_dispatch:
                mock_dispatch.return_value = SpokeResponse(
                    thoughts="Code implemented.",
                    tool_calls=[]
                )
                
                # Mock _parse_tool_calls and _execute_tool_calls
                with patch.object(spine, "_parse_tool_calls") as mock_parse:
                    mock_parse.return_value = []
                    
                    with patch.object(spine, "_execute_tool_calls") as mock_execute:
                         mock_execute.return_value = {"success": ["Modified file"], "failed": []}
                         
                         # Mock input and run_pytest
                         with patch("asyncio.to_thread", side_effect=lambda f, *args, **kwargs: mock_test_result if f == core.hub.run_pytest else (None if f == input else f(*args, **kwargs))):
                            result = await spine.run_autonomous_loop("Add function", max_retries=1)
                         
                            assert result.status == "ok"
                            assert "Code implemented." in result.message
                            assert "**Manual Verification Steps:**" in result.message
                            mock_client.generate_verification_steps.assert_called_once()
