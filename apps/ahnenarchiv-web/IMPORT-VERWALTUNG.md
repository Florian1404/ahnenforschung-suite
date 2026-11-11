# Ahnenarchiv 2.1.1 – Import auswählen, verwerfen und rückabwickeln

Dieses Paket ist ein Update für Ahnenarchiv ab 2.1.0. Es enthält auch den vorherigen Fix für die Zuordnung gleichnamiger Personen. Die Datenbank, `config.php`, Bilder und Originalquellen sind nicht Teil des Pakets.

1. Im Plesk-Dateimanager das ZIP in `stammbaum-huschka.de/httpdocs` entpacken und die enthaltenen Programmdateien überschreiben. Der Dokumentenstamm bleibt `httpdocs/public`.
2. Webseite neu laden und unten in der Patch-Historie prüfen, ob **2.1.1** angezeigt wird.
3. **Linienimport → gespeicherten Import öffnen.** Ein bestehender Entwurf kann weiterverwendet werden. Wähle **Bestehende Person aktualisieren** oder **Person suchen und auswählen**. Suche nach Namen, Geburtsjahr, Geburtsort oder einem anderen bekannten Merkmal und klicke den passenden Treffer an. Namensgleiche erscheinen getrennt.
4. Eine spätere Fassung derselben Quelle mit derselben Quellenkennung und denselben Quell-IDs einlesen. Korrigierte Dateien können sich bei gleichem Namen im Inhalt unterscheiden.

- **Entwurf verwerfen:** Der offene Entwurf wird geschlossen und ggf. aus der Prüfliste genommen. Der Stammbaum bleibt unverändert. Dieselbe Datei kann wieder eingelesen werden.
- **Dauerhaft löschen:** Löscht den Entwurf, seine Importvorschläge und die zugehörige Originaldatei. Eingereichte Importe erst verwerfen; freigegebene Importe erst rückabwickeln.
- **Rückabwicklung prüfen:** Admins sehen vorab, welche neu importierten Datensätze entfernt und welche vorhandenen Daten wiederhergestellt würden. Erst **Jetzt rückabwickeln** führt die Änderung aus. Die Originaldatei bleibt bis zum anschließenden dauerhaften Löschen erhalten.
- **Import anhand der Original-JSON finden:** Die unveränderte Datei wählen. Die App berechnet lokal einen Fingerabdruck und sucht passende gespeicherte Importe; sie lädt die Datei dabei nicht erneut hoch.

Die Rückabwicklung prüft die aufgezeichneten Änderungen des konkreten Imports. Bearbeitete Datensätze und spätere Verknüpfungen blockieren die Aktion vollständig. Ältere Importe brauchen ein vollständiges Vorher-/Nachher-Protokoll; bei ihnen können nicht eindeutig zuordenbare Quell-IDs zu Altbestandsprofilen erhalten bleiben. Eine JSON allein beweist nicht, welche Daten vor dem Import schon im Archiv waren.

Lokal geprüft: Auswahl gleichnamiger Personen im DOM-Test, gespeicherte Auswahl bei erneuter Vorschau, unveränderte Dublettenprüfung, Verwerfen, Neuupload, Löschen, Rechte, Rückabwicklung und Sperre bei späteren Änderungen.
