# Ahnenarchiv für stammbaum-huschka.de

Diese Online-Version läuft mit PHP und MySQL/MariaDB auf normalem Webhosting. Kein Docker, kein Python und kein Node.js auf dem Server. Composer wird ebenfalls nicht benötigt. Die Python-Dateien im vollständigen Projekt gehören zur lokalen Windows-App; die lädst du nicht zum Webserver hoch.

## 1. Domain, Datenbank und PHP

Im netcup-Webhosting-Panel `stammbaum-huschka.de` auswählen. Eine eigene Datenbank mit eigenem Benutzer erstellen; Datenbankserver, Datenbankname, Benutzername und Passwort notieren.

Für diese Domain PHP 8.3 oder höher einstellen, mindestens 128 MB Arbeitsspeicher und `post_max_size` mindestens 16 MB. PDO MySQL, mbstring und fileinfo müssen verfügbar sein. Die Anwendung nutzt MySQL/MariaDB mit InnoDB. Apache beziehungsweise Apache hinter nginx muss .htaccess-Rewrite unterstützen; „Dateien direkt durch nginx bedienen“ für geschützte Verzeichnisse vermeiden. Bei reinem nginx müssen die Rewrite-Regeln entsprechend vom Hostingbetreiber eingerichtet werden.

## 2. Dateien hochladen – richtiger Dokumentenstamm

Den gesamten Inhalt dieses Pakets in ein eigenes Verzeichnis laden, beispielsweise `stammbaum-huschka.de/ahnenarchiv`. Darin liegen `public`, `private`, `seed`, `config.example.php`, `console.php` und diese Anleitung.

Dann den **Dokumentenstamm der Archiv-Domain auf `stammbaum-huschka.de/ahnenarchiv/public` stellen** (Pfad entsprechend deiner Verzeichnisstruktur anpassen). Nur `public` darf öffentlich sein. Niemals das ganze Projekt, `private` oder `seed` zum Dokumentenstamm machen. Zugangsdaten und Originalforschung bleiben eine Ebene darüber. Versteckte Dateien `.htaccess` und `.user.ini` mit hochladen. Marktpay behält seinen eigenen Dokumentenstamm.

Das übergeordnete `.htaccess` sperrt absichtlich Zugriffe, falls der Dokumentenstamm falsch gesetzt wird. Innerhalb von `public` wird der Zugriff wieder erlaubt.

## 3. Konfiguration

`config.example.php` nach `config.php` kopieren und im Dateimanager bearbeiten. Dort:

- `base_url`: `https://stammbaum-huschka.de`, ohne abschließenden `/`.
- Datenbankserver, Name, Benutzer und Passwort exakt aus netcup übernehmen.
- `setup_key`: mindestens 32 zufällige Zeichen aus einem Passwortgenerator.
- `max_upload_bytes`: zunächst `8 * 1024 * 1024`. Größere Werte erst nach Prüfung der Hosting-Limits.
- `require_https`: `true` belassen.

Die Konfiguration ist eine PHP-Datei: Anführungszeichen und Backslashes im Passwort richtig maskieren. Dateirechte möglichst 600, Verzeichnisse 700 oder 750, soweit der Hostingbetrieb es zulässt. PHP muss `private/media` beschreiben können. Kein `chmod 777`.

Ein kostenloses Let's-Encrypt-Zertifikat für die Domain aktivieren und HTTP auf HTTPS umleiten. Der Server vertraut keinen ungeprüften Proxy-Headern. Bei HTTPS muss PHP das HTTPS-Signal vom netcup-Webserver erhalten.

## 4. Einmalige Einrichtung

`https://stammbaum-huschka.de/setup` öffnen. Einrichtungsschlüssel, deinen Namen, E-Mail und ein neues Admin-Passwort (mindestens zwölf Zeichen) eintragen. Der Import übernimmt alle 230 Personen, 87 Familien und die übrigen Originaldaten samt Medien. Einmalig rund 20 MB Paketdaten hochladen, nicht über das Medienformular.

