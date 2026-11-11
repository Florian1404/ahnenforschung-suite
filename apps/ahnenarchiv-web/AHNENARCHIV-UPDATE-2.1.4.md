# Ahnenarchiv – Update 2.1.4: Person löschen / Dubletten zusammenführen

**Stand:** 08.11.2026 · **Basis:** bestehende Installation 2.1.3 (PHP/netcup)

## Vor der Installation

1. **Datenbank sichern** (bei netcup/Plesk per phpMyAdmin als SQL exportieren). Zusätzlich die fünf zu ersetzenden Dateien aus dem Webspace sichern.
2. ZIP **lokal entpacken**, anschließend die Ordner `private/` und `public/` in den **gleichen Projektstamm** wie die laufende Anwendung kopieren. Bestehende Dateien überschreiben, die neue Datei `private/person-admin.php` hinzufügen. **Keinen Webroot extra anlegen.**
3. Kontrollieren: `private/api.php`, `private/person-admin.php`, `public/index.html`, `public/static/app.js`, `public/static/style.css` sind auf dem Server aktuell.
4. Browser mit Strg+F5 neu laden. Angemeldet als Admin unter **Personen** suchen.
5. Die Live-Datenbank wird durch die Installation **nicht automatisch verändert**. Erst eine ausdrückliche Bestätigung einer Aktion schreibt Daten.

## Neue Funktionen

- **Löschen** direkt in der Personensuche sowie auf einer Personendetailseite, nur für Administratoren. Separate, fokussierte native Dialogbox mit Person, ID, Daten und Auswirkungszahlen. Die Aktion ist erst nach Eingabe von `LÖSCHEN` freigegeben.
- Die Löschung ist **reversibel**: Der Personeneintrag wird als `archived_person` archiviert und in normalen Listen ausgeblendet. Seine Eltern-/Partnerbeziehungen werden als `archived_relationship` archiviert, Familiengruppen werden angepasst und Medien-Verweise entfernt. **Andere Personen werden nicht gelöscht.** Medien-Dateien auf der Platte bleiben unangetastet.
- **Zusammenführen**: Quellperson auswählen, Zielperson (die **bleibt**) bewusst suchen und auswählen, Vorschau kontrollieren und `ZUSAMMENFÜHREN` eingeben. Die bisherigen Quell-IDs und Quellenhinweise gehen in den Zieldatensatz ein, Familien und Beziehungen werden umgehängt. Identitätskollisionen bei Geburts-/Sterbedaten, direkte Verwandtschaft und Abstammungskreise werden serverseitig abgewiesen.
- **Korrekturverlauf** oberhalb der Suchergebnisse. Die letzte Korrektur kann rückgängig gemacht werden, wenn die betroffenen Daten inhaltlich unverändert sind. Bei zwischenzeitlichen Änderungen wird der automatische Rückweg verweigert.
- Alle Schreibvorgänge laufen unter demselben Datenbank-Schreib-Lock mit atomaren Transaktionen, Quellen-/Ziel-IDs werden validiert, jeder Vorgang erhält ein Auditprotokoll. Geöffnete Prüfvorschläge auf betroffene Personen blockieren die Aktion.
- Eingeschränkte Freigabelinks bleiben sicher: Ein auf eine einzige gelöschte Person begrenzter Link wird gesperrt, anstatt versehentlich den ganzen Stammbaum freizugeben.

## Konkreter Fall Böck (*1835)

In der Personensuche nicht auf "Löschen" drücken, wenn eigentlich dieselbe Person doppelt vorhanden ist. Zunächst **"Zusammenführen"** wählen:

- **Quelle (wird archiviert):** `imp_51d74b36813ea2c243a6d9524be7ca54bcdd4c4bbc33974eb943d4c940d3036f` – Johann Georg Böck.
- **Ziel (bleibt):** `person_70bc7ccc9f9d18c7bbc7d55084b32041` – Georg Böck, *28.01.1835.
- Vor dem endgültigen Bestätigen die Auswirkungszahlen prüfen. Die Testsimulation anhand des bereitgestellten Böck-Exports ergab sechs betroffene Datensätze. Das ist **kein Beleg dafür**, dass dein Livebestand unverändert denselben Stand hat; die App berechnet beim Klick auf "Zuordnung prüfen" eine neue Vorschau.
- Danach im Profil nachsehen: Maria Anna Schmid ist Partnerin von Georg (*1835); Georg (*1871) ist ihr Kind und **nicht** ihr Ehepartner.

## Technische Hinweise und Grenzen

- Reversible Löschung ist **kein datenschutzrechtlich endgültiges Löschen**. Archivierte Datensätze und Audit-Backups bleiben in der Datenbank erhalten; sie verschwinden nur aus aktivem Stammbaum/Suche/Export.
- Das Update bereinigt keine anderen historischen Fehler von allein. Es kann nachgeordnete Importentwürfe geben, die noch auf alte IDs verweisen; diese dann kontrolliert erneut zuordnen.
- Eine Person darf nicht stillschweigend aufgrund einer Namensähnlichkeit verschmolzen werden; die Zielperson muss explizit gewählt werden.
- Das Update wurde auf Syntax geprüft (`php -l`, `node --check`) und mit einer In-Memory-Testdatenbank sowie dem bereitgestellten Böck-Export getestet, **nicht** gegen die produktive netcup-Datenbank ausgeführt.
- Es wird keine Datenbankmigration und keine Änderung an `config.php` benötigt.

## Enthaltene Update-Dateien

- `private/api.php` – neue Verwaltungsrouten einbinden
- `private/person-admin.php` – Verwaltung, Vorschau, Transaktionen, Audit, Wiederherstellung
- `public/static/app.js` – Such-/Profilschaltflächen und Dialoge
- `public/static/style.css` – Dialogdarstellung
- `public/index.html` – Versionsparameter für Cache-Aktualisierung
