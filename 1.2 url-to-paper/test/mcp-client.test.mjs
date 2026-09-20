import test from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import { spawn } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";

test("MCP timeout covers a response body that never finishes", async (t) => {
  const server = http.createServer((_req, res) => {
    res.writeHead(200, { "content-type": "text/event-stream" });
    res.write('data: {"jsonrpc":"2.0","id":1');
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  t.after(() => server.close());
  const { port } = server.address();
  const moduleUrl = pathToFileURL(fileURLToPath(new URL("../scripts/mcp-client.mjs", import.meta.url))).href;
  const script = `
    import { rpc } from ${JSON.stringify(moduleUrl)};
    try {
      await rpc("tools/call", {}, { timeoutMs: 50 });
      process.exit(2);
    } catch (error) {
      console.error(error.message);
      process.exit(/timed out after 50ms/.test(error.message) ? 0 : 3);
    }
  `;

  const result = await new Promise((resolve) => {
    const child = spawn(process.execPath, ["--input-type=module", "--eval", script], {
      env: { ...process.env, PAPER_MCP: `http://127.0.0.1:${port}/mcp` },
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stderr = "";
    child.stderr.on("data", (chunk) => { stderr += chunk; });
    const timer = setTimeout(() => {
      child.kill();
      resolve({ code: null, stderr: `${stderr}\nchild hung after response headers` });
    }, 500);
    child.on("close", (code) => {
      clearTimeout(timer);
      resolve({ code, stderr });
    });
  });

  assert.equal(result.code, 0, result.stderr);
});
