# ZilpZalp — Oberfläche

Sprachliche Beschreibung der Web-Oberfläche: was der Nutzer sieht, welche Funktionen es gibt und
wie die Seiten zusammenhängen. Diese Beschreibung entsteht in Meilenstein 5a; die Umsetzung
(Architektur, Routen) wird in 5b gebrainstormt und geplant. Übergeordnete Begründungen stehen im
[MVP Design-Spec](../superpowers/specs/2026-06-13-1435-zilpzalp-mvp-design.md); die Design-Vorlage
liegt unter [docs/ui/design/](ui/design/).

## Grundlegendes Erscheinungsbild

Die Anwendung ist durchgängig in Deutsch gehalten und tritt als ein einziges, zusammenhängendes
Werkzeug auf. Jede Seite teilt sich denselben Rahmen: oben eine Kopfleiste mit dem Produktnamen,
einer Navigation mit den drei Bereichen **Übersicht**, **Warteschlange** und **Konfiguration**
sowie einem Umschalter für helle oder dunkle Darstellung. Der gerade geöffnete Bereich ist in der
Navigation hervorgehoben, sodass der Nutzer jederzeit weiß, wo er sich befindet.

Das Aussehen ist ein ruhiges, modernes Werkzeug: viel freier Raum, eine zurückhaltende Akzentfarbe,
abgerundete Kacheln und dezente Abstufungen. Helles und dunkles Thema sind gleichwertig; die
Auswahl bleibt über Sitzungen hinweg erhalten, und standardmäßig folgt die Anwendung der
Voreinstellung des Systems.

Die Anwendung merkt sich bewusst nichts dauerhaft außer der Konfiguration und den abgelegten
Dateien. Alles, was in den Listen erscheint, ist eine Momentaufnahme des aktuellen Zustands; nach
einem Neustart wird sie aus dem überwachten Ordner neu aufgebaut. Erfolgs- und Fehlermeldungen sind
flüchtig: Sie erscheinen kurz und verschwinden wieder, es gibt keine dauerhafte Verlaufshistorie.

## Wiederkehrende Elemente

**Statusanzeige.** Jedes Dokument in der Anwendung hat einen von vier Zuständen, die überall gleich
dargestellt werden:

- *wartet* — das Dokument ist erkannt, die Analyse hat noch nicht begonnen.
- *Analyse* — das Dokument wird gerade ausgewertet.
- *bereit* — die Auswertung ist abgeschlossen, ein Vorschlag liegt vor und das Dokument kann
  geprüft werden.
- *Fehler* — das Dokument konnte nicht gelesen werden (kein Text, beschädigt oder reiner Scan);
  es wurde in den Fehlerordner verschoben.

**Selbsttätige Aktualisierung.** Listen, in denen sich der Zustand ändern kann, aktualisieren sich
von selbst in kurzen Abständen. Der Nutzer sieht den Übergang von *wartet* über *Analyse* zu
*bereit*, ohne die Seite neu laden zu müssen.

**Meldungen.** Nach einer erfolgreichen Verarbeitung oder bei einem Laufzeitfehler erscheint eine
kurze Meldung am oberen Rand des Inhalts. Diese Meldungen sind vorübergehend.

**Bestätigungsprinzip.** Keine Aktion verändert Dateien, ohne dass der Nutzer sie ausdrücklich
bestätigt hat.

## Bereiche und ihre Funktionen

### Übersicht (Startseite)

Die Übersicht ist die Einstiegsseite und gibt dem Werkzeug auf einen Blick ein vollständiges Bild.

Sie zeigt zuoberst vier Zähler — wie viele Dokumente *bereit*, in *Analyse*, im Zustand *wartet*
oder im *Fehler* sind. Darunter stehen die wichtigsten Betriebsangaben zur Orientierung: der
überwachte Ordner, der Ort der Konfigurationsdatei, wie mit dem Original umgegangen wird, wann eine
Zusammenfassung gezeigt wird sowie die Anzahl der eingerichteten Zielordner, Regeln und
Namensmuster. Diese Angaben sind reine Anzeige; geändert wird die Konfiguration im Bereich
Konfiguration.

Schließlich zeigt die Übersicht eine kompakte Vorschau der jüngsten Dokumente in der
Warteschlange. Von dort führt zu jedem bereiten Dokument ein direkter Weg zur Prüfung, und ein
Verweis „Alle anzeigen“ öffnet die vollständige Warteschlange. Zähler und Vorschau aktualisieren
sich selbsttätig. Sind keine Dokumente vorhanden, stehen die Zähler auf null und die Vorschau weist
darauf hin, dass die Warteschlange leer ist.

### Warteschlange

Die Warteschlange listet alle Dokumente, die im überwachten Ordner liegen und noch nicht bestätigt
verarbeitet wurden. Dieser Ordner ist zugleich Eingang und Arbeitsvorrat: Ein Dokument bleibt
sichtbar, bis es bestätigt verarbeitet oder als Fehler aussortiert wurde.

Jeder Eintrag zeigt den Dateinamen, seinen Status und eine kurze Vorschau. Bei bereiten Dokumenten
besteht die Vorschau aus dem vorgeschlagenen Datum, dem erkannten Absender und dem Dokumenttyp; bei
Fehlern aus einem kurzen Grund. Nur bereite Dokumente bieten die Aktion „Prüfen“, die zur
Prüfungsansicht führt. Fehlereinträge sind rein informativ — die Datei liegt bereits im
Fehlerordner; ein erneuter Durchlauf entsteht nur, wenn die Datei wieder in den überwachten Ordner
gelegt wird.

