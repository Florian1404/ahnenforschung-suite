# Versionsablauf ab jetzt

1. **Änderung als Git-Issue** formulieren (Fehler, Feature, Importfehler, Schrifttranskription).
2. **Branch pro Änderung**: `git switch -c fix/personen-suche-xyz`.
3. Nur Quellcode ändern, Tests ausführen, `git diff` prüfen, committen.
4. Im eigenen Staging testen; bei Änderung der Server-App anschließend separat deployen.
5. **Versionsnummer der jeweiligen Komponente** erhöhen und taggen (`matricula-v5.3` oder `ahnenarchiv-web-v2.1.6`).
6. Ergebnis und Quellen in `VERSIONEN.md` und `docs/FUNDSTELLEN.md` dokumentieren; private Familienakten bleiben außerhalb von Git.

**Nie wieder** eine Datei nur als `final-final-neu2.py` verwalten. Git speichert die Entwicklung.
