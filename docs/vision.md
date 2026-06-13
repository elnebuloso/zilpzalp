# Produktvision: ZilpZalp

## Name

Der ZilpZalp ist der Vogel, der seinen eigenen Namen ruft — er ist nach seinem Gesang „zilp-zalp" benannt. Ein Vogel, der sich quasi selbst benennt, als Maskottchen für ein Tool, das Dokumente benennt: Das ist die perfekte Story. Dazu klingt der Name verspielt, ist unverwechselbar und im Software-Bereich mit an Sicherheit grenzender Wahrscheinlichkeit frei — wobei selbst die englische Variante des Vogel („Chiffchaff") nach ihrem Ruf benannt ist.

---

## 1. Kurzfassung

**ZilpZalp** ist ein selbst betreibbares Tool zur assistierten, kontextbasierten Umbenennung von PDF-Dokumenten. Es überwacht einen Watchfolder, erkennt neu eingehende PDFs, analysiert deren eingebetteten Textinhalt und legt sie dem Nutzer in einer Web-UI zur Prüfung vor.

Das Produkt schlägt auf Basis erkannter Informationen wie Datum, Absender, Dokumenttyp und Beschreibung einen passenden Dateinamen vor. Der Nutzer kann Naming-Patterns definieren, wiederkehrende Dokumente über Regeln stabilisieren und die final umbenannten PDFs an einen oder mehrere Zielordner kopieren lassen.

Das Tool richtet sich im ersten Fokus an Privatpersonen, die regelmäßig PDFs aus Scans, E-Mails oder Downloads ablegen und sinnvoll benennen müssen. Es reduziert manuelle Arbeit, vermeidet Fehler und lässt dem Nutzer bewusst die Kontrolle über jede finale Verarbeitung.

Das MVP ist als einfache, monolithische Docker-Anwendung mit Web-UI gedacht. Es verarbeitet zunächst nur textbasierte PDFs mit eingebettetem Text. OCR für gescannte Dokumente bleibt eine spätere Option.

---

## 2. Produktvision

ZilpZalp soll das manuelle Umbenennen privater PDF-Dokumente deutlich vereinfachen, ohne dem Nutzer die Entscheidung vollständig abzunehmen.

Das Produkt verfolgt die Vision, aus unstrukturierten PDF-Eingängen einen kontrollierten, nachvollziehbaren und wiederholbaren Benennungsprozess zu machen. Statt Dateien wie `scan_001.pdf`, `document.pdf` oder kryptische Downloadnamen manuell zu prüfen, erkennt das Tool relevante Inhalte und erzeugt daraus konkrete, prüfbare Vorschläge für Dateinamen.

Der Nutzer bleibt dabei immer entscheidende Instanz. Das Produkt arbeitet nicht als Blackbox, die Dokumente ungeprüft verschiebt oder umbenennt, sondern als assistierendes Werkzeug: Es analysiert, schlägt vor, zeigt Kontext und ermöglicht eine schnelle, bewusste Bestätigung.

Langfristig soll das Produkt einen privaten Dokumenten-Workflow unterstützen, bei dem PDFs aus einem Eingangsort aufgenommen, inhaltlich verstanden, sinnvoll benannt und an definierte Zielorte verteilt werden.

---

## 3. Zielgruppe

### 3.1 Primäre Zielgruppe

Die primäre Zielgruppe sind Privatpersonen, die regelmäßig PDF-Dokumente verwalten müssen.

Typische Quellen sind:

- gescannte Dokumente
- E-Mail-Anhänge
- heruntergeladene Rechnungen
- Verträge
- Versicherungsunterlagen
- Behörden- oder Bankdokumente
- sonstige private Unterlagen

Diese Nutzer haben häufig keine professionelle Dokumentenmanagementlösung, möchten ihre Dateien aber trotzdem geordnet, wiederauffindbar und konsistent benannt ablegen.

### 3.2 Technisches Nutzungsprofil

Das Produkt soll von normalen Privatpersonen betrieben werden können, sofern sie einer guten Anleitung folgen können.

