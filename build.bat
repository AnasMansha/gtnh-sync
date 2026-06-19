@echo off
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --onefile --windowed --name gtnh-sync ^
  --hidden-import=googleapiclient.discovery ^
  --hidden-import=google_auth_oauthlib.flow ^
  main.py
echo.
echo Built: dist\gtnh-sync.exe
