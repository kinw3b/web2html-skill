#!/usr/bin/env node
/**
 * section-audit.mjs — Provenance-gated geometry audit.
 *
 * Fails unless actual values come from a fresh rendered-DOM extraction
 * (source.kind === "rendered-dom" + capturedAt + numeric viewport).
 * Never accept desired copied into actual without DOM provenance.
 *
 * Usage: node section-audit.mjs <geometry.json>
 *
 * geometry.json shape:
 * {
 *   "source": {
 *     "kind": "rendered-dom",
 *     "capturedAt": "ISO-8601",
 *     "viewport": { "width": 1280, "height": 800 },
 *     "implementationRevision": "optional"
 *   },
 *   "items": [
 *     {
 *       "id": "primary-action",
 *       "critical": true,
 *       "properties": {
 *         "width": { "desired": 156, "actual": 156, "tolerance": 1 }
 *       }
 *     }
 *   ]
 * }
 */
import fs from "node:fs";

const path = process.argv[2];
if (!path) {
  console.error("Usage: node section-audit.mjs <geometry.json>");
  process.exit(2);
}

const data = JSON.parse(fs.readFileSync(path, "utf8"));
const provenancePass =
  data.source?.kind === "rendered-dom" &&
  typeof data.source?.capturedAt === "string" &&
  Number.isFinite(data.source?.viewport?.width) &&
  Number.isFinite(data.source?.viewport?.height);
const rows = [];
let criticalFailures = provenancePass ? 0 : 1;

for (const item of data.items ?? []) {
  for (const [property, check] of Object.entries(item.properties ?? {})) {
    const desired = check.desired;
    const actual = check.actual;
    const tolerance = Number(check.tolerance ?? 0);
    const present = desired !== undefined && actual !== undefined;
    const numeric = typeof desired === "number" && typeof actual === "number";
    const drift = !present
      ? "missing"
      : numeric
        ? Math.abs(desired - actual)
        : desired === actual
          ? 0
          : "different";
    const pass = present && (numeric ? drift <= tolerance : drift === 0);
    if (!pass && item.critical) criticalFailures += 1;
    rows.push({
      id: item.id,
      property,
      desired,
      actual,
      tolerance,
      drift,
      critical: Boolean(item.critical),
      result: pass ? "good" : "bad",
    });
  }
}

const report = {
  status: criticalFailures === 0 ? "pass" : "fail",
  provenance: provenancePass
    ? "good"
    : "bad: expected source.kind=rendered-dom, capturedAt, and numeric viewport",
  criticalFailures,
  rows,
};
process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
process.exit(criticalFailures === 0 ? 0 : 1);