Die technische Basis ist Self-hosting per Docker, bevorzugt per Docker Compose. Der Betrieb ist primär für das lokale Heimnetz gedacht, nicht für eine öffentlich erreichbare Internetanwendung.

---

## 4. Problemraum

Privatpersonen sammeln mit der Zeit viele PDF-Dokumente aus unterschiedlichen Quellen. Diese Dateien tragen oft schlechte oder nichtssagende Namen, zum Beispiel:

```text
scan_001.pdf
document.pdf
rechnung.pdf
download.pdf
2024-01.pdf
```

Das eigentliche Problem entsteht beim späteren Wiederfinden und Einordnen dieser Dokumente. Der Nutzer muss jedes PDF öffnen, relevante Informationen suchen und daraus manuell einen passenden Dateinamen erstellen.

Typische Schwierigkeiten sind:

- Dokumente enthalten mehrere Datumsangaben.
- Das richtige Datum ist nicht immer eindeutig.
- Der Absender muss aus dem Inhalt erkannt werden.
- Der Dokumenttyp ist nicht immer direkt ersichtlich.
- Aussagekräftige Beschreibungen müssen manuell formuliert werden.
- Dateinamen werden uneinheitlich vergeben.
- Wiederkehrende Dokumente werden immer wieder neu manuell bewertet.
- Fehler beim Umbenennen oder Ablegen sind wahrscheinlich.
- Der manuelle Prozess kostet unnötig Zeit.

Gerade bei Rechnungen treten mehrere Datumswerte auf, zum Beispiel Rechnungsdatum, Leistungsdatum, Fälligkeitsdatum oder Zahlungsziel. Für den Dateinamen ist aber meist nur eines dieser Daten relevant.

---

## 5. Nutzenversprechen

ZilpZalp reduziert die manuelle Arbeit beim Benennen privater PDF-Dokumente und senkt gleichzeitig das Fehlerrisiko.

Der zentrale Nutzen besteht aus drei Elementen:

1. **Assistierte Vorschläge statt manueller Suche**  
   Das Tool extrahiert relevante Informationen aus dem PDF und bereitet sie direkt für die Benennung auf.

2. **Kontrolle durch Nutzerbestätigung**  
   Der Nutzer bestätigt jedes Dokument vor der finalen Verarbeitung. Dadurch bleibt der Prozess nachvollziehbar und kontrolliert.

3. **Wiederholbarkeit durch Patterns und Regeln**  
   Für wiederkehrende Dokumente können Regeln und Naming-Patterns genutzt werden, damit ähnliche Dokumente konsistent behandelt werden.

Das Produkt ist nicht primär als vollautomatisches KI-System gedacht, sondern als verlässliches Assistenzwerkzeug mit nachvollziehbarer Logik.

---

## 6. Grundprinzipien

### 6.1 Assistiert statt vollautomatisch

Das Produkt verarbeitet Dokumente nicht ungeprüft. Jeder finale Verarbeitungsschritt wird durch den Nutzer bestätigt.

Das reduziert das Risiko falscher Benennungen, falscher Datumswahl oder ungewollter Dateioperationen.

### 6.2 Deterministisch vor KI

Das Produkt soll möglichst deterministisch und nachvollziehbar arbeiten. Regeln, Patterns und explizite Nutzerentscheidungen haben Vorrang vor KI-generierten Vorschlägen.

KI kann optional eingesetzt werden, um Vorschläge zu verbessern, darf aber nicht zur zwingenden Voraussetzung für den Kernnutzen werden.

### 6.3 Self-hosted und lokal betreibbar

Das Produkt wird als selbst betreibbare Docker-Anwendung konzipiert. Die Zielumgebung ist das lokale Heimnetz.

Dadurch bleibt der Betrieb kontrollierbar und unabhängig von einem zentralen Cloud-Dienst.

### 6.4 Datensparsamkeit

Das Produkt speichert dauerhaft nur Daten, die für die Funktion notwendig sind:

- Naming-Patterns
- Regeln
- Zielorte

Original-PDFs, extrahierter Volltext und Verarbeitungshistorien werden im MVP nicht dauerhaft gespeichert.

### 6.5 Kein Dokumentenmanagementsystem

