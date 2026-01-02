from git import Repo

def create_checkpoint(task_id: str) -> None:
    """
    Creates a new branch for the task.
    Fails if working directory is not clean.
    """
    repo = Repo(".")
    
    if repo.is_dirty(untracked_files=True):
        raise Exception("Working directory is not clean. Please commit or stash changes.")
        
    branch_name = f"task/{task_id}"
    repo.git.checkout("-b", branch_name)

def revert_to_main() -> None:
    """
    Reverts to main branch.
    """
    repo = Repo(".")
    repo.git.checkout("main")
