# Ahnenarchiv 2.1.0: geprüfter Import gleichnamiger Personen

Dies sind die Hinweise zum vorherigen Import-Fix für 2.1.0. Die aktuelle Installation und Verwaltung stehen in `IMPORT-VERWALTUNG.md`. In `httpdocs` entpacken und die enthaltenen Programmdateien überschreiben. Es enthält keine Datenbank, Bilder oder Serverkonfiguration. Anschließend den Browser neu laden.

1. Die **aktualisierte** Datei `stammbaum-boeck-schiessl-import.json` unter Linienimport neu einlesen.
2. Die Kennung aus dem früheren Import derselben Quelle beibehalten. Nur für eine neue Quelle ist `boeck-schiessl-2021` der Vorschlag. Alle 101 Personen-IDs sind unverändert.
3. In der Vorschau vorhandene Profile anhand von Lebensdaten, Ort und Partner zuordnen. Ein vorhandener Georg mit dem Datum 28.01.1835 und Ehe mit Maria Anna Schmid gehört zum Johann Georg aus Issing; wegen der getrennten Taufangabe kann hier eine manuelle Zuordnung nötig sein.
4. Erst danach den neuen Entwurf freigeben.

Die Vorschau zeigt bei Namensgleichen zusätzliche Merkmale. Die geprüften Georg-Datensätze tragen die Hauptlinie Böck, auch wenn die Abstammungsverbindung offen bleibt. Dasselbe gilt für Gregorius und Gregor in der Hauptlinie Schießl. Vorhandene Hauptlinien werden nicht überschrieben.

Zwei dokumentierte Lebensläufe dürfen getrennt angelegt werden, auch wenn ihre Abstammung nicht verbunden ist. Gleiche Daten und bloße Namensähnlichkeit reichen nicht als Trennungsbeleg. Neuanlagen müssen ausdrücklich bestätigt werden. Eine in der Vorschau eindeutig als andere Person erkannte Zuordnung wird beim Speichern blockiert.

**Bei bereits freigegebenem Altimport:** Der inkrementelle Import löscht keine alten Elternkanten und ersetzt keine vorhandenen Geburts-/Sterbeangaben. Die vorherige Zuordnung Georg (*1871) / Kreszenz → Georg (*1921) muss im Bestand separat geprüft werden. Einen noch offenen alten Entwurf nicht anstelle dieser Fassung freigeben.

Geprüft mit lokalem PHP-Importer und Testdatenbank: vollständige Freigabe, Wiederverwendung eines vorhandenen Georg/Maria-Profils, keine strittige Elternkante und keine zusätzlichen Datensätze beim Wiederholungsimport. Die Vorschau und der Schutz bei falschen Zuordnungen wurden separat getestet.