Die Liste aktualisiert sich selbsttätig, sodass neu hinzugekommene oder fertig analysierte
Dokumente von allein erscheinen. Ist nichts vorhanden, weist die Seite darauf hin, dass keine
Dokumente in der Warteschlange sind.

### Prüfungsansicht

Die Prüfungsansicht ist das Herzstück: Hier prüft der Nutzer den Vorschlag, wählt das richtige
Datum und bestätigt. Sie ist nur für bereite Dokumente erreichbar und wird über „Prüfen“ aus der
Übersicht oder der Warteschlange geöffnet. Ein Weg zurück zur Warteschlange ist immer vorhanden.

**Datumsauswahl.** Den wichtigsten Teil bildet die Auswahl des Datums, denn das falsche Datum ist
das Hauptrisiko des Werkzeugs. Die Ansicht zeigt *alle* im Dokument gefundenen Datumsangaben als
auswählbare Liste, jede mit dem vereinheitlichten Datum, einem Kontext-Hinweis (etwa
„Rechnungsdatum“ oder „fällig am“) und dem ursprünglichen Fundstück aus dem Dokument. Eine Angabe
ist sinnvoll vorausgewählt, doch der Nutzer kann jederzeit zu jeder anderen wechseln. Es wird keine
Angabe weggelassen oder zusammengefasst. Zusätzlich gibt es eine Möglichkeit zur manuellen Eingabe
eines Datums; sie dient auch dann, wenn das Dokument keine erkennbare Datumsangabe enthält.

**Weitere Felder.** Absender, Dokumenttyp und eine kurze Beschreibung sind aus dem Vorschlag
vorausgefüllt und frei änderbar. Über eine Auswahl lässt sich das Namensmuster bestimmen. Die
Zielordner werden als Mehrfachauswahl angeboten; die vom Vorschlag empfohlenen sind vorausgewählt,
mindestens einer muss gewählt sein.

**Namensvorschau.** Während der Nutzer Datum, Felder oder Muster ändert, zeigt die Ansicht
fortlaufend den daraus entstehenden endgültigen Dateinamen an, sodass das Ergebnis vor der
Bestätigung sichtbar ist.

Mit „Bestätigen“ geht es weiter — je nach Einstellung und Lage entweder direkt zur Ausführung oder
zunächst zur Zusammenfassung.

### Zusammenfassung und Bestätigung

Vor dem tatsächlichen Ablegen kann eine Zusammenfassung erscheinen. Ob sie gezeigt wird, hängt von
der Einstellung ab: immer, nur bei einem Namenskonflikt, oder nie. Ein Namenskonflikt erzwingt die
Zusammenfassung jedoch in jedem Fall. Liegt kein Konflikt vor und ist keine Zusammenfassung
verlangt, wird direkt abgelegt.

Die Zusammenfassung zeigt die Quelldatei, den endgültigen Namen, für jeden gewählten Zielordner den
vollständigen Ablageort und, was mit dem Original geschieht (verschieben, löschen oder behalten).
Existiert an einem Zielort bereits eine gleichnamige Datei, wird dieser Konflikt deutlich markiert.

Beim Umgang mit Konflikten ergänzt das Werkzeug niemals selbsttätig einen Namenszusatz. Stattdessen
bleibt die Ausführung gesperrt, bis der Nutzer den Namen ändert; alternativ kann er den Vorgang
abbrechen und kehrt dann ohne Änderung zur Prüfungsansicht zurück. Bestätigt der Nutzer die
Ausführung, wird das Dokument in die Zielordner kopiert und das Original wie eingestellt behandelt;
danach verschwindet es aus der Warteschlange, und eine kurze Erfolgsmeldung erscheint. Tritt dabei
ein technischer Fehler auf, wird er als vorübergehende Meldung angezeigt.

### Konfiguration

Im Bereich Konfiguration bearbeitet der Nutzer die einzige dauerhaft gespeicherte Einstellung, die
Konfigurationsdatei. Sie wird als reiner Text in einem Eingabefeld angezeigt und kann dort direkt
bearbeitet werden — das deckt alle Einstellungen ab und ist bewusst schlicht gehalten.

Beim Speichern prüft das Werkzeug die Eingabe mit denselben Regeln wie beim Programmstart. Ist alles
gültig, wird die Datei übernommen und eine Erfolgsmeldung erscheint. Ist etwas ungültig, werden die
Fehler verständlich aufgelistet, und die bisherige Konfiguration bleibt unverändert in Kraft — eine
fehlerhafte Eingabe kann den Betrieb also nicht stören.

Eine geänderte Konfiguration gilt für künftig hinzukommende Dokumente. Bereits ausgewertete
Einträge in der Warteschlange behalten ihren Vorschlag und werden nicht von selbst neu bewertet; wer
eine Neubewertung möchte, legt das Dokument erneut in den überwachten Ordner.

## Wege durch die Anwendung

Der übliche Ablauf führt von der **Übersicht** in die **Warteschlange** und von dort über „Prüfen“
in die **Prüfungsansicht**. Nach „Bestätigen“ folgt — je nach Einstellung und Konfliktlage —
entweder unmittelbar die Ausführung oder zunächst die **Zusammenfassung**, von der aus ausgeführt
oder abgebrochen wird. Nach erfolgreicher Ausführung kehrt der Nutzer in die Liste zurück, in der
das verarbeitete Dokument nicht mehr erscheint.

Übersicht, Warteschlange und Konfiguration sind außerdem jederzeit direkt über die Navigation in der
Kopfleiste erreichbar. Aus der Übersicht führen zusätzlich die Dokumentvorschau zur Prüfung und
„Alle anzeigen“ in die vollständige Warteschlange.
