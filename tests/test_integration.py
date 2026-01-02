import os
import subprocess
import time

def test_full_mock_run():
    """Integration test running main.py and checking side effects."""
    # Ensure activity.log doesn't exist or is cleared
    if os.path.exists("activity.log"):
        os.remove("activity.log")
        
    # Run main.py
    process = subprocess.Popen([r".venv\Scripts\python", "main.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate()
    
    assert process.returncode == 0
    assert "Loop finished" in stdout
    
    # Verify activity.log
    assert os.path.exists("activity.log")
    log_content = open("activity.log").read()
    assert "Spine initialized" in log_content
    assert "Starting mock loop" in log_content
    
    # Verify git branch creation (if it succeeded)
    # Note: create_checkpoint might fail if dirty, but we expect it to try.
    # We can check git branch output.
    branches = subprocess.check_output(["git", "branch"], text=True)
    assert "task/mock_task_001" in branches
    
    # Cleanup: return to main and delete the branch
    subprocess.run(["git", "checkout", "master"])
    subprocess.run(["git", "branch", "-D", "task/mock_task_001"])