Das Produkt ist kein vollwertiges DMS. Es soll PDFs sinnvoll benennen und verteilen, aber keine umfassende Dokumentenverwaltung, Suche, Archivierung oder Rechteverwaltung bereitstellen.

---

## 7. Standard-Naming-Pattern

Das Standardformat für Dateinamen lautet:

```text
YYYY-MM-DD__Absender_Dokumenttyp_Beschreibung.pdf
```

Beispiel:

```text
2026-01-15__Stadtwerke_Rechnung_Stromabschlag.pdf
```

Die doppelte Trennung nach dem Datum dient der visuellen Abgrenzung zwischen Zeitbezug und inhaltlichem Teil des Dateinamens.

### 7.1 Bestandteile

| Bestandteil | Bedeutung |
|---|---|
| `YYYY-MM-DD` | relevantes Dokumentdatum |
| `Absender` | erkannter oder gewählter Absender |
| `Dokumenttyp` | z. B. Rechnung, Vertrag, Bescheid, Mitteilung |
| `Beschreibung` | kurze aussagekräftige Ergänzung |
| `.pdf` | ursprüngliches Dateiformat bleibt erhalten |

---

## 8. Naming-Patterns und Regeln

Der Nutzer kann mehrere Naming-Patterns definieren. Diese Patterns können je nach Dokumentart, Absender oder erkanntem Kontext angewendet werden.

Wiederkehrende Dokumente sollen über Regeln stabil erkannt und konsistent benannt werden.

### 8.1 Unterstützte Regelarten im MVP

Das MVP soll Regeln für folgende Zusammenhänge unterstützen:

- erkannter Absender → festes Naming-Pattern
- erkannter Dokumenttyp → festes Naming-Pattern
- erkannte Schlüsselwörter → festes Naming-Pattern
- bevorzugtes Datumsfeld → z. B. Rechnungsdatum statt Fälligkeitsdatum
- wiederkehrender Beschreibungstext → z. B. „Mobilfunkrechnung“, „Stromabschlag“, „Versicherungsbeitrag“

### 8.2 Ziel der Regeln

Regeln sollen nicht zu versteckter Automatisierung führen, sondern bessere Vorschläge erzeugen.

Auch wenn ein Pattern oder eine Regel greift, bleibt der Nutzer im MVP in der Bestätigungsschleife.

---

## 9. Funktionsumfang des MVP

### 9.1 Eingang über Watchfolder

Das MVP überwacht einen Watchfolder. Neu eingehende PDF-Dateien werden erkannt und für die Prüfung vorbereitet.

Im MVP wird ein Watchfolder angenommen.

### 9.2 PDF-Analyse

Das MVP verarbeitet textbasierte PDFs mit eingebettetem Text.

Die Analyse soll relevante Informationen extrahieren, insbesondere:

- Datumsangaben
- mögliche Absender
- mögliche Dokumenttypen
- relevante Schlüsselwörter
- mögliche Beschreibungsvorschläge

OCR ist nicht Teil des MVP.

### 9.3 Web-UI

Die Benutzeroberfläche wird als Web-UI im Browser umgesetzt.

Pro Dokument soll die Prüfansicht folgende Informationen enthalten:

- PDF-Vorschau
- erkannte Datumsangaben
- erkannter oder vorgeschlagener Absender
- erkannter oder vorgeschlagener Dokumenttyp
- Beschreibungsvorschlag
- vorgeschlagene Zielorte
- finaler Dateiname

Der Nutzer kann die Vorschläge prüfen, korrigieren und bestätigen.

### 9.4 Zielordner

Das MVP unterstützt mehrere Zielordner.

Ein Dokument kann nach Bestätigung an einen oder mehrere definierte Zielorte kopiert werden.

Zielorte können:

- manuell pro Dokument gewählt werden
- als Standard-Zielorte vorgeschlagen werden
- über Regeln vorgeschlagen werden

### 9.5 Verarbeitung nach Bestätigung

Nach Nutzerbestätigung wird das PDF mit dem finalen Dateinamen an die gewählten Zielordner kopiert.

Das Original im Watchfolder wird anschließend gemäß Konfiguration behandelt, zum Beispiel:

