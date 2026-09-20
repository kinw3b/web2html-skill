// Apply a prepared Paper token write plan without converting write failures
// into a successful extraction process.

import { paperCreateTokens, tokenWritePlan } from "./library-tokens.mjs";

export async function applyPaperTokenWritePlan({ call, plan, batchSize = 60 }) {
  for (let i = 0; i < plan.deletes.length; i += batchSize) {
    await call("set_tokens", { tokens: plan.deletes.slice(i, i + batchSize) });
  }
  for (let i = 0; i < plan.updates.length; i += batchSize) {
    await call("set_tokens", { tokens: plan.updates.slice(i, i + batchSize) });
  }
  if (plan.creates.length) {
    await call("create_tokens", { tokens: plan.creates });
  }
}

// A foundations render must never paint a complete sheet while leaving Paper's
// Theme panel stale. Upsert every token type Paper supports before writing the
// sheet. Shadows and font styles remain CSS-only because Paper has no matching
// token type; paperCreateTokens owns that explicit filter.
export async function seedPaperLibraryTokens({
  call,
  proposed = [],
  existing = [],
  batchSize = 60,
} = {}) {
  if (!call) throw new Error("seedPaperLibraryTokens needs call()");
  const desired = paperCreateTokens(proposed);
  if (!desired.length) {
    throw new Error("foundations render has no Paper-compatible tokens to seed");
  }
  const plan = tokenWritePlan(desired, existing);
  await applyPaperTokenWritePlan({ call, plan, batchSize });
  return {
    desired: desired.length,
    created: plan.creates.length,
    updated: plan.updates.length,
    names: desired.map((token) => token.name),
  };
}
