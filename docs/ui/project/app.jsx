/* ZilpZalp — App-Wurzel: Routen, Zustand, selbsttätige Aktualisierung, Thema, Tweaks. */

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "dashboard": "Zweispaltig",
  "density": "Normal",
  "accent": "#6E86B8"
}/*EDITMODE-END*/;

const LAYOUT_MAP  = { "Klassisch": "classic", "Zweispaltig": "split", "Fokus": "focus" };
const DENSITY_MAP = { "Kompakt": "compact", "Normal": "", "Luftig": "comfy" };

let toastSeq = 0;

function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);

  const [view, setView]   = useState("overview");
  const [reviewId, setReviewId] = useState(null);
  const [docs, setDocs]   = useState(() => window.ZZ.DOCS.map((d) => ({ ...d })));
  const [configText, setConfigText] = useState(window.ZZ.CONFIG_TEXT);
  const [config, setConfig] = useState(window.ZZ.CONFIG);
  const [toasts, setToasts] = useState([]);

  // ---------- Thema ----------
  const [theme, setTheme] = useState(() => {
    try { return localStorage.getItem("zz-theme") || "dark"; } catch (e) { return "dark"; }
  });
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try { localStorage.setItem("zz-theme", theme); } catch (e) {}
  }, [theme]);

  // ---------- Tweaks -> CSS ----------
  useEffect(() => {
    const dn = DENSITY_MAP[t.density] || "";
    if (dn) document.documentElement.setAttribute("data-density", dn);
    else document.documentElement.removeAttribute("data-density");
  }, [t.density]);

  useEffect(() => {
    const a = t.accent || "#6E86B8";
    const r = document.documentElement.style;
    r.setProperty("--accent", a);
    r.setProperty("--accent-bg", `color-mix(in oklab, ${a} 15%, transparent)`);
    r.setProperty("--accent-line", `color-mix(in oklab, ${a} 60%, transparent)`);
  }, [t.accent]);

  const layout = LAYOUT_MAP[t.dashboard] || "split";

  // ---------- Toasts ----------
  const pushToast = useCallback((msg, kind) => {
    const id = ++toastSeq;
    setToasts((ts) => [...ts, { id, msg, kind }]);
    setTimeout(() => setToasts((ts) => ts.map((x) => x.id === id ? { ...x, out: true } : x)), 3600);
    setTimeout(() => setToasts((ts) => ts.filter((x) => x.id !== id)), 3950);
  }, []);
  const dismissToast = (id) =>
    setToasts((ts) => ts.filter((x) => x.id !== id));

  // ---------- Selbsttätige Aktualisierung (einmalige Simulation) ----------
  const setStatus = useCallback((id, status) => {
    setDocs((ds) => ds.map((d) => {
      if (d.id !== id) return d;
      if (status === "bereit" && d._ready) return { ...d, status, suggestion: d._ready };
      return { ...d, status };
    }));
  }, []);

  const ran = useRef(false);
  useEffect(() => {
    if (ran.current) return; ran.current = true;
    const timers = [
      setTimeout(() => setStatus("d4", "analyse"), 3800),
      setTimeout(() => setStatus("d3", "bereit"),  5200),
      setTimeout(() => setStatus("d4", "bereit"),  9400),
    ];
    return () => timers.forEach(clearTimeout);
  }, [setStatus]);

  // ---------- Navigation ----------
  const go = (v) => { setView(v); window.scrollTo({ top: 0 }); };
  const openReview = (id) => {
    const d = docs.find((x) => x.id === id);
    if (d && d.status === "bereit") { setReviewId(id); setView("review"); window.scrollTo({ top: 0 }); }
  };

  // ---------- Ausführen ----------
  const execute = ({ docId, finalName, folderIds, originalMode }) => {
    go("queue");
    setDocs((ds) => ds.map((d) => d.id === docId ? { ...d, _removing: true } : d));
    setTimeout(() => {
      setDocs((ds) => ds.filter((d) => d.id !== docId));
      const verb = originalMode === "behalten" ? "abgelegt (Original behalten)"
        : originalMode === "löschen" ? "abgelegt (Original gelöscht)" : "abgelegt";
      pushToast(`„${finalName}“ wurde ${verb}.`, "ok");
    }, 440);
  };

  // ---------- Konfiguration speichern ----------
  const saveConfig = (text, parsed) => {
    setConfigText(text);
    setConfig((c) => ({ ...c, originalMode: parsed.originalMode, summaryMode: parsed.summaryMode }));
    pushToast("Konfiguration gespeichert und übernommen.", "ok");
  };

  // ---------- Zähler ----------
  const counts = {
    bereit:  docs.filter((d) => d.status === "bereit").length,
    analyse: docs.filter((d) => d.status === "analyse").length,
    wartet:  docs.filter((d) => d.status === "wartet").length,
    fehler:  docs.filter((d) => d.status === "fehler").length,
  };
  counts.open = counts.bereit;

  const reviewDoc = docs.find((d) => d.id === reviewId);
  const { FOLDERS, PATTERNS } = window.ZZ;

  // Falls das geprüfte Dokument verschwindet, zurück zur Liste.
  useEffect(() => {
    if (view === "review" && (!reviewDoc || reviewDoc.status !== "bereit")) go("queue");
  }, [view, reviewDoc]);

  return (
    <div className="app">
      <Header view={view} go={go} counts={counts} theme={theme}
        toggleTheme={() => setTheme((x) => x === "dark" ? "light" : "dark")} />

      <main className="main">
        {view === "overview" && (
          <Overview docs={docs} counts={counts} config={config}
            folders={FOLDERS} patterns={PATTERNS} go={go} openReview={openReview} layout={layout} />
        )}
        {view === "queue" && <Queue docs={docs} openReview={openReview} />}
        {view === "review" && reviewDoc && (
          <Review doc={reviewDoc} folders={FOLDERS} patterns={PATTERNS} config={config}
            onBack={() => go("queue")} onExecute={execute} />
        )}
        {view === "config" && <Config text={configText} onSave={saveConfig} />}
      </main>

      <Toasts items={toasts} dismiss={dismissToast} />

      <TweaksPanel title="Tweaks">
        <TweakSection label="Übersicht – Layout" />
        <TweakRadio label="Dashboard" value={t.dashboard}
          options={["Klassisch", "Zweispaltig", "Fokus"]}
          onChange={(v) => setTweak("dashboard", v)} />
        <TweakSection label="Darstellung" />
        <TweakRadio label="Dichte" value={t.density}
          options={["Kompakt", "Normal", "Luftig"]}
          onChange={(v) => setTweak("density", v)} />
        <TweakColor label="Akzent" value={t.accent}
          options={["#6E86B8", "#5E927A", "#A8794E", "#7E6BA8"]}
          onChange={(v) => setTweak("accent", v)} />
      </TweaksPanel>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
