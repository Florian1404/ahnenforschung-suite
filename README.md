# Ahnenforschung Suite — eigenes Git-Repository

**Privates Monorepo nur für die Ahnenforschung.** Hier liegen Quellcode, Dokumentation und Git-Versionshistorie, **nicht** die Familienregister, lebende Personen, Urkundenscans oder Datenbank-Dumps.

## Welches Werkzeug ist wofür?

| Bereich | Ordner | Stand im Repo | Verwendungszweck | Status |
| --- | --- | --- | --- | --- |
| Matricula Bestandsbrowser | `tools/matricula/bestandsbrowser/` | **5.2** | Länder/Archive/Orte/Bücher erfassen; SQLite-Katalog; einzelnes Buch gezielt herunterladen | **aktuelle Arbeitsversion** |
| Matricula Downloader alt | `tools/matricula/legacy-downloader/` | historisch, ohne gesicherte Versionsnummer | Älterer GUI-Downloader für Bücher/PDF | Legacy, nur zum Vergleich |
| Matricula Bildschirmfotos | `tools/matricula/screenshot-helper/` | bisheriger AHK-Skriptstand | Manuelle Screenshots aus Matricula-Viewer | Hilfswerkzeug |
| Stammbaum-PDF-Bilder | `tools/pdf-bilder/` | `NEU` (keine SemVer angegeben) | Bilder aus Stammbaum-PDFs in Unterordner exportieren | Hilfswerkzeug |
| Ahnenarchiv auf netcup | `apps/ahnenarchiv-web/` | **2.1.5** | PHP/MySQL-Websoftware, Personen, Beziehungen, Medien, Import | **rekonstruierter Quellstand** |
| Frühere Desktop-App | `legacy/ahnenarchiv-desktop/` | älterer Projektstand | Python-Desktop-Prototyp | Archiv, keine Server-Software |

### Welche Datei starte ich?

- **Matricula auf Windows:** `tools/matricula/bestandsbrowser/matricula-bestand5_2.py` (Python **3.12+**). Details in [README Matricula](tools/matricula/bestandsbrowser/README.md).
- **Bilder aus Stammbaum-PDFs:** `tools/pdf-bilder/stammbaum_bilder.py`.
- **Screenshot-Helfer:** `tools/matricula/screenshot-helper/Issing_Screenshot_Tool.ahk` (AutoHotkey **v2**).
- **Ahnenarchiv Web:** PHP-Dateien aus `apps/ahnenarchiv-web/`, **nicht** das alte Python-Desktop-Projekt. Siehe [Deployment](docs/DEPLOYMENT.md).

## Versionen

Siehe [VERSIONEN.md](VERSIONEN.md) und `git tag -l`.

- Matricula Bestandsbrowser: `matricula-v2`, `matricula-v3`, `matricula-v4`, `matricula-v5`, `matricula-v5.1`, `matricula-v5.2`.
- Web-App: `ahnenarchiv-web-v2.1.0`, `ahnenarchiv-web-v2.1.3`, `ahnenarchiv-web-v2.1.4`, `ahnenarchiv-web-v2.1.5`.

Die Versionsnummern beziehen sich **auf jeweils eine Komponente**, nicht auf das ganze Repo. Nicht vorhandene Zwischenstände (z.B. Ahnenarchiv 2.1.1/2.1.2) wurden **nicht erfunden**. Die Tags markieren aus vorhandenen ZIP-Quellen rekonstruierte Quellstände, keine serverseitig getesteten Releases.

## Lokal arbeiten

```powershell
# Im ausgepackten Repository:
git log --oneline --decorate --all -20
git tag -l
git status

# Matricula GUI starten:
py -3.12 -m pip install requests beautifulsoup4 customtkinter matricula-online-scraper
py -3.12 tools/matricula/bestandsbrowser/matricula-bestand5_2.py
```

`matricula-bestand5_2.py` verwaltet eigene SQLite-/JSON-Dateien im Arbeitsverzeichnis. Sie gehören **nicht ins Git**. Längerfristig können wir Laufzeitdaten unter einem einheitlichen externen `data/`-Verzeichnis bündeln.

## WICHTIG: Abgleich mit dem Server

Der PHP-Code wurde aus den verfügbaren Paketen **2.1.0 → 2.1.3 → 2.1.4 → 2.1.5** zusammengesetzt. Wir haben **keinen Live-Abzug deiner aktuellen netcup-Installation** gemacht. Individuelle Hotfixes direkt auf dem Server können fehlen. **Vor dem ersten Deployment zuerst Live-Code sichern und mit diesem Repo vergleichen.** [Konkrete Schritte](docs/DEPLOYMENT.md).

## Git-Remote

Dieses ZIP enthält ein **lokal initialisiertes Git-Repository mit Commits und Tags**. Es ist noch **kein GitHub-/GitLab-Remote** angelegt. Repository bitte als **PRIVATE** erstellen, danach:

```powershell
git remote add origin git@github.com:DEIN-BENUTZER/ahnenforschung-suite.git
git push -u origin main
git push origin --tags
```

Dazu auf GitHub/GitLab ein **leeres privates Repository ohne automatisch erstellte README** anlegen. Entsprechende GitLab- oder eigene SSH-URL kann statt GitHub verwendet werden. [Sicherheitsregeln](docs/DATENSCHUTZ.md).
