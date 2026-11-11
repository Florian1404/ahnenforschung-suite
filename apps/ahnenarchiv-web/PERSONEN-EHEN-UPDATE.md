# Version 2.1.0: Personen, Hauptlinien und Ehen

Das Update-ZIP in `stammbaum-huschka.de/httpdocs` entpacken und die Programmdateien überschreiben. Der Dokumentenstamm bleibt `httpdocs/public`. Im Browser Strg+F5 drücken. Bestehende Datenbank, Konten, Bilder und `config.php` bleiben erhalten. Keine Neuinstallation oder Migration erforderlich.

## Georg Böck aus dem Traubuch ergänzen

1. Den vorhandenen Georg Böck (* 28.01.1835, Issing) öffnen und **Daten & Hochzeit ergänzen** wählen.
2. **Hauptlinie: Böck**, **Hochzeitsdatum: 08.02.1869**, **Hochzeitsort: Ludenhausen**.
3. Maria Anna Schmid unter **Vorhandene Person auswählen** suchen. Ist sie noch nicht im Archiv, **Ehepartner hier neu anlegen** wählen und Name und Geburtsdatum **12.08.1834** eintragen. Die Hauptlinie kann von Georg übernommen oder separat gewählt werden.
4. Traubuch als Quelle eintragen und **Gemeinsam zur Prüfung speichern**. Unter **Prüfliste** freigeben. Danach erscheint dieselbe Ehe bei beiden Personen und unter **Familie im Stammbaum ansehen**.

Die Angaben sind auch direkt unter **Neue Person** verfügbar. Eine Hochzeit ohne bekannten Partner kann zunächst mit Datum und/oder Ort erfasst werden. Sind die Partner schon verbunden, die **vorhandene Ehe** in der Maske auswählen, um Datum und Ort zu ändern. Die Partnerschaft und vorhandene Kinder bleiben dabei erhalten.

Die Freigabe übernimmt alle Änderungen eines Vorschlags in einer Transaktion. Ein Konflikt oder eine mögliche Namens- und Geburtsdublettenübereinstimmung hält den gesamten Vorschlag an. Ältere Hochzeitsdaten in Biografien bleiben als Text erhalten; sie werden nicht automatisch als strukturierte Daten übernommen. Die bestehende Biografie und Bilder brauchen nicht erneut erfasst zu werden.

Eine manuelle Hauptlinie macht eine Person im Umfang **Gesamte Hauptlinie mit Seitenzweigen** auffindbar. Sie ergänzt keine unbelegte Elternschaft und verändert den Modus **Nur direkte Vorfahren** nicht.

## Prüfung

Tests der Online-Maske für Neuanlage, bestehende Person, vorhandene Ehe, beide Profile und Stammbaum. Isolierte PHP/SQLite-Tests für Freigabe, Rollen, Dubletten, konkurrierende Änderungen und unveränderten Bestand bei Ablehnung. Die Produktionsdatenbank wurde nicht verändert. Die neue Erfassungsmaske ist in diesem Webupdate enthalten.
