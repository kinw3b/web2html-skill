# Orca relay: probe, waves, relay

Read **once** when `harness_probe.py` says `orca reachable`. If it says anything
else, close this file for Orca verbs — never load `orchestration` / `orca-cli`.
**2.3 VALIDATE LOOK still runs `wave.py`** on the `serial` (or `subagent`) rung
(Pitfall #221). Orca is an accelerator for *terminals*. The lease, the gates,
the receipts, and the human stops are identical on every rung.

## Probe — first line after `start` / `resume`

`start` and `resume` already print it. Re-run any time:

```sh
python3 $SKILLS/web2html/scripts/harness_probe.py "$PROJECT" --brief
# harness claude-code · agent claude · orca reachable · waves orca · relay orca-terminal · context 28% (transcript)
```

It writes `qa/harness-probe.json` and always exits 0. Two rungs are chosen:

| Rung | Order | Meaning |
|---|---|---|
| `waves` | `orca` → `subagent` → `serial` | how the parallel-safe unit of 2.3 / 3.2 / 5.2 is fanned out |
| `relay` | `orca-terminal` → `print-prompt` | how a mid-session handoff reaches the next agent |

**Same-source rule (Pitfall #220).** The Orca agent id comes from Orca's own view
of this terminal (`terminal show` → `agentIdentity`), else the harness marker, else
`WEB2HTML_ORCA_AGENT`. If none answers, the Orca rungs are **off**. A Claude
orchestrator spawns Claude workers, a Codex orchestrator spawns Codex workers.
Never pass `--model`; the tier stays advice. `WEB2HTML_WAVE_MODEL` is the operator's
explicit override, nothing else sets it.

**Dispatched worker?** If your prompt carries a live Orca Task / Dispatch preamble,
you are a worker, not the controller: do only the spec, never `start` / `resume` /
`wave.py start` / `relay`. Read the spec's ACCEPTANCE line and send `worker_done`.

## Version-matched guide

The installed `orchestration` and `orca-cli` skills are stubs on purpose. Before
the first Orca verb of a session, print the guide from the binary you will run:

```sh
orca skills get orchestration        # supervised workers, check --wait, release
orca skills get orca-cli             # terminals, worktrees, send receipts
```

Use `ORCA_CLI_COMMAND` when set (the probe prints the resolved path). Never bare
`orca` on Linux outside an Orca terminal. If a verb reports Orca is not running,
that is a lower rung, not a retry.

## Context budget

```sh
python3 $SKILLS/web2html/scripts/context_budget.py "$PROJECT" --brief
# budget: 52.0% of 200k (transcript)  RELAY armed
```

Every `mark` prints this line. Signals, best available wins: Claude Code transcript
usage → opt-in statusline sidecar → the pipeline's own spend ledger (fed by
`--shoot`, `--record`, `mark`). Window: `WEB2HTML_CONTEXT_WINDOW`, else `[1m]` on the
Claude Code model → 1,000,000, else 200,000. Thresholds `WEB2HTML_RELAY_ARM` (50) and
`WEB2HTML_RELAY_FORCE` (75). `unknown` is not an error; then relay on the operator's
call or after ~6 bands per owner.

## Relay — a change of agent, never a yield (Pitfall #218)

Armed → finish the current unit (record the band, write the receipt) → relay:

```sh
python3 $SKILLS/web2html/scripts/pipeline-progress.py relay "$PROJECT" --owner session-2
```

What it does, in order:

1. Refuses unless you hold the lease, the step is agent work (not an active
   human checkpoint), and the disk is at a boundary: no band shot-but-unrecorded,
   no wave with running workers (`--force` overrides both).
2. Writes `qa/handoff-<step>.relayN.md`: project, source, Paper id, board, the step,
   the receipts on disk, the exact first commands (`resume "<project>" --at <step>
   --owner session-2b`), the fidelity lock, and "this is a relay, not a checkpoint".
3. Releases the controller lease exactly as 1.4 / 2.4 done do; appends to `relays[]`.
4. `orca-terminal`: `terminal create --worktree id:<your Orca worktree> --command <same agent>`
   → `terminal wait --for tui-idle` (reads `satisfied`, retries once) → `terminal send
   --enter --wait-submit 10` (reads `accepted`). Started → **end your turn** with one
   board line. No CTA. No question.
5. Not started (`satisfied` false twice, `accepted` false) → the lease comes **back
   to you**, the prompt is printed, exit 3. Continue in place or paste it. A run is
   never left ownerless.
6. `print-prompt` (no Orca): prints the block like `handoff-2.0.md`, exit 0. The
   operator pastes it into a new session of the same agent.

Successor: `resume "<project>" --at <step> --owner session-2b`. The step stays
`active`; continue it, mark it done, walk on. Owners chain `session-2b`, `-2c`, ….

**Pre-warm.** At 1.4 / 2.4 / 3.4, while the human reviews, an Orca rung may
`terminal create` the next session's terminal early; send the handoff prompt only
after the checkpoint is signed.

## Waves — parallel reads, serial writes

**2.3 VALIDATE LOOK is required.** After `--shoot-open`, run `wave.py
prepare/start/wait/apply`. Skipping it fails `section_22_gate.py` (Pitfall
#221). 3.2 companion receipts and 5.2 page bodies may wave when the probe
rung is `orca` or `subagent`; they may stay serial.

The worker is a read-only reviewer in the `agent_loop.py` lane: SHA snapshot, one
reviewer lease per task, one finding file under `qa/agent-findings/<run>/<phase>/`.
The controller shoots, applies, records. `section_22_gate.py` requires an
applied `qa/agent-runs/<run>/2.3/wave.json` covering every band; it still
cannot tell `orca` from `serial` — both write that file.

| Step | Task | Worker does (read-only) | Controller does |
|---|---|---|---|
| 2.3 | one open band | Read the three `NN-<band>-{1600,768,390}-side.png`, write verdict + `seen` + misses + patch proposal | `--shoot` every open band **before** `prepare`; after the wave: apply each patch, `--record` from the finding, `--shoot` the next round |
| 3.2 | one companion skill | run `web-design-guidelines` / `find-animation-opportunities` / `apple-design` on `index-polish.html`; write the report `.md` + finding | `apply` promotes each report to `qa/<skill>.md` (Pitfall #215) |
| 5.2 | one interior page | author `astro/src/pages/{slug}.astro` `<main>` only | serial `get_jsx` dumps first; `record-phase-5-pages.py` after |

Never a wave: 1.2 / 1.3 (serial Paper writes), 2.2 (one author, one vocabulary).

```sh
W=$SKILLS/web2html/scripts/wave.py
# 2.3 — REQUIRED. Controller first shoots every open band, then:
python3 $SKILLS/web2html/scripts/paper_23_validate.py "$PROJECT" --shoot-open
python3 $W prepare "$PROJECT" --phase 2.3 --run-id r1            # snapshot + one lease per open band
python3 $W start   "$PROJECT" --phase 2.3 --run-id r1            # orca: run-create + worker-start per task
python3 $W wait    "$PROJECT" --phase 2.3 --run-id r1            # one check --wait; validates, releases, acks
python3 $W ready   "$PROJECT" --phase 2.3 --run-id r1            # exit 0 when every finding is current
python3 $W apply   "$PROJECT" --phase 2.3 --run-id r1            # prints patch + --record per band
```

`start` on the `subagent` or `serial` rung prints each task spec instead: dispatch
it to your harness's subagent (same model family) or do it yourself, write the
same finding file, then `ready` / `apply`. That is still a 2.3 wave — do not
fall back to a solo Read loop. `wave.py check … --agent <task>` is the
worker's self-check on every harness. Do not substitute this harness's
subagent tool for `orca orchestration worker-start` when the adapter is `orca`.

Orca rules the helper keeps, and you must keep when driving verbs by hand:

- `worker-start` non-zero → **never relaunch**; read `failedStage`; the remaining
  tasks drop a rung.
- `check --wait` timeout or empty → a checkpoint, not a failure. `wait` exits 4 when a
  worker asked or escalated: answer with `orca orchestration reply --id <id> --body …`,
  then `wait … --ack <delivery>`.
- After an accepted `worker_done`, the settled terminal is released (`worker-release`),
  never `terminal close`d. `ready` + `apply` release the reviewer leases.
- Workers never edit `rebuild/`, `qa/paper-measure/*.validate.json`, or `qa/<skill>.md`.
  A finding whose `inputSha256` no longer matches the snapshot is stale and rejected.

Default `--max-workers`: 2.3 → 4, 3.2 → 3, 5.2 → 2 (the 5.2 two-author policy).
The old "max two workers" at 2.3 is about in-process **writers**; wave reviewers
do not write the ship.

## Documents open in the Orca browser

Inside a reachable Orca, every HTML the pipeline hands the human opens as an Orca
browser tab in the coordinator's worktree (`open_doc.py` → `orca tab create --url
file://… --worktree id:$ORCA_WORKTREE_ID`): the live board at `start`, the 2.4 TAGS
review, the 3.4 lock / polish / report trio, the 5.6 built routes. Outside Orca, or
when the tab cannot be created, the same call falls back to the previous opener
(Chrome on macOS, `open` / `xdg-open` otherwise). `WEB2HTML_BROWSER=default` keeps
Chrome; `=orca` refuses the fallback and prints the URI. The Capture Tool still
needs a Chromium with the extension and Paper opens in its own app; neither goes
through this path. Orca 1.4.206 exposes no pane placement for browser tabs — the
tab lands in the worktree's browser surface and is made active.

## Budget you are aiming at

Agent wall-clock for the homepage run, human stops excluded: median ≈ 33 min today,
≈ 25 with waves at 2.3 / 3.2 plus concurrent 768/390 shots inside
`capture-session.mjs`; heavy sites ≈ 40. Session 1 is the long pole and has no
agent-level parallelism (Paper writes are serial).
