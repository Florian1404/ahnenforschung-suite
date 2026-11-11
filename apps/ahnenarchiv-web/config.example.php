<?php
return [
    'base_url' => 'https://stammbaum-huschka.de',
    // Exakten Datenbankserver aus dem netcup-Panel eintragen (nicht raten).
    'dsn' => 'mysql:host=DATENBANKSERVER;port=3306;dbname=DATENBANKNAME;charset=utf8mb4',
    'db_user' => 'DATENBANKBENUTZER',
    'db_password' => 'HIER-DATENBANKPASSWORT',
    // Vor dem ersten Aufruf durch mindestens 32 zufällige Zeichen ersetzen.
    'setup_key' => 'HIER-EINEN-LANGEN-ZUFAELLIGEN-SCHLUESSEL-EINTRAGEN',
    'max_upload_bytes' => 8 * 1024 * 1024,
    'require_https' => true,
    // Für Einladungen: vorhandene Absenderadresse dieser Domain verwenden.
    'mail_from' => 'noreply@stammbaum-huschka.de',
    'invite_mail_enabled' => true,
    // Optional: bezahlte PDF-/Bilderkennung. Schlüssel nur hier auf dem Server speichern.
    'import_ocr_api_key' => '',
    'import_ocr_model' => 'gpt-4.1',
];
