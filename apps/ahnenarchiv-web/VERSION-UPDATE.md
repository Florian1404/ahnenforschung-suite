# Update auf v1.3.0

`ahnenarchiv-v1.3.0-update.zip` im Dateimanager in `stammbaum-huschka.de/httpdocs` hochladen und genau dort entpacken. Vorhandene Dateien überschreiben. Danach Strg+F5.

Das Paket enthält den Linienimport und das Bild-Popup mit. Es kann direkt auf die ursprüngliche PHP-Installation oder einen der bisherigen Updates angewendet werden. Keine erneute Einrichtung nötig; `config.php` ist nicht enthalten.

Auf der Anmeldeseite, in der Seitenleiste und in der Leseansicht erscheint **v1.3.0 · Was ist neu?**. Anklicken öffnet die Historie mit Datum und Änderungen. Schließen per Escape, Schließen-Taste oder Klick daneben.

Die Entwicklungsstände 1.0.0 bis 1.2.0 wurden rückwirkend nummeriert. Das Fenster beschreibt die Funktionen der ausgelieferten Version, nicht eine Liste der auf diesem Server ausgeführten Installationen. PDF-/Bilderkennung braucht weiterhin einen API-Schlüssel; siehe `IMPORT-UPDATE.md`.

## Künftige Versionspflege

Die Liste `RELEASES` am Anfang von `app/static/app.js` ist die Quelle für die Versionsanzeige und die Historie. Neue Version mit Datum, Titel und Änderungen vorne ergänzen; vorhandene Einträge behalten. Danach dieselbe Datei nach `online/public/static/app.js` kopieren und die Versionsparameter in beiden `index.html`-Dateien aktualisieren. `CHANGELOG.md` passend aktualisieren. So zeigt ein neues Release seine Änderungen und lädt neue Browserdateien.
