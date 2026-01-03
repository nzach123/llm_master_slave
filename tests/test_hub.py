import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from core.hub import Spine
from core.specs import DispatchStep, AgentResult, SpokeResponse

@pytest.fixture
def mock_spine():
    """Fixture to create a Spine instance with mocked internal components."""
    with patch("core.hub.load_config"), \
         patch("core.hub.setup_logging"), \
         patch("core.hub.CoderSpoke"), \
         patch("core.hub.ReviewerSpoke"), \
         patch("core.hub.ResearcherSpoke"), \
         patch("core.hub.Troubleshooter"), \
         patch("core.hub.JudgeSpoke"), \
         patch("core.hub.TaskQueue"), \
         patch("core.hub.GeminiClient"), \
         patch("core.hub.ConsensusScorer"):  # Though we replaced it, init might still try to use it if not fully removed or if mocked
        spine = Spine()
        # Mocking resource_lock since it's an asyncio.Lock which needs an event loop
        spine.resource_lock = AsyncMock()
        spine.resource_lock.__aenter__.return_value = None
        spine.resource_lock.__aexit__.return_value = None
        return spine

@pytest.mark.asyncio
@patch("core.hub.create_checkpoint")
async def test_spine_run_mock_loop(mock_checkpoint, mock_spine):
    """Test the mock loop runs and validates results."""
    # Mocking dispatch_to_agent to avoid real network/retry latency in unit test
    with patch.object(mock_spine, "dispatch_to_agent", new_callable=AsyncMock) as mock_dispatch:
        mock_dispatch.return_value = SpokeResponse(
            thoughts="Mock success", 
            tool_calls=[]
        )
        
        await mock_spine.run_mock_loop()
        
        # Verify checkpoint was called
        mock_checkpoint.assert_called_once_with("mock_task_001")
        # Verify dispatch was called
        mock_dispatch.assert_called_once()

@pytest.mark.asyncio
@patch("core.hub.create_checkpoint")
@patch("tools.git_tools.get_current_branch")
@patch("core.hub.wait_for_resources", return_value=True)
async def test_spine_run_autonomous_loop(mock_wait, mock_get_branch, mock_checkpoint, mock_spine):
    """Test the autonomous loop uses Planner and dispatches tasks."""
    mock_get_branch.return_value = "main"

    # Mock Planner
    mock_spine.planner.generate_plan.return_value = DispatchStep(
        agent="MockAgent",
        task="Generated Task",
        context_files=[]
    )
    # Mock _negotiate_plan to skip negotiation logic for this test
    mock_spine._negotiate_plan = AsyncMock(return_value=DispatchStep(
        agent="coder",
        task="Generated Task",
        context_files=[]
    ))
    
    # Mock asyncio.to_thread for input()
    with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_input:
        mock_input.return_value = "" # Simulate User pressing Enter
        
        with patch.object(mock_spine, "dispatch_to_agent", new_callable=AsyncMock) as mock_dispatch:
            mock_dispatch.return_value = SpokeResponse(
                thoughts="Autonomous success",
                tool_calls=[]
            )

            await mock_spine.run_autonomous_loop("User Goal")

            # Verify checkpoint
            mock_checkpoint.assert_called()
            # Verify dispatch (negotiation may dispatch to researcher, then coder)
            mock_dispatch.assert_called()

@pytest.mark.asyncio
@patch("core.hub.wait_for_resources", return_value=True)
async def test_spine_retry_logic(mock_wait, mock_spine):
    """Test that dispatch_to_agent retries on failure using tenacity."""
    step = DispatchStep(agent="coder", task="task", context_files=[])
    
    # We need to patch the handle_task method on the CoderSpoke instance
    # Since mock_spine.coder is a Mock, we can set its handle_task side effect
    mock_spine.coder.handle_task = AsyncMock()
    
    # Fail once, then succeed
    mock_spine.coder.handle_task.side_effect = [Exception("Fail"), SpokeResponse(thoughts="Success", tool_calls=[])]

    result = await mock_spine.dispatch_to_agent(step)

    assert result.thoughts == "Success"
    assert mock_spine.coder.handle_task.call_count == 2
