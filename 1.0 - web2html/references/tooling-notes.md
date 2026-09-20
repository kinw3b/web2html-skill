# Tooling notes — exact invocations that work

Read this **before** calling any pipeline script. Every entry below cost a failed
run and wasted context at least once. These are signatures and environment
facts, not theory.

---

## Environment (macOS, this machine)

| Fact | Consequence |
|---|---|
| **Playwright is installed for Python only** (`~/Library/Python/3.9/.../playwright`) | `import { chromium } from "playwright"` in a `.mjs` under the project **fails** with `ERR_MODULE_NOT_FOUND`. Write capture scripts in Python (`from playwright.sync_api import sync_playwright`). The `url-to-paper` scripts work because they resolve from their own skill directory. |
| **`cd` inside a Bash call does not reliably persist** | A later call can silently run from the Templates root and "find nothing". Always use absolute paths, or prefix each call with `cd <project> &&`. A skill invocation resets cwd. |
| Shell heredocs with `xargs -P -I{}` and nested quotes | Fails with `xargs: command line cannot be assembled, too long`. Write a small `.sh` file and run it instead. |

---

## Script signatures

### Retired: `discover-urls.mjs` / `capture-sections.mjs` / `site-to-paper.mjs`

These three scripts (the visible-Chrome, multi-page discovery + capture +
import workflow) are deleted (2.10.1). 1.2 is `hover-reel/scripts/capture-session.mjs`
— headless, one route (`/`), one hidden Chrome. The freeze traps these notes
used to describe (unbounded `onload` waits, `--keep-open` in a loop, piping
capture through `tail`) are fixed inside `capture-session.mjs` itself; if a
run still looks stuck past ~20s of silence, kill the PID and rerun with live
logs rather than waiting (Pitfall #112).

### `website-to-html/scripts/capture-build.py`

Mangles the URL (collapses `//`, then reports `index.html not found`). Use a local
Python Playwright shot script instead — see `qa/shot.py` in any completed project
for a working one. Note the pipeline no longer uses a server at all: pass an
absolute `file://…/rebuild/index.html` path.

### `website-to-html/scripts/section-diff-loop.py`

Pairs build blocks to source screenshots **in document order**. If the build has
a `<header>` as its first block and the scrape's `section-01.png` is the Hero,
every pair is shifted by one. Always pass explicit pairs:

```sh
python3 .../section-diff-loop.py "file://$PWD/rebuild/index.html" source-site/screenshots qa/diffs \
  --pair best-food-for:1 --pair browse-our-menu:2 ...
```

---

## Context discipline (this is what actually blows the budget)

| Do | Don't |
|---|---|
| Crop before reading: `Image.open(p).crop(box).save(small)` then `Read` the crop | `Read` a 1600×5593 full-page PNG — one read can cost more than an entire stage |
| Use **Edit/Write** tools to change files under `rebuild/` | `cat >> rebuild/css/x.css <<'EOF'` — the harness detects the out-of-band write and echoes the **whole file** back into context. Twice, that is thousands of lines. |
| Ask agents to return compact JSON with a hard shape | Let agents return prose; five agents × prose is a large fraction of the budget |
| Extract page content **once** into `analysis/content-<page>.json`, verbatim | Re-dump the same section three times because the first dump was lossy |
| `grep -c` / `head` on greps | Dump whole HTML or CSS files into the transcript |

**Screenshot rule of thumb:** full-page reads only when you genuinely need
whole-page rhythm. For everything else crop to the section, and downscale — a
900px-wide crop is legible for structural review and a fraction of the cost.
