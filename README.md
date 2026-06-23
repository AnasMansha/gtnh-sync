# GTNH Sync

**Automatically back up your GregTech: New Horizons world saves to Google Drive.**

GTNH Sync is a small Windows app that lives in your system tray (near the clock). It finds your newest GTNH backup zip, asks if you want to upload it, and skips the upload if that file is already on Google Drive.

No command line needed after setup — just run it once, sign in to Google, and forget about it.

---

## What you need

- **Windows 10 or 11**
- A **Google account** (Gmail works)
- **Prism Launcher** (or any launcher) with GTNH backups saved as zip files
- About **15 minutes** for one-time setup

Backup files must be named like this (default format of backups):

```
2026-06-15-16-07-32.zip
```

(year-month-day-hour-minute-second.zip — this is Prism’s default format.)

---

## Quick start (easiest)

### Step 1 — Download the app

1. Go to the [**Releases**](https://github.com/AnasMansha/gtnh-sync/releases) page on GitHub.
2. Open the **latest** release and download **`gtnh-sync.exe`** from the Assets section.
3. Put it somewhere permanent, for example:

   ```
   C:\Tools\gtnh-sync\gtnh-sync.exe
   ```

   > **Tip:** Avoid the Downloads folder — Windows may block or delete files there.

### Step 2 — Set up Google Drive access (one time)

The app needs permission to upload files to _your_ Google Drive. You create a free “key” in Google’s developer console. This sounds technical, but just follow the steps:

1. Open **[Google Cloud Console](https://console.cloud.google.com/)** and sign in.
2. Click **Select a project** → **New Project**.
   - Name it anything (e.g. `GTNH Backup`) → **Create**.
3. Enable the Drive API:
   - Left menu → **APIs & Services** → **Library**
   - Search **Google Drive API** → click it → **Enable**
4. Set up the consent screen:
   - **APIs & Services** → **OAuth consent screen**
   - Choose **External** → **Create**
   - App name: `GTNH Sync` (or anything)
   - User support email: your email
   - Developer contact: your email
   - **Save and Continue** through the scopes page (defaults are fine)
   - On **Test users**, click **Add users** and add **your own Gmail address**
   - **Save and Continue** → **Back to Dashboard**
5. Create login credentials:
   - **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth client ID**
   - Application type: **Desktop app**
   - Name: `GTNH Sync` → **Create**
   - Click **Download JSON** (download icon on the new credential)
6. Rename the downloaded file to **`credentials.json`**
7. Copy it to this folder (create the folder if it doesn’t exist):

   ```
   %APPDATA%\gtnh-sync\
   ```

   **How to open that folder:**
   - Press `Win + R`
   - Type `%APPDATA%\gtnh-sync` and press Enter
   - Paste `credentials.json` there

   > **Important:** Never share `credentials.json` or upload it to GitHub. It’s personal to your Google project.

### Step 3 — Run the app

1. Double-click **`gtnh-sync.exe`**.
2. A browser window opens — sign in with Google and click **Allow**.
3. Look for a **green circle icon** in the system tray (click the `^` arrow near the clock if you don’t see it).

You’re done! The app will check for backups when Windows starts.

---

## Point the app at your backups folder

The first time you run the app, it creates a settings file here:

```
%APPDATA%\gtnh-sync\config.json
```

Open it in Notepad and set **`backups_path`** to where your GTNH backups live.

**Prism Launcher (typical path):**

```
C:\Users\YourName\AppData\Roaming\PrismLauncher\instances\GT New Horizons\minecraft\backups
```

Replace `YourName` with your Windows username. If your instance has a different name, change that part too.

**How to find your folder:**

1. Open Prism Launcher → right-click your GTNH instance → **Folder**
2. Go into `minecraft` → `backups`
3. Copy the path from the File Explorer address bar
4. In `config.json`, use double backslashes: `C:\\Users\\...`

See [`config.json.example`](config.json.example) for a full example.

---

## How to use it every day

### On Windows login

If you haven’t synced or skipped today, the app will:

1. Find your newest backup zip
2. If it’s **already on Google Drive** → quietly marks today as done (no popup)
3. If it’s **new** → shows a popup:

   | Button     | What it does                                    |
   | ---------- | ----------------------------------------------- |
   | **Yes**    | Upload the backup now                           |
   | **No**     | Skip for today (won’t ask again until tomorrow) |
   | **Cancel** | Decide later (will ask again today)             |

### Tray menu (right-click the green icon)

| Menu item               | What it does                               |
| ----------------------- | ------------------------------------------ |
| **Last synced**         | Shows when the last upload finished        |
| **Sync now**            | Check and upload manually                  |
| **Open backups folder** | Opens your local backups folder            |
| **Run at startup**      | Toggle whether the app starts with Windows |
| **Exit**                | Close the app                              |

During upload, the menu shows progress like `Uploading 2026-06-15-16-07-32.zip (42%)`.

### Where files go on Google Drive

Uploads appear in a folder called **`GTNH Backups`** in your Google Drive. You can rename this in `config.json` (`drive_folder_name`).

The app keeps at most **3 backups** on Drive. Before each upload, it deletes older backups and keeps only the **2 newest** ones, then uploads the new file.

---

## Troubleshooting

### “Missing Google OAuth credentials”

`credentials.json` is not in `%APPDATA%\gtnh-sync\`. Repeat [Step 2](#step-2--set-up-google-drive-access-one-time) above.

### Browser doesn’t open / sign-in fails

- Make sure you added yourself as a **Test user** on the OAuth consent screen.
- Delete `%APPDATA%\gtnh-sync\token.json` and run the app again to sign in fresh.

### “No backup zip found”

- Check `backups_path` in `config.json` points to the right folder.
- Confirm backup files are named `YYYY-MM-DD-HH-MM-SS.zip`.

### Upload seems stuck at 0%

Large backups (several GB) can take a while before the percentage moves. Right-click the tray icon — the menu shows live progress. As long as it eventually increases, the upload is working.

### App doesn’t start with Windows

Right-click the tray icon → make sure **Run at startup** is checked.

### Something else went wrong

Check the log file:

```
%APPDATA%\gtnh-sync\gtnh-sync.log
```

---

## Files on your PC (reference)

| File                                   | Purpose                                      |
| -------------------------------------- | -------------------------------------------- |
| `%APPDATA%\gtnh-sync\credentials.json` | Your Google OAuth key (you create this)      |
| `%APPDATA%\gtnh-sync\token.json`       | Saved Google sign-in (created automatically) |
| `%APPDATA%\gtnh-sync\config.json`      | Backup folder path and settings              |
| `%APPDATA%\gtnh-sync\gtnh-sync.log`    | Error and activity log                       |

---

## Build from source (developers)

Requires **Python 3.11+**.

```powershell
git clone https://github.com/AnasMansha/gtnh-sync.git
cd gtnh-sync
pip install -r requirements.txt
python main.py
```

**Build a standalone `.exe`:**

```powershell
build.bat
```

Output: `dist\gtnh-sync.exe`

Copy `credentials.json.example` to `%APPDATA%\gtnh-sync\credentials.json` and fill in your values from Google Cloud Console.

---

## Publishing a release (maintainers)

Releases are built automatically by GitHub Actions when you push a version tag. You do **not** need to run `build.bat` or upload the exe by hand.

```powershell
git tag v1.0.0
git push origin v1.0.0
```

GitHub will build `gtnh-sync.exe` on Windows and publish a release with the file attached. Tags must start with `v` (for example `v1.0.0`, `v1.0.1`).

Check progress under the repo’s **Actions** tab. When it finishes, the new release appears on the **Releases** page.

---

## Project structure

```
gtnh-sync/
├── main.py              # Tray app and sync flow
├── drive_client.py      # Google Drive API
├── sync_engine.py       # Finds latest backup zip
├── config.py            # Settings and paths
├── build.bat            # Build script for Windows exe
├── .github/workflows/   # Auto-build release on version tags
├── requirements.txt     # Python dependencies
├── credentials.json.example
└── config.json.example
```

---

## License

[MIT](LICENSE) — free to use and modify.

---

## Privacy

GTNH Sync only uploads files **you** choose to sync. It uses Google’s official Drive API with the `drive.file` scope, which means it can only see files it created — not your entire Drive. Credentials and tokens stay on your computer in `%APPDATA%\gtnh-sync\`.
