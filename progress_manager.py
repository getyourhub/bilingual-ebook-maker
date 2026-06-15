import threading
from typing import Dict, Optional


class ProgressManager:
    def __init__(self):
        self._tasks: Dict[str, dict] = {}
        self._results: Dict[str, dict] = {}
        self._lock = threading.Lock()

    def init_task(self, task_id: str):
        with self._lock:
            self._tasks[task_id] = {
                "task_id": task_id,
                "status": "initializing",
                "phase": "init",
                "percent": 0,
                "message": "Starting...",
                "error": None
            }

    def update(self, task_id: str, phase: str, percent: int, message: str):
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].update({
                    "phase": phase,
                    "percent": percent,
                    "message": message,
                    "status": "error" if phase == "error" else "processing"
                })

    def get(self, task_id: str) -> dict:
        with self._lock:
            return self._tasks.get(task_id, {
                "task_id": task_id,
                "status": "unknown",
                "percent": 0,
                "message": "Task not found"
            })

    def set_result(self, task_id: str, result: dict):
        with self._lock:
            self._results[task_id] = result
            if task_id in self._tasks:
                self._tasks[task_id]["status"] = "done"
                self._tasks[task_id]["percent"] = 100
                self._tasks[task_id]["message"] = "Translation complete!"

    def get_result(self, task_id: str) -> Optional[dict]:
        with self._lock:
            return self._results.get(task_id)