- löschen
- in einen Processed-/Archivordner verschieben
- anderweitig definiert behandeln

Das Löschen ist damit nicht zwingend fest verdrahtet, sondern Teil der Betriebs- und Sicherheitskonfiguration.

### 9.6 Fehlerhafte oder nicht lesbare PDFs

Nicht lesbare oder fehlerhafte PDFs werden in einen fest vorkonfigurierten Fehlerordner verschoben, zum Beispiel:

```text
error/
```

Dadurch blockieren sie den Watchfolder nicht und bleiben für manuelle Prüfung erhalten.

### 9.7 Namenskonflikte

Wenn im Zielordner bereits eine Datei mit demselben Namen existiert, entscheidet der Nutzer manuell.

Das Tool soll keine automatische Suffix- oder Zeitstempellogik erzwingen.

### 9.8 Hash-basierte Duplikaterkennung

> **Entscheidung (MVP-Design):** Aus dem MVP gestrichen. Die Hash-Duplikaterkennung ist
> Komfort, nicht Kern; sie wird auf eine spätere Version verschoben, um das MVP-Risiko zu
> senken. Eine identische Datei unter anderem Namen wird im MVP nicht automatisch erkannt.

### 9.9 Finale Zusammenfassung

Eine Zusammenfassung vor der finalen Verarbeitung ist konfigurierbar.

Mögliche Modi:

- immer anzeigen
- nur bei Konflikten anzeigen
- nach Bestätigung direkt verarbeiten

Die Zusammenfassung kann enthalten:

- ursprünglicher Dateiname
- finaler Dateiname
- gewählte Zielordner
- Namenskonflikte
- geplante Behandlung des Originals

---

## 10. Vorschlagslogik

Das Produkt arbeitet primär regelbasiert und nachvollziehbar. Ergänzend können lokale Heuristiken verwendet werden.

Optional kann ein KI-Modell angebunden werden, insbesondere für:

- Beschreibungsvorschläge
- Absender-Erkennung
- Dokumenttyp-Erkennung

Die KI-Anbindung ist pro Installation konfigurierbar. Möglich sind lokale Modelle oder externe APIs.

Wichtig ist: Der Kernnutzen des Produkts darf nicht von KI abhängen. Das Tool muss auch ohne KI brauchbare Vorschläge erzeugen können.

---

## 11. Datenhaltung

Das MVP speichert dauerhaft nur die für den Betrieb notwendigen Konfigurationsdaten.

Dauerhaft gespeichert werden:

- Naming-Patterns
- Regeln für Absender, Dokumenttyp, Schlüsselwörter, bevorzugtes Datum und Beschreibung
- Zielorte

Nicht dauerhaft gespeichert werden:

- Original-PDFs
- extrahierter Volltext aus PDFs
- Verarbeitungshistorie
- fachliche Protokolle über verarbeitete Dokumente
- Nutzerentscheidungen als Lernhistorie

Es wird keine fachliche Verarbeitungshistorie geführt. Das bedeutet: Das Tool speichert nicht dauerhaft, welche PDFs verarbeitet wurden, wie sie vorher hießen oder wohin sie kopiert wurden.

Technische Fehlerausgaben können für Betrieb und Fehlersuche notwendig sein, sind aber nicht als produktseitige Dokumenthistorie zu verstehen.

---

## 12. Datenschutz

Datenschutz ist eine wichtige Anforderung, aber nicht das alleinige Hauptargument des Produkts.

Der datenschutzfreundliche Charakter ergibt sich aus mehreren Eigenschaften:

- Self-hosting
- Betrieb im lokalen Heimnetz
- keine dauerhafte Speicherung von Original-PDFs
- keine dauerhafte Speicherung extrahierter Volltexte
- keine fachliche Verarbeitungshistorie
- konfigurierbare KI-Anbindung
- Kernfunktion ohne externe KI nutzbar

Das Hauptversprechen bleibt jedoch produktivitätsorientiert: weniger manuelle Arbeit, weniger Fehler und kontrolliertes Umbenennen von PDFs.

---

## 13. Architekturannahmen

Das MVP wird als einfache, monolithische Docker-App gedacht.

