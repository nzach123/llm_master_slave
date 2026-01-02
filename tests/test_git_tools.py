import pytest
from unittest.mock import patch, MagicMock
from tools.git_tools import create_checkpoint, revert_to_main, rollback

@patch("tools.git_tools.Repo")
def test_create_checkpoint_new_branch(mock_repo_cls):
    """Test creating a checkpoint branch when it doesn't exist."""
    mock_repo = mock_repo_cls.return_value
    mock_repo.is_dirty.return_value = False
    
    # Mock heads dictionary to simulate branch not existing
    mock_repo.heads = {}

    # Mock the new branch object returned by create_head
    mock_branch = MagicMock()
    mock_repo.create_head.return_value = mock_branch

    task_id = "123"
    create_checkpoint(task_id)

    # Verify create_head was called
    mock_repo.create_head.assert_called_once_with("task/123")
    mock_branch.checkout.assert_called_once()

@patch("tools.git_tools.Repo")
def test_create_checkpoint_existing_branch(mock_repo_cls):
    """Test checking out existing branch."""
    mock_repo = mock_repo_cls.return_value
    mock_repo.is_dirty.return_value = False
    
    # Mock existing branch
    mock_branch = MagicMock()
    mock_repo.heads = {"task/123": mock_branch}

    task_id = "123"
    create_checkpoint(task_id)

    # Verify create_head was NOT called
    mock_repo.create_head.assert_not_called()
    
    # Verify existing branch was checked out
    mock_branch.checkout.assert_called_once()

@patch("tools.git_tools.Repo")
def test_create_checkpoint_dirty(mock_repo_cls):
    """Test exception when repo is dirty."""
    mock_repo = mock_repo_cls.return_value
    mock_repo.is_dirty.return_value = True

    with pytest.raises(Exception, match="Working directory is not clean"):
        create_checkpoint("123")

@patch("tools.git_tools.Repo")
def test_revert_to_main(mock_repo_cls):
    """Test reverting to main."""
    mock_repo = mock_repo_cls.return_value

    revert_to_main()

    mock_repo.git.checkout.assert_called_once_with("main", "-f")
