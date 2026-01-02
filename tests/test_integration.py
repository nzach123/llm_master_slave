import os
import subprocess
import shutil
import pytest

def test_full_mock_run(tmp_path):
    """Integration test running main.py in a fresh git repo."""
    # Setup fresh git repo in tmp_path
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    
    # Initialize repo
    subprocess.run(["git", "init"], cwd=repo_dir)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir)
    
    # Copy necessary files to repo_dir, excluding __pycache__
    def ignore_pycache(path, names):
        return [n for n in names if n == '__pycache__']
        
    shutil.copytree("core", repo_dir / "core", ignore=ignore_pycache)
    shutil.copytree("tools", repo_dir / "tools", ignore=ignore_pycache)
    shutil.copy("main.py", repo_dir / "main.py")
    
    # Create initial commit with .gitignore
    (repo_dir / "README.md").write_text("initial")
    (repo_dir / ".gitignore").write_text("activity.log\n__pycache__/\n")
    subprocess.run(["git", "add", "."], cwd=repo_dir)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=repo_dir)
    subprocess.run(["git", "branch", "-M", "master"], cwd=repo_dir)

    # Run main.py in the new repo
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_dir)
    python_exe = os.path.abspath(".venv/Scripts/python.exe")
    
    process = subprocess.Popen(
        [python_exe, "main.py"], 
        cwd=repo_dir,
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        text=True,
        env=env
    )
    stdout, stderr = process.communicate()
    
    # Debug print on failure
    if process.returncode != 0:
        print(f"STDOUT: {stdout}")
        print(f"STDERR: {stderr}")
    
    assert process.returncode == 0
    
    # Verify activity.log in repo_dir
    log_file = repo_dir / "activity.log"
    assert log_file.exists()
    log_content = log_file.read_text()
    
    # Verify git branch creation
    branches = subprocess.check_output(["git", "branch"], cwd=repo_dir, text=True)
    if "task/mock_task_001" not in branches:
        print(f"LOG CONTENT:\n{log_content}")
        print(f"BRANCHES: {branches}")
        status = subprocess.check_output(["git", "status"], cwd=repo_dir, text=True)
        print(f"GIT STATUS:\n{status}")
        
    assert "task/mock_task_001" in branches