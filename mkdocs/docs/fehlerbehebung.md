# Fehlerbehebung

ZilpZalp macht Fehler sichtbar, **ohne** eine fachliche Historie aufzubauen. Es gibt
drei Fehlerarten.

## Unlesbares / leeres PDF

Enthält ein PDF keinen Text (z. B. ein reiner Scan ohne Textebene — **kein OCR im MVP**)
oder ist es korrupt, verschiebt ZilpZalp die Datei in den `error/`-Ordner und markiert
den Queue-Eintrag als `error` mit Kurzgrund.

Der `error/`-Ordner ist die **einzige dauerhafte Fehlerspur** — eine Datei am Rand des
Workflows, kein Protokoll. Prüfe die Datei, behandle sie außerhalb von ZilpZalp und
lege sie ggf. korrigiert erneut in den Watchfolder.

## Technischer Laufzeitfehler

Schlägt z. B. das Kopieren fehl (Zielpfad weg, fehlende Schreibrechte), erscheint der
Fehler **transient** am Queue-Eintrag und wird zusätzlich in die Container-Logs
geschrieben:

```bash
docker compose logs -f backend
```

Transiente Fehler verschwinden bei Neustart/Rescan, da der Zustand neu aus dem
Watchfolder abgeleitet wird.

## Konfigurationsfehler

- **Beim Start:** Ist `config.yaml` ungültig oder fehlt ein Pflichtpfad, startet der
  Backend-Container nicht. Die Ursache steht in den Logs:

    ```bash
    docker compose logs backend
    ```

- **Zur Laufzeit (Änderung in der Oberfläche):** Ungültige Eingaben werden mit
  Validierungsfehler abgewiesen; die bisherige Konfiguration bleibt aktiv.

## Container-Diagnose

```bash
docker compose ps                       # laufen beide Container?
curl -fsS http://localhost:8000/health  # Backend gesund? -> {"status":"ok"}
docker compose logs -f backend          # Live-Logs des Backends
docker compose logs -f docs             # Live-Logs der Doku-Site
```

## Dateien werden nicht erkannt

- Liegt das PDF wirklich im gemounteten Watchfolder (`./data/inbox` → `/data/inbox`)?
- Auf WSL2/Windows: liegt der Ordner auf einem **nativen Linux-Pfad**? Auf `/mnt/c/…`
  sind Dateisystem-Events unzuverlässig.
- Ein Neustart (`docker compose restart backend`) erzwingt einen initialen Scan.

!!! note "Logs sind Betriebsdaten, keine Dokumenthistorie"
    Die Container-Logs (stdout) dienen Betrieb und Debugging. Sie sind bewusst **keine**
    produktseitige Historie der verarbeiteten Dokumente.
