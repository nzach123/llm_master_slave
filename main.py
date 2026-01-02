import argparse
from core.hub import Spine

def main():
    parser = argparse.ArgumentParser(description="Conductor Spine Controller")
    parser.add_argument("--autonomous", metavar="INTENT", type=str, help="Run autonomous loop with user intent")
    parser.add_argument("--queue", action="store_true", help="Process pending tasks in the queue")
    parser.add_argument("--add-task", metavar="INTENT", type=str, help="Add a task to the queue and exit")
    args = parser.parse_args()

    spine = Spine()
    from tools.queue import TaskQueue
    queue = TaskQueue()
    
    if args.add_task:
        task_id = queue.add_task(args.add_task)
        print(f"Task added to queue: {task_id}")
        return

    if args.queue:
        pending = queue.get_pending_tasks()
        if not pending:
            print("No pending tasks in queue.")
            return
        
        print(f"Found {len(pending)} pending tasks. Processing...")
        for task in pending:
            print(f"\nProcessing Task {task['task_id']}: {task['intent']}")
            queue.update_task_status(task["task_id"], "running")
            try:
                result = spine.run_autonomous_loop(task["intent"])
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
            result = spine.run_autonomous_loop(args.autonomous)
            queue.update_task_status(task_id, "completed", result.message)
            print(f"Loop finished. Result: {result.message}")
        except Exception as e:
            queue.update_task_status(task_id, "failed", str(e))
            print(f"Loop failed: {e}")
            raise
    else:
        print("Starting Spine Mock Loop...")
        result = spine.run_mock_loop()
        print(f"Loop finished. Result: {result.message}")

if __name__ == "__main__":
    main()