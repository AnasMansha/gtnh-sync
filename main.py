from __future__ import annotations

import ctypes
import logging
import os
import sys
import threading
import winreg
from dataclasses import dataclass
from pathlib import Path

import pystray
from PIL import Image, ImageDraw

from config import APP_NAME, AppConfig, app_data_dir
from drive_client import DriveClient
from sync_engine import BackupFile, find_latest_backup

logging.basicConfig(
    filename=app_data_dir() / "gtnh-sync.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
ICON_SIZE = 64


@dataclass
class SyncProgress:
    phase: str = "idle"
    filename: str | None = None
    percent: float | None = None

    def message(self) -> str:
        if self.phase == "uploading" and self.filename:
            if self.percent is not None:
                return f"Uploading {self.filename} ({self.percent:.0f}%)"
            return f"Uploading {self.filename}"
        if self.phase == "checking":
            return "Checking Google Drive..."
        if self.phase == "preparing":
            return "Preparing sync..."
        return "Sync in progress"


class SyncApp:
    def __init__(self) -> None:
        self.config = AppConfig.load()
        self.drive = DriveClient()
        self._icon: pystray.Icon | None = None
        self._sync_lock = threading.Lock()
        self._busy = False
        self._progress = SyncProgress()
        self._last_menu_percent = -1.0

    def run(self) -> None:
        if self.config.run_at_startup:
            self._set_startup(True)

        threading.Thread(target=self._startup_check, daemon=True).start()

        menu = pystray.Menu(
            pystray.MenuItem(
                lambda _: self._status_line(),
                None,
                enabled=False,
            ),
            pystray.MenuItem("Sync now", self._on_manual_sync),
            pystray.MenuItem("Open backups folder", self._on_open_backups),
            pystray.MenuItem(
                "Run at startup",
                self._on_toggle_startup,
                checked=lambda _: self.config.run_at_startup,
            ),
            pystray.MenuItem("Exit", self._on_exit),
        )
        self._icon = pystray.Icon(APP_NAME, self._create_icon(), APP_NAME, menu)
        self._icon.run()

    def _create_icon(self) -> Image.Image:
        img = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse((4, 4, ICON_SIZE - 4, ICON_SIZE - 4), fill=(46, 125, 50, 255))
        draw.polygon(
            [(ICON_SIZE // 2, 14), (ICON_SIZE - 16, ICON_SIZE - 18), (16, ICON_SIZE - 18)],
            fill=(255, 255, 255, 255),
        )
        return img

    def _executable_command(self) -> str:
        if getattr(sys, "frozen", False):
            return f'"{sys.executable}"'
        script = Path(__file__).resolve()
        return f'"{sys.executable}" "{script}"'

    def _set_startup(self, enabled: bool) -> None:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE
        )
        try:
            if enabled:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, self._executable_command())
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
        finally:
            winreg.CloseKey(key)
        self.config.run_at_startup = enabled
        self.config.save()

    def _startup_check(self) -> None:
        if self.config.synced_today() or self.config.skipped_today():
            log.info("Startup check skipped: already synced or skipped today")
            return
        self._run_sync_flow(prompt_if_needed=True, daily=True)

    def _on_manual_sync(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        threading.Thread(
            target=self._run_sync_flow, kwargs={"prompt_if_needed": True, "daily": False}, daemon=True
        ).start()

    def _on_open_backups(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        path = Path(self.config.backups_path)
        if path.is_dir():
            os.startfile(path)
        else:
            self._notify("Backups folder not found", str(path))

    def _on_toggle_startup(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        self._set_startup(not self.config.run_at_startup)

    def _on_exit(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        if self._icon:
            self._icon.stop()

    def _status_line(self) -> str:
        if self._busy:
            return self._progress.message()
        return f"Last synced: {self.config.last_synced_display()}"

    def _set_progress(
        self, phase: str, *, filename: str | None = None, percent: float | None = None
    ) -> None:
        self._progress = SyncProgress(phase=phase, filename=filename, percent=percent)
        self._refresh_menu()

    def _on_upload_progress(self, percent: float) -> None:
        self._progress.percent = percent
        if percent - self._last_menu_percent >= 5 or percent >= 100:
            self._last_menu_percent = percent
            self._refresh_menu()

    def _notify(self, title: str, message: str) -> None:
        log.info("%s: %s", title, message)
        if self._icon:
            try:
                self._icon.notify(message, title)
            except Exception:
                pass

    def _show_prompt(self, backup: BackupFile) -> str:
        msg = (
            f"Latest backup: {backup.filename}\n"
            f"Size: {backup.size_mb:.1f} MB\n\n"
            "Upload to Google Drive?\n\n"
            "Yes = sync now\nNo = skip today\nCancel = decide later"
        )
        # MB_YESNOCANCEL | MB_ICONQUESTION
        result = ctypes.windll.user32.MessageBoxW(0, msg, APP_NAME, 3 | 0x20)
        if result == 6:  # IDYES
            return "sync"
        if result == 7:  # IDNO
            return "skip_today"
        return "cancel"

    def _run_sync_flow(self, *, prompt_if_needed: bool, daily: bool) -> None:
        if not self._sync_lock.acquire(blocking=False):
            self._notify("Sync in progress", self._progress.message())
            return

        self._busy = True
        self._last_menu_percent = -1.0
        try:
            self._set_progress("preparing")
            backups_dir = Path(self.config.backups_path)
            backup = find_latest_backup(backups_dir)
            if backup is None:
                msg = f"No backup zip found in {backups_dir}"
                log.warning(msg)
                if not daily:
                    self._notify("No backup found", msg)
                return

            self._set_progress("checking")
            folder_id = self.drive.get_or_create_folder(self.config.drive_folder_name)
            if self.drive.file_exists_in_folder(folder_id, backup.filename):
                log.info("Already on Drive: %s", backup.filename)
                self.config.mark_synced(backup.filename)
                if not daily:
                    self._notify(
                        "Already up to date",
                        f"{backup.filename} is already on Google Drive.",
                    )
                return

            if prompt_if_needed:
                action = self._show_prompt(backup)
                if action == "skip_today":
                    self.config.mark_skipped_today()
                    return
                if action == "cancel":
                    return
                if action != "sync":
                    return

            log.info("Uploading %s", backup.filename)
            self._set_progress("uploading", filename=backup.filename, percent=0)
            self._notify("Syncing...", self._progress.message())
            self.drive.upload_file(
                folder_id, backup.path, on_progress=self._on_upload_progress
            )
            self.config.mark_synced(backup.filename)
            log.info("Upload complete: %s", backup.filename)
            self._notify("Sync complete", f"Uploaded {backup.filename}")
            self._refresh_menu()
        except Exception as exc:
            log.exception("Sync failed")
            self._notify("Sync failed", str(exc))
        finally:
            self._busy = False
            self._progress = SyncProgress()
            self._last_menu_percent = -1.0
            self._refresh_menu()
            self._sync_lock.release()

    def _refresh_menu(self) -> None:
        if self._icon:
            self._icon.update_menu()


def main() -> None:
    SyncApp().run()


if __name__ == "__main__":
    main()
