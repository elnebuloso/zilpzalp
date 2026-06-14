# Design: Health-Endpunkte für Kubernetes-Probes

**Status:** abgenommen · **Datum:** 2026-06-14

## Ziel

Drei dedizierte HTTP-Endpunkte bereitstellen, die `startupProbe`,
`readinessProbe` und `livenessProbe` eines Kubernetes-Deployments bedienen.
Die Endpunkte spiegeln den echten internen Komponenten-Zustand wider, sind also
keine drei Aliase für „Prozess antwortet". Ergänzt die geplanten Backlog-Punkte
**Helm Chart** und **CI-Pipeline** fürs Container-Deployment.

## Semantik der Probes

| Endpunkt | Frage | 200 wenn alles wahr | k8s-Konsequenz bei 503 |
|---|---|---|---|
| `GET /healthz/startup` | „Hochfahren fertig?" | `startup_done` | wartet weiter, **kein** Kill |
| `GET /healthz/ready` | „Bereit für Verkehr?" | `startup_done` **und** Worker-Thread lebt **und** Watcher-Observer lebt | Pod aus Service genommen (**kein** Restart) |
| `GET /healthz/live` | „Neustart nötig?" | Worker-Thread lebt **und** Watcher-Observer lebt | Pod-**Restart** |

Jeder Endpunkt ist eine eigene Bool-Kombination der Signale
`startup_done` und `threads_alive` — drei inhaltlich unterscheidbare Checks.

### Antwortformat

- **Gesund:** `200` mit Body `{"status": "ok"}`.
- **Ungesund:** `503` mit Body `{"status": "unavailable", "checks": {...}}`,
  wobei `checks` die einzelnen Bool-Werte des jeweiligen Endpunkts enthält
  (z. B. `{"worker": false, "watcher": true}`), damit beim Debuggen sichtbar
  ist, welcher Check rot ist.

## Signal-Quellen

- **`startup_done`** — neues Flag `app.state.started`. Initial `False`, am Ende
  der Lifespan-Startup-Phase (nach `watcher.start()`) auf `True` gesetzt.
- **`worker.is_alive()`** — neue Public-Methode auf `Worker`, gibt
  `self._thread.is_alive()` zurück.
- **`watcher.is_alive()`** — neue Public-Methode auf `Watcher`, gibt
  `self._observer.is_alive()` zurück (die Logik existiert intern bereits in
  `Watcher.stop()`).

Begründung Worker-Thread als Liveness-Signal: Der Worker fängt
Verarbeitungsfehler bewusst ab (`except Exception` in `worker.py`), damit der
Thread nicht an einzelnen Dokumenten stirbt. Ein dennoch toter Worker-Thread ist
deshalb ein echter Defekt, bei dem ein Pod-Restart die korrekte Reaktion ist.

## Code-Struktur

- **Neues Modul** `backend/src/zilpzalp/web/health.py` mit eigenem `APIRouter`.
  Die Handler lesen `app.state` über das `Request`-Objekt
  (`request.app.state.started`, `.worker`, `.watcher`).
- **`main.py`**: `app.include_router(health_router)`; Flag `app.state.started`
  in der Lifespan setzen; das bestehende `GET /health` **entfernen**.
- **`worker.py`**: Public-Methode `is_alive()` ergänzen.
- **`watcher.py`**: Public-Methode `is_alive()` ergänzen.

## Bestehendes `/health` & Docker

- `GET /health` wird **ersatzlos entfernt** (kein Alias).
- Docker-`HEALTHCHECK` in `Dockerfile.backend` zeigt künftig auf
  `/healthz/live` statt `/health`.
- Doku-Referenzen auf `/health` in `mkdocs/docs/installation.md` und
  `mkdocs/docs/fehlerbehebung.md` werden auf `/healthz/live` aktualisiert.

## Tests

Neues `backend/tests/test_health.py`:

- Happy-Path: `/healthz/startup`, `/healthz/ready`, `/healthz/live` liefern je
  `200` und `{"status": "ok"}` (innerhalb `with TestClient(app)`, damit die
  Lifespan-Startup-Phase durchläuft).
- Worker tot: `worker.is_alive` per Monkeypatch auf `False` →
  `/healthz/ready` und `/healthz/live` liefern `503`, `/healthz/startup`
  bleibt `200`.
- Watcher tot: `watcher.is_alive` per Monkeypatch auf `False` → analog `503`
  bei `ready`/`live`, `startup` bleibt `200`.

Bestehender Test `test_health_with_valid_config` in `test_main.py` entfällt
(prüft das entfernte `/health`).

## Nicht im Scope

- Helm-Chart-Werte und CI-Pipeline (eigene Backlog-Punkte).
- Tiefe Abhängigkeits-Checks (Disk-Space, Watchfolder erreichbar, JVM-Health) —
  bewusst weggelassen (YAGNI); die Probes prüfen ausschließlich den
  Prozess-internen Thread-/Startup-Zustand.
