from git import Repo, Head
import logging

logger = logging.getLogger(__name__)

def get_current_branch() -> str:
    repo = Repo(".")
    return repo.active_branch.name

def create_checkpoint(task_id: str) -> str:
    """
    Creates a new branch for the task and returns its name.
    If the branch already exists (resume scenario), checks it out.
    Fails if working directory is not clean.
    """
    repo = Repo(".")
    
    # We allow dirty state ONLY if we are already on the correct task branch (resuming mid-work)
    # But for safety, let's enforce clean state before switching/creating.
    if repo.is_dirty(untracked_files=True):
        # Exception: if we are already on the target branch, maybe we don't care?
        # But safest is to require clean start.
        raise Exception("Working directory is not clean. Please commit or stash changes before starting/resuming autonomous loop.")
        
    branch_name = f"task/{task_id}"

    # Check if branch exists
    if branch_name in repo.heads:
        logger.info(f"Task branch {branch_name} already exists. Checking out...")
        repo.heads[branch_name].checkout()
    else:
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
