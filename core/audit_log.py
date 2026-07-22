"""Log de auditoria: registra toda alteração (real ou simulada) em log.txt."""

from __future__ import annotations

import getpass
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class LogEntry:
    timestamp: str
    user: str
    action: str
    target: str
    field: str
    before: Any
    after: Any
    dry_run: bool
    extra: dict[str, Any] = field(default_factory=dict)


def make_entry(
    *,
    action: str,
    target: str,
    field_name: str,
    before: Any,
    after: Any,
    dry_run: bool,
    extra: dict[str, Any] | None = None,
) -> LogEntry:
    return LogEntry(
        timestamp=datetime.now(UTC).isoformat(timespec="seconds"),
        user=getpass.getuser(),
        action=action,
        target=target,
        field=field_name,
        before=before,
        after=after,
        dry_run=dry_run,
        extra=extra or {},
    )


def append_log(log_path: Path, entry: LogEntry) -> None:
    """Escreve uma linha JSON por evento — fácil de auditar depois."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")


def read_log(log_path: Path, limit: int = 200) -> list[dict[str, Any]]:
    """Lê as últimas `limit` entradas do log (mais recentes primeiro)."""
    if not log_path.exists():
        return []
    lines = log_path.read_text(encoding="utf-8").splitlines()
    entries = [json.loads(line) for line in lines if line.strip()]
    return list(reversed(entries[-limit:]))
