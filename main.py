import argparse
import os
from core.hub import Spine

def ensure_project_structure():
    """Ensure that the required project directories exist."""
    required_dirs = ["docs/", "src/", "artifacts/"]
    for d in required_dirs:
        if not os.path.exists(d):
            os.makedirs(d)
            print(f"Created directory: {d}")

def main():
    ensure_project_structure()
    parser = argparse.ArgumentParser(description="Conductor Spine Controller")
    parser.add_argument("--autonomous", metavar="INTENT", type=str, help="Run autonomous loop with user intent")
    parser.add_argument("--queue", action="store_true", help="Process pending tasks in the queue")
    parser.add_argument("--project", action="store_true", help="Run the full Project Loop (Macro/Micro)")
    parser.add_argument("--add-task", metavar="INTENT", type=str, help="Add a task to the queue and exit")
    parser.add_argument("-i", "--interactive", action="store_true", help="Run in interactive mode")
    args = parser.parse_args()

    spine = Spine()
    from tools.queue import TaskQueue
    queue = TaskQueue()
    
    if args.add_task:
        task_id = queue.add_task(args.add_task)
        print(f"Task added to queue: {task_id}")
        return

    if args.project:
        print("Starting Project Loop (Macro/Micro)...")
        spine.run_project_loop()

    elif args.queue:
        # Check for interrupted tasks first
        running = queue.get_running_tasks()
        if running:
            print(f"Found {len(running)} interrupted tasks. Attempting to resume...")
            for task in running:
                print(f"\nResuming Task {task['task_id']}: {task['intent']}")
                try:
                    result = spine.run_autonomous_loop(task["intent"], existing_task_id=task["task_id"])
                    queue.update_task_status(task["task_id"], "completed", result.message)
                    print(f"Task {task['task_id']} completed.")
                except Exception as e:
                     queue.update_task_status(task["task_id"], "failed", str(e))
                     queue.add_attempt(task["task_id"], str(e))
                     print(f"Task {task['task_id']} failed: {e}")

        pending = queue.get_pending_tasks()
        if not pending:
            print("No pending tasks in queue.")
            return
        
        print(f"Found {len(pending)} pending tasks. Processing...")
        for task in pending:
            print(f"\nProcessing Task {task['task_id']}: {task['intent']}")
            queue.update_task_status(task["task_id"], "running")
            try:
                result = spine.run_autonomous_loop(task["intent"], existing_task_id=task["task_id"])
                queue.update_task_status(task["task_id"], "completed", result.message)
                print(f"Task {task['task_id']} completed.")
            except Exception as e:
                queue.update_task_status(task["task_id"], "failed", str(e))
                queue.add_attempt(task["task_id"], str(e))
                print(f"Task {task['task_id']} failed: {e}")
                
    elif args.autonomous:
        print(f"Starting Spine Autonomous Loop with intent: {args.autonomous}")
        # Automatically track this one-off task in the queue too
        task_id = queue.add_task(args.autonomous, status="running")
        try:
            result = spine.run_autonomous_loop(args.autonomous, existing_task_id=task_id)
            queue.update_task_status(task_id, "completed", result.message)
            print(f"Loop finished. Result: {result.message}")
        except Exception as e:
            queue.update_task_status(task_id, "failed", str(e))
            print(f"Loop failed: {e}")
            raise
    elif args.interactive:
        print("Starting Interactive Mode. Type 'exit' to quit.")
        while True:
            try:
                user_input = input("\n>> Enter task: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ["exit", "quit"]:
                    break
                
                print(f"Running task: {user_input}")
                # Track in queue
                task_id = queue.add_task(user_input, status="running")
                
                try:
                    result = spine.run_autonomous_loop(user_input, existing_task_id=task_id)
                    queue.update_task_status(task_id, "completed", result.message)
                    print(f"Task completed.\nResult: {result.message}")
                except Exception as e:
                    queue.update_task_status(task_id, "failed", str(e))
                    print(f"Task failed: {e}")
                    
            except KeyboardInterrupt:
                print("\nExiting interactive mode...")
                break
                
    else:
        print("Starting Spine Mock Loop...")
        result = spine.run_mock_loop()
        print(f"Loop finished. Result: {result.message}")

if __name__ == "__main__":
    main()