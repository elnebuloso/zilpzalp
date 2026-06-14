/* ZilpZalp — Übersicht (Startseite) mit 3 Layout-Varianten. */

function Counter({ kind, n, big }) {
  const meta = ZZUtil.STATUS[kind === "bereit" ? "bereit" : kind === "analyse" ? "analyse" : kind === "wartet" ? "wartet" : "fehler"];
  const colorVar = {
    bereit: "var(--st-ready)", analyse: "var(--st-ana)",
    wartet: "var(--st-wait)", fehler: "var(--st-err)",
  }[kind];
  return (
    <div className={"counter" + (big ? " big" : "")} style={{ "--c": colorVar }}>
      <div className="c-num" style={{ color: n > 0 ? colorVar : "var(--text-3)" }}>{n}</div>
      <div className="c-label"><span className="c-tag" style={{ color: colorVar }}><span className="dot" /><span>{meta.label}</span></span></div>
    </div>
  );
}

function CountersRow({ counts }) {
  return (
    <div className="counters">
      <Counter kind="bereit"  n={counts.bereit}  />
      <Counter kind="analyse" n={counts.analyse} />
      <Counter kind="wartet"  n={counts.wartet}  />
      <Counter kind="fehler"  n={counts.fehler}  />
    </div>
  );
}

function Betriebsangaben({ config, folders, patterns }) {
  const summaryLabel = { immer: "immer", bei_konflikt: "bei Konflikt", nie: "nie" }[config.summaryMode];
  const originalLabel = { verschieben: "verschieben", "löschen": "löschen", behalten: "behalten" }[config.originalMode];
  const cells = [
    { k: "Überwachter Ordner", v: config.watchedFolder, mono: true },
    { k: "Konfigurationsdatei", v: config.configPath, mono: true },
    { k: "Umgang mit Original", v: originalLabel },
    { k: "Zusammenfassung", v: summaryLabel },
    { k: "Zielordner", v: String(folders.length) },
    { k: "Namensmuster", v: String(patterns.length) },
    { k: "Regeln", v: "2" },
  ];
  return (
    <div className="card card-pad">
      <h2 className="card-h">Betriebsangaben</h2>
      <div className="info-grid">
        {cells.map((c, i) => (
          <div className={"info-cell" + (cells.length % 2 === 1 && i === cells.length - 1 ? " span2" : "")} key={c.k}>
            <div className="info-k">{c.k}</div>
            <div className={"info-v" + (c.mono ? " mono" : "")}>{c.v}</div>
          </div>
        ))}
      </div>
      <p className="faint" style={{ fontSize: 12.5, margin: "13px 2px 0" }}>
        Reine Anzeige — geändert wird im Bereich Konfiguration.
      </p>
    </div>
  );
}

function RecentPreview({ docs, go, openReview, limit }) {
  const recent = docs.slice(0, limit || 5);
  return (
    <div className="card card-pad">
      <div className="section-head">
        <h3>Jüngste Dokumente</h3>
        <button className="link" onClick={() => go("queue")}>
          Alle anzeigen <Ic.arrowRight style={{ width: 14, height: 14 }} />
        </button>
      </div>
      {recent.length === 0 ? (
        <EmptyState title="Die Warteschlange ist leer" sub="Neue Dokumente erscheinen hier, sobald sie im überwachten Ordner liegen." />
      ) : (
        <div className="preview-list">
          {recent.map((d) => (
            <div className="preview-item" key={d.id}>
              <Ic.file className="ficon" style={{ width: 26, height: 30 }} />
              <div style={{ minWidth: 0 }}>
                <div className="pi-name">{d.filename}</div>
                <div className="pi-sub">
                  {d.status === "bereit" && d.suggestion
                    ? <span>{ZZUtil.germanDate(d.suggestion.dates.find((x) => x.preselected)?.iso)} · {d.suggestion.sender} · {d.suggestion.docType}</span>
                    : d.status === "fehler"
                    ? <span style={{ color: "var(--st-err)" }}>{d.errorReason}</span>
                    : d.status === "analyse" ? "wird ausgewertet …" : "wartet auf Analyse"}
                </div>
              </div>
              {d.status === "bereit"
                ? <button className="btn sm primary" onClick={() => openReview(d.id)}>Prüfen</button>
                : <StatusBadge status={d.status} />}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Overview({ docs, counts, config, folders, patterns, go, openReview, layout }) {
  // ---- Variante: Fokus (bereit groß hervorgehoben) ----
  if (layout === "focus") {
    return (
      <div className="view-enter">
        <div className="view-head">
          <h1 className="view-title">Übersicht</h1>
          <p className="view-sub">Das Werkzeug auf einen Blick. Zähler und Vorschau aktualisieren sich selbsttätig.</p>
        </div>
        <div className="dash-cols">
          <div className="dash-stack">
            <div className="card card-pad" style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: 26, alignItems: "center" }}>
              <div className="counter big" style={{ "--c": "var(--st-ready)", border: "none", boxShadow: "none", background: "transparent", padding: 0 }}>
                <div className="c-num" style={{ color: counts.bereit > 0 ? "var(--st-ready)" : "var(--text-3)" }}>{counts.bereit}</div>
                <div className="c-label" style={{ marginTop: 14 }}><StatusBadge status="bereit" /> <span className="faint" style={{ marginLeft: 4 }}>zur Prüfung</span></div>
              </div>
              <div className="dash-hero-counters">
                <Counter kind="analyse" n={counts.analyse} />
                <Counter kind="wartet"  n={counts.wartet} />
                <Counter kind="fehler"  n={counts.fehler} />
                <div className="counter" style={{ display: "grid", placeItems: "center", borderStyle: "dashed" }}>
                  <button className="link" onClick={() => go("queue")}>Warteschlange <Ic.arrowRight style={{ width: 14, height: 14 }} /></button>
                </div>
              </div>
            </div>
            <RecentPreview docs={docs} go={go} openReview={openReview} limit={5} />
          </div>
          <Betriebsangaben config={config} folders={folders} patterns={patterns} />
        </div>
      </div>
    );
  }

  // ---- Variante: Zweispaltig (Vorschau im Mittelpunkt, Angaben als Seitenleiste) ----
  if (layout === "split") {
    return (
      <div className="view-enter">
        <div className="view-head">
          <h1 className="view-title">Übersicht</h1>
          <p className="view-sub">Das Werkzeug auf einen Blick. Zähler und Vorschau aktualisieren sich selbsttätig.</p>
        </div>
        <div className="dash-cols">
          <div className="dash-stack">
            <CountersRow counts={counts} />
            <RecentPreview docs={docs} go={go} openReview={openReview} limit={6} />
          </div>
          <Betriebsangaben config={config} folders={folders} patterns={patterns} />
        </div>
      </div>
    );
  }

  // ---- Variante: Klassisch (gestapelt) ----
  return (
    <div className="view-enter">
      <div className="view-head">
        <h1 className="view-title">Übersicht</h1>
        <p className="view-sub">Das Werkzeug auf einen Blick. Zähler und Vorschau aktualisieren sich selbsttätig.</p>
      </div>
      <div className="dash-stack">
        <CountersRow counts={counts} />
        <Betriebsangaben config={config} folders={folders} patterns={patterns} />
        <RecentPreview docs={docs} go={go} openReview={openReview} limit={5} />
      </div>
    </div>
  );
}

Object.assign(window, { Overview });