Die Anwendung umfasst innerhalb eines deploybaren Containers beziehungsweise einer einfachen Docker-Compose-Installation:

- Watchfolder-Überwachung
- PDF-Textanalyse
- Vorschlagslogik
- Web-UI
- Regel- und Pattern-Verwaltung
- Zielordner-Verwaltung
- Dateioperationen
- Fehlerbehandlung

Der konkrete Konfigurationsspeicher wird im Visionsdokument nicht festgelegt. Wichtig ist nur, dass die notwendigen Konfigurationsdaten dauerhaft gespeichert werden können, ohne Originaldokumente oder extrahierte Volltexte dauerhaft abzulegen.

---

## 14. Installation und Betrieb

Das Produkt soll bevorzugt per Docker Compose installiert werden.

Ziel ist eine Installation, die auch normale Privatpersonen mit guter Anleitung durchführen können.

Die Dokumentation muss daher mindestens erklären:

- benötigte Verzeichnisse
- Watchfolder
- Zielordner
- Fehlerordner
- Konfiguration
- Start per Docker Compose
- Zugriff auf die Web-UI
- grundlegende Fehlerfälle

Die Anwendung ist für das lokale Heimnetz gedacht. Ein öffentlich erreichbarer Betrieb über das Internet ist nicht Ziel des MVP.

---

## 15. Nicht-Ziele des MVP

Folgende Punkte sind bewusst nicht Teil des MVP:

- OCR für gescannte PDFs
- vollautomatische Verarbeitung ohne Nutzerbestätigung
- Mobile App
- Desktop-App
- Mehrbenutzer- oder Rollenverwaltung
- Cloud-Synchronisation
- Verarbeitung anderer Dateitypen als PDF
- dauerhafte Speicherung von Originaldokumenten
- externes Nutzerkonto- oder Login-System
- komplexes Dokumentenmanagementsystem mit Ordnerverwaltung und Suche

Das MVP bleibt fokussiert auf einen klaren Workflow:

```text
Watchfolder → PDF erkennen → Inhalt analysieren → Vorschlag anzeigen → Nutzer bestätigt → PDF kopieren → Original gemäß Konfiguration behandeln
```

---

## 16. Erfolgskriterien

Eine erste nutzbare Version gilt als erfolgreich, wenn folgende Kriterien erfüllt sind:

1. Mindestens 80 % der PDFs erhalten direkt einen brauchbaren Startpunkt für den Namensvorschlag.
2. Der Nutzer benötigt pro PDF weniger als 15 Sekunden zur Prüfung.
3. Wiederkehrende Dokumente werden zuverlässig erkannt.
4. Es gibt keine dauerhafte Datenhaltung über Konfiguration, Patterns, Regeln und Zielorte hinaus.
5. Ein privater Dokumenten-Workflow wird vollständig abgedeckt: Eingang über Watchfolder, Prüfung in der Web-UI, Umbenennung, Kopie an Zielorte und konfigurierte Behandlung des Originals.

Da das MVP rein regelbasiert arbeitet, ist ein vollständiger Vorschlag beim Erstkontakt mit
einem unbekannten Absender kaum erreichbar — die Beschreibung ist deterministisch am
schwersten. Der Erfolg bemisst sich daher am **brauchbaren Startpunkt plus schneller
Bestätigung**, nicht am perfekten Erstvorschlag: Das Tool füllt vor, was es sicher weiß
(Datum, ggf. Dokumenttyp), der Nutzer ergänzt den Rest in unter 15 Sekunden.

Ein Startpunkt gilt als brauchbar, wenn er:

- mindestens ein korrektes Datum als Vorschlag sichtbar macht
- einem definierten Naming-Pattern entspricht
- die sicher erkennbaren Bestandteile (Datum, ggf. Dokumenttyp) korrekt vorbefüllt
- eine schnelle, fehlerarme Ergänzung der übrigen Bestandteile (Absender, Beschreibung) erlaubt

Bei wiederkehrenden Dokumenten mit eingerichteter Regel werden Absender, Dokumenttyp und
Beschreibung zusätzlich korrekt vorgeschlagen.

---

