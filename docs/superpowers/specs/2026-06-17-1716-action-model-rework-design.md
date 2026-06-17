# Aktionsmodell-Überarbeitung — Design

Status: abgenommen · Datum: 2026-06-17

Adressiert Backlog-Idee „Aktionsmodell überarbeiten — Skip ≠ Löschen, eigener
Entfernen-Button" und führt die Trennung der Original-Disposition in zwei
Einstellungen ein.

## Problem

Heute disponiert `_dispose()` ([processor.py](../../../backend/src/zilpzalp/processor.py))
das Inbox-Original für **zwei** verschiedene Wege identisch: beim Bestätigen
(Ablegen) **und** beim Überspringen — beides per `config.original_handling`.
Daraus folgen zwei Schwächen:

1. **Überspringen löscht.** Der „Überspringen"-Button in der Queue-Liste
   ([_queue_list.html](../../../backend/src/zilpzalp/web/templates/_queue_list.html))
   und in der Review ([review.html](../../../backend/src/zilpzalp/web/templates/review.html))
   wirft das Original weg (bei `delete` unwiderruflich). „Weiterblättern" und
   „wegwerfen" sind dieselbe Aktion — gefährlich und unintuitiv.
2. **Eine Einstellung für zwei Situationen.** Nach dem Ablegen existiert das
   Original doppelt (Kopie liegt in den Zielordnern) → `delete` ist verlustfrei.
   Beim bewussten Wegwerfen existiert **keine** Kopie → `trash` ist das sichere
   Verhalten. Ein einzelnes Flag kann die sinnvolle Asymmetrie
   („nach Ablegen löschen, beim Entfernen in den Papierkorb") nicht ausdrücken.

Die Übersicht ([_overview.html](../../../backend/src/zilpzalp/web/templates/_overview.html))
hat zudem gar keine Entfernen-Aktion.

## Zielbild: drei getrennte Aktionen

| Aktion | Orte | Dateiwirkung am Original | Navigation danach |
|---|---|---|---|
| **Bestätigen** | Review | kopiert in Ziele, dann Disposition per `when_filed` | nächstes bereites Dokument, sonst `/` |
| **Überspringen** | Review | **keine** | nächstes bereites Dokument **nach** dem aktuellen, sonst `/` |
| **Entfernen** | Queue · Übersicht · Review | Disposition per `when_removed` | Review → nächstes/`/`; Liste → bleibt auf der Liste |

Überspringen wird damit rein navigatorisch; das Dokument bleibt unangetastet in
der Warteschlange (Status bleibt `ready`).

## 1. Config: `originals`-Gruppe ersetzt `original_handling`

`original_handling` entfällt. Neu, verschachtelt:

```yaml
originals:
  when_filed: delete    # delete | trash — Original nach erfolgreichem Ablegen
  when_removed: trash   # delete | trash — Original beim bewussten Entfernen
```

In [config.py](../../../backend/src/zilpzalp/config.py):

```python
class Originals(BaseModel):
    when_filed: Literal["delete", "trash"]
    when_removed: Literal["delete", "trash"]

class Config(BaseModel):
    ...
    originals: Originals
    # original_handling entfällt
```

Beide Felder sind Pflicht. **Breaking Change** (bewusst, Projekt bleibt auf
Major 1): bestehende `config.yaml` mit `original_handling` und ohne `originals`
schlägt mit `ConfigError` fehl. Migrationsnotiz im
[CHANGELOG](../../../backend/CHANGELOG.md).

Mitzuziehen:
- [config.default.yaml](../../../backend/config.default.yaml) und
  [config.example.yaml](../../../backend/config.example.yaml) auf `originals`
  umstellen (Default: `when_filed: delete`, `when_removed: trash`).

## 2. Processor

[processor.py](../../../backend/src/zilpzalp/processor.py):

- `_dispose(source, paths, mode)` — Modus (`"delete" | "trash"`) und Trash-Pfad
  werden **explizit** übergeben statt aus `config` gelesen. Unverändert: bei
  `trash` Verschieben nach `paths.trash` (mit `_unique_name`), bei `delete`
  `unlink(missing_ok=True)`.
- `process(...)` ruft `_dispose(source, config.paths, config.originals.when_filed)`.
- `skip(...)` **entfällt komplett** — Überspringen ist keine Dateioperation mehr.
- Neu: `remove(source, config)` → disponiert per `config.originals.when_removed`.
  **Tolerant**, wenn das Original nicht (mehr) im Watchfolder liegt (z. B.
  Error-Einträge, deren Datei bereits nach `error/` verschoben wurde): wenn
  `source` nicht existiert, keine Disposition, kein Fehler — es wird nur der
  Queue-Eintrag entfernt (siehe Routes). Rückgabe analog `ProcessResult`
  (`copied=[]`), `original_destination=None` bei `delete`/fehlend.

## 3. Routes

[web/routes.py](../../../backend/src/zilpzalp/web/routes.py):

**Helper.** `_next_ready_after(queue, current_id)` — liefert das erste `ready`,
reviewbare Dokument **nach** `current_id` in der bestehenden newest-first-Sortierung
(`_by_mtime_desc`). Keines danach → `None`. (Vorwärts-Sweep; verhindert das
Hin-und-her-Springen zwischen zwei `ready`-Einträgen.)

**Überspringen** — `POST /documents/{id}/skip`:
- Keine Datei-, Queue- oder Cache-Änderung.
- Ziel: `_next_ready_after(queue, id)`; keiner → `/` (Startseite, von dort kann
  man hochladen). Antwort: `HX-Redirect`. Kein Flash/Toast (stilles Blättern).

**Entfernen** — `POST /documents/{id}/remove?from=review|queue|overview`:
- `processor.remove(entry.path, config)`, dann `queue.remove(entry.path)` und
  `cache.remove(entry.path)`.
- Eintrag bereits weg (`entry is None`) → `HX-Redirect` passend zu `from`.
- Antwort nach `from`:
  - `review` → `_next_ready(queue)` (aktueller ist jetzt entfernt) bzw. `/`.
  - `queue` → `HX-Redirect /queue`.
  - `overview` → `HX-Redirect /`.
- `from` wird server-seitig auf die drei erlaubten Werte geprüft; unbekannt → `/`.
- Toast `toast.removed` (mit Dateiname) als Flash.

**Inline-Bestätigung** — `GET /documents/{id}/remove-control?from=…&confirm=0|1`:
- Liefert das Partial `_remove_control.html` im Idle- (`confirm=0`) bzw.
  Bestätigen-Zustand (`confirm=1`). Reiner UI-Toggle, keine Seiteneffekte.
- Eintrag weg → leeres/idle Partial (defensive; der Eintrag verschwindet beim
  nächsten Listen-Reload ohnehin).

**Bestätigen/Ablegen** — `confirm` / `execute` / `_execute`:
- `original_label` (Review + Summary) kommt künftig aus
  `config.originals.when_filed` statt `config.original_handling`.
- **Vereinheitlichung:** `_execute` springt bei „nichts mehr bereit" auf `/`
  statt bisher `/queue` (gleiche Upload-Logik wie beim Skip). Restliche
  Confirm-/Conflict-/Summary-Logik bleibt unverändert.

## 4. Inline-Bestätigung (htmx, kein JavaScript)

Statt `hx-confirm` (Browser-`confirm()`-Dialog) ein server-gerenderter
Zwei-Zustands-Toggle. Neues Partial
`backend/src/zilpzalp/web/templates/_remove_control.html` mit stabilem Wrapper:

```html
<span id="rm-{{ entry.id }}" class="rm-control">
  {% if confirm %}
    <span class="rm-hint">{{ t('confirm.remove', target=t('original.' ~ when_removed)) }}</span>
    <button class="btn sm danger"
            hx-post="/documents/{{ entry.id }}/remove?from={{ from }}">{{ t('action.yes') }}</button>
    <button class="btn sm ghost"
            hx-get="/documents/{{ entry.id }}/remove-control?from={{ from }}&confirm=0"
            hx-target="#rm-{{ entry.id }}" hx-swap="outerHTML">{{ t('action.no') }}</button>
  {% else %}
    <button class="btn sm ghost"
            hx-get="/documents/{{ entry.id }}/remove-control?from={{ from }}&confirm=1"
            hx-target="#rm-{{ entry.id }}" hx-swap="outerHTML">{{ t('action.remove') }}</button>
  {% endif %}
</span>
```

- Alle Swaps treffen `#rm-{id}` mit `outerHTML`; der Wrapper ist Teil des Partials.
- „Ja" postet das eigentliche Entfernen (→ `HX-Redirect`, Abschnitt 3).
- `when_removed` und `from` werden ins Partial gereicht, damit Hinweis und
  Ziel-Redirect stimmen. Der Kontext (`from`) wird beim Einbetten gesetzt.
- Verlässt der Nutzer den Bestätigen-Zustand ohne „Nein", bleibt er bis zum
  nächsten Reload bestehen — unkritisch.

Eine kleine danger-Button-Variante (`.btn.sm.danger`) im CSS ergänzen, falls noch
nicht vorhanden.

## 5. Templates

- **_queue_list.html**: „Überspringen"-Button entfernen; stattdessen
  `_remove_control.html` mit `from='queue'` (alle Status). „Prüfen"-Link bleibt
  bei `ready`.
- **_overview.html**: `_remove_control.html` mit `from='overview'` ergänzen
  (alle Status); „Prüfen" bei `ready`.
- **review.html**: „Bestätigen" bleibt; „Überspringen" verliert `hx-confirm`
  (reine Navigation); `_remove_control.html` mit `from='review'` ergänzen.
- **overview.html**: Info-Panel-Zelle „Umgang mit Original" → zwei Zeilen
  „beim Ablegen" (`when_filed`) / „beim Entfernen" (`when_removed`).

## 6. i18n (de + en)

[locales/de.json](../../../backend/src/zilpzalp/web/locales/de.json),
[locales/en.json](../../../backend/src/zilpzalp/web/locales/en.json):

Neu:
- `action.remove` — „Entfernen" / „Remove"
- `action.yes` — „Ja" / „Yes"
- `action.no` — „Nein" / „No"
- `confirm.remove` — „Entfernen? Original → {target}" / „Remove? Original → {target}"
  (`{target}` = `original.delete`/`original.trash`)
- `toast.removed` — „„{filename}" wurde entfernt." / „„{filename}" was removed."
- `overview.original_when_filed` — „Original beim Ablegen" / „Original when filed"
- `overview.original_when_removed` — „Original beim Entfernen" / „Original when removed"

Entfallen: `confirm.skip`, `toast.skipped`, `overview.original_handling`.
`original.delete` / `original.trash` bleiben (Hinweistext + Info-Panel).

## 7. Tests

- **test_processor**: `skip` raus; `remove` rein (beide Modi: `delete` löscht
  Original, `trash` verschiebt nach `paths.trash`); Toleranz bei fehlendem
  Original (kein Fehler). `process` disponiert per `when_filed`.
- **test_config**: `originals`-Schema (beide Felder Pflicht, nur `delete|trash`);
  Config ohne `originals` bzw. mit altem `original_handling` → `ConfigError`.
- **test_routes**: Skip = keine Dateioperation + Sprung auf next-after-current
  bzw. `/`; Remove disponiert + `from`-abhängiger Redirect + `toast.removed`;
  Remove auf Error-Eintrag (Original fehlt) → nur Queue-Eintrag weg, kein Fehler;
  `remove-control` liefert beide Zustände; `original_label` aus `when_filed`.
- **conftest / test_main**: Config-Fixtures auf `originals` umstellen.

## Gelöste Backlog-Offene-Frage

Übersprungene Dokumente bleiben `ready` in der Queue und werden **nicht**
re-enqueued (der Worker analysiert nur bei neuem Watchfolder-Event oder
`reanalyze_all` nach Config-Änderung) → keine Dauer-Re-Analyse. Nach einem
Neustart greift der normale Re-Scan des Watchfolders (akzeptiert; Cache-Reuse
über Neustart ist ein separates Backlog-Item).

## Bewusst nicht enthalten (YAGNI)

- Kein htmx-Teil-Swap der Listen beim Entfernen — voller `HX-Redirect` ist
  konsistent zum bestehenden Muster und genügt dem Ein-Nutzer-Tool.
- Kein automatisches Zurückklappen des Bestätigen-Zustands bei Fokusverlust.
- Keine Entfernen-Historie / Undo über den `trash`-Ordner hinaus.
