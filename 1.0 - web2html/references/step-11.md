# 1.1 — Light scrape

Read this when you **enter 1.1**. Do not load `SKILL.md` again.

**One script. Do not author a long contract, inspect font name tables, copy
into `rebuild/`, or self-host fonts.**

```sh
python3 $SKILLS/web2html/scripts/pipeline-progress.py mark "$PROJECT" --step 1.1 --status active
"$SKILLS/web2html/scripts/scrape-web.sh" "$URL" source-site
python3 $SKILLS/web2html/scripts/pipeline-progress.py mark "$PROJECT" --step 1.1 --status done
```

That is curl of the one URL, then `scrape_light.py`: images + **Latin
`U+0000-00FF` fonts only**, in parallel. Time box: **under 30 seconds**.
1.2 `localize-html-images.mjs` reuses `source-site/assets/` and downloads any
remaining live images — do not re-download the scrape. Self-host into
`rebuild/fonts/` + `css/fonts.css` at **2.1** (`verify-fonts.py`), not here.

The script writes a stub `qa/fidelity-contract.md` (homepage-only,
`web-responsive`, 1600 / 768 / 390). **Do not rewrite it. Do not interview.**

## Scope

**Default and hard cap: 1 page (`/`).** Extra sitemap routes stay in the
scrape; they do not enter Paper. CMS posts, Contact, Pricing, Features, and
404 stay out unless the user **explicitly** names those routes **and**
`--allow-multi-page`. **Exit** if `plan.pages.length > 1` without that flag.

**One page ≠ one artboard.** Desktop / 768 / 390 of `/` are required
viewports of the same page. A required viewport cannot sit on allow-drift as
“not re-captured.”

Default `web-responsive`: 390×844, 768×1024, 1280×800, 1600. Load
pixel-perfect `responsive-scope-playbook.md` only when the user named a
non-default scope.

## Artifacts

```
source-site/index.html
source-site/index.raw.html
source-site/pages.json
source-site/scraped-tokens.md
source-site/assets/          # images + Latin fonts only
qa/fidelity-contract.md      # stub
qa/asset-ledger.json
qa/regressions.json          # []
```

**Forbidden.** Treating the scrape as the build. Firecrawl-to-HTML. Writing
`rebuild/index.html`. Downloading every unicode-range woff2 (Pitfall #185).
Copying sibling-project assets. Playwright in 1.1.

Mark done when `source-site/` exists (or the stub contract / `scraped-tokens.md`).
