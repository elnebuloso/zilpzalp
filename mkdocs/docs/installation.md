# Installation

ZilpZalp wird als zwei Container betrieben: das **Backend** (Weboberfläche +
Verarbeitung) und die **Doku-Site** (diese Dokumentation). Beide werden über
`docker-compose.yml` gestartet.

## Voraussetzungen

- Docker und Docker Compose v2
- Ein Linux-Host (oder WSL2). **Hinweis:** Auf gemounteten Windows-Pfaden (`/mnt/c/…`)
  sind Dateisystem-Events unzuverlässig — lege Watchfolder/Zielordner auf native
  Linux-Pfade.

## Ordner und Volumes

ZilpZalp arbeitet ausschließlich über gemountete Verzeichnisse. Das Compose-Setup
erwartet relativ zum Repo-Root:

| Host-Ordner | Container-Pfad | Zweck |
|---|---|---|
| `./config` | `/config` | enthält `config.yaml` (einzige dauerhafte Einstellung) |
| `./data/inbox` | `/data/inbox` | **Watchfolder** — hier landen neue PDFs |
| `./data/error` | `/data/error` | unlesbare/fehlerhafte PDFs |
| `./data/processed` | `/data/processed` | verarbeitete Originale (bei `original_handling: move`) |
| `./targets` | `/targets` | Zielordner für die abgelegten Dateien |

## Schritt für Schritt

1. **Ordner und Konfiguration anlegen:**

    ```bash
    mkdir -p config data/inbox data/error data/processed targets/finanzen
    cp backend/config.example.yaml config/config.yaml
    ```

2. **`config/config.yaml` anpassen.** Die Pfade darin sind **Container-Pfade**
   (`/data/inbox`, `/targets/finanzen`, …), nicht Host-Pfade. Details in der
   [Konfiguration](konfiguration.md).

3. **Container bauen und starten:**

    ```bash
    docker compose up -d --build
    ```

4. **Aufrufen:**
    - Weboberfläche: <http://localhost:8000>
    - Diese Dokumentation: <http://localhost:8001>

5. **Status prüfen:**

    ```bash
    docker compose ps
    curl -fsS http://localhost:8000/health
    ```

    Erwartet: `{"status":"ok"}`.

## Stoppen / Aktualisieren

```bash
docker compose down          # stoppt beide Container
docker compose up -d --build # nach Änderungen neu bauen und starten
```

!!! note "Startverhalten"
    Beim Start scannt ZilpZalp den Watchfolder einmalig und nimmt danach neue Dateien
    live über Dateisystem-Events auf. Ein unbestätigtes PDF taucht nach einem Neustart
    wieder in der Queue auf — der Watchfolder ist die Quelle der Wahrheit.
