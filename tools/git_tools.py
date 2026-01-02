from git import Repo, Head
import logging

logger = logging.getLogger(__name__)

def get_current_branch() -> str:
    repo = Repo(".")
    return repo.active_branch.name

def create_checkpoint(task_id: str) -> str:
    """
    Creates a new branch for the task and returns its name.
    Fails if working directory is not clean.
    """
    repo = Repo(".")
    
    if repo.is_dirty(untracked_files=True):
        raise Exception("Working directory is not clean. Please commit or stash changes before starting autonomous loop.")
        
    branch_name = f"task/{task_id}"
    new_branch = repo.create_head(branch_name)
    new_branch.checkout()
    logger.info(f"Created and checked out task branch: {branch_name}")
    return branch_name

def rollback(original_branch: str, task_branch: str = None) -> None:
    """
    Rolls back to the original branch and optionally deletes the failed task branch.
    Uses hard reset to ensure a clean state.
    """
    repo = Repo(".")
    logger.warning(f"Rolling back to {original_branch}...")
    
    # Force checkout original branch
    repo.git.checkout(original_branch, "-f")
    
    # Hard reset to ensure exact match with original state
    repo.git.reset("--hard", "HEAD")
    repo.git.clean("-fd")
    
    if task_branch and task_branch != original_branch:
        try:
            repo.delete_head(task_branch, force=True)
            logger.info(f"Deleted failed task branch: {task_branch}")
        except Exception as e:
            logger.warning(f"Could not delete branch {task_branch}: {e}")

def revert_to_main() -> None:
    """
    Reverts to main branch.
    """
    repo = Repo(".")
    repo.git.checkout("main", "-f")
