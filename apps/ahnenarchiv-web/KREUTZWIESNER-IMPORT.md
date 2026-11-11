# Kreutzwiesner-Import · 1.6.1

1. Das komplette ZIP in den bestehenden Ahnenarchiv-Projektordner entpacken, in dem `private`, `public` und deine `config.php` liegen. Ordner zusammenführen, enthaltene Dateien überschreiben.
2. Webseite mit Strg+F5 neu laden und als Admin **Forschungsmodule → Kreutzwiesner importieren** öffnen.
3. Den Abgleich ansehen und **Kreutzwiesner jetzt importieren** anklicken. Danach **Archiv öffnen** wählen.

Das Paket enthält alle bisherigen Onlinefunktionen einschließlich der Diagramme. Die Konfiguration, die Datenbank und bestehende Medien werden beim Entpacken nicht ersetzt. Neue Dateien liegen im eigenen Unterordner `private/media/kreutzwiesner`. Der Datenbankimport startet erst mit dem Importbutton. Keine SQL-Datei, kein manuelles Hochladen eines JSON-Exports und keine neue Einrichtung nötig.

## Inhalt und Abgleich

- 176 Quellenseiten mit vollständigem PDF-Text, Seitenlinks und Bildpositionen.
- 521 Personenkarten und 22 zusätzliche Listeneinträge, zu 402 Personendatensätzen zusammengeführt. Unbekannte Personen bleiben getrennte Platzhalter.
- 147 Familien, 480 Verbindungsdatensätze, 52 Forschungsfragen.
- Original-PDF und 363 unterschiedliche eingebettete Abbildungen. Abbildungen haben Seitenbezug; daraus wird keine ungeprüfte Porträtzuordnung erzeugt. Das Original erhält Beschnitt und Bildmasken.
- 11 Personen tragen die ursprünglichen Huschka-IDs, darunter Irma, Anton, Otto und Florians Familie. Auf der gespeicherten Basis kommen 391 Personen hinzu; danach sind 621 Personen vorhanden. Die tatsächliche Vorschau verwendet den aktuellen Serverbestand.

Der JSON-Export liegt unter `private/imports/kreutzwiesner/stammbaum-kreutzwiesner.json` und kann im Modul heruntergeladen werden. Die ursprüngliche Huschka-Datei bleibt eigenständig erhalten. In Personendetails führt **Kreutzwiesner-Quelle öffnen** auf die betreffende PDF-Seite.

## Umgang mit Widersprüchen

Bestehende Vorzugswerte und bestätigte Verbindungen bleiben erhalten. Ergänzungen führen Quellenverweise, Alternativen und den Originaltext mit. Unterschiedliche Geburtstage, wiederverwendete Quellennummern und zweifelhafte Elternzuordnungen werden ausdrücklich dokumentiert. Die Quellennummer allein gilt nicht als Personenidentität. Adoptionen werden getrennt geführt; der widersprüchliche Adoptiv-/Pflegeelternstatus bei Leopoldine bleibt ungeklärt.

Die Geschwisterlisten sind als Personen erfasst. Nicht eindeutig zuordenbare Eltern aus den Keller-/Muszits-Listen bleiben Forschungsfragen. Die Darstellung Nicola/Stephen mit gleichem Geburtstag und Geburtsjahr wird als ungeklärte Verbindung gespeichert und erscheint nicht als bestätigte Elternschaft. Original und Übersicht bleiben zum Nachprüfen erhalten. Bilder mit Text wurden nicht vollständig separat OCR-transkribiert; sie stehen im Original-PDF und als Bilddateien zur Verfügung.

## Technische Prüfung

Der Import ist nur für angemeldete Admins ausführbar. Vorschau und Import prüfen den aktuellen Datenbestand. Änderungen nach einer Vorschau erfordern einen neuen Abgleich. Dateien werden auf ihre SHA-256-Prüfsummen geprüft. Alle Datensätze werden in einer Datenbanktransaktion mit Änderungsverlauf geschrieben. Ein abgeschlossener Import derselben PDF wird nicht erneut ausgeführt.

39 automatisierte Tests bestanden, außerdem bestehende Stammbaumprüfung und Prüfung der Diagramme nach dem Testimport. Getestet mit PHP 8.3 und einer isolierten SQLite-Testdatenbank; die produktive Anwendung verwendet weiterhin MySQL/MariaDB. Kein Import in die Live-Datenbank und kein Live-Test auf netcup erfolgt. Das aktuelle Datenbankbackup kann bei Bedarf über die üblichen Hostingwerkzeuge wiederhergestellt werden.
