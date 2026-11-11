# Komponenten- und Versionsübersicht

## Aktuelle Stände im übergebenen Repository

| Komponente | Aktueller Stand | Ausgangsdatei | Bemerkung |
| --- | --- | --- | --- |
| Matricula-Bestandsbrowser | **5.2** | `matricula-bestand5_2.py` + `README-Matricula-5_2.txt` | SQLite, Download ausgewählter Einzelbücher, PDF optional |
| Separater Matricula-Downloader | **Legacy, nicht nummeriert** | `matricula-multi-scrapper (1).py` | Älterer experimenteller Stand; 5.2 für Bestandsverwaltung bevorzugt |
| Screenshot-Tool | **Stand des AHK-Skripts** | `Issing_Screenshot_Tool.ahk` | Keine dokumentierte SemVer |
| PDF-Bilder-Extraktor | **Stand NEU** | `stammbaum_bilder_NEU.py` | Keine dokumentierte SemVer |
| Web-Ahnenarchiv | **2.1.5 (Patchstand)** | v2.1.0 Basis + Patch v2.1.3 + v2.1.4 + v2.1.5 | **Nicht** mit Live-Server abgeglichen |
| Python-Desktop-Prototyp | **historisch** | `ahnenarchiv-projekt.zip` | Nicht die PHP-Server-Software |

## Historische Stände in der Git-Historie

- Matricula: 2, 3, 4, 5, 5.1, 5.2 — jeweils aus namentlich entsprechender Python-Datei. Tags: `matricula-v2`, `matricula-v3`, `matricula-v4`, `matricula-v5`, `matricula-v5.1`, `matricula-v5.2`.
- Ahnenarchiv Web: `ahnenarchiv-web-v2.1.0`, `ahnenarchiv-web-v2.1.3`, `ahnenarchiv-web-v2.1.4`, `ahnenarchiv-web-v2.1.5`.
- 2.1.1 und 2.1.2 sind **nicht** als rekonstruierte Version markiert, da keine vollständigen Paketstände vorliegen.

`git log --oneline --decorate --all` zeigt wann welche Komponente aktualisiert wurde. Um ältere **einzelne** Dateien zu vergleichen:

```bash
git diff matricula-v5.1 matricula-v5.2 -- tools/matricula/bestandsbrowser/matricula-bestand5_2.py
git diff ahnenarchiv-web-v2.1.3 ahnenarchiv-web-v2.1.5 -- apps/ahnenarchiv-web
```

Die Git-Commitdaten sind das Erstellungsdatum dieser **rekonstruierten Historie**; sie sind **keine** echten historischen Release-Zeitpunkte.
