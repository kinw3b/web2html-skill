---
name: paper-mcp-programmatic
description: "Batch Paper MCP calls from code: recipes and pitfalls."
---

# Paper MCP, programmatically

Driving the Paper Desktop MCP server (http://127.0.0.1:29979/mcp, live while Paper.app has a file open) in bulk from `execute_code`: batch style queries, node screenshots, tree walks, and gold-vs-rebuild visual QA. Faster than one Hermes tool_call per node when you need dozens of measurements.

## Raw JSON-RPC helper (copy into execute_code)

Two hard rules learned the expensive way:
1. **Bare tool names** — `get_computed_styles`, not `mcp__paper__get_computed_styles` (the prefix form answers "Unknown tool").
2. **Explicit `fileId` on every call** — raw JSON-RPC does NOT share the Hermes MCP tool layer's "currently open file" session state, and that state can drop mid-session anyway. Get the id once from `list_files` / the project's `qa/paper-file.json`.

```python
import json, urllib.request

FILE_ID = "<paper-file-id>"

def paper(method, args, timeout=120):
    args = dict(args); args.setdefault("fileId", FILE_ID)
    req = urllib.request.Request(
        "http://127.0.0.1:29979/mcp",
        data=json.dumps({"jsonrpc":"2.0","id":1,"method":"tools/call",
                         "params":{"name":method,"arguments":args}}).encode(),
        headers={"Content-Type":"application/json",
                 "Accept":"application/json, text/event-stream"})
    raw = urllib.request.urlopen(req, timeout=timeout).read().decode(errors="replace")
    if "data:" in raw[:200]:  # SSE stream: take last data: line
        raw = [l[5:].strip() for l in raw.splitlines() if l.startswith("data:")][-1]
    body = json.loads(raw)
    if "error" in body: return {"error": body["error"]}
    return "\n".join(c.get("text","") for c in body.get("result",{}).get("content",[]) if c.get("type")=="text")
```

`get_screenshot` returns an image content-part instead of text — for those, keep the raw body and pull `result.content[].data` (base64) where `type=="image"`, then `Image.open(io.BytesIO(base64.b64decode(data)))`.

## Recipes

- **Orient first:** `get_basic_info` → artboard list; `get_tree_summary {nodeId, depth}` from the artboard down to find section/container node ids. Never guess section ids.
- **Batch styles:** `get_computed_styles {nodeIds:[...]}` accepts many ids in one call — filter keys to what matters (padding/gap/font/border/radius) before printing.
- **Leaf text styles:** text nodes hide 2-3 frames deep; recurse `get_children` until `component=="Text"`, then batch those ids into `get_computed_styles`.
- **Positions:** `get_children` returns each child's `x`/`y` — use it to derive gaps, insets, and row heights without extra tools.
- **Compare sheets:** PIL side-by-side GOLD (Paper screenshot) / REBUILD (Playwright shot), 880px halves, labels, save to /tmp → `vision_analyze` with a pointed question ("what causes the height delta? ignore photo crop").
- **Verify geometry:** Playwright `bounding_box()` on the real DOM to confirm widths/heights match Paper numbers after each CSS fix.

## Paper reading pitfalls

- **Integer-rounded node frames.** Paper rounds text-frame heights (a 2-line 27.2px block frames at 56px, not 54.4; a 5-line quote at 140, not 136). Section-height residuals of ≤~15px after all inner geometry matches exactly are frame rounding, not a style delta — verify inner widths/heights via `get_children` positions and accept. Do not chase them with padding hacks.
- **Serializer-merged text nodes.** Captures can merge adjacent text into ONE text node (testimonial name+role, counter title+description). Check the live captured source HTML for the true pattern (sizes/weights/colors of each part) before rendering or "fixing" — render the multi-type reality, not the merged node.
- **Wrong-node screenshots.** Screenshotting a guessed id can return a 56×56 icon instead of the section. Always confirm the node via `get_tree_summary` from the artboard first, and sanity-check the returned image size.
- **Shot scripts keyed on `<section id=…>`** miss `<header>`/`<footer>` elements — screenshot those manually with Playwright.

## Rebuild-side pitfalls (seen repeatedly in 2.3 loops)

- **Stray `max-width` on section wrappers** renders a section 1520px wide instead of full-bleed 1600 with a ~1460 container inside. Keep sections full-bleed; put the container cap on the inner shell, and clear double-applied global shell padding for that section. Diagnose with Playwright bounding_box on section vs shell vs frame.
- **Fixed card heights:** Paper cards are fixed-height (e.g. 417×480 service cards, 420×341 testimonial cards). Set `height` + `justify-content: center` on the rebuild card rather than relying on padding to reach it. Height deltas of ±30–50px almost always trace to missing fixed height or wrong padding on cards.
- **Card counts differ from instinct:** Paper is gold — if Paper shows 2 blog cards, ship 2, even if the captured source HTML had 3. Same for step counts.
- **Container widths vary per section** — don't assume one shared container width (kp-mortex: testimonials/why/cta/footer 1460, blog/services 1300, faq 1090, process 1227).

## Relation to web2html

This is the infra layer under the web2html 2.3 measure loop (that pipeline's own reference files govern its gates/receipts; this skill governs the Paper-measurement technique itself).
