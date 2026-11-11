$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
py -3 -m venv .venv-win
if ($LASTEXITCODE -ne 0) { throw 'Python 3 wird benötigt.' }
& .\.venv-win\Scripts\python.exe -m pip install -r requirements.txt pywebview==6.1 keyring==25.7.0 pyinstaller==6.16.0
if ($LASTEXITCODE -ne 0) { throw 'Abhängigkeiten konnten nicht installiert werden.' }
& .\.venv-win\Scripts\python.exe -m PyInstaller --noconfirm --clean --windowed --onedir --name Ahnenarchiv --paths . --add-data 'app/static;app/static' --add-data 'seed;seed' --collect-all uvicorn --collect-all sqlalchemy --collect-all keyring --collect-all webview --hidden-import keyring.backends.Windows desktop/launcher.py
if ($LASTEXITCODE -ne 0) { throw 'EXE-Build fehlgeschlagen.' }
Write-Host 'Fertig: dist\Ahnenarchiv\Ahnenarchiv.exe. Den gesamten Ordner auf Papas Rechner kopieren.'
