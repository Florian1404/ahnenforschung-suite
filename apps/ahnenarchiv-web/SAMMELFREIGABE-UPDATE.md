# Ahnenarchiv 1.6.2 – Linien gemeinsam übernehmen

1. ZIP in den bestehenden Projektordner entpacken. Enthaltene `private`- und `public`-Ordner zusammenführen und Dateien überschreiben.
2. Webseite mit Strg+F5 neu laden. Die vorhandene JSON nicht erneut hochladen.
3. Unter **Linie importieren → Gespeicherte Importentwürfe** den vorhandenen Kreutzwiesner-Entwurf mit **Linie fortsetzen** öffnen. Eindeutige Treffer werden zugeordnet, neue Personen sind vorbelegt. **Gesamte Linie übernehmen (402 Personen)** übernimmt die Linie gemeinsam.

Wenn die Linie bereits zur Freigabe eingereicht wurde, erscheint **Gesamte Linie freigeben**. Der vorhandene Vorschlag wird übernommen; es wird kein neuer Import angelegt.

Wenn stattdessen viele einzelne Vorschläge in der **Prüfliste** warten: die passende Quelle auswählen, **Alle angezeigten auswählen**, dann **Auswahl gemeinsam freigeben**. Die Auswahl bleibt auf diese Quelle beschränkt, sofern du den Quellenfilter gesetzt hast. Andere Vorschläge bleiben offen. Höchstens 500 Vorschläge pro Sammelfreigabe.

Eindeutige Quell-ID oder Name mit vollständigem Geburtsdatum werden automatisch vorbelegt. Namensgleichheiten ohne eindeutigen Treffer bleiben zur Prüfung offen. Bewusst gespeicherte Zuordnungen und übersprungene Personen bleiben erhalten. Der neue Ablauf funktioniert auch mit bereits gespeicherten Entwürfen.

Die Freigabe schreibt Forschungsdaten ins Archiv. Sie erklärt ungeklärte Elternschaft nicht automatisch für biologisch bestätigt. Einzelprüfung, Quellen und Änderungsverlauf bleiben verfügbar. Bei einem Konflikt wird die gesamte Auswahl zurückgerollt. Ein erneut gesendeter Freigabeaufruf erzeugt keine doppelten Datensätze.

Das ZIP enthält die aktuelle Online-Anwendung, keine Konfiguration, Seed-Daten, Datenbank oder importierten Medien. Es ist keine Neueinrichtung und keine SQL-Migration nötig. Das zuvor separat angebotene PDF-Importmodul wird für diesen Ablauf nicht benötigt.

Geprüft: sechs neue UI-Tests und fünf neue API-Tests, darunter die Vorbelegung aller 402 Personen (391 neu, elf bestehend), gemeinsame Freigabe von 402 Einzelvorschlägen, Fortsetzen eines vorhandenen Entwurfs, Rechteprüfung und vollständiges Rollback bei veralteten Datensätzen. Bestehende UI-, API- und JSON-Linienimport-Prüfungen ebenfalls bestanden. PHP 8.3 mit isolierter SQLite-Testdatenbank; kein Test auf dem Live-Server.
