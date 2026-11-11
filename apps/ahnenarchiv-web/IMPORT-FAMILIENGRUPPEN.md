# Ahnenarchiv 2.1.3 – Import bei mehreren Familiengruppen

Dieses kumulative Update enthält die bisherigen Importkorrekturen. Das ZIP in Plesk unter `stammbaum-huschka.de/httpdocs` entpacken, Programmdateien überschreiben und die Seite neu laden. Der Dokumentenstamm bleibt `httpdocs/public`.

Unter **Linienimport** den vorhandenen Entwurf wieder öffnen. Die JSON muss nicht neu eingelesen werden. Bereits zur Freigabe eingereichte ältere Entwürfe bei einem Versionskonflikt ablehnen und erneut prüfen.

Beim Übernehmen prüft Ahnenarchiv die vorhandenen Familiengruppen. Gibt es eine eindeutig passende Hochzeit, verwendet der Import diesen vorhandenen Eintrag. Bei mehreren möglichen Zuordnungen zeigt er die betroffenen Namen und Hochzeitsangaben. Wer fortfährt, übernimmt die übrigen geprüften Angaben. Für offene Familiengruppen wird keine Gruppe angelegt, ergänzt, zusammengelegt oder gelöscht. Bereits eindeutig zugeordnete Personen und ihre separat geprüften Verbindungen bleiben im Import enthalten.

An einer bestehenden Familiengruppe wird nach der Vorschau nur dann etwas gespeichert, wenn sie sich seit der Prüfung nicht geändert hat. Die bestehende JSON und die Quellenkennung können weiterverwendet werden.
