> **RETIRED as a live 2.0 join recipe.** Keep the height-delta check as a
> 3.x watch. §2 below (`get_jsx` as structure source) is historical —
> 2.0 authors from the Paper visual brief, not from replaying `get_jsx`
> output. Do not teach Stage P → get_jsx / 2.2.a as the build.

# Running this pipeline lean

Written after a 6-page run that completed Stages F→7 but exhausted its context
before Steps 8–10. Note the headline finding: the run's biggest waste was not any
single expensive call — it was paying for Stage P and then never querying it. Everything here is about spending tokens where they buy
fidelity, and not spending them anywhere else.

---

## 1. The height-delta check — highest signal per token in the whole pipeline

Capture the live page and the build page full-height, and **compare the two
numbers**. Do not look at the images yet.

```python
# both sides get the same scroll-walk + settle, then:
h = page.evaluate("document.body.scrollHeight")
```

| Delta | Almost always means |
|---|---|
| < 5% | Spacing drift — a Step 8 concern |
| 10–20% | A component is collapsed (a card grid became a row, a list lost its cards) |
| > 25% | **A whole section is missing** |

In a prior lean QA run this instantly localized every serious defect:
about 3176 vs 4430 (missing video band), book 1445 vs 2282 (missing map),
home 5593 vs 6839 (menu grid collapsed + missing top bar).

**Run it at the end of Step 2, not at Step 7.** It costs one number per page and
it tells you where to point expensive vision review. Reviewing a section whose
height already matches is mostly wasted budget.

---

## 2. Get structure from `get_jsx`, not from a parser you wrote

Stage P already produced structure + measured styles. Query it:

```
get_children(<artboard id>)   # section list with node ids
get_jsx(<section id>)         # structure + exact values for that section
```

This is Paper's **Copy as… → Copy as React CSS / Tailwind**, over MCP. It is
verbose (SVGs inline, a few thousand tokens per section) and it is still the
cheap option: in a prior lean QA run, *not* calling it produced a collapsed card
grid and truncated copy, which then cost a QA agent, a verification round and a
fix round to recover — several times the price of the call.

Only when there is no MCP connection, fall back to parsing `capture/*.html` into
`analysis/content-<page>.json` — verbatim, ordered, **no dedup, no truncation**,
with per-section image lists and repeat counts. See Pitfall #13.

This also kills the most common context leak: re-dumping the same section three
times because each earlier dump was lossy in a different way.

---

## 3. Look at pixels cheaply

- **Crop, then read.** A 1600×5593 full-page PNG is one of the most expensive
  single objects you can put in context. Crop to the section and downscale to
  ~900px wide; structural review stays reliable.
- **One top-strip crop per site** (top 140px) at Stage L — catches the utility
  bar, real header background, and whether the header CTA is a pill or a plain
  link (Pitfall #14).
- Full-page reads: at most one, for whole-page rhythm, late.

---

## 4. Order that avoids rework

```
scrape + capture (parallel)  →  content JSON  →  top-strip crop  →  shared chrome
  →  homepage  →  height-delta all pages  →  interior pages  →  targeted QA
```

**Build the shared chrome first.** Header, footer and the utility bar are shared
organisms; `design-library/library.json` already reports which sections repeat
and how often. One edit at the shared layer corrected six pages in this run —
the best fix ratio available. Getting them wrong first means re-patching every
page later.

---

## 5. Where the orchestrator's budget actually goes

Measured, roughly in order:

1. Reading full-page screenshots
2. Tool-signature trial and error → **fixed by `references/tooling-notes.md`; read it first**
3. Shell `cat >>` on `rebuild/` files echoing whole files back → **use Edit/Write**
4. Re-extracting content after a lossy first pass → **fixed by §2 (use `get_jsx`)**
5. Agent reports → demand compact JSON with a fixed shape
6. Writing the actual site files → irreducible, this is the deliverable

Items 1–5 are all avoidable. Item 6 is the only one that should dominate.

---

## 6. Open proposal — parallelise the *build*, not the QA

**Status:** open proposal, not current policy. As of v2.0.0 the skill has **no**
parallel stage: Stage P is single-agent (Paper writes must stay serial) and Step 7
is one agent, one pass. If parallelism is ever added back, this is where it should
go — the build — because that is where token cost scales with page count.

With the 5-page cap this is rarely worth it. For a larger site, consider **one
build agent per interior page** after
the homepage and shared chrome are settled and the token set is frozen:

- The homepage establishes tokens, chrome and component vocabulary — it must stay
  with the orchestrator.
- Interior pages are then largely assembly from the same components. Give each
  agent its artboard node id and let it call `get_jsx` **itself** — the verbose
  structure lands in the agent's context, not the orchestrator's. This is the
  single best argument for the split.
- Each agent writes exactly one `rebuild/<page>.html` — no shared-file contention,
  which is the reason the serial rule exists in the first place.
- Orchestrator keeps CSS ownership; agents may only request new component classes,
  never author them (otherwise the design library fragments).

This preserves the real constraint (one writer per file, one owner for CSS) while
moving per-page extraction cost off the orchestrator's context. **Not yet
adopted** — flagged for a future run to try deliberately.
