# Matricula Bestandsbrowser – aktuell 5.2

**Start unter Windows:**

```powershell
py -3.12 -m pip install requests beautifulsoup4 customtkinter matricula-online-scraper
py -3.12 matricula-bestand5_2.py
```

Optional für PDF-Erstellung: `py -3.12 -m pip install img2pdf`.

Die Anwendung kann große Metadatenbestände katalogisieren und **gezielt ein Buch** herunterladen. Laufzeitdateien (SQLite-Katalog, lokaler Config-Pfad, Buchbilder) sind git-ignoriert. Bei HTTP 403/429 respektiert die aktuelle Version die Sperre. Siehe `README-v5.2-original.txt`.

**Git-Historie:** Ältere Stände 2, 3, 4, 5, 5.1 und 5.2 sind **Tags**, keine Kopien `tool-final2.py`. `git show matricula-v5.1:tools/matricula/bestandsbrowser/matricula-bestand5_2.py` zeigt das vorherige Skript (ursprünglich als `matricula-bestand5_1.py` überliefert).

**Hinweis:** Dateiname ist für alle Git-Stände als `matricula-bestand5_2.py` normalisiert; der Inhalt des jeweiligen Tags entspricht der historischen Quelldatei, einschließlich deren ursprünglicher Kopfzeile. Es wurden noch keine ausführlichen Live-Regressionstests ausgeführt.
