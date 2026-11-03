"""Trusted ID ↔ content_sha256 binding for frozen PRED/DEC artifacts (G1-R3).

Production path uses a persistent file with flock + atomic replace so separate
CLI processes observe prior bindings.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Iterable

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None  # type: ignore


class IdRegistry:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path is not None else None
        self._map: dict[str, str] = {}
        self.reload()

    def reload(self) -> None:
        self._map = {}
        if not self.path or not self.path.exists():
            return
        text = self.path.read_text(encoding="utf-8")
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            row = json.loads(line)
            self._map[str(row["id"])] = str(row["content_sha256"])

    def check(self, artifact_id: str, content_sha256: str) -> str | None:
        """Return error/status code if known; None if new."""
        prev = self._map.get(artifact_id)
        if prev is None:
            return None
        if prev != content_sha256:
            return "ID_HASH_CONFLICT"
        return "ID_REPLAY_SAME"

    def register(self, artifact_id: str, content_sha256: str) -> None:
        self._map[artifact_id] = content_sha256

    def save(self) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            json.dumps({"id": k, "content_sha256": v}, sort_keys=True)
            for k, v in sorted(self._map.items())
        ]
        payload = "\n".join(lines) + ("\n" if lines else "")
        fd, tmp_name = tempfile.mkstemp(
            prefix=self.path.name + ".",
            suffix=".tmp",
            dir=str(self.path.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_name, self.path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    def _lock_path(self) -> Path:
        assert self.path is not None
        return self.path.with_suffix(self.path.suffix + ".lock")

    def check_and_register(
        self,
        bindings: Iterable[tuple[str, str]],
    ) -> tuple[str, dict[str, str]]:
        """Atomically reload, check, update, and persist bindings.

        Returns (status, detail) where status is:
          - "ok_new" — at least one new binding written
          - "ok_replay" — all bindings identical to existing
          - "ID_HASH_CONFLICT" — same id, different hash
        """
        items = [(str(i), str(h)) for i, h in bindings]
        if self.path is None:
            # In-memory only (tests)
            statuses: list[str] = []
            for aid, h in items:
                code = self.check(aid, h)
                if code == "ID_HASH_CONFLICT":
                    return "ID_HASH_CONFLICT", {"id": aid}
                if code == "ID_REPLAY_SAME":
                    statuses.append("replay")
                else:
                    statuses.append("new")
                    self.register(aid, h)
            if statuses and all(s == "replay" for s in statuses):
                return "ok_replay", {}
            return "ok_new", {}

        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("", encoding="utf-8")
        lock_path = self._lock_path()
        lock_path.touch(exist_ok=True)
        with open(lock_path, "a+", encoding="utf-8") as lockf:
            if fcntl is not None:
                fcntl.flock(lockf.fileno(), fcntl.LOCK_EX)
            try:
                self.reload()
                statuses = []
                for aid, h in items:
                    code = self.check(aid, h)
                    if code == "ID_HASH_CONFLICT":
                        return "ID_HASH_CONFLICT", {"id": aid}
                    if code == "ID_REPLAY_SAME":
                        statuses.append("replay")
                    else:
                        statuses.append("new")
                        self.register(aid, h)
                if any(s == "new" for s in statuses):
                    self.save()
                    return "ok_new", {}
                return "ok_replay", {}
            finally:
                if fcntl is not None:
                    fcntl.flock(lockf.fileno(), fcntl.LOCK_UN)
