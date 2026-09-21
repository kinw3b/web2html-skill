# Live board, todos, never-reuse

Read **once at summon**. Then mark as you walk. Do not reload `SKILL.md`.

## First action

New run:

```sh
python3 $SKILLS/web2html/scripts/pipeline-progress.py start /path/to/templates/<project>
```

Continued session 2 or 3 — **never `start`** (it resets the board, Pitfall #179):

```sh
python3 $SKILLS/web2html/scripts/pipeline-progress.py resume . --at 2.1 --owner session-2
```

`start` writes **and opens** `<project>/pipeline.html` **once**. `resume`,
`mark`, and later sessions never reopen it — assume that tab is still open.
If **start** does not open the board, **stop**. Print the `file://` URI. Never overwrite the spec
`web2html/pipeline.html`. Never pass the web2html repo as `start` root.
Derive `<project>` from the URL slug under `Documents/templates/<project>`.

Stamp every boundary:

```sh
python3 $SKILLS/web2html/scripts/pipeline-progress.py mark "$PROJECT" --step 1.2 --status active
python3 $SKILLS/web2html/scripts/pipeline-progress.py mark "$PROJECT" --step 1.2 --status done
```

`mark` cannot open 2.1+ while 1.1–1.4 are unfinished. `skip` fails.

## Todos

One todo per child. IDs **are** the board IDs. Prefer `TodoWrite`.

| Parent | Child | Name |
|---|---|---|
| 1.0 | 1.1 | Light scrape (URL + images + Latin fonts) |
| 1.0 | 1.2 | Homepage, breakpoints + geometry postflight |
| 1.0 | 1.3 | Mine once + create Design Library + Buttons/Components + source-CSS hover |
| 1.0 | 1.4 | Human checkpoint |
| 2.0 | 2.1 | Design System |
| 2.0 | 2.2 | Author semantic responsive page |
| 2.0 | 2.3 | Validate each section vs Paper |
| 2.0 | 2.4 | Sign-off → 3.0 polish |
| 3.0 | 3.1 | QA pass 1 — a11y + contrast + anti-slop |
| 3.0 | 3.2 | QA pass 2 — 1.3 source-CSS hover + painted burger drawer + FAQ accordion + nav dropdowns + mandatory GSAP in-view + guidelines a11y |
| 3.0 | 3.3 | Semantics + SEO sweep (freeze-structure) |
| 3.0 | 3.4 | Human checkpoint |
| 4.0 | 4.1 | Sitemap (optional) |
| 4.0 | 4.2 | Capture pages (optional) |
| 4.0 | 4.3 | Seed tokens (optional) |
| 4.0 | 4.4 | Human review (optional) |
| 5.0 | 5.1 | Scaffold Astro (optional) |
| 5.0 | 5.2 | Author pages (optional) |
| 5.0 | 5.3 | Desktop QA (optional) |
| 5.0 | 5.4 | Responsive (optional) |
| 5.0 | 5.5 | Wire routes + SEO (optional) |
| 5.0 | 5.6 | Human checkpoint (optional) |

Exactly one foreground child `in_progress`. Enter → `mark --status active` +
todo. Exit → `done` then next `in_progress`. Banner:

```
▶ 1.2 — Breakpoints · Paper + geometry   [1.1✓ ▶1.2 1.3 1.4 | 2.0 | 2.4]
NEXT  3.1  QA pass 1                     [after 2.4 done — Session 3 polish not started]
```

Idle (no active step, run not finished) is **NEXT**, never Ready. After 2.4
done the Here/Next strip is `2.4 signed` → `3.1 Session 3 polish — not started`.

Human stops: **1.4**, **2.4**, **3.4**, optional **4.4**, and optional **5.6**. Everything else runs.

## Session yield

Each session returns to the human at **exactly one** checkpoint. Do not
stop, ask, or fire a Continue CTA anywhere else.

| Session | Runs without yielding | Yields at |
|---|---|---|
| 1 · capture | 1.1 → 1.2 → 1.3 → 1.4 | **1.4** |
| 2 · build | 2.1 → 2.2 → 2.3 → 2.4 | **2.4** |
| 3 · QA | 3.1 → 3.2 → 3.3 → 3.4 | **3.4** |
| 4 · pages (optional) | 4.1 → 4.2 → 4.3 → 4.4 | **4.4** |
| 5 · astro site (optional) | 5.1 → 5.2 → 5.3 → 5.4 → 5.5 → 5.6 | **5.6** |

**Session 2:** do not stop after emitting 2.1, after authoring 2.2, or
mid-2.3. Sign every homepage section at 1600 / 768 / 390 in this session
(disk clips; VALIDATE LOOK is `wave.py`; no Paper MCP). The only stop is
2.4 (TAGS Chrome + Continue). Pitfall #192 #195.

## Human stop CTA (any harness)

Do **not** ask for a paragraph. Fire one native blocking choice / CTA /
question tool if this session has one (Hermes `clarify`, Claude Code
`AskUserQuestion`, Cursor `AskQuestion`, Codex approval cards). Do **not**
invent a tool this harness does not expose. If it does not: print the
same labels and wait. Timeout or a dismissed card → stay stopped. Human
checkpoints are not "use best judgement." Pitfall #190.

### 1.4 — two-option question modal

Session 1 yields **once**. After `mark --step 1.4 --status active` (Paper
open, browser open on the stamped source URL, `qa/paper-human-review.md`
written), fire **one** question. If the mark printed `capture doctor: FAIL`,
relay the printed fix command in the question text.

**Instructions in the question (required — not extra choices):**

- Walk 1600 / 768 / 390, FRAME `Navigation`, FRAME `Buttons`, FRAME
  `Components`, and the Design Library. Pin comments on anything wrong.
  2.0 will not start until those threads are handled.
- Capture Tool is optional leftover live hover. The stamped tab is already
  open; `pipeline-progress.py open-capture` re-opens it. Do not treat it as
  required.

**Choices, in this order, with these labels:**

1. `Done & continue to next step`
3. `Provide hand-off prompt to start fresh session`

Typed equivalents: `Continue` / the first label → choice 1. `handoff` /
the second label → choice 3.

| Choice | Agent does |
|---|---|
| **1 · Done & continue to next step** | `mark --step 1.4 --status done` and continue into 2.1 **in this session**. The mark still writes `qa/handoff-2.0.md`. |
| **3 · Provide hand-off prompt** | Do not start 2.1. If `qa/paper-human-review.md` exists, `mark --step 1.4 --status done` (that prints the prompt). If not, `pipeline-progress.py handoff` (draft) and stay stopped. |

### 2.4 — Continue to 3.0 polish

Last action is a blocking **Continue to 3.0 polish (3.1–3.4)**. The resume
token is still the word `Continue` in every harness. Do not mark the step
done until Continue (or a clear equivalent). Polish has not run. Do not
create `index-polish.html` here — 3.1 copies the lock when it goes active.

The live board after 2.4 done must read **NEXT 3.1** (Session 3 polish —
not started), never a vague Ready, and must not show a polish file that
has not been worked.

### 3.4 — two-option (homepage finish vs optional Phase 4)

After the polish compare, fire **one** question:

1. `Done — finish homepage run` → write `qa/phase-4-skipped.json`, `mark --step 3.4 --status done` (tidy).
2. `Continue to optional Phase 4` → write `qa/phase-4-opted.json`, `mark --step 3.4 --status done` (no tidy), then `mark --step 4.1 --status active`.

### 4.4 — two-option (Paper finish vs optional Phase 5)

Walk the extra Paper pages, pin comments, write `qa/phase-4-review.md`. Then fire **one** question:

1. `Done — finish Paper run` → write `qa/phase-5-skipped.json`, `mark --step 4.4 --status done` (tidy).
2. `Continue to optional Phase 5` → write `qa/phase-5-opted.json`, `mark --step 4.4 --status done` (no tidy, prints `qa/handoff-5.0.md`), then `mark --step 5.1 --status active`.

### 5.6 — single Continue

`open-phase-5-review.py` writes `qa/phase-5-review.md` and opens the built home + first interior from `astro/dist` on `file://`. Walk every route (shared chrome = 3.4 polish; bodies = Paper). Then **Continue** and `mark --step 5.6 --status done` (tidy). Keeps `rebuild/` + `astro/` + `pipeline.html`.

Stops:

| Stop | When the CTA fires | Choice does |
|---|---|---|
| **1.4** after Paper open | `qa/paper-human-review.md` written, Paper open | see the two 1.4 choices above |
| **2.4** after TAGS Chrome | `qa/build-checkpoint-opened.json` | `mark --step 2.4 --status done` |
| **3.4** after 2.4 lock + QA polish + report | `open-human-review.py` opened Chrome on both HTML files | `mark --step 3.4 --status done` |
| **4.4** after extra Paper pages | `qa/phase-4-review.md` written, Paper open | see the two 4.4 choices above |
| **5.6** after the built Astro routes open | `qa/phase-5-review.md` | `mark --step 5.6 --status done` |

## Never reuse another project

Every run builds from **this** project's capture. Forbidden: `cp`/`rsync` of
another `rebuild/`, `tokens.css`, `capture/`, `design-library/`, Paper file,
`source-site/assets/`, or stale `qa/`. Skills (this package) are reusable;
project evidence is not. Paper files are not reusable either — 1.2 always
`create_file` (Pitfall #187).

Before 1.1 writes: `pwd`, `ls`, `ls ..` — similarly-named siblings are the trap.

## Do not ask

Once you have a URL, run. Do not ask to capture extra pages, skip the library,
skip QA, or pick a browser. Chrome. Homepage only. Stage L is work, not a prompt.

Folder contract: `references/gates.md`.