Die Einrichtung ist durch den Schlüssel geschützt und wird nach erfolgreichem Import in der Datenbank dauerhaft gesperrt. Sie überschreibt keine bestehenden Datensätze. Danach `setup_key` in config.php leeren. Bereits bei angefangener Einrichtung ohne Erfolg Serverprotokoll prüfen, statt Datensätze manuell zu löschen.

Jetzt auf der Startseite anmelden. Otto registriert sich über „Neues Konto anlegen“. Unter **Benutzer** sein Konto aktivieren und zu **Admin** machen. Beide Admins können die Prüfliste bearbeiten.

## 5. Funktionskontrolle vor dem Teilen

Eine Ergänzung einreichen: Der bestätigte Datensatz muss unverändert bleiben. Ergänzung freigeben: Neuer Wert erscheint, alter Stand ist in der Historie. Eine neue Person zunächst als Vorschlag anlegen; zugehörige Bilder dürfen erst nach Freigabe der Person endgültig übernommen werden. Unbekannte Personen brauchen eine vorläufige Bezeichnung, z. B. „Unbekannte Person im Huschka-Hochzeitsfoto“.

Ein Foto und einen Scan hochladen. Das Standardlimit ist 8 MB pro Datei. Die Oberfläche verkleinert größere JPG/PNG/WebP-Dateien im Browser auf JPEG; die lokale Originaldatei bleibt unverändert. Transparenz geht bei dieser Verkleinerung verloren. PDFs werden nicht verändert und müssen unter dem Limit liegen.

Einen Leselink erzeugen und in einem privaten Browserfenster öffnen. Lebende Personen und Bilder sind zunächst verborgen; ausdrücklich freigeben, falls gewünscht. Gruppenbilder werden nur freigegeben, wenn alle zugeordneten Personen sichtbar sind. Widerruf des Links direkt testen.

## 6. Papas Offline-App

Windows-App aus dem vollständigen Projekt neu bauen. Im Bereich Synchronisierung `https://stammbaum-huschka.de` und Ottos Online-Konto eintragen. Die API-Adressen und Antwortfelder sind zur bisherigen lokalen App kompatibel. Der aktualisierte Desktop verwendet ebenfalls 8 MB Uploadlimit. Eine früher gebaute Version mit 20 MB sollte ersetzt werden. Noch nicht übertragene übergroße Dateien aus alten lokalen Installationen werden nicht still verändert: neu verkleinert einreichen und die alte Warteschlange gezielt prüfen.

Ohne Internet sind Personen, Stammbaum und gespeicherte Medien nutzbar; Ergänzungen bleiben in der lokalen Warteschlange. Freigaben laufen über den Online-Server. Die EXE wird auf Windows gebaut; dieses Webhosting-Paket enthält keine fertige EXE.

## 7. Sicherung und Export

Datenbank über netcup sichern **und** `private/media` getrennt mit sichern; JSON allein enthält keine Bilddateien, Benutzer und Sitzungen. Eine Wiederherstellung testweise prüfen. Originalimport bleibt im Paket erhalten. Im angemeldeten Admin-Browser liefert `/api/export` einen JSON-Forschungsexport inklusive Vorschlägen. Optional per SSH: `php console.php check`, `php console.php export > export.json`.

Serverfehler werden mit einer neutralen Meldung beantwortet. Details im PHP-/Webserver-Fehlerprotokoll lesen. Keine Zugangsdaten an öffentliche Fehlermeldungen oder Screenshots hängen.

## Grenzen

Dies ist eine individuell entwickelte Anwendung, kein bereits lange betriebenes fertiges Produkt. Die beigefügte Validierung nennt tatsächliche Tests und offene Punkte. Auf deinem netcup-Konto ist noch nichts installiert oder live getestet. Konto-Freigabe erfolgt manuell; automatisierte E-Mail-Bestätigung, Passwort-zurücksetzen und Zwei-Faktor-Anmeldung sind noch nicht enthalten. Hochzeiten bleiben vollständig im Import erhalten; einen vollständigen Mehrfach-Ehen-Editor gibt es noch nicht.
