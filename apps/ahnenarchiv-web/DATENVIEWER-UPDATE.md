# Ahnenarchiv 1.7.0 – Datenviewer

Update in stammbaum-huschka.de/httpdocs entpacken, Dateien überschreiben und Ordner zusammenführen. Strg+F5. Keine Neueinrichtung. config.php, Datenbank und hochgeladene Bilder bleiben erhalten.

Menü Datenviewer oder Forschungsmodule → Datenviewer. Auch Linie importieren bietet einen Einstieg zum vorherigen Lesen einer Datei.

Unterstützt JSON (eingerückt, Zahlenzeichenfolgen unverändert), JSONL/NDJSON, GEDCOM (beschriftete Angaben mit Personenreferenzen), CSV/TSV (Tabellenansicht, Trennzeichenwahl) und reine Textansichten für TXT, XML, YAML sowie andere Textdateien. YAML/XML werden nicht semantisch ausgewertet. GEDCOM-Datumsangaben und unbekannte Tags bleiben unverändert; der Viewer ist kein genealogischer Validierer.

Datei wählen oder Text einfügen; lesbare Ansicht und Originaltext umschalten, suchen, lesbaren Text herunterladen. Verarbeitung ausschließlich im Browser, ohne API-Upload oder Datenbankänderung. Dateiinhalte werden beim Verlassen des Viewers nicht gespeichert.

Bis 5 MB; Vorschau maximal 2000 Textzeilen / 200.000 Zeichen. Tabellen zeigen 100 Zeilen pro Seite, bis 100 Spalten und 3000 Zeichen je Zelle. Textdownload enthält den vollständigen lesbaren Inhalt. CSV bis 50.000 Zeilen. UTF-8/UTF-16 und Windows-1252 auswählbar. ANSEL benötigt vorherigen UTF-8-Export; Warnung wird angezeigt. Verschachteltes JSON bis 100 Ebenen. Fehlerhafte Dateien bleiben als Originaltext sichtbar.

Kein PDF-, Bild- oder Excel-Binärviewer. CSV kann unabhängig von der Importfunktion gelesen werden; der Viewer erweitert die DB-Importformate nicht. Bestehende Import- und Freigabeabläufe bleiben bestehen.

Validierung: 10 Parser-/DOM-Tests und direkte Menü-/Importmodul-Integration bestanden. Kein Test im produktiven Hosting und kein vollständiger Browser-/Mobiltest. Tests: im Ordner module-checks npm install, dann npm run test:viewer.
