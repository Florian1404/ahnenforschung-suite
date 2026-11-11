# 2.1.0 – Personen, Hauptlinien und Hochzeiten

- Hauptlinie, Hochzeitsdatum und Hochzeitsort direkt bei neuer Person oder unter Daten & Hochzeit ergänzen erfassen.
- Vorhandenen Ehepartner auswählen oder in derselben Maske mit Geburtsname und Lebensdaten neu anlegen; eine gemeinsame Freigabe.
- Hochzeit in beiden Profilen, vorhandene Ehen bearbeiten und beide Partner im Familienstammbaum anzeigen.
- Manuell zugeordnete Personen in der Hauptlinie auffindbar, auch ohne bereits erfassten Abstammungsanschluss.

# 2.0.1 – Gleiche Verwaltungsansicht für alle Admins

- Aktuelle Kontorolle wird auch in bereits geöffneten Sitzungen geladen; Adminnavigation und Prüfliste aktualisieren sich automatisch.
- Mein Konto zeigt Name, E-Mail und Rolle mit manueller Aktualisierung.
- Leselinks bleiben schreibgeschützt, bieten aber den Wechsel zur eigenen Anmeldung.
- Serverrechte bleiben für jeden Aufruf verbindlich; keine Sonderrechte nach Namen oder Erstkonto.

# 2.0.0 – Inkrementeller Import

- Stabile Quellenkennung und Quellpersonen-IDs werden wiedererkannt; Wiederholungen ergänzen den vorhandenen Bestand.
- Neuzugänge benötigen ausdrückliche Bestätigung; mögliche Dubletten im Bestand oder in der Datei sperren die Neuanlage serverseitig.
- Familiengruppen werden ergänzt, Verbindungen dedupliziert und der Bestand bei Freigabe unter Schreibsperre erneut geprüft.

# 1.9.0 – Reihenfolge und Abstammung

- Personen und Kinder standardmäßig nach Geburtsdatum, älteste zuerst. Vorlagen-/d’Aboville-Nummern als zusätzliche natürliche Sortierung.
- Adoptiv-, Pflege-, Stief- und Annahmeverbindungen werden nicht mehr automatisch wie Abstammung in die Hauptlinie aufgenommen.
- Weitere Familienbeziehungen bleiben separat aufklappbar; ein Schalter zeigt Querverbindungen auf Wunsch auch in der Linie und den Diagrammen.

# 1.8.2 – Bekannte Namen zuerst

- Personen mit bekannten Namen werden alphabetisch ab A sortiert; Fragezeichen, fehlende Namen, Unbekannt und N. N. kommen an das Ende.
- Namensplatzhalter bleiben auch bei absteigender Namens- und Datumssortierung hinten.
- Die gleiche Reihenfolge gilt in Personenauswahllisten und beim Export der Suchtreffer.

# 1.8.1 – Hauptlinien

- Huschka, Kreutzwiesner, Böck und Schiessl als große Hauptlinien-Schaltflächen mit Bezugsperson und Personenanzahl.
- Linien folgen erfassten Vorfahren und ihren Familienzweigen; Benda und andere Nachnamen sind optionale Untergruppen innerhalb der Hauptlinie.
- Eigene Bezugsperson auswählbar, direkte Vorfahren als kompakte Ansicht, Hauptlinie auf Personenkarten und im Export erkennbar.

# 1.8.0 – Linienauswahl und Personensuche

- Übergeordnete Linienauswahl mit Personenanzahl und wählbarem Umfang: Namensträger oder Nachkommen mit Partnern.
- Personensuche nach Namen, Geburt, Tod oder frühester erfasster Hochzeit auf- und absteigend sortieren.
- Stammbaum auf die gewählte Linie eingrenzen und gefilterte Suchergebnisse als JSON exportieren.
- Alle gespeicherten Personenangaben strukturiert aufklappen; vollständige Originaldaten zusätzlich sichtbar.

# 1.7.0 – Datenviewer

- JSON, JSONL, GEDCOM, CSV und TSV lokal im Browser lesbar anzeigen und durchsuchen.
- GEDCOM-Felder erhalten deutsche Beschriftungen; CSV erscheint als Tabelle mit Seitennavigation.
- Originaltext, Zeichensatzauswahl, Text einfügen und Download der lesbaren Ansicht. XML, YAML und TXT als Textansicht.

# 1.6.2 – Sammelfreigabe und direkter Linienimport

