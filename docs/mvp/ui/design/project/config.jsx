/* ZilpZalp — Konfiguration (einzige dauerhaft gespeicherte Einstellung). */

function validateConfig(text) {
  const errors = [];
  const getVal = (key) => {
    const m = text.match(new RegExp("^\\s*" + key + "\\s*=\\s*\"?([^\"#\\n]+?)\"?\\s*(#.*)?$", "m"));
    return m ? m[1].trim() : null;
  };
  if (!/^\s*überwachter_ordner\s*=/m.test(text))
    errors.push("Pflichtangabe fehlt: überwachter_ordner");
  const orig = getVal("original");
  if (!orig) errors.push("Pflichtangabe fehlt: original");
  else if (!["verschieben", "löschen", "behalten"].includes(orig))
    errors.push(`Ungültiger Wert für original: \"${orig}\" — erlaubt: verschieben | löschen | behalten`);
  const sum = getVal("zusammenfassung");
  if (!sum) errors.push("Pflichtangabe fehlt: zusammenfassung");
  else if (!["immer", "bei_konflikt", "nie"].includes(sum))
    errors.push(`Ungültiger Wert für zusammenfassung: \"${sum}\" — erlaubt: immer | bei_konflikt | nie`);
  if (!/\[zielordner\]/.test(text))
    errors.push("Abschnitt [zielordner] fehlt — mindestens ein Zielordner ist nötig");
  const open = (text.match(/\[/g) || []).length, close = (text.match(/\]/g) || []).length;
  if (open !== close) errors.push("Unausgeglichene Klammern in einem Abschnittstitel");
  return { errors, parsed: { originalMode: orig, summaryMode: sum } };
}

function Config({ text, onSave }) {
  const [value, setValue] = useState(text);
  const [errors, setErrors] = useState([]);
  const dirty = value !== text;

  useEffect(() => { setValue(text); setErrors([]); }, [text]);

  const save = () => {
    const { errors, parsed } = validateConfig(value);
    if (errors.length) { setErrors(errors); return; }
    setErrors([]);
    onSave(value, parsed);
  };

  return (
    <div className="view-enter">
      <div className="view-head">
        <h1 className="view-title">Konfiguration</h1>
        <p className="view-sub">
          Die einzige dauerhaft gespeicherte Einstellung — als reiner Text. Beim Speichern wird mit
          denselben Regeln wie beim Programmstart geprüft; eine fehlerhafte Eingabe kann den Betrieb nicht stören.
        </p>
      </div>

      <div className="config-wrap">
        <textarea
          className="code-editor"
          spellCheck={false}
          value={value}
          onChange={(e) => { setValue(e.target.value); if (errors.length) setErrors([]); }} />

        {errors.length > 0 && (
          <div className="val-errors">
            <div className="ve-title"><Ic.warn style={{ width: 16, height: 16 }} /> Konfiguration nicht übernommen — die bisherige bleibt in Kraft</div>
            <ul>{errors.map((e, i) => <li key={i}>{e}</li>)}</ul>
          </div>
        )}

        <div className="config-bar">
          {dirty
            ? <span className="muted" style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}><span className="dirty-dot" /> Ungespeicherte Änderungen</span>
            : <span className="faint" style={{ fontSize: 13 }}>Gespeichert · gilt für künftig hinzukommende Dokumente</span>}
          <div className="spacer" />
          <button className="btn" disabled={!dirty} onClick={() => { setValue(text); setErrors([]); }}>Verwerfen</button>
          <button className="btn primary" disabled={!dirty} onClick={save}>Speichern & prüfen</button>
        </div>

        <p className="faint" style={{ fontSize: 12.5, marginTop: 4, lineHeight: 1.6 }}>
          Eine geänderte Konfiguration gilt für künftig hinzukommende Dokumente. Bereits ausgewertete
          Einträge behalten ihren Vorschlag; für eine Neubewertung das Dokument erneut in den überwachten Ordner legen.
        </p>
      </div>
    </div>
  );
}

Object.assign(window, { Config });
