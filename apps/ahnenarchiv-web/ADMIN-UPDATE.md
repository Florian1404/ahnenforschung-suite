# Version 2.0.1 – Gemeinsame Adminansicht

## Installation

Das Update in `stammbaum-huschka.de/httpdocs` entpacken und die Programmdateien überschreiben. Dokumentenstamm bleibt `httpdocs/public`. Danach Strg+F5. Datenbank, Konten, Konfiguration und Bilder bleiben erhalten. Das Paket enthält auch die Programmänderungen aus 2.0.0.

## Papas Zugang prüfen

1. Das Archiv über die normale Domain `https://stammbaum-huschka.de/` öffnen und mit dem eigenen Konto anmelden. Ein Link mit `#share=...` öffnet bewusst ausschließlich die Leseansicht; dort führt „Mit eigenem Konto öffnen“ zur normalen Anmeldung beziehungsweise zur bereits vorhandenen Sitzung.
2. Unter „Mein Konto“ stehen Name, E-Mail-Adresse und aktuelle Rolle. Für beide Admins muss dort „Administrator“ stehen.
3. Steht dort „Mitforschender“, kann ein bestehender Admin das richtige Konto unter „Benutzer“ anhand der E-Mail identifizieren und mit „Zu Admin“ hochstufen. Es gibt keine automatische Hochstufung nach Namen oder Familienbeziehung.
4. Die geöffnete Sitzung übernimmt eine geänderte Rolle spätestens bei der nächsten regulären Prüfung nach etwa 15 Sekunden, bei Rückkehr zum Fenster oder beim Navigieren. „Zugriffsrechte aktualisieren“ lädt den aktuellen Stand sofort.

## Gleiche Rechte

Alle aktiven Konten mit Rolle `admin` erhalten dieselbe Navigation und Verwaltungsrechte: gesamte Prüfliste und Freigaben, Benutzer anlegen und Rollen ändern, Einladungen verwalten, Freigabelinks und Forschungsmodule verwalten. Es gibt kein privilegiertes Erstkonto. Die vorhandene Sperre gegen das Deaktivieren oder Herabstufen des eigenen Adminaccounts bleibt bestehen.

Rollen werden bei jeder Serveranfrage aus der Benutzerverwaltung geprüft. Der Browser übernimmt aktuelle Rollen jetzt zusätzlich für seine Darstellung. Normale Mitglieder erhalten dadurch keine Adminrechte. Leselinks bleiben schreibgeschützt.

## Prüfung

Sechs UI-Tests prüfen zwei unterschiedliche Adminidentitäten, Hochstufung während einer Sitzung ohne Verlust offener Formulare, Herabstufung, Leselinks, die Kontoanzeige und eine verspätete Antwort nach Abmeldung. Ein HTTP-Test gegen isoliertes PHP/SQLite prüft die gleichen Verwaltungsendpunkte, Freigabe fremder Vorschläge und Benutzeranlage durch den zweiten Admin, Hoch- und Herabstufung mit unverändertem Sitzungstoken sowie die Zugriffssperre für Mitglieder. 31 bestehende Tests für Importoberfläche, Linien und Datenviewer sind ebenfalls erfolgreich.

Die laufenden Konten auf dem netcup-Server wurden nicht verändert oder ausgelesen. Die dort gespeicherte Rolle muss bei Bedarf wie oben geprüft werden.

Entwickler: `npm run test:admin-access` im Ordner `module-checks`; HTTP-Test mit `PHP_BIN=php python3 module-checks/tests/admin_access_api_test.py` vom Projektordner aus. Die HTTP-Testdatei nutzt die isolierte Serverfixture aus `incremental_api_test.py`.
