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
mountet standardmäßig den mitgelieferten `demo/`-Ordner (relativ zum Repo-Root):

| Host-Ordner | Container-Pfad | Zweck |
|---|---|---|
| `./demo/config` | `/config` | enthält `config.yaml` (einzige dauerhafte Einstellung) |
| `./demo/data/inbox` | `/data/inbox` | **Watchfolder** — hier landen neue PDFs |
| `./demo/data/error` | `/data/error` | unlesbare/fehlerhafte PDFs |
| `./demo/data/processed` | `/data/processed` | verarbeitete Originale (bei `original_handling: move`) |
| `./demo/targets` | `/targets` | Zielordner für die abgelegten Dateien |

## Schnellstart (Demo)

Der `demo/`-Ordner ist startklar und enthält bereits eine Beispiel-Rechnung in der
Inbox. Einfach bauen und starten:

```bash
docker compose up -d --build
```

Dann aufrufen:

- Weboberfläche: <http://localhost:8000> — die Beispiel-Rechnung erscheint sofort in der Queue
- Diese Dokumentation: <http://localhost:8001>

Status prüfen:

```bash
docker compose ps
curl -fsS http://localhost:8000/health
```

Erwartet: `{"status":"ok"}`.

## Eigene Dokumente / Echtbetrieb

Für den Echtbetrieb passt du die Demo an deine Bedürfnisse an:

1. **Konfiguration anpassen:** [`demo/config/config.yaml`](https://github.com/elnebuloso/zilpzalp/blob/main/demo/config/config.yaml)
   editieren (Ziele, Regeln, Namensmuster). Die Pfade darin sind **Container-Pfade**
   (`/data/inbox`, `/targets/finanzen`, …), nicht Host-Pfade — Details in der
   [Konfiguration](konfiguration.md).

2. **PDFs ablegen:** eigene Dateien in `demo/data/inbox` legen.

3. **Optional eigene Ordner:** Statt `demo/` kannst du in `docker-compose.yml` beliebige
   Host-Pfade auf dieselben Container-Pfade mounten.

## Stoppen / Aktualisieren

```bash
docker compose down          # stoppt beide Container
docker compose up -d --build # nach Änderungen neu bauen und starten
```

!!! note "Startverhalten"
    Beim Start scannt ZilpZalp den Watchfolder einmalig und nimmt danach neue Dateien
    live über Dateisystem-Events auf. Ein unbestätigtes PDF taucht nach einem Neustart
    wieder in der Queue auf — der Watchfolder ist die Quelle der Wahrheit.