Eindeutige Personenzuordnungen werden vorbelegt; Admins übernehmen eine ganze Linie gemeinsam. Bestehende Entwürfe sind fortsetzbar. Die Prüfliste bietet Quellenfilter und atomare Sammelfreigabe bis 500 ausgewählter Vorschläge.

# 1.6.1 – Kreutzwiesner-Import

176-seitiges PDF mit Quellen, Karten und Abbildungen in JSON übertragen. Separates Admin-Modul gleicht vor dem Import den aktuellen Bestand ab. Namensgleichstände sind zuzuordnen; bestehende Vorzugsangaben bleiben erhalten. Vollständiger Import in einer Transaktion, mit Änderungsverlauf und Wiederholungsschutz.

## 1.6.0 – Fächer, Kreis, Sanduhr und Ahnentafel

- Neue SVG-Diagramme mit sechs Generationen, Zoom, direkten Personenlinks und Grafikexport.
- Sanduhr mit Vorfahren und Nachkommen; Ahnentafel mit neutralen Pfadnummern bis acht Generationen.
- Mehrfache Vorfahren, fehlende Elternpositionen, Unsicherheit und Zyklusbegrenzung sichtbar.
- Direkter Einstieg aus der bestehenden Stammbaumansicht.

## 1.5.0 – Forschungsmodule

- Modulverwaltung, Familienexplorer, Recherche & Datenprüfung, Quellen-/Fundstellenansicht, Chronik und Jahrestage.

## 1.4.8 – Geburtsnamen und Stammbaum

- Gespeicherte Geburtsnamen erscheinen direkt auf Stammbaumkarten und Personenlisten, unabhängig vom Geburtsort.
- Eltern-Kind-Verbindungen werden ohne Pfeilspitzen dargestellt; Belegstatus und Familienzweige bleiben erhalten.
- Geburtsnamen können als Ergänzung zur Admin-Freigabe eingereicht werden und erscheinen auch in freigegebenen Leseansichten.

## 1.4.7 – Einladungsmails

- Einladungsmails enthalten eine Text- und HTML-Version mit anklickbarem Einladungsbutton.
- UTF-8-Inhalte werden für den Mailtransport Base64-kodiert; MIME-Struktur und Zeilenumbrüche vereinheitlicht.
- Mailtests prüfen beide dekodierten Nachrichtenteile und den vollständigen Einladungslink.

## 1.4.6 – Benutzer und Einladungen

- Admins können aktive Mitglieder oder weitere Admins direkt anlegen.
- Einladung per E-Mail mit einmaligem Link, eigenem Passwort und sieben Tagen Gültigkeit.
- Offene Einladungen anzeigen und widerrufen; Versandprobleme werden mit kopierbarem Link angezeigt.

# 1.4.5 – Familienzweige statt Liniengewirr

- Eltern mit identischer Zuordnung werden in einem gemeinsamen Familienzweig mit Kinderlinie zusammengefasst.
- Geschwister und ihre Partner werden nach ihrer Herkunft angeordnet, statt alphabetisch über die ganze Generation verteilt.
- Ein Pfeil pro Kind und mehr Abstand zwischen Generationen machen große Familien besser lesbar.
- Unterschiedliche Elternpaare und unterschiedliche Belegstände erhalten getrennte Zweige.

# 1.4.4 – Eindeutige Stammbaumlinien

- Grüne Eltern-Kind-Verbindungen erhalten Pfeilspitzen am tatsächlichen Kind und getrennte Anschlusspunkte.
- Linien über mehrere Generationen werden außen geführt, damit sie keine fremden Personenkarten durchlaufen.
- Partnerlinien verbinden die Kartenränder; weiter entfernte Partner werden oberhalb ihrer Karten verbunden.
- Belegstatus und gespeicherte Familienverbindungen bleiben unverändert.

# 1.4.3 – Anmeldung ohne Zugangsdaten im Link

- Anmeldung, Registrierung und Einrichtung verwenden ausdrücklich POST, auch wenn JavaScript ausfällt.
- Zugangsdaten aus alten URL-Parametern werden entfernt; Loginfelder werden nicht durch die App vorbelegt.
- Unter Mein Konto kann das eigene Passwort geändert werden; alle bisherigen Sitzungen dieses Kontos werden dabei widerrufen.

# 1.4.2 – Vorlage übernehmen und zügig bestätigen

