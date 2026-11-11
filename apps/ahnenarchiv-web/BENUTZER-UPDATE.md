# Update 1.4.7

ZIP in stammbaum-huschka.de/httpdocs entpacken und Dateien überschreiben. Anschließend Strg+F5. Enthält die vorherigen Updates. config.php und bestehende Daten bleiben erhalten; die Einladungstabelle wird beim ersten Aufruf automatisch angelegt. Keine Neueinrichtung ausführen.

Unter Benutzer können Admins sofort aktive Mitglieder oder Admins erstellen oder per E-Mail einladen. Einladungslinks gelten sieben Tage, sind einmalig und können widerrufen werden. Der Empfänger setzt sein Passwort selbst. Erneute Einladung derselben E-Mail widerruft den alten Link. Bestehende Konten werden nicht überschrieben.

Versand erfolgt über PHP mail() des Webhostings. In config.php bei Bedarf hinzufügen:

```php
'mail_from' => 'deine-vorhandene-adresse@stammbaum-huschka.de',
'invite_mail_enabled' => true,
```

Eine tatsächlich eingerichtete Absenderadresse auf der Domain verwenden. Ohne Konfiguration wird noreply@stammbaum-huschka.de verwendet. Meldung „an Mailserver übergeben“ bestätigt die Annahme, nicht die Zustellung. Spamordner prüfen. Falls Versand scheitert, zeigt die App den kopierbaren Link. Der Link wird nur einmal angezeigt und serverseitig nur gehasht gespeichert.

Direkt angelegte Nutzer können ihr Startpasswort unter Mein Konto ändern. Einladungen gewähren die vom Admin ausgewählte Rolle ohne zusätzliche Freigabe. Alle Kontovorgänge werden ohne Passwörter oder Einladungstokens protokolliert.

1.4.7: Mailformat mit Text- und HTML-Version korrigiert. Nach Upload eine neue Einladung für denselben Empfänger senden; der alte Link wird dabei widerrufen. Bereits versandte Mails ändern sich nicht.
