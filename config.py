import json
import os
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path

APP_NAME = "GTNH Sync"
DEFAULT_BACKUPS_PATH = (
    r"C:\Users\YourName\AppData\Roaming\PrismLauncher"
    r"\instances\GT New Horizons\minecraft\backups"
)
DEFAULT_DRIVE_FOLDER = "GTNH Backups"
MAX_DRIVE_BACKUPS = 3
KEEP_DRIVE_BACKUPS_BEFORE_UPLOAD = MAX_DRIVE_BACKUPS - 1


def app_data_dir() -> Path:
    base = Path(os.environ.get("APPDATA", Path.home()))
    path = base / "gtnh-sync"
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    return app_data_dir() / "config.json"


def credentials_path() -> Path:
    return app_data_dir() / "credentials.json"


def token_path() -> Path:
    return app_data_dir() / "token.json"


@dataclass
class AppConfig:
    backups_path: str = DEFAULT_BACKUPS_PATH
    drive_folder_name: str = DEFAULT_DRIVE_FOLDER
    last_synced_at: str | None = None
    last_synced_file: str | None = None
    last_prompt_skipped_date: str | None = None
    run_at_startup: bool = True

    @classmethod
    def load(cls) -> "AppConfig":
        path = config_path()
        if not path.exists():
            return cls()
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**known)

    def save(self) -> None:
        with config_path().open("w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)

    def synced_today(self) -> bool:
        if not self.last_synced_at:
            return False
        synced = datetime.fromisoformat(self.last_synced_at).date()
        return synced == date.today()

    def skipped_today(self) -> bool:
        if not self.last_prompt_skipped_date:
            return False
        return self.last_prompt_skipped_date == date.today().isoformat()

    def mark_synced(self, filename: str) -> None:
        self.last_synced_at = datetime.now().isoformat(timespec="seconds")
        self.last_synced_file = filename
        self.save()

    def mark_skipped_today(self) -> None:
        self.last_prompt_skipped_date = date.today().isoformat()
        self.save()

    def last_synced_display(self) -> str:
        if not self.last_synced_at:
            return "Never"
        dt = datetime.fromisoformat(self.last_synced_at)
        return dt.strftime("%b %d, %Y %I:%M %p")
