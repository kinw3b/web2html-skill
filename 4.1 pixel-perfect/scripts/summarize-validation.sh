#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  summarize-validation.sh \
    --report <validation.json> \
    [--previous <previous-summary.json>] \
    [--issue-ledger <issue-ledger.json>] \
    [--previous-issue-ledger <previous-issue-ledger.json>] \
    [--mode <iteration|final>] \
    [--format <json|md>] \
    [--viewport-label <label>] \
    [--top <count>]

Notes:
- Reads full validator output and emits a compact projection for LLM-facing updates.
- Does not modify validator artifacts.
- Use --mode iteration during refine loops and --mode final at completion handoff.
USAGE
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 2
  }
}

REPORT=""
PREVIOUS=""
ISSUE_LEDGER=""
PREVIOUS_ISSUE_LEDGER=""
MODE="iteration"
FORMAT="json"
VIEWPORT_LABEL=""
TOP_N="3"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --report)
      REPORT="$2"
      shift 2
      ;;
    --previous)
      PREVIOUS="$2"
      shift 2
      ;;
    --issue-ledger)
      ISSUE_LEDGER="$2"
      shift 2
      ;;
    --previous-issue-ledger)
      PREVIOUS_ISSUE_LEDGER="$2"
      shift 2
      ;;
    --mode)
      MODE="$2"
      shift 2
      ;;
    --format)
      FORMAT="$2"
      shift 2
      ;;
    --viewport-label)
      VIEWPORT_LABEL="$2"
      shift 2
      ;;
    --top)
      TOP_N="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

[[ -n "$REPORT" ]] || {
  usage
  exit 2
}

[[ -f "$REPORT" ]] || {
  echo "Report file not found: $REPORT" >&2
  exit 2
}

case "$MODE" in
  iteration|final) ;;
  *)
    echo "Unknown mode: $MODE" >&2
    exit 2
    ;;
esac

case "$FORMAT" in
  json|md) ;;
  *)
    echo "Unknown format: $FORMAT" >&2
    exit 2
    ;;
esac

if ! [[ "$TOP_N" =~ ^[0-9]+$ ]]; then
  echo "--top must be a non-negative integer" >&2
  exit 2
fi

require_cmd jq
require_cmd awk

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT

failed_checks_file="$tmpdir/failed_checks.json"
top_drifts_file="$tmpdir/top_drifts.json"
failure_delta_file="$tmpdir/failure_delta.json"
issue_delta_file="$tmpdir/issue_delta.json"
summary_file="$tmpdir/summary.json"

