# Ahnenarchiv 2.1.5 — Ereignisse bearbeiten und einzeln löschen

## Installation auf netcup

1. **Vorher Sicherung anlegen:** MySQL/MariaDB-Datenbank und die aktuelle PHP-Installation sichern. Beim Upload vorhandene Datenbank und Mediendateien nicht ersetzen.
2. Das Paket entpacken und die enthaltenen Verzeichnisse `private/` und `public/` in die jeweilige bestehende Ahnenarchiv-Installation kopieren, mit gleicher Ordnerstruktur. Andere Dateien werden nicht benötigt.
3. Browser neu laden (ggf. Strg+F5); die Asset-Version lautet 2.1.5.
4. Mit einem Administratorkonto eine Person öffnen.

## Neue Funktionen

- Datum und Ort für **Geburt, Taufe, Tod und Bestattung** können getrennt bearbeitet oder gelöscht werden. Außerdem gibt es „Gesamtes Ereignis löschen“.
- **Hochzeiten** erscheinen einmal pro Datum/Ort; bei identischen Hochzeiten aus mehreren Familiengruppen erscheint eine entsprechende Warnung. Datum, Ort oder das gesamte Hochzeitsereignis können einzeln korrigiert/gelöscht werden.
- Jede Aktion benötigt ein **separates Dialogfenster**, eine Server-Vorschau der betroffenen Datenbankeinträge und eine ausdrückliche Bestätigung durch Eingabe von `ÄNDERN` bzw. `LÖSCHEN`.
- **Rekursive Spiegelbereinigung:** Bearbeitete/gelöschte Hochzeitsangaben werden bei exakt übereinstimmendem Datum/Ort innerhalb derselben beteiligten Familien-/Personendatensätze synchron angepasst. Es werden **niemals Partner-, Eltern-Kind-Beziehungen, Familien oder Personen rekursiv gelöscht**. Die Vorschau zeigt sämtliche veränderten Datensätze an.
- Ein Admin kann Ereignisänderungen über „Ereignisänderungen / Rückgängig“ wiederherstellen, solange der Datensatz seitdem unverändert geblieben ist.

## Wichtiger Hinweis zur doppelten Hochzeit bei Maria Anna Böck

Die beiden angezeigten Ehen 08.02.1869 / Ludenhausen werden im Export durch **zwei Familiengruppen mit verschiedenen Georg-Böck-Personen-IDs** verursacht. Version 2.1.5 zeigt sie nur einmal mit einer **Dublettwarnung**, um die Ansicht übersichtlich zu machen. Die Dublette selbst wird nicht automatisch aufgelöst. Bitte **Georg Böck (1835) und Johann Georg Böck (1835) über die Personen-Zusammenführung** aus 2.1.4 kontrolliert vereinigen. **Nicht die historisch richtige Hochzeit löschen, nur weil sie zweimal angezeigt wurde!**

## Datenschutz / Betrieb

Das ZIP enthält **nur Quellcode und diese Anleitung**, keine Datenbank, Nutzerdaten, Fotos, Passwörter oder Konfigurationswerte. Der Eingriff erfolgt ausschließlich durch angemeldete Administratoren; serverseitige Berechtigungsprüfung und Versionierungsabgleich sind enthalten.

## Prüfung

- PHP-Syntaxprüfung und JavaScript-Syntaxprüfung: bestanden.
- Anzeige mit echtem Böck-JSON-Export: eine Ehe mit Hinweis auf die zwei Familiengruppen.
- PHP-Logik mit simuliertem Datenbankbestand: Hochzeitsdatum und -ort werden in gespiegelten Einträgen konsistent geändert/entfernt, Eltern-Kind-Listen bleiben erhalten; ungültiges Datum wird abgewiesen.
- **Kein Live-Test auf dem netcup-Server durchgeführt.** Vor produktivem Einsatz Sicherung anlegen.
