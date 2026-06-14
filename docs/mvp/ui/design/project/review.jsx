/* ZilpZalp — Prüfungsansicht (Herzstück) + Zusammenfassung. */

function Snippet({ text, mark }) {
  if (!mark) return <span>{text}</span>;
  const i = text.indexOf(mark);
  if (i < 0) return <span>{text}</span>;
  return (
    <span>{text.slice(0, i)}<mark>{mark}</mark>{text.slice(i + mark.length)}</span>
  );
}

function Review({ doc, folders, patterns, config, onBack, onExecute }) {
  const sug = doc.suggestion;
  const preDate = sug.dates.find((d) => d.preselected) || sug.dates[0];

  const [dateId, setDateId]       = useState(preDate ? preDate.id : "manual");
  const [manualDate, setManualDate] = useState("");
  const [sender, setSender]       = useState(sug.sender);
  const [docType, setDocType]     = useState(sug.docType);
  const [desc, setDesc]           = useState(sug.description);
  const [patternId, setPatternId] = useState(sug.pattern);
  const [sel, setSel]             = useState(sug.recommended.slice());
  const [showSum, setShowSum]     = useState(false);

  const isManual = dateId === "manual";
  const iso = isManual ? manualDate : (sug.dates.find((d) => d.id === dateId)?.iso || "");
  const validDate = !!iso;

  const pattern = patterns.find((p) => p.id === patternId) || patterns[0];
  const ext = "." + (doc.filename.split(".").pop() || "pdf");
  const finalName = ZZUtil.buildName(pattern.template, { datum: iso, absender: sender, typ: docType }, ext);
  const segs = ZZUtil.segmentsForName(pattern.template, { datum: iso, absender: sender, typ: docType });

  // Konflikt-Erkennung
  const existing = window.ZZ.EXISTING;
  const conflicts = sel.filter((fid) => (existing[fid] || []).includes(finalName));
  const hasConflict = conflicts.length > 0;

  // sanfter Aufblitzen-Effekt der Namensvorschau bei Änderung
  const [pulse, setPulse] = useState(false);
  const first = useRef(true);
  useEffect(() => {
    if (first.current) { first.current = false; return; }
    setPulse(true);
    const t = setTimeout(() => setPulse(false), 460);
    return () => clearTimeout(t);
  }, [finalName]);

  const toggleFolder = (fid) =>
    setSel((s) => (s.includes(fid) ? s.filter((x) => x !== fid) : [...s, fid]));

  const canConfirm = validDate && sel.length > 0;

  const onBestaetigen = () => {
    if (!canConfirm) return;
    const needSummary = config.summaryMode === "immer" || hasConflict;
    if (needSummary) setShowSum(true);
    else doExecute();
  };

  const doExecute = () => {
    onExecute({
      docId: doc.id,
      finalName,
      folderIds: sel,
      originalMode: config.originalMode,
    });
  };

  const originalLabel = { verschieben: "verschieben", "löschen": "löschen", behalten: "behalten" }[config.originalMode];

  return (
    <div className="view-enter">
      <button className="link back-link" onClick={onBack}>
        <Ic.arrowLeft style={{ width: 15, height: 15 }} /> Zurück zur Warteschlange
      </button>

      <div className="view-head" style={{ marginBottom: 22 }}>
        <h1 className="view-title">Dokument prüfen</h1>
        <p className="view-sub mono" style={{ fontSize: 13.5 }}>{doc.filename}</p>
      </div>

      <div className="review-grid">
        {/* ---------- linke Spalte: Datum + Felder ---------- */}
        <div className="dash-stack">
          {/* Datumsauswahl */}
          <div className="card card-pad">
            <h2 className="card-h" style={{ marginBottom: 6 }}>Datum wählen</h2>
            <p className="muted" style={{ fontSize: 13, margin: "0 0 16px" }}>
              Alle im Dokument gefundenen Datumsangaben — nichts wird weggelassen. Eine ist vorgewählt; wechseln Sie bei Bedarf.
            </p>
            <div className="date-list">
              {sug.dates.map((d) => (
                <button key={d.id}
                  className={"date-opt" + (dateId === d.id ? " sel" : "")}
                  onClick={() => setDateId(d.id)}>
                  <span className="date-radio"><span className="date-radio-dot" /></span>
                  <span style={{ minWidth: 0 }}>
                    <span style={{ display: "flex", alignItems: "baseline", gap: 12, flexWrap: "wrap" }}>
                      <span className="date-iso">{ZZUtil.germanDate(d.iso)}</span>
                      <span className="date-ctx"><span className="ctx-label">{d.label}</span></span>
                    </span>
                    <span className="date-snippet" style={{ display: "block" }}>
                      „<Snippet text={d.snippet} mark={d.mark} />“
                    </span>
                  </span>
                </button>
              ))}
            </div>

            {/* manuelle Eingabe */}
            <div className={"manual-date" + (isManual ? " sel" : "")} style={{ marginTop: 10 }}>
              <button className="date-radio" style={{ padding: 0 }}
                onClick={() => setDateId("manual")} aria-label="manuell"><span className="date-radio-dot" /></button>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13.5, fontWeight: 560, marginBottom: isManual ? 8 : 0 }}>
                  Datum manuell eingeben
                </div>
                {isManual && (
                  <input type="date" className="input" value={manualDate}
                    onChange={(e) => setManualDate(e.target.value)} style={{ maxWidth: 200 }} autoFocus />
                )}
              </div>
            </div>
          </div>

          {/* weitere Felder */}
          <div className="card card-pad">
            <h2 className="card-h">Felder</h2>
            <div className="field">
              <label className="field-label">Absender</label>
              <input className="input" value={sender} onChange={(e) => setSender(e.target.value)} />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
              <div className="field">
                <label className="field-label">Dokumenttyp</label>
                <input className="input" value={docType} onChange={(e) => setDocType(e.target.value)} />
              </div>
              <div className="field">
                <label className="field-label">Namensmuster</label>
                <select className="select" value={patternId} onChange={(e) => setPatternId(e.target.value)}>
                  {patterns.map((p) => (
                    <option key={p.id} value={p.id}>{p.label} — {p.template}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="field">
              <label className="field-label">Beschreibung</label>
              <textarea className="textarea" value={desc} onChange={(e) => setDesc(e.target.value)} />
            </div>
            <div className="field">
              <label className="field-label">
                Zielordner <span className="faint" style={{ fontWeight: 400 }}>· mindestens einer · empfohlen vorgewählt</span>
              </label>
              <div className="folder-grid">
                {folders.map((f) => {
                  const on = sel.includes(f.id);
                  const rec = sug.recommended.includes(f.id);
                  return (
                    <button key={f.id} className={"folder-chip" + (on ? " on" : "")} onClick={() => toggleFolder(f.id)}>
                      <span className="fk-box">{on && <Ic.checkSm style={{ width: 12, height: 12 }} />}</span>
                      <span style={{ minWidth: 0 }}>
                        <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          {f.name}
                          {rec && <span className="faint" style={{ fontSize: 10.5, fontWeight: 600, letterSpacing: ".04em", textTransform: "uppercase" }}>empf.</span>}
                        </span>
                        <span className="fk-path">{f.path}</span>
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* ---------- rechte Spalte: Namensvorschau ---------- */}
        <div className="name-preview">
          <div className="np-box">
            <h2 className="card-h" style={{ marginBottom: 4 }}>Endgültiger Dateiname</h2>
            <p className="faint" style={{ fontSize: 12.5, margin: "0 0 10px" }}>Aktualisiert sich fortlaufend.</p>
            <div className={"np-final" + (pulse ? "" : "")}>
              {segs.map((s, i) => (
                <span key={i} className={"seg" + (pulse && s.key === "datum" ? " flash" : "")}
                  style={s.key !== "lit" ? { color: "var(--text)" } : { color: "var(--text-3)" }}>
                  {s.text}
                </span>
              ))}
              <span className="seg" style={{ color: "var(--text-3)" }}>{ext}</span>
            </div>

            <div className="np-meta">
              <div className="np-meta-row"><span className="k">Datum</span><span className="v mono">{validDate ? ZZUtil.germanDate(iso) : "— bitte wählen"}</span></div>
              <div className="np-meta-row"><span className="k">Muster</span><span className="v">{pattern.label}</span></div>
              <div className="np-meta-row"><span className="k">Zielordner</span><span className="v">{sel.length}</span></div>
              <div className="np-meta-row"><span className="k">Original</span><span className="v">{originalLabel}</span></div>
            </div>

            {hasConflict && (
              <div className="conflict-banner" style={{ marginTop: 16, marginBottom: 0 }}>
                <Ic.warn className="cb-ic" style={{ width: 18, height: 18 }} />
                <span>Im Zielordner liegt bereits eine gleichnamige Datei. Die Ausführung bleibt gesperrt, bis Sie den Namen ändern.</span>
              </div>
            )}

            <div className="review-actions">
              <button className="btn ghost" onClick={onBack}>Abbrechen</button>
              <button className="btn primary" style={{ flex: 1, justifyContent: "center" }}
                disabled={!canConfirm} onClick={onBestaetigen}>
                Bestätigen <Ic.arrowRight style={{ width: 15, height: 15 }} />
              </button>
            </div>
            {!canConfirm && (
              <p className="faint" style={{ fontSize: 12, margin: "10px 2px 0", textAlign: "center" }}>
                {!validDate ? "Bitte ein Datum wählen." : "Mindestens einen Zielordner wählen."}
              </p>
            )}
          </div>
        </div>
      </div>

      {showSum && (
        <Summary
          doc={doc} finalName={finalName} folders={folders} sel={sel}
          conflicts={conflicts} originalLabel={originalLabel}
          onCancel={() => setShowSum(false)} onExecute={doExecute} />
      )}
    </div>
  );
}

/* ---------------- Zusammenfassung & Bestätigung ---------------- */
function Summary({ doc, finalName, folders, sel, conflicts, originalLabel, onCancel, onExecute }) {
  const hasConflict = conflicts.length > 0;
  const selFolders = folders.filter((f) => sel.includes(f.id));
  return (
    <div className="modal-scrim" onClick={onCancel}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h2 className="modal-title">Zusammenfassung</h2>
          <p className="modal-sub">Prüfen Sie die Ablage. Keine Datei wird ohne diese Bestätigung verändert.</p>
        </div>
        <div className="modal-body">
          {hasConflict && (
            <div className="conflict-banner">
              <Ic.warn className="cb-ic" style={{ width: 18, height: 18 }} />
              <span>
                <b>Namenskonflikt.</b> Es wird kein Zusatz automatisch ergänzt — bitte den Namen in der Prüfung ändern.
                Die Ausführung ist gesperrt.
              </span>
            </div>
          )}
          <div className="sum-row">
            <div className="sum-k">Quelldatei</div>
            <div className="sum-v mono">{doc.filename}</div>
          </div>
          <div className="sum-row">
            <div className="sum-k">Endgültiger Name</div>
            <div className="sum-v mono" style={{ color: "var(--text)" }}>{finalName}</div>
          </div>
          <div className="sum-row">
            <div className="sum-k">Ablageorte</div>
            <div className="sum-v" style={{ flex: 1 }}>
              {selFolders.map((f) => {
                const conf = conflicts.includes(f.id);
                return (
                  <div className={"dest-line" + (conf ? " conflict" : "")} key={f.id}>
                    {conf ? <Ic.warn style={{ width: 14, height: 14, flex: "none" }} /> : <Ic.folder style={{ width: 14, height: 14, flex: "none", color: "var(--text-3)" }} />}
                    <span style={{ wordBreak: "break-all" }}>{f.path}/{finalName}{conf && "  · existiert bereits"}</span>
                  </div>
                );
              })}
            </div>
          </div>
          <div className="sum-row">
            <div className="sum-k">Original</div>
            <div className="sum-v">wird <b>{originalLabel}</b></div>
          </div>
        </div>
        <div className="modal-foot">
          <button className="btn ghost" onClick={onCancel}>Abbrechen</button>
          <button className="btn primary" disabled={hasConflict} onClick={onExecute}>
            <Ic.check style={{ width: 15, height: 15 }} /> Ausführen
          </button>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { Review });
