import test from "node:test";
import assert from "node:assert/strict";
import {
  applyPaperTokenWritePlan,
  seedPaperLibraryTokens,
} from "../scripts/paper-token-writer.mjs";

test("token replacement failures propagate before later writes", async () => {
  const calls = [];
  const failure = new Error("set_tokens rejected");

  await assert.rejects(
    () => applyPaperTokenWritePlan({
      call: async (name, args) => {
        calls.push({ name, args });
        throw failure;
      },
      plan: {
        deletes: [{ id: "duplicate", name: "--color-ink", delete: true }],
        updates: [{ id: "ink", name: "--color-ink", value: "#111111" }],
        creates: [{ name: "--color-accent", value: "#FF0000", type: "color" }],
      },
    }),
    failure,
  );

  assert.deepEqual(calls.map(({ name }) => name), ["set_tokens"]);
});

test("token creation failures propagate", async () => {
  await assert.rejects(
    () => applyPaperTokenWritePlan({
      call: async (name) => {
        if (name === "create_tokens") throw new Error("create_tokens rejected");
      },
      plan: {
        deletes: [],
        updates: [],
        creates: [{ name: "--color-accent", value: "#FF0000", type: "color" }],
      },
    }),
    /create_tokens rejected/,
  );
});

test("foundations rendering upserts every Paper-compatible library token", async () => {
  const calls = [];
  const result = await seedPaperLibraryTokens({
    call: async (name, args) => calls.push({ name, args }),
    existing: [{ name: "--color-ink", value: "#000000" }],
    proposed: [
      { type: "color", name: "--color-ink", value: "#0D2C35" },
      { type: "spacing", name: "--spacing-4", value: "16px" },
      { type: "radius", name: "--radius-md", value: "6px" },
      { type: "shadow", name: "--shadow-sm", value: "0 1px 2px #0000000d" },
      { type: "fontStyle", name: "--font-style-italic", value: "italic" },
    ],
  });

  assert.deepEqual(calls.map(({ name }) => name), ["set_tokens", "create_tokens"]);
  assert.deepEqual(calls[0].args.tokens, [
    { name: "--color-ink", value: "#0D2C35" },
  ]);
  assert.deepEqual(calls[1].args.tokens.map((token) => token.name), [
    "--spacing-4",
    "--radius-md",
  ]);
  assert.equal(result.desired, 3);
  assert.equal(result.updated, 1);
  assert.equal(result.created, 2);
});

test("foundations rendering refuses an empty Paper token seed", async () => {
  await assert.rejects(
    () => seedPaperLibraryTokens({ call: async () => {}, proposed: [] }),
    /no Paper-compatible tokens/,
  );
});
