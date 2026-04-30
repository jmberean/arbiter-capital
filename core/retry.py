"""Exponential backoff with jitter and heartbeat helpers for daemon processes."""
import logging
import random
import time
import threading
from typing import Callable, Optional

logger = logging.getLogger("retry")

HEARTBEAT_INTERVAL = 5.0   # seconds between heartbeat publishes
SILENCE_THRESHOLD  = 30.0  # seconds before peer is considered silent


def with_backoff(
    fn: Callable,
    *,
    max_attempts: int = 8,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: float = 0.5,
    exceptions: tuple = (Exception,),
) -> object:
    """Call fn(), retrying with exponential backoff on failure.

    Raises the last exception if all attempts are exhausted.
    """
    attempt = 0
    while True:
        try:
            return fn()
        except exceptions as exc:
            attempt += 1
            if attempt >= max_attempts:
                logger.error(f"All {max_attempts} attempts failed: {exc}")
                raise
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            delay += random.uniform(0, jitter * delay)
            logger.warning(f"Attempt {attempt} failed ({exc}). Retrying in {delay:.1f}s…")
            time.sleep(delay)


class HeartbeatEmitter:
    """Publishes a HEARTBEAT message on the AXL bus every HEARTBEAT_INTERVAL seconds.

    Run start() in a background thread. Call stop() on shutdown.
    """

    def __init__(self, axl_node, daemon_id: str):
        self._node = axl_node
        self._daemon_id = daemon_id
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self._thread = threading.Thread(target=self._loop, daemon=True, name=f"hb-{self._daemon_id}")
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=HEARTBEAT_INTERVAL + 1)

    def _loop(self):
        while not self._stop_event.wait(timeout=HEARTBEAT_INTERVAL):
            try:
                self._node.publish("HEARTBEAT", {
                    "daemon_id": self._daemon_id,
                    "ts": time.time(),
                })
            except Exception as exc:
                logger.warning(f"HeartbeatEmitter({self._daemon_id}): publish failed: {exc}")


class HeartbeatMonitor:
    """Tracks the last-seen heartbeat from each daemon.

    Call record(daemon_id) each time a HEARTBEAT arrives.
    Call is_silent(daemon_id) to check if the peer has been quiet for > SILENCE_THRESHOLD seconds.
    """

    def __init__(self):
        self._last_seen: dict[str, float] = {}
        self._lock = threading.Lock()

    def record(self, daemon_id: str):
        with self._lock:
            self._last_seen[daemon_id] = time.time()

    def is_silent(self, daemon_id: str, threshold: float = SILENCE_THRESHOLD) -> bool:
        with self._lock:
            last = self._last_seen.get(daemon_id)
        if last is None:
            return True
        return (time.time() - last) > threshold

    def last_seen(self, daemon_id: str) -> Optional[float]:
        with self._lock:
            return self._last_seen.get(daemon_id)
