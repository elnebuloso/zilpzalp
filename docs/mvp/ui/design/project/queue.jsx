/* ZilpZalp — Warteschlange. */

function QueueRow({ doc, openReview }) {
  const d = doc;
  let preview;
  if (d.status === "bereit" && d.suggestion) {
    const pre = d.suggestion.dates.find((x) => x.preselected) || d.suggestion.dates[0];
    preview = (
      <div className="qfile-prev">
        <span className="chip mono">{ZZUtil.germanDate(pre?.iso)}</span>
        <span className="sep">·</span><span className="chip">{d.suggestion.sender}</span>
        <span className="sep">·</span><span className="chip">{d.suggestion.docType}</span>
      </div>
    );
  } else if (d.status === "fehler") {
    preview = <div className="qfile-prev" style={{ color: "var(--st-err)" }}>{d.errorReason}</div>;
  } else if (d.status === "analyse") {
    preview = <div className="qfile-prev">wird ausgewertet …</div>;
  } else {
    preview = <div className="qfile-prev">wartet auf Analyse</div>;
  }

  return (
    <div className={"qrow" + (d.status === "fehler" ? " dimmed" : "") + (d._removing ? " removing" : "")}>
      <Ic.file className="ficon" />
      <div className="qfile">
        <div className="qfile-name">{d.filename}</div>
        {preview}
      </div>
      <StatusBadge status={d.status} />
      <div style={{ width: 92, display: "flex", justifyContent: "flex-end" }}>
        {d.status === "bereit"
          ? <button className="btn sm primary" onClick={() => openReview(d.id)}>
              Prüfen <Ic.arrowRight style={{ width: 14, height: 14 }} />
            </button>
          : <span style={{ width: 1 }} />}
      </div>
    </div>
  );
}

function Queue({ docs, openReview }) {
  return (
    <div className="view-enter">
      <div className="view-head">
        <h1 className="view-title">Warteschlange</h1>
        <p className="view-sub">
          Alle Dokumente im überwachten Ordner, die noch nicht bestätigt verarbeitet wurden.
          Ein Eintrag bleibt sichtbar, bis er bestätigt verarbeitet oder als Fehler aussortiert wurde.
        </p>
      </div>
      {docs.length === 0 ? (
        <EmptyState
          title="Keine Dokumente in der Warteschlange"
          sub="Sobald eine Datei im überwachten Ordner liegt, erscheint sie hier von allein." />
      ) : (
        <div className="qlist">
          {docs.map((d) => (
            <QueueRow key={d.id} doc={d} openReview={openReview} />
          ))}
        </div>
      )}
    </div>
  );
}

Object.assign(window, { Queue });
