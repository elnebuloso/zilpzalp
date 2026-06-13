# zilpzalp

Self-hosted PDF renamer with a human in the loop. Zilpzalp watches a folder, reads incoming PDFs, and suggests clean filenames from date, sender and document type — you review, confirm, done. Docker, local, no cloud.

## Entwicklung: nächsten Meilenstein bearbeiten

Jeder Meilenstein wird in einer frischen Session geplant und umgesetzt (Tracking: [docs/roadmap.md](docs/roadmap.md)). Kopierfertiger Prompt — er erkennt den nächsten Meilenstein selbst, nichts manuell ausfüllen:

```
Schreibe den Implementierungsplan für den nächsten offenen Meilenstein aus docs/roadmap.md.

Lies zuerst docs/roadmap.md und bestimme den nächsten Meilenstein (oberste Zeile mit
Status 📋). Entnimm ihm Name, Scope und die referenzierten §§. Lies die Architektur-Referenz
docs/superpowers/specs/2026-06-13-1435-zilpzalp-mvp-design.md (die genannten §§) sowie den
bereits vorhandenen Code unter backend/src/zilpzalp/, auf dem der Meilenstein aufbaut.

Nutze das superpowers:writing-plans Skill. Bite-sized TDD-Tasks, exakte Pfade, vollständiger
Code/Tests in jedem Schritt. Tech: Python + FastAPI, uv, pytest, src-Layout unter
backend/src/zilpzalp/. Halte dich strikt an den Scope der Roadmap-Zeile und schließe alles
aus, was laut Roadmap erst spätere Meilensteine liefern — frag nach, wenn der Scope unklar ist.

Plan speichern als docs/superpowers/plans/YYYY-MM-DD-HHMM-<kurzname>.md, dann die betreffende
Meilenstein-Zeile in docs/roadmap.md aktualisieren (Plan-Link, Status 📝). Committen.
Vor jedem push fragen.
```
