# Report Template

Use one of these two modes:

1. `Iteration report` for refine loops (LLM-facing, compact, delta-oriented).
2. `Final report` for completion handoff (full-fidelity, complete audit trail).

Do not enforce fixed token caps. Keep iteration output concise by structure (failures and deltas only), not by hard limits.

---

## Iteration Report
- Mode: `iteration`
- Validation artifact file:
- Previous summary file (if any):
- Issue ledger file (if any):
- Profile:
- Overall status:
- Global diff:
- Failed check count:
- New failures vs previous summary:
- Resolved failures vs previous summary:

### Viewport Deltas
Repeat this block for each required viewport.

#### Viewport: <width>x<height>
- Status:
- Failed checks only:
- Top drift offenders:
- Changed component-property rows only:
- Marked issue status changes only:

### Next Action
- Highest-priority fix target:
- Re-capture needed (yes/no):
- Targeted slice requests needed (if any):

---

## Final Report
Use these exact headings in this exact order.

## Execution Plan
- Source type:
- Measurement approach:
- Implementation target:
- Validation approach:
- Known risks:

## Viewport Set + Profile Selection
- Source classification: `web-responsive` | `web-fixed` | `mobile-nonadaptive` | `mobile-adaptive`
- Selected viewport set:
- Validation profile: `lenient` | `portable` | `strict` | `ultra`
- Selection reason:
- Deviations from defaults:

## Acceptance Contract
- Must-match list:
- Ignore list:
- Portable-allowed drift:

## Measurement Spec
- Screen metadata:
- Component hierarchy:
- Section-by-section measurements:
- Typography spec:
- Color palette:
- Border and radius spec:
- Iconography spec:
- Asset parity + user decisions:
- Interaction and state notes:
- Platform translation notes:

## Asset Parity + User Decisions
- Decision summary (must match Measurement Spec section 8):
- Missing assets:
- Fallback options presented:
- User decision (required when assets are missing):
- Expected visual impact of chosen path:

## Implementation Notes
- Sections implemented:
- Explicit values used:
- Non-default styling decisions:
- Blockers encountered:

## Primary Validation Artifacts
- Reference artifacts used:
- Marked comparison screenshots used (if provided):
- Why these artifacts are primary:

## Validation Results (per viewport)
Repeat this block for each required viewport.

### Viewport: <width>x<height>
- Global pixel difference:
- Per-section differences:
- Text baseline/text block drift:
- Spacing deltas:
- Color deltaE checks:
- Pass/fail summary:
- Component-Property Validation Table (required):

| Component | Property | Desired Value | Actual Value | Drift | Result (`good` \| `bad` \| `bad_with_reason`) | Reason |
|---|---|---|---|---|---|---|
| header_title | font_size | 24px | 24px | 0px | good | |
| tab_selected | color | #5B5CE6 | #625FE9 | deltaE 1.8 | bad | |
| send_icon | icon_family | Lucide | FontAwesome6 | different family | bad_with_reason | Temporary fallback approved by user |

- Marked Issue Checklist:
  - Issue id:
  - Resolved (yes/no):
  - Status (`fixed` | `accepted_by_user` | `renderer_only_drift`):
  - Reason (required for `renderer_only_drift`):

## Validation Freshness
- Latest substantive UI edit reference:
- Latest capture set reference:
- Report generated after latest capture (yes/no):
- Post-edit full loop completed (`capture -> compare -> fix -> re-capture`) (yes/no):

## Open Mismatches or Blockers
- Remaining mismatch list:
- Root cause:
- Next refinement action:

## User Verification Handoff
- Done statement ("I believe this is done"):
- Side-by-side visual proof:
  - Reference/design image:
  - Actual app image:
- User verification question asked (yes/no):
- Missed-detail prompt included (yes/no):
