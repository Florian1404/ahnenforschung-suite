# Inkrementeller Import – Version 2.0.0

## Installation auf netcup

Das Update-ZIP im bestehenden `stammbaum-huschka.de/httpdocs` entpacken und die Programmdateien überschreiben. Der Dokumentenstamm bleibt `httpdocs/public`. Die vorhandene `config.php`, Bilder, Datenbank und Benutzer bleiben erhalten. Anschließend im Browser mit Strg+F5 neu laden. Keine erneute Einrichtung starten.

## Einen Stammbaum ergänzen

1. Im Importbereich JSON oder GEDCOM hochladen. Eine feste Datenquellen-Kennung verwenden, zum Beispiel `kreutzwiesner`.
2. Bei jeder weiteren Fassung derselben Quelle diese Kennung und die ursprünglichen Personen-IDs beibehalten. IDs dürfen nicht mit anderen Personen wiederverwendet werden.
3. Den Abgleich prüfen. Gespeicherte Quellzuordnungen und bestehende IDs werden wiedererkannt. Eindeutiger vollständiger Name mit vollständigem Geburtsdatum wird als bestehende Person vorgeschlagen.
4. Bei möglichen Treffern eine vorhandene Person zuordnen oder den Eintrag überspringen. Eine Neuanlage ist dann gesperrt. Mögliche Dubletten innerhalb der Datei zuerst bereinigen oder einen Eintrag überspringen und erneut prüfen.
5. Nur tatsächlich neue Personen ohne erkannten Dublettenverdacht ausdrücklich als neu bestätigen. Unbekannte Namen erlauben keine Neuanlage. Vorhandene unbekannte Namen können bei gleicher Identität ergänzt werden.
6. Den Änderungsvorschlag zur Prüfung einreichen. Erst die Admin-Freigabe übernimmt Ergänzungen und speichert die Quellzuordnungen.

## Was übernommen wird

- Fehlende Angaben werden ergänzt. Abweichende bereits vorhandene Werte bleiben erhalten und werden als Konflikt angezeigt. Eine Korrektur bekannter Werte erfolgt separat über die Personenbearbeitung.
- Zusatzinformationen wie Originalnummern, Quellen, Notizen, Berufe und Wohnsitze werden ergänzt. Identische Listeneinträge werden nicht erneut angelegt.
- Bestehende Familien erhalten zusätzliche Kinder; vorhandene Verbindungen werden wiederverwendet. Unterschiedliche Hochzeiten oder mehrere passende Familien erfordern Klärung.
- Eine unveränderte Datei derselben Quelle wird als vorhandener Import wiedererkannt. Bereits freigegebene unveränderte Inhalte erzeugen keinen zweiten Änderungsvorschlag.
- Bei der Freigabe wird der aktuelle Bestand unter Schreibsperre erneut geprüft. Zwischenzeitlich entstandene mögliche Dubletten oder Änderungen können die Freigabe anhalten. Zwei nacheinander freigegebene identische Vorschläge erzeugen keine zusätzlichen Personen oder Familien.

## Grenzen und bestehende Importe

Die Erkennung braucht nachvollziehbare Identitäten. Bei gleichzeitig geänderten IDs, Namen und Lebensdaten ist eine sichere automatische Zuordnung nicht möglich. Treffer bleiben daher zur manuellen Zuordnung stehen; sie werden nicht zwangsweise neu angelegt. Schon vorhandene Dubletten werden durch dieses Update weder gelöscht noch automatisch zusammengeführt.

Offene Importvorschläge aus Versionen vor 2.0.0 müssen mit Quellenkennung erneut eingelesen werden. Bereits freigegebene Datensätze bleiben bestehen. Beim ersten Abgleich ohne gespeicherte Quellzuordnung sind bestehende Personen zu prüfen; auch eine reine Zuordnung ohne neue Sachangaben benötigt die Freigabe.

Der Datenviewer kann zusätzlich CSV und andere Textformate anzeigen. Diese Anzeige ist kein Datenbankimport. Der feste Kreutzwiesner-Quellenimport bleibt separat; weitere JSON-Fassungen werden über den inkrementellen Import eingelesen. JSON/GEDCOM erfordern keinen KI-API-Schlüssel.

## Validierung

Automatisiert geprüft: 13 PHP/SQLite-Szenarien für Abgleich, Freigabe und Rollback; ein HTTP-Ablauf von Upload bis wiederholter Freigabe; vier UI-Tests zum Import sowie 27 Regressionstests für Linien und Datenviewer. Testumgebung: PHP 8.3 und SQLite, ohne produktive Datenbank oder echten Mailversand. Kein Test auf dem produktiven MySQL-Server.

Entwickleraufrufe: `php tests/test_incremental.php`, `PHP_BIN=php python3 module-checks/tests/incremental_api_test.py`, sowie im Ordner `module-checks` nach Installation der Abhängigkeiten `npm run test:incremental-ui`, `npm run test:lines` und `npm run test:viewer`.