- Eindeutige Elternschaft sowie Ehen und Partnerschaften aus der ursprünglichen PDF werden beim nächsten Öffnen als Admin automatisch als belegt übernommen.
- Ausdrücklich fragliche, individuell bewertete und zur Prüfung eingereichte Verbindungen bleiben ausgenommen.
- Einzelbestätigungen bleiben auf der Personenseite; rote Felder zeigen die wartende Freigabe.
- Nach Freigabe verschwindet das Bestätigungsfeld; offene Anträge verhindern doppelte Einreichungen.

# 1.4.1 – Prüfliste aufräumen

- Die Prüfliste zeigt nur noch offene Vorschläge.
- Freigegebene und abgelehnte Fälle verschwinden nach Freigabe oder Aktualisieren aus der Prüfliste; gespeicherte Vorschläge und Änderungsverlauf bleiben erhalten.

# 1.4.0 – Familienverbindungen prüfen

- Belegstatus bestehender Eltern-Kind-Verbindungen und Partnerschaften direkt bei der Person prüfen.
- Belegt oder ausdrücklich ungeklärt mit Quelle einreichen; Übernahme erst nach Admin-Freigabe.
- Sammelprüfung eindeutiger Elternschaft aus der ursprünglichen Vorlage; sieben ausdrücklich fragliche Verbindungen bleiben ausgenommen.
- Unbekannte Namen und biologische Einordnung werden getrennt vom Belegstatus geführt.

# Ahnenarchiv – Patch-Historie

Bisherige Entwicklungsstände rückwirkend nummeriert. Neuester Stand zuerst.

## 1.3.2 – 2026-10-09 – Belegte Familienverbindungen

- Durchgezogene Linien kennzeichnen belegte Elternschaft unabhängig von der biologischen Einordnung.
- Die vier ausdrücklich bestätigten Verbindungen in der direkten Familienlinie können unter Benutzer zur Freigabe eingereicht werden.
- Andere ungeklärte Verbindungen bleiben gestrichelt; Änderungen werden protokolliert.

## 1.3.1 – 2026-10-09 – Porträtzuordnungen korrigieren

- Korrektur dreier vertauschter Porträtzuordnungen aus dem Erstimport vorbereitet.
- Admins können die Korrektur unter Benutzer zur Prüfung anlegen und mit Bildvorschau in der Prüfliste freigeben.
- Personenanhänge und Bildzuordnungen werden gemeinsam korrigiert; zwischenzeitliche Änderungen verhindern die Übernahme.

## 1.3.0 – 2026-10-09 – Version & Patch-Historie

- Versionshinweis auf der Anmeldeseite, im Archiv und in der Leseansicht.
- Klick auf die Version öffnet die Patch-Historie mit Datum und Änderungen.
- Versionsanzeige bleibt auch am Handy sichtbar.
- Neue Versionsnummern in den Dateiadressen sorgen dafür, dass der Browser aktualisierte Dateien lädt.

## 1.2.0 – 2026-10-09 – Neue Familienlinien importieren

- JSON- und GEDCOM-Import mit bearbeitbarem JSON-Entwurf und Personenzuordnung.
- Mögliche Dubletten und widersprüchliche Angaben werden zur Prüfung angezeigt.
- Neue Linien werden erst nach Admin-Freigabe gemeinsam übernommen; Fehler verhindern die gesamte Übernahme.
- Originaldateien bleiben als Quellen erhalten.
- Optionale PDF-/PNG-/JPG-Erkennung über OpenAI: eigener API-Schlüssel und ausdrückliche Übertragungsbestätigung erforderlich.

## 1.1.0 – 2026-10-09 – Bilder direkt im Archiv ansehen

- Personenbilder öffnen in einem Popup auf derselben Seite.
- Sanfte Vergrößerung beim Öffnen; Bildklick schaltet die Originalgröße ein oder aus.
- Schließen per Escape, Schließen-Taste oder Klick neben das Popup.

## 1.0.0 – 2026-10-09 – PHP-Version für netcup

- Online-Archiv für PHP und MySQL auf netcup-Webhosting eingerichtet.
- Personensuche, Familienverbindungen und schematischer Stammbaum.
- Registrierung, Anmeldung und Admin-Verwaltung.
- Ergänzungen und Bilder werden vor der Übernahme durch einen Admin geprüft.
- Teilbare Leselinks mit einstellbarer Sichtbarkeit und Widerruf.
- Änderungsverlauf, Export und Schnittstelle für den lokalen Abgleich.
