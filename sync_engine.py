import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

BACKUP_PATTERN = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-(\d{2})\.zip$"
)


@dataclass(frozen=True)
class BackupFile:
    path: Path
    filename: str
    timestamp: datetime

    @property
    def size_mb(self) -> float:
        return self.path.stat().st_size / (1024 * 1024)


def parse_backup_name(name: str) -> datetime | None:
    match = BACKUP_PATTERN.match(name)
    if not match:
        return None
    y, mo, d, h, mi, s = (int(g) for g in match.groups())
    return datetime(y, mo, d, h, mi, s)


def find_latest_backup(backups_dir: Path) -> BackupFile | None:
    if not backups_dir.is_dir():
        return None

    latest: BackupFile | None = None
    for path in backups_dir.glob("*.zip"):
        ts = parse_backup_name(path.name)
        if ts is None:
            continue
        candidate = BackupFile(path=path, filename=path.name, timestamp=ts)
        if latest is None or candidate.timestamp > latest.timestamp:
            latest = candidate
    return latest
