# Design: MkDocs-Doku als GitHub Page

## Ziel

Die MkDocs-Material-Dokumentation unter [`mkdocs/`](../../../mkdocs/) wird
automatisch als GitHub Page unter
**https://elnebuloso.github.io/zilpzalp/** veröffentlicht — ausgelöst nur bei
Änderungen am Doku-Folder.

## Mechanik

Ein neuer Workflow `.github/workflows/docs.yml` baut die Doku und pusht das
Ergebnis per `mkdocs gh-deploy --force` auf einen `gh-pages`-Branch. GitHub
Pages serviert diesen Branch.

Vollständig unabhängig vom bestehenden release-please-Flow für das Backend:
separater Workflow, eigener Trigger, kein Versions-Bump.

## Trigger

```yaml
on:
  push:
    branches: [main]
    paths:
      - 'mkdocs/**'
  workflow_dispatch:
```

Läuft nur, wenn unter `mkdocs/**` etwas geändert wurde — plus manueller Button.
Änderungen an `Dockerfile.mkdocs` lösen bewusst **kein** Deploy aus, da der
Workflow per pip baut, nicht über das Dockerfile.

## Job

Standard-Vorgehen aus der Material-Doku
(<https://squidfunk.github.io/mkdocs-material/publishing-your-site/>):

- `actions/checkout`
- Git-Identität für den Bot setzen
- `actions/setup-python`
- Cache für `.cache` (mkdocs-material Build-Cache)
- `pip install "mkdocs-material>=9,<10"` — auf Major **9** gepinnt, passend zu
  `Dockerfile.mkdocs` (`squidfunk/mkdocs-material:9`)
- `mkdocs gh-deploy --force --strict -f mkdocs/mkdocs.yml`

`permissions: contents: write` zum Pushen des `gh-pages`-Branch. `--strict`
bricht den Deploy bei kaputten Links/Refs ab — analog zum bestehenden
`mkdocs build --strict` im Dockerfile.

## Config-Anpassung

In `mkdocs/mkdocs.yml` wird ergänzt:

```yaml
site_url: https://elnebuloso.github.io/zilpzalp/
```

Nötig für korrekte Canonical-Links, Sitemap und damit `navigation.instant`
sauber funktioniert.

## Einmaliger manueller Schritt

Nach dem ersten erfolgreichen Workflow-Run existiert der `gh-pages`-Branch.
Dann einmalig in GitHub: *Settings → Pages → Source = „Deploy from a branch" →
`gh-pages` / `root`*. Nicht per Code automatisierbar.
