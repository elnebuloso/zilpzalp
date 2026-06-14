/* ZilpZalp — gemeinsame Bausteine, Icons, Helfer. */
const { useState, useEffect, useRef, useCallback } = React;

/* ---------------- Helfer ---------------- */
const STATUS = {
  wartet:  { label: "wartet",  cls: "b-wait",  c: "var(--st-wait)" },
  analyse: { label: "Analyse", cls: "b-ana",   c: "var(--st-ana)" },
  bereit:  { label: "bereit",  cls: "b-ready", c: "var(--st-ready)" },
  fehler:  { label: "Fehler",  cls: "b-err",   c: "var(--st-err)" },
};

function germanDate(iso) {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-");
  return `${d}.${m}.${y}`;
}

// Dateiname-tauglicher Teil: Leerzeichen -> Bindestrich, Umlaute behalten.
function slug(s) {
  return (s || "").trim().replace(/\s+/g, "-").replace(/[\/\\:*?"<>|]/g, "");
}

function buildName(template, parts, ext) {
  const filled = template
    .replace("{datum}", parts.datum || "")
    .replace("{absender}", slug(parts.absender) || "Unbekannt")
    .replace("{typ}", slug(parts.typ) || "Dokument");
  return filled + (ext || ".pdf");
}

function segmentsForName(template, parts) {
  // gibt [{key, text}] für hervorgehobene Vorschau zurück
  const order = [];
  const re = /\{(datum|absender|typ)\}|([^{}]+)/g;
  let mt;
  while ((mt = re.exec(template))) {
    if (mt[1]) {
      const val = mt[1] === "datum" ? (parts.datum || "")
        : mt[1] === "absender" ? (slug(parts.absender) || "Unbekannt")
        : (slug(parts.typ) || "Dokument");
      order.push({ key: mt[1], text: val });
    } else {
      order.push({ key: "lit", text: mt[2] });
    }
  }
  return order;
}

/* ---------------- Icons (einfache geometrische Glyphen) ---------------- */
const Ic = {
  sun: (p) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" {...p}>
      <circle cx="12" cy="12" r="4.2" /><path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5 5l1.4 1.4M17.6 17.6L19 19M19 5l-1.4 1.4M6.4 17.6L5 19" />
    </svg>
  ),
  moon: (p) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" {...p}>
      <path d="M20 14.5A8 8 0 1 1 9.5 4a6.3 6.3 0 0 0 10.5 10.5z" />
    </svg>
  ),
  file: (p) => (
    <svg viewBox="0 0 38 44" fill="none" {...p}>
      <path d="M7 3h17l8 8v28a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z" fill="var(--surface-2)" stroke="var(--border-strong)" strokeWidth="1.3"/>
      <path d="M24 3v6a2 2 0 0 0 2 2h6" fill="none" stroke="var(--border-strong)" strokeWidth="1.3"/>
      <path d="M11 22h16M11 28h16M11 34h10" stroke="var(--text-3)" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  ),
  arrowRight: (p) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...p}>
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  ),
  arrowLeft: (p) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...p}>
      <path d="M19 12H5M11 6l-6 6 6 6" />
    </svg>
  ),
  check: (p) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" {...p}>
      <path d="M4 12.5l5 5L20 6.5" />
    </svg>
  ),
  checkSm: (p) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" {...p}>
      <path d="M5 12.5l4.5 4.5L19 7" />
    </svg>
  ),
  x: (p) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" {...p}>
      <path d="M6 6l12 12M18 6L6 18" />
    </svg>
  ),
  warn: (p) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...p}>
      <path d="M12 3.5L22 20H2L12 3.5z" /><path d="M12 10v4.5M12 17.4v.1" />
    </svg>
  ),
  inbox: (p) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}>
      <path d="M3 13l3-8h12l3 8v6a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-6z" /><path d="M3 13h5l1.5 2.5h5L16 13h5" />
    </svg>
  ),
  folder: (p) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" {...p}>
      <path d="M3 6.5A1.5 1.5 0 0 1 4.5 5h4l2 2.5h7A1.5 1.5 0 0 1 19 9v8.5a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 3 17.5v-11z" />
    </svg>
  ),
};

/* ZilpZalp-Marke: zwei einfache Blätter/Schwingen (nur einfache Formen). */
function BrandMark({ className }) {
  return (
    <svg className={className} viewBox="0 0 26 26" fill="none">
      <rect x="1" y="1" width="24" height="24" rx="7" fill="var(--accent-bg)" stroke="var(--accent-line)" strokeWidth="1"/>
      <circle cx="13" cy="13" r="6.4" fill="none" stroke="var(--accent)" strokeWidth="1.7"/>
      <circle cx="13" cy="13" r="1.9" fill="var(--accent)"/>
    </svg>
  );
}

/* ---------------- Statusabzeichen ---------------- */
function StatusBadge({ status }) {
  const s = STATUS[status] || STATUS.wartet;
  return (
    <span className={"badge " + s.cls}>
      <span className="dot" />{s.label}
    </span>
  );
}

/* ---------------- Toasts ---------------- */
function Toasts({ items, dismiss }) {
  return (
    <div className="toasts">
      {items.map((t) => (
        <div key={t.id} className={"toast " + (t.kind === "err" ? "err" : "ok") + (t.out ? " out" : "")}>
          {t.kind === "err" ? <Ic.warn className="t-ic" /> : <Ic.checkSm className="t-ic" />}
          <span>{t.msg}</span>
          <button className="t-x" onClick={() => dismiss(t.id)} aria-label="schließen"><Ic.x style={{ width: 14, height: 14 }} /></button>
        </div>
      ))}
    </div>
  );
}

/* ---------------- Kopfleiste ---------------- */
function Header({ view, go, counts, theme, toggleTheme }) {
  const items = [
    { id: "overview", label: "Übersicht" },
    { id: "queue",    label: "Warteschlange", count: counts.open },
    { id: "config",   label: "Konfiguration" },
  ];
  const active = view === "review" ? "queue" : view;
  return (
    <header className="header">
      <div className="header-inner">
        <div className="brand" onClick={() => go("overview")}>
          <BrandMark className="brand-mark" />
          <span className="brand-name">Zilp<span className="z2">Zalp</span></span>
        </div>
        <nav className="nav">
          {items.map((it) => (
            <button key={it.id}
              className={"nav-item" + (active === it.id ? " active" : "")}
              onClick={() => go(it.id)}>
              {active === it.id && <span className="nav-dot" />}
              {it.label}
              {it.count > 0 && <span className="nav-count">{it.count}</span>}
            </button>
          ))}
        </nav>
        <div className="header-spacer" />
        <button className="theme-toggle" onClick={toggleTheme}
          aria-label="Darstellung umschalten" title={theme === "dark" ? "Helles Thema" : "Dunkles Thema"}>
          {theme === "dark" ? <Ic.sun style={{ width: 18, height: 18 }} /> : <Ic.moon style={{ width: 18, height: 18 }} />}
        </button>
      </div>
    </header>
  );
}

/* ---------------- Leerzustand ---------------- */
function EmptyState({ icon, title, sub }) {
  const I = icon || Ic.inbox;
  return (
    <div className="empty">
      <I className="e-mark" />
      <div className="e-title">{title}</div>
      {sub && <div className="e-sub">{sub}</div>}
    </div>
  );
}

Object.assign(window, {
  ZZUtil: { STATUS, germanDate, slug, buildName, segmentsForName },
  Ic, BrandMark, StatusBadge, Toasts, Header, EmptyState,
});
