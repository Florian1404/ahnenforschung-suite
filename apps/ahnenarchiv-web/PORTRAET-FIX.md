# v1.3.1 – Porträtzuordnungen berichtigen

Die drei Porträtzuordnungen aus dem Erstimport waren vertauscht:

| Person | Bisheriges Bild | Richtiges Bild aus Originalseite |
| --- | --- | --- |
| Tyler Alexander Huschka | Luca | Tyler, Seite 147 |
| Luca Maximilian Huschka | Leonie | Luca, Seite 148 |
| Leonie Sophia Huschka | Tyler | Leonie, Seite 149 |

## Vorhandene Online-Datenbank korrigieren

1. `ahnenarchiv-v1.3.1-update.zip` in `stammbaum-huschka.de/httpdocs` hochladen und dort entpacken. Vorhandene Dateien überschreiben.
2. Webseite mit Strg+F5 neu laden und als Admin anmelden.
3. **Benutzer → Datenkorrekturen → Porträtkorrektur zur Prüfung anlegen**.
4. In der **Prüfliste** die bisherigen und richtigen Bilder nebeneinander prüfen.
5. **Prüfung bestätigen & freigeben**.

Erst die Freigabe ändert die Personen und Medienzuordnungen. Alle sechs Datensätze werden in einer Transaktion berichtigt. Zusätzliche Daten und andere Bilder bleiben erhalten. Eine zwischenzeitliche Änderung verhindert die gesamte Übernahme; dann Vorschlag ablehnen und neu anlegen. Eine von der erwarteten Ausgangslage abweichende Porträtzuordnung wird nicht blind überschrieben. Ein wiederholter Klick legt keinen zweiten offenen Korrekturvorschlag an; nach erfolgreicher Korrektur erscheint „bereits korrekt“.

Die Korrektur betrifft `portraet_medien_id`, die zugehörigen Personenanhänge und die Gegenverknüpfung in den Medien. Bilddateien selbst werden nicht vertauscht oder überschrieben. Alle Änderungen stehen im Änderungsverlauf. Für Neuinstallationen sind die Seed-Zuordnungen bereits korrigiert.

Das Update enthält ebenfalls den bisherigen Importer, das Bild-Popup und die Versionshistorie. Kein erneutes Setup; `config.php` ist nicht enthalten. Die neue Datenkorrektur ist ausschließlich für Admins verfügbar.

Validiert mit neun PHP/MySQL-Integrationstests; zusätzlich separater Test der Korrektur mit realer MariaDB für Berechtigung, unveränderten Bestand vor Freigabe, vollständigen Rollback bei Versionskonflikt, sechs richtige Verknüpfungen, Audit und Wiederholungsschutz. Frontend-Syntax und bestehende Importansichten geprüft.
