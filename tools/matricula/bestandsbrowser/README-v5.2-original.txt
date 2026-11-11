MATRICULA BESTANDSBROWSER 5.2
============================

WICHTIG VOR DEM TEST
-------------------
1. Die bestehende Datei matricula-bestand-oesterreich-v4.json sowie die
   zugehörigen Status-/Journaldateien sicherheitshalber kopieren.
2. matricula-bestand5_2.py in denselben Ordner wie die bestehenden
   Bestandsdateien der Version 5.1 kopieren.
3. Der Downloader benötigt Python 3.12 oder neuer.

INSTALLATION (Windows PowerShell, Beispiel mit Python 3.12)
---------------------------------------------------------
py -3.12 -m pip install -U requests beautifulsoup4 customtkinter matricula-online-scraper

Optional für die PDF-Erstellung:
py -3.12 -m pip install -U img2pdf

START
-----
py -3.12 matricula-bestand5_2.py

BEDIENUNG
---------
- Die vorhandene Österreich-JSON wird beim Start geladen.
- Eine lokale SQLite-Datenbank matricula-katalog.sqlite3 wird erstellt.
  Sie enthält Metadaten/Downloadstatus, NICHT die Buchseiten.
- Beim ersten Start gleicht die Anwendung vorhandene Buch-Metadaten
  mit SQLite ab; spätere Starts nutzen einen Änderungs-Fingerabdruck.
- In der Baumliste Land > Bundesland > Archiv > Ort > Buch aufklappen.
- Alternativ Ort, Signatur oder Titel in das Buchsuchfeld eingeben,
  „Bücher suchen“ klicken und einen Treffer auswählen.
- Download-Zielordner wählen, „Ausgewähltes Buch herunterladen“ klicken.
- Ein automatischer Massendownload wird NICHT gestartet.
- Download-Status wird in SQLite gespeichert und im Baum angezeigt.
- „Dateien prüfen“ kontrolliert, ob registrierte Bilddateien noch da sind.
- „Ordner öffnen“ öffnet den lokalen Speicherort.
- „Buch als PDF“ verwendet die lokal heruntergeladenen Bilder.
- „Downloadstatus exportieren“ erzeugt eine TSV-Übersicht.

DATEIEN
-------
matricula-katalog.sqlite3                SQLite-Datenbank (SQLite-WAL Dateien können hinzukommen)
matricula-local-config.json              lokale Konfiguration für Zielpfad
Matricula_Buecher/                       Standard-Ablage für Bilddateien
  Land/Archiv/Ort/Signatur_Buch-ID/
    bilder/                              Buchseiten als Dateien
    manifest.json                        Herkunft, Signatur, Seitenanzahl, Status

DATENSCHUTZ / ZUGRIFF
--------------------
Bitte aktuelle Nutzungsbedingungen von Matricula beachten.
Bei HTTP 403/429 wird abgebrochen; es gibt keine Umgehung von Sperren.
Es werden nur bewusst ausgewählte Einzelbücher heruntergeladen.

QUALITÄT
--------
Die Datei wurde mit Python-Syntaxprüfung und lokalen Tests einschließlich
simuliertem Download sowie SQLite-Statuswechsel geprüft.
Ein realer Matricula-Download wurde hier nicht ausgeführt.
Die bloße Existenz einiger Bilder garantiert nicht, dass keine einzelne
Buchseite fehlt. Im Zweifel Seitenzahl/Seitensequenz mit dem Viewer vergleichen.
