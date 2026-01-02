import pytest
from unittest.mock import MagicMock, patch
from tools.git_tools import create_checkpoint, revert_to_main

@patch("tools.git_tools.Repo")
def test_create_checkpoint(mock_repo_cls):
    """Test creating a checkpoint branch."""
    mock_repo = mock_repo_cls.return_value
    mock_repo.is_dirty.return_value = False # Clean working directory
    
    task_id = "123"
    create_checkpoint(task_id)
    
    # Verify we initialized repo at current dir
    mock_repo_cls.assert_called_once_with(".")
    
    # Verify we checked out a new branch
    mock_repo.git.checkout.assert_called_once_with("-b", "task/123")

@patch("tools.git_tools.Repo")
def test_create_checkpoint_dirty(mock_repo_cls):
    """Test that checkpoint fails if repo is dirty."""
    mock_repo = mock_repo_cls.return_value
    mock_repo.is_dirty.return_value = True
    
    with pytest.raises(Exception, match="Working directory is not clean"):
        create_checkpoint("123")

@patch("tools.git_tools.Repo")
def test_revert_to_main(mock_repo_cls):
    """Test reverting to main."""
    mock_repo = mock_repo_cls.return_value
    
    revert_to_main()
    
    mock_repo.git.checkout.assert_called_once_with("main")
