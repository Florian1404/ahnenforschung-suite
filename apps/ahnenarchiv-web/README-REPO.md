# Ahnenarchiv-Websoftware (PHP / MySQL)

**Aktueller verfügbarer Patchstand: 2.1.5.** Zusammengesetzt aus v2.1.0-ZIP, Import-Familiengruppen 2.1.3, Person-Admin 2.1.4, Ereignisverwaltung 2.1.5.

**Achtung:** Das ist ein rekonstruiertes Code-Paket, keine gesicherte 1:1-Kopie des aktiven netcup-Servers. Hotfixes und Serverkonfiguration fehlen ggf. Siehe `../../docs/DEPLOYMENT.md`.

- `public/`: Webroot und JavaScript/CSS-Oberfläche.
- `private/`: API, Nutzer, Import, Familienbeziehungen, Person-/Ereignisaktionen. Nicht öffentlich bereitstellen.
- `config.example.php`: Platzhalter, **keine** Zugangsdaten.
- `private/imports/` und `private/media/`: personenbezogene Laufzeitdaten, absichtlich ausgeschlossen.

Vor einem Serverdeploy **zuerst Live-Code und Datenbankbackup** sichern. Der Git-Checkout enthält weder produktive DB noch Fotos.
