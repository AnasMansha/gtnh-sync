from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from config import KEEP_DRIVE_BACKUPS_BEFORE_UPLOAD, credentials_path, token_path
from sync_engine import parse_backup_name

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


class DriveClient:
    def __init__(self) -> None:
        self._service = None

    def _get_credentials(self) -> Credentials:
        creds: Credentials | None = None
        token = token_path()
        creds_file = credentials_path()

        if token.exists():
            creds = Credentials.from_authorized_user_file(str(token), SCOPES)

        if creds and creds.valid:
            return creds

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token.write_text(creds.to_json(), encoding="utf-8")
            return creds

        if not creds_file.exists():
            raise FileNotFoundError(
                f"Missing Google OAuth credentials at {creds_file}. "
                "See README.md for setup steps."
            )

        flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
        creds = flow.run_local_server(port=0)
        token.write_text(creds.to_json(), encoding="utf-8")
        return creds

    @property
    def service(self):
        if self._service is None:
            creds = self._get_credentials()
            self._service = build("drive", "v3", credentials=creds, cache_discovery=False)
        return self._service

    def get_or_create_folder(self, folder_name: str) -> str:
        query = (
            f"name = '{folder_name}' and "
            "mimeType = 'application/vnd.google-apps.folder' and "
            "trashed = false"
        )
        results = (
            self.service.files()
            .list(q=query, spaces="drive", fields="files(id, name)")
            .execute()
        )
        files = results.get("files", [])
        if files:
            return files[0]["id"]

        metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        folder = self.service.files().create(body=metadata, fields="id").execute()
        return folder["id"]

    def file_exists_in_folder(self, folder_id: str, filename: str) -> bool:
        safe_name = filename.replace("'", "\\'")
        query = (
            f"name = '{safe_name}' and "
            f"'{folder_id}' in parents and "
            "trashed = false"
        )
        results = (
            self.service.files()
            .list(q=query, spaces="drive", fields="files(id)")
            .execute()
        )
        return bool(results.get("files"))

    def list_backups_in_folder(self, folder_id: str) -> list[tuple[str, str]]:
        query = f"'{folder_id}' in parents and trashed = false"
        results = (
            self.service.files()
            .list(q=query, spaces="drive", fields="files(id, name)", pageSize=100)
            .execute()
        )

        backups: list[tuple[str, str, datetime]] = []
        for file_info in results.get("files", []):
            timestamp = parse_backup_name(file_info["name"])
            if timestamp is None:
                continue
            backups.append((file_info["id"], file_info["name"], timestamp))

        backups.sort(key=lambda item: item[2], reverse=True)
        return [(file_id, name) for file_id, name, _ in backups]

    def prune_old_backups(
        self, folder_id: str, keep: int = KEEP_DRIVE_BACKUPS_BEFORE_UPLOAD
    ) -> list[str]:
        backups = self.list_backups_in_folder(folder_id)
        deleted: list[str] = []
        for file_id, name in backups[keep:]:
            self.service.files().delete(fileId=file_id).execute()
            deleted.append(name)
        return deleted

    def upload_file(
        self,
        folder_id: str,
        file_path: Path,
        on_progress: Callable[[float], None] | None = None,
    ) -> None:
        metadata = {"name": file_path.name, "parents": [folder_id]}
        media = MediaFileUpload(str(file_path), resumable=True)
        request = self.service.files().create(
            body=metadata, media_body=media, fields="id"
        )
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status and on_progress:
                on_progress(status.progress() * 100)
