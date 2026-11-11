# Ahnenarchiv Web — netcup/Plesk Deployment (sicherer Weg)

## Vor dem ersten Mal: Echten Serverstand abgleichen

1. **Dateien und Datenbank des produktiven Servers vollständig sichern**, inkl. `config.php`, geschütztem `private/media/`, Uploads, Logs und Datenbank (getrennt, verschlüsselt, NICHT in Git).
2. Quellcode vom Server herunterladen **ohne** `config.php`, Medien, personenbezogene Daten und Datenbankexporte ins Git-Repo aufzunehmen.
3. Mit `apps/ahnenarchiv-web` diffen. Die Versionsfolge im Repo stammt aus Patch-ZIPs, **nicht** aus einem aktuellen Live-Snapshot.
4. Unterschiede einzeln prüfen: Server-Hotfixes übernehmen oder Repo-Stand anpassen; danach neue Git-Commits.
5. In einer **Staging-Kopie** mit eigener Test-DB prüfen: Login, Rollen, Imports, Dubletten-Zusammenführung, Löschen/Undo, Ereigniskorrekturen, Medienlinks, Genealogieansicht.
6. Erst nach erfolgreichem Backup und Staging-Test selektiv `apps/ahnenarchiv-web` hochladen. **Keinen Git-Ordner, keine Testdaten, keine `config.example.php` als Ersatz der bestehenden `config.php`** hochladen.
7. Webroot der Domain muss auf das `public/`-Verzeichnis zeigen. `private/` bleibt außerhalb des Webroots.

## PHP-Checks

```powershell
# Mit installiertem PHP bzw. in deiner Testumgebung:
php -l apps/ahnenarchiv-web/private/api.php
php -l apps/ahnenarchiv-web/private/import.php
```

## Wichtige Grenzen

- Das Tag `ahnenarchiv-web-v2.1.5` markiert den **letzten hier vorhandenen Patchstand**, nicht automatisch die aktuelle Produktivversion.
- Datenbankschema und bestehende Altbeziehungen auf dem Live-Server müssen vor mutierenden Importen geprüft werden.
- Ein Quell-Commit ist **kein** Datenbank-Backup.
- Nicht alle Bestandteile der historischen v2.1.0-ZIP sind notwendigerweise im Live-Code gleich.
