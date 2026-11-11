> Onlineversion: **1.6.2 vom 15.10.2026**, inklusive drei Forschungsmodulen. Details: `online/MODUL-UPDATE.md`. Die lokale Windows-Oberfläche bleibt auf ihrem bisherigen Stand.

# Ahnenarchiv · Familie Huschka

Stand 09.10.2026: Die Online-Version verwendet **PHP 8.3+ und MySQL/MariaDB**, passend zum netcup-Webhosting 2000 und `stammbaum-huschka.de`. Docker, Caddy und PostgreSQL sind aus dem Projekt entfernt. Der Windows-Client nutzt weiterhin seinen lokalen Python-Dienst und SQLite.

## Jetzt installieren

1. ZIP entpacken. **Nur den Inhalt von `online`** in ein eigenes Archiv-Verzeichnis im Webhosting hochladen.
2. Dokumentenstamm der Archiv-Domain auf dessen Unterverzeichnis **`public`** setzen.
3. Eigene Datenbank und SSL einrichten; `online/config.example.php` nach `config.php` kopieren und Zugangsdaten sowie zufälligen Einrichtungsschlüssel eintragen.
4. `https://stammbaum-huschka.de/setup` öffnen, Schlüssel eingeben und deinen Admin anlegen.
5. Otto registriert sich; du aktivierst sein Konto unter Benutzer und gibst ihm die Admin-Rolle.

Die vollständige Schrittfolge steht in **`online/NETCUP-START.md`**. Die Konfiguration, privaten Bilder und Originaldaten gehören außerhalb des öffentlichen Dokumentenstamms. Keine Datenbankpasswörter mitgeliefert.

## Funktionen

Personensuche, schematischer Stammbaum mit Eltern-/Partnerlinien, Registrierung/Login, Admin-Freigabe neuer Konten, Prüfliste für Lebensdaten, neue Personen, Bilder und Beziehungen. Änderungen werden erst nach bewusster Adminfreigabe bestätigt. Quellen, alte Datenstände, Historie und Konfliktprüfung bleiben erhalten. Flo und Otto können beide Admin sein; auch eigene Vorschläge durchlaufen die Prüfliste.

Benannte unbekannte Personen können als vorläufiger Personenvorschlag Bilder erhalten. Die Bildfreigabe wartet auf die Personenfreigabe. Dateien benötigen Titel und Personenzuordnung. Maximal 8 MB pro Datei; größere JPG/PNG/WebP-Fotos werden im Browser auf JPEG verkleinert. PDF-Dateien vorher passend aufteilen. Große Bilddateien werden nicht auf dem Webserver neu kodiert; für deren Prüfung wird kein GD benötigt.

Leselinks sind widerrufbar und ausschließlich lesend. Lebende/unklare Personen und Medien bleiben standardmäßig verborgen. Gruppenbilder brauchen ausschließlich Personen innerhalb des Freigabebereichs. Private Forschungsnotizen werden nicht öffentlich ausgegeben.

Die mitgelieferte Forschung umfasst unverändert 230 Personen/Platzhalter, 87 Familienverbindungen, 212 Bilder, Original-PDF, weitere Quellen und Prüfhinweise. Das Setup importiert den vollständigen Bestand ohne Überschreiben. Originaldaten liegen sowohl beim Desktop-Erstbestand als auch im Online-Installationsordner bei.

## Papas Windows-App bauen

Auf Windows mit Python 3.12 (64 Bit), aus dem Projektordner:

```powershell
powershell -ExecutionPolicy Bypass -File .\desktop\build.ps1
```

Ergebnis: `dist\Ahnenarchiv\Ahnenarchiv.exe` mit Begleitdateien. Den **gesamten Ordner** auf Papas Windows-Rechner kopieren. Microsoft Edge WebView2 Runtime muss vorhanden sein. Papa braucht danach kein installiertes Python.

Ein privater GitHub-Actions-Build ist über `.github/workflows/windows-build.yml` vorbereitet; kein Repository wurde angelegt oder hochgeladen. Der Bestand enthält private Familieninformationen.

Beim ersten Start ist der mitgelieferte Stammbaum offline verfügbar. Unter **Synchronisierung** `https://stammbaum-huschka.de` und Ottos Admin-Konto eintragen. Dauerhafte SQLite-Warteschlange, automatische Wiederholung alle 45 Sekunden, stabile Vorschlags-/Upload-IDs verhindern doppelte Einträge. Freigaben brauchen Internet und laufen am PHP-Server. Token liegen im Windows-Anmeldeinformationsspeicher.

Lokale Daten: `%LOCALAPPDATA%\Ahnenarchiv`. Diesen Ordner beim Programmupdate behalten. Installation ist an Konto und Server gebunden. Ein abgelaufener Token kann durch erneute Anmeldung ersetzt werden. Aktualisierten Windows-Client neu bauen, damit die 8-MB-Grenze und Fotoverkleinerung übereinstimmen.

## Validierung und verbleibende Arbeit

PHP-Syntax geprüft. Integration gegen **PHP 8.3.6 und MariaDB 10.11.14**, mit 128 MB PHP-Speicherlimit und mehreren PHP-Workern: fünf umfangreiche Integrationstests bestanden. Sie prüfen vollständigen verlustfreien Import inklusive Dateiinhalt, Rollen, Freigaben, Wiederherstellung, parallele Konflikte, private Uploads, öffentliche Freigaben, Abstammungszyklen und den realen Desktop-Abgleich mit PHP.

Die vorhandenen 16 Tests der lokalen Python-Anwendung sowie der Stammbaum-Test mit 230 Knoten bestanden ebenfalls. Details: `VALIDIERUNG.md`.

**Nicht durchgeführt:** Installation auf deinem netcup-Konto, visueller Browser-/Windows-WebView-Test und Windows-EXE-Build. Dieses Paket enthält den Quellcode und die Webhosting-Dateien, keine fertige EXE. Vor öffentlichem Teilen die Funktionskontrolle aus der Hosting-Anleitung durchführen.

Passwort-zurücksetzen, E-Mail-Verifikation und Zwei-Faktor-Anmeldung sind noch nicht umgesetzt. Hochzeiten bleiben aus dem Import erhalten; ein vollständiger Editor für mehrere Ehen fehlt noch. Datenbank und privaten Medienordner gemeinsam sichern und eine Wiederherstellung prüfen.

## Entwicklertests

```bash
python -m pytest -q tests/test_app.py
node tests/test_tree.cjs
python -m pytest -q tests/test_php.py
```

PHP muss für den letzten Befehl lokal vorhanden sein. Ohne MariaDB-Variablen testet dieser mit SQLite als Testadapter. Für eine **leere, ausschließlich für Tests bestimmte** MySQL/MariaDB-Datenbank `AHNEN_MYSQL_DSN`, `AHNEN_MYSQL_USER`, `AHNEN_MYSQL_PASSWORD` setzen; keine produktive Datenbank verwenden. PHP-Server werden nur für die Testlaufzeit auf localhost gestartet. Online-Produktivbetrieb erfordert MySQL/MariaDB; SQLite ist lediglich Testadapter bzw. Desktop-Speicher.