## 17. Risiken

### 17.1 Falsches Datum

Ein wesentliches Risiko ist die Wahl eines falschen Datums.

Viele Dokumente enthalten mehrere Datumsangaben, zum Beispiel:

- Rechnungsdatum
- Leistungsdatum
- Fälligkeitsdatum
- Zahlungsziel
- Erstellungsdatum
- Zeitraumangaben

Das Tool muss diese Daten sichtbar machen und darf nicht intransparent ein Datum auswählen. Der Nutzer muss erkennen können, welches Datum für den Dateinamen vorgeschlagen wird.

### 17.2 Ungenaue Beschreibung

Ein weiteres Risiko ist eine zu allgemeine oder ungenaue Beschreibung.

Eine Beschreibung wie `Dokument`, `Rechnung` oder `Mitteilung` kann formal korrekt sein, hilft aber später nur begrenzt beim Wiederfinden.

Das Tool sollte daher kurze, aber aussagekräftige Beschreibungsvorschläge erzeugen und wiederkehrende Beschreibungstexte über Regeln unterstützen.

---

## 18. Offene Fragen

Die meisten dieser Punkte wurden im MVP-Design entschieden (siehe
`docs/superpowers/specs/2026-06-13-1435-zilpzalp-mvp-design.md`). Der Stand:

### 18.1 Login und Sicherheitsmodell

**Entschieden: kein Login im MVP.** Das Produkt ist für das lokale Heimnetz gedacht; wer das
Netz erreicht, erreicht das Tool. Die Verantwortung für den Netzzugang liegt beim Betreiber
und wird in der Doku als Hinweis aufgenommen.

### 18.2 Konfigurationsspeicher

**Entschieden: YAML-Konfigurationsdatei** (`config.yaml`) im gemounteten Config-Volume.
Transparent, versionierbar, hand- und UI-editierbar; passt zur Datensparsamkeit.

### 18.3 KI-Anbindung

**Entschieden: Das MVP arbeitet rein regelbasiert.** Eine KI-Anbindung ist nicht Teil des MVP,
wird aber als sauber gekapselter, später implementierbarer Erweiterungspunkt in der
Vorschlagslogik vorgesehen. Der Kernnutzen bleibt unabhängig von KI.

### 18.4 OCR als spätere Option

OCR ist nicht Teil des MVP. Es bleibt aber als spätere Option möglich, um gescannte PDFs ohne eingebetteten Text verarbeiten zu können.

### 18.5 Detailverhalten bei Hash-Duplikaten

**Hinfällig:** Die Hash-Duplikaterkennung wurde aus dem MVP gestrichen (siehe 9.8).

### 18.6 Technische Fehlerausgaben

**Entschieden:** Technische Laufzeitfehler werden nach `stdout` geloggt (Container-Logs) und in
der UI transient am betroffenen Eintrag angezeigt. Unlesbare PDFs landen im `error/`-Ordner.
Diese Ausgaben sind Betriebs-/Debug-Information, keine fachliche Verarbeitungshistorie.

---

## 19. Zusammenfassung

ZilpZalp ist ein fokussiertes, self-hosted Werkzeug für Privatpersonen, die PDF-Dokumente kontrolliert, konsistent und mit weniger manueller Arbeit umbenennen möchten.

Das Produkt löst kein allgemeines Dokumentenmanagementproblem, sondern einen klar abgegrenzten Workflow: PDFs aus einem Watchfolder werden analysiert, dem Nutzer mit Kontext in einer Web-UI vorgelegt, nach definierten Patterns benannt und nach Bestätigung an Zielorte kopiert.

Die Stärke des Produkts liegt nicht in maximaler Automatisierung, sondern in nachvollziehbarer Assistenz: Regeln, Patterns, sichtbare Kontextinformationen und Nutzerbestätigung bilden den Kern. KI kann optional unterstützen, bleibt aber austauschbar und nicht zwingend.

Das MVP ist bewusst schlank gehalten und konzentriert sich auf textbasierte PDFs, eine Web-UI, einen Watchfolder, mehrere Zielordner, regelgestützte Namensvorschläge und kontrollierte Dateioperationen.
