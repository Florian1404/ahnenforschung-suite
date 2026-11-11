# v1.3.2 – Belegte Elternschaft durchgezogen darstellen

Die Darstellung unterschied bisher ausschließlich anhand von `biologisch_bestaetigt`. Belegte Elternschaft ist eine eigenständige Information. Dafür gibt es jetzt `belegt: true`. Durchgezogene Linien erscheinen bei belegter/biologisch bestätigter Elternschaft sowie freigegebenen Adoptiv-, Pflege- oder Stiefverbindungen. Ungeklärte Diagrammzuordnungen bleiben gestrichelt.

## Auf der vorhandenen Website

1. `ahnenarchiv-v1.3.2-update.zip` in `stammbaum-huschka.de/httpdocs` hochladen und dort entpacken; vorhandene Dateien überschreiben.
2. Mit Strg+F5 neu laden. Der Versionshinweis muss v1.3.2 zeigen.
3. Als Admin: **Benutzer → Datenkorrekturen → Familienverbindungen zur Prüfung anlegen**.
4. In der **Prüfliste** den Vorschlag **Belegte Familienverbindungen bestätigen** prüfen und **Prüfung bestätigen & freigeben**.
5. Stammbaum wieder öffnen.

Das Einspielen der Dateien allein verändert die bereits installierte Datenbank noch nicht. Erst die Freigabe bestätigt diese vier vorhandenen Verbindungen:

- Otto Anton Huschka → Florian Huschka
- Maria Stephanie Huschka → Florian Huschka
- Florian Huschka → Luca Maximilian Huschka
- Daniela Huschka → Luca Maximilian Huschka

Grundlage ist Flos ausdrückliche Bestätigung am 09.10.2026. Die Bestätigung wird protokolliert. Biologische Einordnung und alle anderen Verbindungen bleiben erhalten. Keine pauschale Bestätigung weiterer Familienlinien. Die vier Änderungen werden gemeinsam gespeichert; zwischenzeitliche Änderungen verhindern die Übernahme. Bei Konflikt Vorschlag ablehnen und neu zur Prüfung anlegen.

Neuinstallationen verwenden bereits die bestätigten Seed-Verbindungen. Bestehende Archive benötigen die oben beschriebene Freigabe. Das Paket enthält alle bisherigen Updates einschließlich Porträtkorrektur, Bild-Popup, Importer und Patch-Historie. Kein neues Setup und keine Änderung an `config.php` erforderlich.

## Prüfung

Zehn PHP/MySQL-Integrationstests bestanden, darunter gezielte Bestätigung der vier Beziehungen, unveränderter Bestand vor Freigabe, Admin-Berechtigung, vollständiger Rollback bei Versionskonflikt, Wiederholungsschutz und Belegstatus in der Leseansicht. Zusätzlich Frontend-Prüfung der Linienentscheidung und Stammbaumprüfung mit 230 Knoten und weiter sichtbaren ungeklärten Linien.
