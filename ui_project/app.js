// UI Dashboard JavaScript
// Polls Flask API endpoints and updates the dashboard

document.addEventListener('DOMContentLoaded', function () {
    const taskList = document.getElementById('task-list');
    const healthStatus = document.getElementById('health-status');
    const logContainer = document.getElementById('log-container');
    const errorMessage = document.getElementById('error-message');
    const taskForm = document.getElementById('task-form');

    // Fetch tasks and update the task list
    async function fetchTasks() {
        try {
            const response = await fetch('/api/tasks');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            const tasks = await response.json();
            taskList.innerHTML = '';

            if (tasks.length === 0) {
                taskList.innerHTML = '<li class="empty">No pending tasks</li>';
                return;
            }

            tasks.forEach(task => {
                const li = document.createElement('li');
                li.className = `task-item status-${task.status}`;
                li.innerHTML = `
                    <span class="task-id">${task.task_id}</span>
                    <span class="task-intent">${task.intent}</span>
                    <span class="badge-${task.status}">${task.status}</span>
                `;
                taskList.appendChild(li);
            });
            clearError();
        } catch (error) {
            showError('Error fetching tasks: ' + error.message);
        }
    }

    // Fetch system health and update status
    async function fetchSystemHealth() {
        try {
            const response = await fetch('/api/health');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            const data = await response.json();
            healthStatus.innerHTML = `
                <div class="health-item">
                    <span class="label">RAM:</span>
                    <span class="value">${data.ram_gb} GB</span>
                </div>
                <div class="health-item">
                    <span class="label">VRAM:</span>
                    <span class="value">${data.vram_gb} GB</span>
                </div>
                <div class="health-item">
                    <span class="label">Status:</span>
                    <span class="value status-${data.status}">${data.status}</span>
                </div>
            `;
            clearError();
        } catch (error) {
            showError('Error fetching health: ' + error.message);
        }
    }

    // Fetch logs and update display
    async function fetchLogs() {
        try {
            const response = await fetch('/api/logs');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            const data = await response.json();
            logContainer.innerHTML = '';

            if (!data.logs || data.logs.length === 0) {
                logContainer.innerHTML = '<p class="empty">No logs yet</p>';
                return;
            }

            // Show most recent logs first
            data.logs.reverse().forEach(line => {
                const p = document.createElement('p');
                p.className = 'log-line';
                p.textContent = line;
                logContainer.appendChild(p);
            });
            clearError();
        } catch (error) {
            showError('Error fetching logs: ' + error.message);
        }
    }

    // Handle form submission
    async function createTask(event) {
        event.preventDefault();
        const taskInput = document.getElementById('task-description');
        const taskText = taskInput.value.trim();

        if (!taskText) {
            showError('Please enter a task description');
            return;
        }

        try {
            const response = await fetch('/api/tasks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ task: taskText })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || response.statusText);
            }

            taskInput.value = '';
            fetchTasks(); // Refresh task list
            clearError();
        } catch (error) {
            showError('Error creating task: ' + error.message);
        }
    }

    // Error display helpers
    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.style.display = 'block';
    }

    function clearError() {
        errorMessage.style.display = 'none';
    }

    // Queue control functions
    const queueStatusEl = document.getElementById('queue-status');
    const startQueueBtn = document.getElementById('start-queue-btn');

    async function startQueue() {
        try {
            startQueueBtn.disabled = true;
            startQueueBtn.textContent = 'Starting...';

            const response = await fetch('/api/queue/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            const data = await response.json();

            if (data.status === 'started' || data.status === 'already_running') {
                updateQueueStatus(true, data.pid);
                clearError();
            } else {
                throw new Error(data.error || 'Failed to start queue');
            }
        } catch (error) {
            showError('Error starting queue: ' + error.message);
            startQueueBtn.disabled = false;
            startQueueBtn.textContent = '▶ Start Queue';
        }
    }

    async function checkQueueStatus() {
        try {
            const response = await fetch('/api/queue/status');
            const data = await response.json();
            updateQueueStatus(data.running, data.pid);
        } catch (error) {
            console.error('Error checking queue status:', error);
        }
    }

    function updateQueueStatus(running, pid) {
        if (running) {
            queueStatusEl.textContent = `Running (PID: ${pid})`;
            queueStatusEl.className = 'queue-status status-running';
            startQueueBtn.disabled = true;
            startQueueBtn.textContent = '⏳ Processing...';
        } else {
            queueStatusEl.textContent = 'Stopped';
            queueStatusEl.className = 'queue-status status-stopped';
            startQueueBtn.disabled = false;
            startQueueBtn.textContent = '▶ Start Queue';
        }
    }

    // Initial fetch
    fetchTasks();
    fetchSystemHealth();
    fetchLogs();
    checkQueueStatus();

    // Set up polling intervals
    setInterval(fetchTasks, 5000);      // Every 5 seconds
    setInterval(fetchSystemHealth, 10000); // Every 10 seconds
    setInterval(fetchLogs, 3000);       // Every 3 seconds
    setInterval(checkQueueStatus, 2000); // Every 2 seconds

    // Attach form handler
    if (taskForm) {
        taskForm.addEventListener('submit', createTask);
    }

    // Attach queue button handler
    if (startQueueBtn) {
        startQueueBtn.addEventListener('click', startQueue);
    }
});