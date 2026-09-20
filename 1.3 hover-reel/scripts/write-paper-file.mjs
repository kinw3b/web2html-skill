// write-to-paper.mjs targets whichever file its own MCP session made sticky,
// which is not necessarily the file this session is working in. This wrapper
// passes fileId explicitly so the write lands in the intended file.
//
//   node write-paper-file.mjs <htmlFile> <targetNodeId> <fileId> [mode]

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { importSibling } from './skill-paths.mjs';

const { call } = await importSibling('url-to-paper', 'scripts/mcp-client.mjs');

const [, , file, targetNodeId, fileId, mode = 'insert-children'] = process.argv;
if (!file || !targetNodeId || !fileId) {
  console.error('usage: node write-paper-file.mjs <htmlFile> <targetNodeId> <fileId> [mode]');
  process.exit(1);
}

const html = readFileSync(resolve(file), 'utf8');
console.error(`· writing ${html.length} bytes → ${targetNodeId} in ${fileId} (${mode})`);

const result = await call('write_html', { html, targetNodeId, mode, fileId });

const created = [];
for (const item of result.content ?? []) {
  if (item.type === 'text') {
    try {
      const parsed = JSON.parse(item.text);
      if (parsed.createdNodes) created.push(...parsed.createdNodes);
    } catch { /* not JSON */ }
  }
}
console.error(created.length ? `· created ${created.length} node(s)` : `· ${JSON.stringify(result).slice(0, 200)}`);
if (result.isError) process.exitCode = 1;
