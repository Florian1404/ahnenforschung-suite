# Sicherheit, Datenschutz und Rechte

- Repo **privat** halten. Keine lebenden Personen, Familienforschungsexporte, Scan-ZIPs, Adressen, Personenbilder oder Standesamtsurkunden committen.
- Zugangsdaten nur in `apps/ahnenarchiv-web/config.php` auf dem Server (ignoriert); nicht in `config.example.php` eintragen.
- Datenbank-Dumps separat verschlüsselt sichern; niemals in Git oder dem Repository-ZIP versenden.
- Matricula-Scans gehören in lokalen Speicher außerhalb des Repositories. Lizenz-/Nutzungsbedingungen und robots.txt beachten, 403/429 respektieren und keinen Massendownload automatisch starten.
- Vor einem Remote-Push `git status`, `git diff --cached`, `git ls-files` prüfen.
- Nicht nur aktuelle Arbeitskopie, auch **Git-Historie** auf Secrets prüfen! Historie ohne Geheimnisse neu aufbauen, falls zuvor etwas eingecheckt wurde.
- Externe genealogische JSON-/GEDCOM-Imports unter `research/private/` oder außerhalb des Repos ablegen.
