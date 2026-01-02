from tinydb import TinyDB, Query
import uuid
import datetime
from typing import List, Dict, Optional, Any

class TaskQueue:
    def __init__(self, db_path: str = "tasks.json"):
        self.db = TinyDB(db_path)
        self.tasks = self.db.table("tasks")
        
    def add_task(self, intent: str, status: str = "pending", priority: int = 1) -> str:
        """Adds a new task to the queue."""
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        self.tasks.insert({
            "task_id": task_id,
            "intent": intent,
            "status": status,
            "priority": priority,
            "created_at": datetime.datetime.now().isoformat(),
            "updated_at": datetime.datetime.now().isoformat(),
            "attempts": 0,
            "history": [],
            "git_branch": None, # Track git branch
            "last_step_index": 0 # Track progress
        })
        return task_id

    def get_pending_tasks(self) -> List[Dict]:
        """Returns all pending tasks sorted by priority."""
        Task = Query()
        # Also return running tasks if we want to resume them?
        # For now, just pending.
        pending = self.tasks.search(Task.status == "pending")
        return sorted(pending, key=lambda x: x["priority"], reverse=True)

    def get_running_tasks(self) -> List[Dict]:
        """Returns tasks that were interrupted (status='running')."""
        Task = Query()
        return self.tasks.search(Task.status == "running")

    def update_task_status(self, task_id: str, status: str, result: Optional[str] = None) -> None:
        """Updates the status of a task."""
        Task = Query()
        update_data = {
            "status": status,
            "updated_at": datetime.datetime.now().isoformat()
        }
        if result:
            update_data["result"] = result
            
        self.tasks.update(update_data, Task.task_id == task_id)

    def update_task_state(self, task_id: str, git_branch: str = None, step_index: int = None):
        """Updates the execution state (branch, step) of a task."""
        Task = Query()
        update_data = {
            "updated_at": datetime.datetime.now().isoformat()
        }
        if git_branch:
            update_data["git_branch"] = git_branch
        if step_index is not None:
            update_data["last_step_index"] = step_index

        self.tasks.update(update_data, Task.task_id == task_id)

    def add_attempt(self, task_id: str, error: str) -> None:
        """Records a failed attempt."""
        Task = Query()
        task = self.tasks.get(Task.task_id == task_id)
        if task:
            attempts = task.get("attempts", 0) + 1
            history = task.get("history", [])
            history.append({
                "timestamp": datetime.datetime.now().isoformat(),
                "error": error
            })
            self.tasks.update({
                "attempts": attempts,
                "history": history,
                "updated_at": datetime.datetime.now().isoformat()
            }, Task.task_id == task_id)

    def get_task(self, task_id: str) -> Optional[Dict]:
        """Retrieves a specific task."""
        Task = Query()
        return self.tasks.get(Task.task_id == task_id)

    def close(self) -> None:
        """Close the TinyDB connection to release file locks."""
        if self.db:
            self.db.close()
