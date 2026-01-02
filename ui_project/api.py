import sys
import os

# Add project root to path so we can import tools module
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from flask import Flask, request, jsonify, send_from_directory
from tools.queue import TaskQueue
from tools.resource_monitor import get_available_ram, get_available_vram
import logging
import subprocess
import threading

# Track queue process
queue_process = None
queue_lock = threading.Lock()

app = Flask(__name__, static_folder='.')

# Singleton queue instance
queue = TaskQueue(os.path.join(PROJECT_ROOT, "tasks.json"))

# Configure logging - use separate logger to avoid conflicting with queue subprocess
# Suppress Werkzeug HTTP request spam in logs
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.ERROR)  # Only log errors from werkzeug

# Set up our app logger to append to activity.log
app_logger = logging.getLogger('dashboard')
app_logger.setLevel(logging.INFO)
log_file = os.path.join(PROJECT_ROOT, 'activity.log')
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
app_logger.addHandler(file_handler)

@app.route('/')
def serve_index():
    """Serve the main dashboard HTML."""
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files (JS, CSS)."""
    return send_from_directory('.', filename)

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """List all pending tasks from the queue."""
    try:
        tasks = queue.get_pending_tasks()
        return jsonify(tasks)
    except Exception as e:
        app_logger.error(f"Error fetching tasks: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks', methods=['POST'])
def add_task():
    """Add a new task to the queue."""
    data = request.get_json()
    if not data or 'task' not in data:
        return jsonify({"error": "Invalid JSON payload. Missing 'task' key."}), 400
    try:
        task_id = queue.add_task(data['task'])
        app_logger.info(f"Task added: {task_id} - {data['task']}")
        return jsonify({"message": "Task added successfully", "task_id": task_id}), 201
    except Exception as e:
        app_logger.error(f"Error adding task: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def get_health():
    """Return system resource status (RAM/VRAM)."""
    try:
        ram = get_available_ram()
        vram = get_available_vram()
        return jsonify({
            "ram_gb": round(ram, 2),
            "vram_gb": round(vram, 2),
            "status": "healthy" if ram > 2.0 and vram > 2.0 else "low"
        })
    except Exception as e:
        app_logger.error(f"Error fetching health: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Return the last 50 lines from activity.log."""
    log_path = os.path.join(PROJECT_ROOT, 'activity.log')
    try:
        with open(log_path, 'r') as file:
            lines = file.readlines()[-50:]
        return jsonify({"logs": [line.strip() for line in lines]})
    except FileNotFoundError:
        return jsonify({"logs": [], "message": "No log file found yet."})
    except Exception as e:
        app_logger.error(f"Error fetching logs: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/queue/start', methods=['POST'])
def start_queue():
    """Start processing the task queue in a background process."""
    global queue_process
    
    with queue_lock:
        # Check if already running
        if queue_process is not None and queue_process.poll() is None:
            return jsonify({
                "status": "already_running",
                "message": "Queue processor is already running",
                "pid": queue_process.pid
            }), 200
        
        try:
            # Get python executable path
            python_exe = os.path.join(PROJECT_ROOT, '.venv', 'Scripts', 'python.exe')
            main_py = os.path.join(PROJECT_ROOT, 'main.py')
            
            # Start queue processor as subprocess
            queue_process = subprocess.Popen(
                [python_exe, main_py, '--queue'],
                cwd=PROJECT_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )
            
            app_logger.info(f"Queue processor started with PID: {queue_process.pid}")
            return jsonify({
                "status": "started",
                "message": "Queue processor started",
                "pid": queue_process.pid
            }), 201
            
        except Exception as e:
            app_logger.error(f"Error starting queue: {e}")
            return jsonify({"error": str(e)}), 500

@app.route('/api/queue/status', methods=['GET'])
def queue_status():
    """Check if the queue processor is running."""
    global queue_process
    
    with queue_lock:
        if queue_process is None:
            return jsonify({"running": False, "status": "not_started"})
        
        poll = queue_process.poll()
        if poll is None:
            return jsonify({"running": True, "status": "running", "pid": queue_process.pid})
        else:
            return jsonify({"running": False, "status": "finished", "exit_code": poll})

if __name__ == '__main__':
    print("Starting UI Dashboard on http://localhost:5000")
    app.run(debug=True, port=5000)