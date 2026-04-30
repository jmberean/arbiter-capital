from __future__ import annotations

import json
import os
import time
from pathlib import Path
from core.persistence import STATE_DIR

HEAD_FILE = STATE_DIR / "audit_chain_head.json"


class AuditChainHead:
    def __init__(self):
        self._data = json.loads(HEAD_FILE.read_text()) if HEAD_FILE.exists() else {"head": None}

    @property
    def head(self) -> str | None:
        return self._data.get("head")

    def advance(self, tx_hash: str) -> None:
        self._data = {"head": tx_hash, "updated": time.time()}
        tmp = HEAD_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data))
        os.replace(tmp, HEAD_FILE)
