# Update 1.4.3

ZIP unter stammbaum-huschka.de/httpdocs entpacken, überschreiben, Strg+F5. config.php bleibt erhalten. Auch public/index.php und setup.html werden aktualisiert. Alle bisherigen Änderungen sind enthalten.

Nur den Link https://stammbaum-huschka.de/ teilen, ohne Parameter oder Zugangsdaten. Neue Nutzer registrieren ihr eigenes Konto.

Anmelde-, Registrierungs- und Einrichtungsformulare verwenden explizit POST. Ein JavaScript-Ausfall darf keine Zugangsdaten als URL-Parameter übertragen. Alte Parameter auf Start-/Einrichtungsseite werden entfernt und nicht zur Anmeldung verwendet. Bereits geteilte Links, Browserhistorien oder Serverprotokolle können dadurch nicht rückwirkend bereinigt werden.

Wenn das Passwort bereits in einem Link stand: Einloggen → Mein Konto → Passwort ändern. Dabei werden alle bestehenden Sitzungen des Kontos beendet. Anschließend mit neuem Passwort anmelden. Browser/Passwortmanager können unabhängig von der App gespeicherte Zugangsdaten ausfüllen. Die App trägt selbst keine Zugangsdaten ein.
