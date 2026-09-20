#!/usr/bin/env node
// Generic CLI for any Paper MCP tool.
//
// Usage: node paper-mcp.mjs <tool> '<json-args>'
//        node paper-mcp.mjs --list

import { call, listTools } from "./mcp-client.mjs";

const [, , toolName, argsJson] = process.argv;

if (!toolName || toolName === "--list") {
  for (const t of await listTools()) {
    const req = t.inputSchema?.required?.join(", ") || "";
    console.log(`${t.name}${req ? `  (required: ${req})` : ""}`);
    if (t.description) {
      console.log(`    ${t.description.split("\n")[0].slice(0, 150)}`);
    }
  }
  process.exit(0);
}

let args = {};
if (argsJson) {
  try {
    args = JSON.parse(argsJson);
  } catch {
    console.error(`args must be valid JSON, got: ${argsJson}`);
    process.exit(1);
  }
}

const result = await call(toolName, args);

for (const item of result.content ?? []) {
  if (item.type === "text") console.log(item.text);
  else console.log(`[${item.type}]${item.mimeType ? ` ${item.mimeType}` : ""} (${(item.data || "").length} b64 chars)`);
}
if (result.isError) process.exitCode = 1;
