from git import Repo, Head
import logging

def create_checkpoint(task_id: str, strict: bool = False) -> None:
    """
    Creates a new branch for the task, or checks out an existing one.
    
    Args:
        task_id: The task identifier used for the branch name.
        strict: If True, also fail on untracked files. Default False ignores untracked.
    """
    repo = Repo(".")
    
    if repo.is_dirty(untracked_files=strict):
        raise Exception("Working directory is not clean. Please commit or stash changes.")
        
    branch_name = f"task/{task_id}"
    if branch_name in repo.heads:
        repo.git.checkout(branch_name)  # Resume existing branch
    else:
        repo.git.checkout("-b", branch_name)  # Create new branch

def revert_to_main() -> None:
    """
    Reverts to main branch.
    """
    repo = Repo(".")
    repo.git.checkout("main", "-f")
