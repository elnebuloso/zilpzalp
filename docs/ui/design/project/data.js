/* ZilpZalp — Beispieldaten (deutscher Dokumentenbestand) + Modell.
   Reine Momentaufnahme; bei Neustart würde sie aus dem Ordner neu aufgebaut. */
window.ZZ = (function () {

  // ----- Zielordner -----
  const FOLDERS = [
    { id: "finanzen-rechnungen", name: "Finanzen / Rechnungen", path: "~/Dokumente/Finanzen/Rechnungen" },
    { id: "steuer-2026",         name: "Steuer / 2026",          path: "~/Dokumente/Steuer/2026" },
    { id: "versicherung",        name: "Versicherungen",         path: "~/Dokumente/Versicherungen" },
    { id: "behoerden",           name: "Behörden",               path: "~/Dokumente/Behörden" },
    { id: "archiv",              name: "Archiv / 2026",          path: "~/Dokumente/Archiv/2026" },
  ];

  // ----- Namensmuster -----
  const PATTERNS = [
    { id: "standard", label: "Standard",  template: "{datum}_{absender}_{typ}" },
    { id: "kompakt",  label: "Kompakt",   template: "{datum}_{typ}_{absender}" },
    { id: "absender", label: "Absender",  template: "{absender}_{datum}" },
  ];

  // Dateien, die in den Zielordnern bereits liegen (für Konflikterkennung).
  const EXISTING = {
    "finanzen-rechnungen": [
      "2026-06-01_NetCom-Deutschland_Rechnung.pdf",  // -> erzeugt Konflikt
    ],
  };

  // ----- Betriebsangaben / Konfiguration -----
  const CONFIG = {
    watchedFolder: "~/Dokumente/Eingang",
    configPath:    "~/.config/zilpzalp/config.toml",
    originalMode:  "verschieben",      // verschieben | löschen | behalten
    summaryMode:   "bei_konflikt",     // immer | bei_konflikt | nie
  };

  const CONFIG_TEXT =
`# ZilpZalp — Konfiguration
# Die einzige dauerhaft gespeicherte Einstellung.

überwachter_ordner = "~/Dokumente/Eingang"
original           = "verschieben"      # verschieben | löschen | behalten
zusammenfassung    = "bei_konflikt"     # immer | bei_konflikt | nie

[zielordner]
finanzen-rechnungen = "~/Dokumente/Finanzen/Rechnungen"
steuer-2026         = "~/Dokumente/Steuer/2026"
versicherung        = "~/Dokumente/Versicherungen"
behoerden           = "~/Dokumente/Behörden"
archiv              = "~/Dokumente/Archiv/2026"

[namensmuster]
standard = "{datum}_{absender}_{typ}"
kompakt  = "{datum}_{typ}_{absender}"
absender = "{absender}_{datum}"

[regeln]
# Absender enthält "Finanzamt"  ->  behoerden, steuer-2026
# Dokumenttyp ist "Rechnung"     ->  finanzen-rechnungen
`;

  // ----- Dokumente in der Warteschlange -----
  // status: 'wartet' | 'analyse' | 'bereit' | 'fehler'
  const DOCS = [
    {
      id: "d1",
      filename: "rechnung_stadtwerke_mai.pdf",
      status: "bereit",
      suggestion: {
        sender: "Stadtwerke Aurich",
        docType: "Rechnung",
        description: "Stromabrechnung – Jahresverbrauch 2025/26",
        pattern: "standard",
        recommended: ["finanzen-rechnungen"],
        dates: [
          { id: "a", iso: "2026-05-14", label: "Rechnungsdatum",   snippet: "Rechnungsdatum: 14.05.2026", mark: "14.05.2026", preselected: true },
          { id: "b", iso: "2026-06-02", label: "fällig am",         snippet: "Bitte zahlbar bis zum 02.06.2026 ohne Abzug.", mark: "02.06.2026" },
          { id: "c", iso: "2026-04-30", label: "Abrechnungsende",   snippet: "Abrechnungszeitraum 01.05.2025 – 30.04.2026", mark: "30.04.2026" },
        ],
      },
    },
    {
      id: "d2",
      filename: "finanzamt_bescheid_2025.pdf",
      status: "bereit",
      suggestion: {
        sender: "Finanzamt Bremen-Mitte",
        docType: "Steuerbescheid",
        description: "Einkommensteuerbescheid für 2025",
        pattern: "standard",
        recommended: ["behoerden", "steuer-2026"],
        dates: [
          { id: "a", iso: "2026-05-28", label: "Bescheiddatum",     snippet: "Bescheid für 2025 vom 28.05.2026", mark: "28.05.2026", preselected: true },
          { id: "b", iso: "2026-06-30", label: "Einspruchsfrist",   snippet: "Der Einspruch muss bis zum 30.06.2026 eingehen.", mark: "30.06.2026" },
          { id: "c", iso: "2025-12-31", label: "Veranlagungsjahr",  snippet: "Veranlagungszeitraum: 01.01.2025 – 31.12.2025", mark: "31.12.2025" },
        ],
      },
    },
    {
      id: "d3",
      filename: "scan_2026-06-14_0931.pdf",
      status: "analyse",
      suggestion: null,
      _ready: {
        sender: "Amtsgericht Oldenburg",
        docType: "Schreiben",
        description: "Mitteilung – Aktenzeichen 4 C 211/26",
        pattern: "standard",
        recommended: ["behoerden"],
        dates: [
          { id: "a", iso: "2026-06-09", label: "Datum des Schreibens", snippet: "Oldenburg, den 09.06.2026", mark: "09.06.2026", preselected: true },
          { id: "b", iso: "2026-06-23", label: "Frist", snippet: "Stellungnahme bis spätestens 23.06.2026", mark: "23.06.2026" },
        ],
      },
    },
    {
      id: "d4",
      filename: "police_nordstern_hausrat.pdf",
      status: "wartet",
      suggestion: null,
      // Vorbereitete Auswertung, wird beim Wechsel auf 'bereit' gesetzt:
      _ready: {
        sender: "Nordstern Versicherung",
        docType: "Versicherungspolice",
        description: "Hausratversicherung – Police-Nr. HR-884213",
        pattern: "standard",
        recommended: ["versicherung"],
        dates: [
          { id: "a", iso: "2026-06-10", label: "Ausstellungsdatum", snippet: "Ausgestellt am 10.06.2026", mark: "10.06.2026", preselected: true },
          { id: "b", iso: "2026-07-01", label: "Versicherungsbeginn", snippet: "Versicherungsbeginn: 01.07.2026", mark: "01.07.2026" },
          { id: "c", iso: "2027-07-01", label: "nächste Fälligkeit", snippet: "Beitrag fällig zum 01.07.2027", mark: "01.07.2027" },
        ],
      },
    },
    {
      id: "d5",
      filename: "img_4821.jpg",
      status: "fehler",
      errorReason: "Kein Text erkannt – reiner Scan ohne Textebene",
    },
    {
      id: "d6",
      filename: "netcom_rechnung_juni.pdf",
      status: "bereit",
      suggestion: {
        sender: "NetCom Deutschland",
        docType: "Rechnung",
        description: "Mobilfunk – Abrechnung Juni 2026",
        pattern: "standard",
        recommended: ["finanzen-rechnungen"],
        dates: [
          { id: "a", iso: "2026-06-01", label: "Rechnungsdatum",   snippet: "Rechnungsdatum 01.06.2026", mark: "01.06.2026", preselected: true },
          { id: "b", iso: "2026-06-15", label: "fällig am",         snippet: "Fälligkeit: 15.06.2026", mark: "15.06.2026" },
        ],
      },
    },
  ];

  return { FOLDERS, PATTERNS, EXISTING, CONFIG, CONFIG_TEXT, DOCS };
})();
