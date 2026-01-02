import pytest
import os
from tools.queue import TaskQueue

def test_add_get_task(tmp_path):
    db_path = tmp_path / "test_tasks.json"
    q = TaskQueue(str(db_path))
    
    task_id = q.add_task("Test intent", priority=10)
    assert task_id.startswith("task_")
    
    task = q.get_task(task_id)
    assert task["intent"] == "Test intent"
    assert task["priority"] == 10
    assert task["status"] == "pending"

def test_get_pending_tasks(tmp_path):
    db_path = tmp_path / "test_tasks.json"
    q = TaskQueue(str(db_path))
    
    q.add_task("Low priority", priority=1)
    q.add_task("High priority", priority=5)
    
    pending = q.get_pending_tasks()
    assert len(pending) == 2
    assert pending[0]["priority"] == 5
    assert pending[1]["priority"] == 1

def test_update_status(tmp_path):
    db_path = tmp_path / "test_tasks.json"
    q = TaskQueue(str(db_path))
    
    task_id = q.add_task("Status test")
    q.update_task_status(task_id, "completed", result="All good")
    
    task = q.get_task(task_id)
    assert task["status"] == "completed"
    assert task["result"] == "All good"

def test_add_attempt(tmp_path):
    db_path = tmp_path / "test_tasks.json"
    q = TaskQueue(str(db_path))
    
    task_id = q.add_task("Attempt test")
    q.add_attempt(task_id, "First failure")
    q.add_attempt(task_id, "Second failure")
    
    task = q.get_task(task_id)
    assert task["attempts"] == 2
    assert len(task["history"]) == 2
    assert task["history"][0]["error"] == "First failure"
