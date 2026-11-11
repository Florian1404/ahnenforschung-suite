# 1.8.2 – Hauptlinien verständlich auswählen

In stammbaum-huschka.de/httpdocs entpacken, Ordner zusammenführen, Dateien überschreiben, Strg+F5. Keine Neueinrichtung. Enthält 1.8.0 und frühere Programmupdates.

Oben in Personen und Stammbaum stehen große Hauptlinien-Schaltflächen mit Personenanzahl und Bezugsperson. Huschka startet bei Anton Otto Huschka (1911), Kreutzwiesner bei Irma Huschka geb. Kreutzwiesner (1922), Böck bei Maria Stephanie Huschka geb. Böck (1956), Schiessl bei Theresia Böck geb. Schiessl, soweit die Bezugsperson im Bestand vorhanden ist. Fehlende Bezugspersonen werden als solche angezeigt. Dies sind Ansichtsdefinitionen, keine neuen genealogischen Behauptungen oder Änderungen an Personendaten.

Eine Hauptlinie umfasst die erfassten Vorfahren ihrer Bezugsperson, danach deren Nachkommen und Partner. Partner werden zuletzt hinzugefügt; deren Vorfahren nicht durchlaufen. Durch vorhandene gemeinsame Vorfahren und Nachkommen können Linien überlappen. Auch ungeklärte Beziehungen werden weiterhin berücksichtigt. Alternativ nur direkte Vorfahren anzeigen.

Unter Andere Bezugsperson kann eine eigene Linie aus einer beliebigen vorhandenen Person gebildet werden. Diese Ansichtsentscheidung gilt für die aktuelle Sitzung.

Erst innerhalb der Hauptlinie wird optional ein Familien-/Geburtsname gewählt. Damit steht bei Benda die Hauptlinie ausdrücklich dabei. Suche, Sortierung und JSON-Export verwenden die Hauptlinie plus optionalen Namen und Suchtext. Der klassische Stammbaum zeigt die gewählte Hauptlinie und bleibt durch direkte Vorfahren/nahe Familie eingrenzbar.

Falls die Auswahl nach dem Upload nicht erscheint: Version in der Fußzeile kontrollieren (1.8.2), dann Strg+F5. Das Dokumentenstammverzeichnis bleibt public; das ZIP gehört eine Ebene darüber nach httpdocs.

Validierung: 12 Linien-/DOM-Tests und 10 Datenviewer-Tests bestanden. Benda-Zuordnung ausdrücklich mit den mitgelieferten Kreutzwiesner-Daten geprüft. Keine Prüfung im produktiven Hosting oder vollständiger Browser-/Mobiltest.

1.8.2: Namensplatzhalter (Fragezeichen, Unbekannt, N. N., leere oder rein symbolische Namen) stehen nach den identifizierbaren Namen, auch bei absteigender Sortierung und Datumsfeldern. Die Daten werden nicht geändert.

## 1.9.0 – Wichtig: neue Standardansicht

Standard ist jetzt Geburtsdatum aufsteigend. Vorlagen-/d’Aboville-Nummern werden als überlieferte Kennungen aus original_nummern bzw. expliziten d’Aboville-Feldern angezeigt; keine Nummern werden errechnet. Verschiedene Nummerierungssysteme/Bezugspersonen können nicht zu einem neuen gemeinsamen Stammbaumcode vereinheitlicht werden. Fehlende Nummern zuletzt.

Hauptlinien und Familiendiagramme schließen explizite Adoptiv-, Pflege-, Stief- und Annahmeverbindungen standardmäßig aus der Traversierung aus. Partner bleiben zuletzt ergänzte Begleitpersonen. Querverbindungen per Schalter einschaltbar. Elterneinträge aus der Vorlage werden nicht pauschal als biologisch bewiesen erklärt. Bei doppelten Einträgen für dieselben Personen hat eine ausdrücklich erfasste Adoption Vorrang vor einer bloßen Diagrammzuordnung.

Bei Anton/Johanna enthält die alte Vorlage eine Annahme mit ungeklärter Rechtsform, der Kreutzwiesner-Import eine explizite Adoption. Beide erscheinen bei Anton separat unter Adoptivbeziehungen & Querverbindungen statt unter den Kindern seiner Abstammungslinie. Julius Kohl bleibt als bereits erfasster Elternteil sichtbar; keine Daten werden aufgrund dieser UI-Änderung überschrieben oder gelöscht.

Die gewählte Linie und der Querverbindungs-Schalter gelten nun auch für Familienexplorer-Diagramme.

1.9.0 geprüft mit 17 Linien-/Sortier-/DOM-Tests plus 10 Datenviewer-Tests. Hanna-Fall mit alter Annahme und neuer Adoptivzuordnung, klassischem Stammbaum und Diagramm-Datenausschnitt geprüft. Keine produktive netcup- oder vollständige Browserprüfung.
