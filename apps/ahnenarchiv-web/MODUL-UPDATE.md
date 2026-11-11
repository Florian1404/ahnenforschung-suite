# Ahnenarchiv 1.6.0 – Diagramme

Eine ZIP, vollständig über die bestehende Installation kopieren. Der Inhalt gehört in den vorhandenen Projektordner mit private, public und config.php. Programmdateien überschreiben und Ordner zusammenführen. Nicht bestehende Ordner löschen. Danach Strg+F5. Keine Einrichtung erneut ausführen.

Alle Funktionen von 1.5.0 sind enthalten: Modulverwaltung, Familienexplorer, Recherche & Datenprüfung und Chronik & Jahrestage. Neu in 1.6.0:

- Fächerdiagramm und Kreisdiagramm mit bis zu sechs Vorfahrengenerationen.
- Sanduhr: Vorfahren oben, Nachkommen unten, Ausgangsperson einmal in der Mitte.
- Nummerierte Ahnentafel bis acht Generationen mit eigenen Pfadnummern; dies ist keine Vater-/Mutter- oder Kekulé-Nummerierung. Auch mehr als zwei erfasste Elternteile bleiben je Zweig enthalten.
- Direkte Schaltflächen unter Stammbaum; die gewählte Person ist der Ausgangspunkt. Alternativ Forschungsmodule → Familienexplorer.
- Personen per Klick oder Tab/Enter öffnen, Diagramme vergrößern oder in Originalgröße mit Scrollen ansehen.
- Diagramm als selbstständige SVG-Grafik herunterladen; Drucken/als PDF speichern über den Browser.
- Gestrichelte Umrandung: ungeklärter Verbindungsweg. Unbekannte Elternpositionen bleiben als solche gekennzeichnet. Mehrfach auftretende Vorfahren werden je Zweig gezeigt und mit ↺ markiert.
- Abstammungskreise werden pro Zweig gestoppt. Darstellungsgrenzen werden ausdrücklich angezeigt (1500 Positionen im Fächer oder der Ahnentafel; 600 je Richtung in der Sanduhr).

Die Diagramme werten nur bestehende freigegebene Datensätze aus. Es werden keine Personen oder Verbindungen geändert und keine Elternrollen geraten. Die Baumpositionen ordnen sich nach Namen und ID, nicht nach vermutetem Geschlecht. Die Diagramme stehen zunächst angemeldeten Online-Nutzern zur Verfügung; die bisherige lokale Windows-App bleibt erhalten.

Die Komplett-Update-ZIP enthält keine config.php, keine Datenbank, keine Seed-Daten und keine Mediendateien. Die vollständigen Quellpakete behalten die vorhandenen Seed-Dateien für Neuinstallationen bei; bestehende private Konfiguration und hochgeladene Medien bleiben erhalten.

30 Tests bestanden: 19 Fach-/Diagrammtests, 6 DOM-Oberflächentests, 5 PHP-API-Tests. Bestehende Stammbaumprüfung für 230 Personen und 260 Beziehungen bestanden; PHP-/JavaScript-Syntax geprüft. SVG-Ausgaben von Fächer, Kreis und Sanduhr gerendert und visuell geprüft. Kein Test im produktiven netcup-Hosting, kein MySQL-Lauf in dieser Sitzung und keine vollständige Browser-/Mobilgeräteprüfung. Der offene Fehler mit leeren Einladungsmails wird in diesem Update nicht bearbeitet.
