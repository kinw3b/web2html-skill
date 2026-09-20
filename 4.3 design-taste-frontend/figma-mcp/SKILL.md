---
name: figma-mcp
description: Use when installing or calling Figma MCP in Hermes.
---

# Figma MCP (Hermes)

Wire and call Figma through the **desktop Dev Mode MCP** (`http://127.0.0.1:3845/mcp`). Do not install or authorize the catalog remote server (`https://mcp.figma.com/mcp`) unless the user explicitly asks for remote.

## When to Use

- Check / install / test Figma MCP
- A `figma.com` design, FigJam, or Make URL is the source
- Pixel-perfect or implement-from-Figma work that needs node context

Don't use for Paper MCP (that's `paper`). Don't treat a Figma login wall in the browser as the access path when MCP is the request.

## Prerequisites

- Figma **desktop app** open (not just the browser tab)
- Desktop MCP enabled in the file: Shift+D → Inspect → Enable desktop MCP server
- Listener: `http://127.0.0.1:3845/mcp`

## Procedure

1. **Confirm local server.** `hermes mcp list` must show `figma-desktop` → `http://127.0.0.1:3845/mcp` → enabled. POST initialize to `:3845` must return HTTP 200. If the port is down, the Figma app MCP toggle is off — don't add a remote server as a substitute.
2. **Install if missing (non-interactive).** Catalog `setup_mcp` `figma` is the *remote* OAuth server — skip it.
   ```
   printf 'n\nY\n' | hermes mcp add figma-desktop --url http://127.0.0.1:3845/mcp
   ```
   First prompt is auth (answer `n`); second is enable all tools (`Y`). Then `hermes mcp test figma-desktop` must report connected and 6 tools.
3. **Keep remote off.** If `figma` exists with url `https://mcp.figma.com/mcp` and `enabled: true`, set `mcp_servers.figma.enabled` false via `hermes config set`. Leave the local entry as the only enabled Figma server.
4. **Gate the URL before any tool call.** Path `/design/`, `/board/` (FigJam), or Make: continue. Path `/slides/`: stop. Desktop MCP returns *tools are only available for design, FigJam, and Make files* even with a valid `node-id`. Ask for a Design-file link (or a duplicate of the slide in a Design file). Do not retry `get_screenshot` / `get_metadata` / `get_design_context` on the same Slides URL.
5. **Parse `node-id`.** From `?node-id=69-2563` use `69:2563` (hyphen → colon). No `node-id` means current selection in the desktop app — the matching file must be focused there.
6. **Call tools.** Prefer injected `mcp_figma_desktop_*` in a session that started *after* the server was added. If this chat predated the add, say tools load next session; do not claim they are in the current schema.

## Pitfalls

- Do not run `setup_mcp` / `hermes mcp install figma` for this user — that installs remote OAuth, which they do not want.
- `hermes mcp add --url` defaults the auth prompt to yes; an empty/cancelled prompt aborts before tools are saved. Always pipe `n` then `Y`.
- A 200 from `:3845` only proves the desktop server is up, not that the open file type is supported. Check the URL path first.
- `get_screenshot`'s schema mentions Slides; the running desktop server still rejects `/slides/` files. Trust the file-type error, not the schema blurb.

## Verification

- `hermes mcp list`: `figma-desktop` enabled, catalog `figma` disabled or absent
- `hermes mcp test figma-desktop`: connected, 6 tools
- On a `/design/` URL with `node-id`, `get_metadata` or `get_screenshot` returns node content, not the file-type error
