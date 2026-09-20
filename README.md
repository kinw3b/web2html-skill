# Web2Html Skills

Point at any live URL. Get named layers, semantic HTML, and a reusable CSS token system. Then agents scale the rest of the pages.

## Install

```bash
npx github:kinw3b/web2html-skill
```

One command, fully reported. The installer:

1. Copies the skills to `~/.web2html/skills` — a permanent home. npx's own cache is disposable and is cleaned up at the end of the run.
2. Symlinks each skill by its plain name into every agent skills folder it knows: Claude Code, Cursor, Codex, Hermes, and `~/.agents/skills`. Existing symlinks are repointed and listed. Real folders are never touched.
3. Installs the npm dependencies the capture skills need (Playwright, plus Chromium if it is not already cached), so the first run has no surprises.

It does **not** install the Paper Capture Tool browser extension or its native bridge. That is an optional, separate download, only needed for the hover-capture step: [kinw3b/paper-bridge](https://github.com/kinw3b/paper-bridge).

Flags:

```
--dry-run        print the plan, change nothing
--home <dir>     install home (default ~/.web2html/skills)
--skip-deps      do not run npm install inside the skills
--skip-browser   do not download Playwright's Chromium
```

Or clone and link the checkout directly (edits are live immediately):

```bash
git clone https://github.com/kinw3b/web2html-skill.git
cd web2html-skill
node scripts/npx-install.js
```

Skill docs refer to `$SKILLS`. Set it once, to any linked folder:

```bash
export SKILLS="$HOME/.claude/skills"
```

## Skills included

| Skill | Invoke | What it does |
|---|---|---|
| **web2html** | `/web2html` | Main orchestrator — the full pipeline |
| **url-to-paper** | — | 1.2: Capture live pages into Paper |
| **hover-reel** | — | 1.3: Capture hover/component states |
| **design-tokens** | — | 2.1: Token extraction |
| **pixel-perfect** | — | 4.1: Pixel-perfect rebuilds |
| **impeccable** | — | 4.2: Design quality audit |
| **design-taste-frontend** | — | 4.3: Frontend design taste |
| **emil-design-eng** | — | 4.4: Motion & interaction polish |
| **find-animation-opportunities** | — | 4.5: Motion suggestions |
| **apple-design** | — | 4.6: Apple-style UI patterns |
| **web-design-guidelines** | — | 4.7: Accessibility & best practices |
| **frontend-design** | — | 4.8: Design direction |

## Usage

Once installed, open your AI agent and type:

```
Convert https://example.com to HTML
```

or use the shorthand:

```
/web2html
```

## Pipeline

The run spans three sessions:

1. **Capture** (1.1–1.4) — Scrape, Paper import, Design Library, human sign-off
2. **Build** (2.1–2.4) — Design System, author, validate, TAGS checkpoint
3. **QA** (3.1–3.4) — Accessibility, hover parity, semantics, human checkpoint
4. **Pages** (4.1–4.4, optional) — Extra URLs as Paper pages
5. **Astro** (5.1–5.6, optional) — Convert to Astro site

## License

MIT — fork it, ship it, just don't `!important` it.

## Links

- [Live demo](https://web2html.com)
- [Paper](https://paper.design/downloads)
- [Report a bug](https://github.com/kinw3b/web2html-skill/issues)
