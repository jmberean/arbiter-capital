# core/persistence.py
import json, os, threading
from pathlib import Path

STATE_DIR = Path(__file__).resolve().parent.parent / "state"
STATE_DIR.mkdir(exist_ok=True)
_LOCK = threading.Lock()

class CursorStore:
    def __init__(self, process_name: str):
        self.path = STATE_DIR / f"{process_name}.cursors.json"
        self._cache = json.loads(self.path.read_text()) if self.path.exists() else {}

    def get(self, topic: str) -> int: return int(self._cache.get(topic, 0))

    def set(self, topic: str, last_id: int) -> None:
        with _LOCK:
            self._cache[topic] = int(last_id)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._cache))
            os.replace(tmp, self.path)
