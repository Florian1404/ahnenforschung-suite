# Ahnenarchiv 2.1.2 – Import über d’Aboville-IDs

Dieses kumulative Update ersetzt die Importpakete 2.1.0 und 2.1.1. Im Plesk-Dateimanager in `stammbaum-huschka.de/httpdocs` entpacken, enthaltene Programmdateien überschreiben und die Webseite neu laden. Der Dokumentenstamm bleibt `httpdocs/public`.

1. In der Patch-Historie Version **2.1.2** prüfen.
2. Unter **Linienimport** die neue `stammbaum-boeck-schiessl-daboville.json` einlesen. **Dieselbe Kennung wie beim bisherigen Import** verwenden, z. B. `bock-schiessl`, wenn diese Kennung bereits verwendet wurde. Bereits zur Freigabe eingereichte alte Entwürfe verwerfen und neu einlesen. Bereits freigegebene Importe bleiben bestehen.
3. Die offenen Fälle prüfen. Erkannte Zuordnungen sind auf Wunsch einblendbar. Eindeutige nummerierte Neuzugänge können gemeinsam vorgemerkt werden. Die Freigabe bleibt ein eigener Schritt.

Die Identität im Import besteht aus **Nummernkreis und Nummer**. Ein Nummernkreis bezeichnet eine konkrete Stammtafel bzw. einen Ausschnitt mit eigener Nummerierung, nicht nur einen Nachnamen. Derselbe Mensch kann mehrere belegte Nummern aus verschiedenen Nummernkreisen haben. Die bestehende interne Profil-ID bleibt bei Zuordnungen erhalten. Bei einer Neuanlage mit Nummer wird die Profil-ID aus Quellenkennung und Nummernschlüssel abgeleitet. Die bisherigen JSON-IDs bleiben als Verweise für Familien, Verbindungen und ältere Importe erhalten. Bloße Namensähnlichkeit löst keine automatische Zuordnung aus.

Beispiele aus der Böck-Tafel auf Seite 7: Johann Georg (`1-M`), Georg 1871 (`1.1-M`), Georg 1921 (`1.1.1-M`). Die beiden mit `1-M` beschrifteten Personen Anton Schießl und Andreas März auf Seite 5 gehören zu getrennten Nummernkreisen. Die JSON enthält geprüfte Nummernkreise für 98 der 101 Personen. Drei ohne belegte Nummer behalten ihre Quell-ID.

Fehlt im Altbestand die Nummer, kann ein eindeutiger Treffer über Name und vollständiges Geburtsdatum erkannt werden. Ein passendes belegtes Taufdatum am selben Ort ist für einen Altbestandseintrag möglich, ohne die Datumsfelder gleichzusetzen oder zu überschreiben. Bei Georg 1921 zeigt die Importquelle den **12.01.1921**, während im gezeigten Bestand der **21.01.1921** steht. Ohne weiteren eindeutigen Anker ist diese Zuordnung offen; ein abweichendes bestehendes Datum wird bei einer Zuordnung nicht stillschweigend ersetzt.

Neue JSON-Quellen können pro Person ein Feld wie dieses verwenden:

```json
"daboville_ids": [
  {"kreis": "boeck-2021-s7", "nummer": "1.1-M"}
]
```

Nummernkreis und Nummer bei Folgeimporten beibehalten. Identische Nummern im selben Nummernkreis bei verschiedenen Personen müssen vor der Freigabe geklärt werden. Für Familien und Verbindungen weiterhin explizite JSON-IDs angeben.