jq '
  def section_failures:
    (.sections // [])
    | map(select(.pass == false) | {
        id,
        check_type: "section",
        metric: "diff_percent",
        value: .diff_percent,
        threshold: .threshold_percent,
        drift: .diff_percent,
        severity_ratio: (if (.threshold_percent // 0) == 0 then 0 else (.diff_percent / .threshold_percent) end)
      });
  def text_failures:
    (.text_checks // [])
    | map(select(.pass == false) | {
        id,
        check_type: "text",
        metric: "drift_px",
        value: .drift_px,
        threshold: .threshold_px,
        drift: .drift_px,
        severity_ratio: (if (.threshold_px // 0) == 0 then 0 else (.drift_px / .threshold_px) end)
      });
  def spacing_failures:
    (.spacing_checks // [])
    | map(select(.pass == false) | {
        id,
        check_type: "spacing",
        metric: "drift_px",
        value: .drift_px,
        threshold: .threshold_px,
        drift: .drift_px,
        severity_ratio: (if (.threshold_px // 0) == 0 then 0 else (.drift_px / .threshold_px) end)
      });
  def color_failures:
    (.color_checks // [])
    | map(select(.pass == false) | {
        id,
        check_type: "color",
        metric: "delta_e",
        value: .delta_e,
        threshold: .threshold_delta_e,
        drift: .delta_e,
        severity_ratio: (if (.threshold_delta_e // 0) == 0 then 0 else (.delta_e / .threshold_delta_e) end)
      });
  (section_failures + text_failures + spacing_failures + color_failures)
' "$REPORT" >"$failed_checks_file"

jq --argjson top "$TOP_N" '
  sort_by(.severity_ratio) | reverse | .[:$top]
' "$failed_checks_file" >"$top_drifts_file"

if [[ -n "$PREVIOUS" && -f "$PREVIOUS" ]]; then
  jq -n \
    --slurpfile previous "$PREVIOUS" \
    --slurpfile current "$failed_checks_file" '
      def ids(arr): arr | map(.id);
      {
        compared_to: "previous_summary",
        new_failures: ((ids($current[0]) - ids($previous[0].failed_checks // [])) | unique),
        resolved_failures: ((ids($previous[0].failed_checks // []) - ids($current[0])) | unique)
      }
    ' >"$failure_delta_file"
else
  jq -n '{compared_to: null, new_failures: [], resolved_failures: []}' >"$failure_delta_file"
fi

if [[ -n "$ISSUE_LEDGER" && -f "$ISSUE_LEDGER" && -n "$PREVIOUS_ISSUE_LEDGER" && -f "$PREVIOUS_ISSUE_LEDGER" ]]; then
  jq -n \
    --slurpfile current "$ISSUE_LEDGER" \
    --slurpfile previous "$PREVIOUS_ISSUE_LEDGER" '
      def resolved_status(s): (s == "fixed" or s == "accepted_by_user" or s == "renderer_only_drift");
      def to_map(arr): reduce arr[] as $i ({}; .[$i.id] = $i.status);
      (to_map($current[0])) as $cur
      | (to_map($previous[0])) as $prev
      | ($cur | keys) as $cur_ids
      | ($prev | keys) as $prev_ids
      | {
          new: ($cur_ids - $prev_ids),
          resolved: [
            ($cur_ids[] | select(($prev[.] != null) and (resolved_status($cur[.])) and (resolved_status($prev[.]) | not)))
          ],
          regressed: [
            ($cur_ids[] | select(($prev[.] != null) and (resolved_status($prev[.])) and (resolved_status($cur[.]) | not)))
          ],
          unchanged_count: [
            ($cur_ids[] | select(($prev[.] != null) and ($prev[.] == $cur[.])))
          ] | length
        }
    ' >"$issue_delta_file"
else
  jq -n '{new: [], resolved: [], regressed: [], unchanged_count: 0}' >"$issue_delta_file"
fi

summary_json=$(jq -n \
  --arg mode "$MODE" \
  --arg report_path "$REPORT" \
  --arg viewport_label "$VIEWPORT_LABEL" \
  --slurpfile report "$REPORT" \
  --slurpfile failed "$failed_checks_file" \
  --slurpfile top "$top_drifts_file" \
  --slurpfile delta "$failure_delta_file" \
  --slurpfile issue_delta "$issue_delta_file" '
  ($report[0].image_dimensions.width | tostring) as $w
  | ($report[0].image_dimensions.height | tostring) as $h
  | ($viewport_label | if length > 0 then . else ($w + "x" + $h) end) as $vp
  | {
      mode: $mode,
      report_path: $report_path,
      profile: $report[0].profile,
      overall_status: (if $report[0].pass then "pass" else "fail" end),
      global: {
        diff_percent: $report[0].global.diff_percent,
        threshold_percent: $report[0].global.threshold_percent,
        pass: $report[0].global.pass
      },
      viewport_status: [
        {
          viewport: $vp,
          status: (if $report[0].pass then "pass" else "fail" end),
          failed_check_count: ($failed[0] | length)
        }
      ],
      failed_checks: $failed[0],
      top_drifts: $top[0],
      failure_delta: $delta[0],
      issue_deltas: $issue_delta[0],
      next_actions: (
        if $report[0].pass then
          ["No blocking validation failures. Proceed with final verification handoff or next viewport."]
        else
          ["Fix top drift offenders first, then re-capture and re-run validation.",
           "Request targeted slices only for failed components if additional context is needed."]
        end
      )
    }
')

printf '%s\n' "$summary_json" >"$summary_file"

if [[ "$FORMAT" == "json" ]]; then
  cat "$summary_file"
  exit 0
fi

jq -r '
  "## Validation Summary (" + .mode + ")\n" +
  "- Report artifact: `" + .report_path + "`\n" +
  "- Profile: `" + .profile + "`\n" +
  "- Overall: `" + .overall_status + "`\n" +
  "- Global diff: " + (.global.diff_percent | tostring) + "% (threshold " + (.global.threshold_percent | tostring) + "%)\n" +
  "- Failed checks: " + ((.failed_checks | length) | tostring) + "\n" +
  "- New failures vs previous summary: " + ((.failure_delta.new_failures | length) | tostring) + "\n" +
  "- Resolved failures vs previous summary: " + ((.failure_delta.resolved_failures | length) | tostring) + "\n" +
  "- Issue deltas: new=" + ((.issue_deltas.new | length) | tostring) +
    ", resolved=" + ((.issue_deltas.resolved | length) | tostring) +
    ", regressed=" + ((.issue_deltas.regressed | length) | tostring) + "\n\n" +
  "### Top Drifts\n" +
  (
    if (.top_drifts | length) == 0 then "- none\n"
    else (.top_drifts | map("- `" + .id + "` [" + .check_type + "] value=" + (.value|tostring) + ", threshold=" + (.threshold|tostring) + ", ratio=" + (.severity_ratio|tostring)) | join("\n")) + "\n"
    end
  ) +
  "\n### Next Actions\n" +
  (.next_actions | map("- " + .) | join("\n")) + "\n"
' "$summary_file"
