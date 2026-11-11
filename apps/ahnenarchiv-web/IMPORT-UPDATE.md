# Familienlinien importieren

## Update auf dem vorhandenen netcup-Hosting

1. `ahnenarchiv-importer-update.zip` im Plesk-Dateimanager in `stammbaum-huschka.de/httpdocs` hochladen.
2. Genau dort entpacken. Vorhandene Dateien überschreiben.
3. Webseite mit Strg+F5 neu laden. Im Menü erscheint **Linie importieren**.

Kein erneutes Setup und keine neue Datenbank nötig. Das Update verwendet die vorhandenen Tabellen. `config.php`, Mediendateien und freigegebene Stammdaten sind nicht im Update enthalten. Das Bild-Popup ist weiterhin enthalten. Den Dokumentenstamm bei `httpdocs/public` belassen.

## Ablauf

Bezeichnung und Datei auswählen → einlesen → JSON und Personenzuordnung prüfen → zur Freigabe einreichen → Admin prüft vollständige Angaben und übernimmt oder lehnt ab.

Importentwürfe und Originalquellen sind nur für den Einreicher und Admins sichtbar. Eine vorgeschlagene Linie erscheint erst nach Admin-Freigabe im Stammbaum. Alle Änderungen eines Imports laufen in einer Transaktion. Ein Konflikt oder Abstammungskreis verhindert die gesamte Übernahme. Auch ein Admin muss einen eigenen Import ausdrücklich freigeben.

Bestehende Personen ausdrücklich zuordnen, um eine neue Linie anzuschließen. Gleiche Namen sind nur Dublettenhinweise. Bei Zuordnung werden leere/unbekannte Felder ergänzt. Abweichende vorhandene Werte bleiben erhalten; Konflikte werden angezeigt. Gewünschte Änderungen an bereits bekannten Werten separat als Ergänzung einreichen. Mehrere Quellpersonen auf denselben vorhandenen Datensatz sind nicht erlaubt.

Korrekturen im JSON werden mit der Einreichung gespeichert. Wenn nach Einreichung ein Fehler auffällt: Import in der Prüfliste ablehnen, Entwurf erneut öffnen, korrigieren und erneut einreichen. Admins können fremde Entwürfe prüfen; Änderungen und erneute Einreichung macht der ursprüngliche Einreicher. Eine bereits freigegebene Linie kann nicht erneut über denselben Entwurf eingereicht werden.

## Formate und Grenzen

- JSON: unser Archivformat mit `personen`, optional `familien`, `beziehungen`, `hinweise`; alternativ eine Personenliste. Quellen-IDs sind eindeutig. Verbindungen müssen auf Personen in derselben Datei verweisen. Lebensereignisse enthalten `datum.iso` und `ort_original`. Geburts-, Hochzeits-, Sterbe-, Tauf- und Bestattungsdaten bleiben auch bei unbekannten Werten vorhanden. Die Originaldatei bewahrt Zusatzfelder, die nicht in die bearbeitbaren Personenfelder übernommen werden.
- GEDCOM `.ged` / `.gedcom`: UTF-8 und deklarierte ANSI-Dateien; `INDI`, `FAM`, Namen, Geschlecht, Geburt, Tod, Taufe, Bestattung, Familienheirat, Partner, Kinder und einfache Notizen. Genau bekannte Daten werden normalisiert. Ungefähre Daten/Datumsbereiche behalten ihren Originaltext ohne erfundenes exaktes Datum. Elternschaft ist zunächst ungeklärt. Sondertags, weitere Namensvarianten, externe/verlinkte Medien, erweiterte Quellenstrukturen und Kalender werden nicht vollständig konvertiert; die Originaldatei bleibt als Beleg erhalten. ANSEL bitte im Ausgangsprogramm nach UTF-8 exportieren.
- PDF, PNG, JPG: optionale automatische Erkennung mit OpenAI. Nur Admins können kostenpflichtige Erkennung starten. Pro Datei muss die Übertragung ausdrücklich bestätigt werden. Schrift und Linien können falsch gelesen werden: alle Ergebnisse am Original prüfen. Reine Porträtfotos liefern keine verlässlichen Namen oder Verwandtschaften; diese normal als Bild einer benannten Person hochladen.
- Aktuelles Uploadlimit aus `config.php`, standardmäßig 8 MB; höchstens 500 Personen und 3.000 Verbindungen pro Import. Große PDFs in kleinere Teile aufteilen. Namen oder vorläufige Bezeichnungen sind Pflicht. Namenslose GEDCOM-Personen bitte vor dem Import benennen.
- JSON/GEDCOM bleiben auf dem eigenen Hosting. Verlinkte Medien werden nicht automatisch von fremden URLs geladen. Die hochgeladene Originalquelle wird erst nach Freigabe den übernommenen Personen zugeordnet. Für öffentliche Freigabelinks gilt weiterhin deren Medien- und Personensichtbarkeit.

## PDF-/Bilderkennung aktivieren

In der bestehenden `httpdocs/config.php` vor dem abschließenden `];` ergänzen:

```php
    'import_ocr_api_key' => 'HIER-DEIN-OPENAI-API-SCHLUESSEL',
    'import_ocr_model' => 'gpt-4.1',
```

Andere Einträge unverändert lassen. Das Konto benötigt API-Guthaben bzw. aktivierte API-Abrechnung; das ChatGPT-Abonnement stellt dem PHP-Server keinen API-Schlüssel bereit. Der Schlüssel gehört ausschließlich in `config.php`, nie in JavaScript oder einen öffentlich geteilten Screenshot. PHP benötigt cURL und ausgehendes HTTPS zu `api.openai.com`. Der Server sendet nur die ausdrücklich ausgewählte PDF/Bilddatei und den Extraktionsauftrag; keine vorhandene Archivdatenbank. `store=false` wird mitgesendet; die übrigen Aufbewahrungsbedingungen des API-Anbieters gelten trotzdem. Erkennung läuft höchstens 120 Sekunden; bei Abbruch Datei verkleinern und erneut versuchen.

Ohne Schlüssel funktionieren JSON und GEDCOM sofort. PDF-/Bilderkennung meldet dann klar, dass sie noch nicht eingerichtet ist.

## Geprüft

Acht PHP/MySQL-Integrationstests gegen eine isolierte MariaDB: unveränderter Originalimport, bestehende Rechte/Freigaben, Offline-Synchronisierung sowie neue Linienentwürfe, Personenzuordnung, Konflikterhalt, Quellen, Freigabe/Ablehnung, Versionskonflikte und Abstammungskreise mit vollständigem Rollback. Parser- und OCR-Transporttests verwenden einen simulierten Dienst und keinen realen API-Schlüssel. Frontend-Renderprüfungen decken Dublettenhinweise, Zuordnungsoberfläche, Prüfdetails und HTML-Escaping ab. PHP-/JavaScript-Syntax geprüft. Keine visuelle Browserprüfung und keine echte KI-Erkennung auf deinem Hosting durchgeführt.

Referenzen: https://developers.openai.com/api/docs/guides/file-inputs und https://gedcom.io/specifications/FamilySearchGEDCOMv7.html
