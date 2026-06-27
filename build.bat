@echo off
pip install -r requirements.txt
pip install pyinstaller
python -c "from PIL import Image; img=Image.open('logo.png').convert('RGBA'); img.save('logo.ico', format='ICO', sizes=[(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)])"
pyinstaller gtnh-sync.spec
echo.
echo Built: dist\gtnh-sync.exe
