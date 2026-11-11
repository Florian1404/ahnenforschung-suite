# Ahnenforschung Suite zu GitHub pushen

Ziel: **privates** `Florian1404/ahnenforschung-suite`, einschließlich Commit-Historie und Tags.

Falls noch nicht vorhanden, Git und GitHub CLI installieren:

```powershell
winget install --id Git.Git --exact
winget install --id GitHub.cli --exact
```

Git-Repository-ZIP komplett entpacken (auch den versteckten Ordner `.git`), PowerShell im Ordner öffnen und starten:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\push-to-github.ps1
```

Bei der ersten Ausführung GitHub im Browser anmelden. Das Skript legt das Repo bei Bedarf privat an und pusht `main` und Versionstags ohne Force Push. Es überträgt **keine** Live-Datenbank und verändert **keinen** netcup-Server. 
