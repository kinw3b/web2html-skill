---
name: webflow-mcp
description: Use when editing a Webflow site via Webflow MCP in Hermes.
---

# Webflow MCP (Hermes)

Edit Webflow sites through the `mcp__webflow__*` tools (Data API + live Designer bridge). A Webflow Designer URL (`<shortName>.design.webflow.com/?pageId=…&workflow=canvas`) or "connect to this Webflow page" is an **MCP request, not a browser request** — do not open the Designer in a browser (local profiles are often locked; the user wants MCP). Only fall back to a browser if the user asks.

## Procedure

1. **Load tools.** They are deferred: `tool_search ["webflow"]` → `tool_describe` the ones needed (`webflow_guide_tool`, `data_sites_tool`, `data_pages_tool`, `designer_tool`, `data_element_tool`, `data_element_builder`, `data_assets_tool`). Every call needs `session_id`, `agent_id`, `context`.
2. **Guide first.** Call `webflow_guide_tool` with `session_id: "start"`. It issues a `ses_…` id — reuse that exact id and the same `agent_id` on every later call. The guide is ~85 KB and spills to a file: grep the spill file for the tool family you need instead of reading it.
3. **Resolve the site.** `data_sites_tool > list_sites` (summary). The Designer subdomain equals the site `shortName`. Never assume a site id.
4. **Resolve the page from the Designer, not the URL.** `designer_tool` with `get_current_page` + `get_current_mode` + `get_selected_element` in one call. This both proves the bridge is connected and returns the true page id — the `pageId` query param in a pasted URL can be mangled (extra/missing characters) and will 404 or hit the wrong page. Cross-check with `data_pages_tool > list_pages` when a page link target is needed.
5. **Announce the target before editing.** State page name + slug ("editing Courses `/courses`") so the user can confirm you are on the right page — they will ask otherwise.
6. **Map the page.** `data_element_tool > query_elements` with `element_filter.style` on the section class (e.g. `module`) and `children_depth: -1`. Record element ids of headings, paragraphs, pills, buttons, images per module.
7. **Repurpose before you build.** Match each target block to an existing module with the closest structure and keep its classes: `set_text` on headings/paragraphs/buttons, `set_link`, `set_image_asset`, `set_style` to swap a variant (`pill is-new` → `pill`). Create new elements only for structure the module lacks; duplicate a whole module by building a new Section with the same class names when an extra block is needed.
8. **Verify after every build.** `query_elements` by `element_id` with `children_depth: -1` on what you just created. Builder results (`return_element_info`) show type/styles but not text children.
9. **Show the user.** `designer_tool > select_element` on the first edited element. Data-API edits do not always repaint the canvas live — tell the user a Designer refresh may be needed.

## Pitfalls

- `set_text` fails with "This element doesn't support text" on Block/div elements (pills; a builder `TextBlock` also reports as Block). Set text on a child DOM `span` instead — see Recipes.
- `set_text` on a Heading or Paragraph replaces **all** children, including accent `Span`/`Emphasized` nodes. Set the base text first, then append a `BY_CUSTOM_TAG em` (or `span`) with the accent class.
- `data_element_builder` `set_text` is ignored on Paragraph / TextBlock / `BY_CUSTOM_TAG p`; the element is created with Webflow's default lorem `String` and your `children` are appended after it. Either build with no children and `set_text` afterwards (plain text), or build with children then `remove_element` the lorem `String` id (mixed formatting).
- Builder defaults leave placeholders everywhere: Paragraph → lorem string, TextBlock → "This is some text inside of a div block.", `ul` → 3 placeholder `ListItem`s ahead of yours. Always query `children_depth: -1` and remove them.
- `set_style` replaces the whole class list — pass every class the element should keep.
- `remove_element` is destructive with no undo from the API; remove only ids you queried in this session.
- Image assets for a swap must already exist: `data_assets_tool > list_assets` (newest first) and pass the asset id; upload via `asset_tool` (public URL) if missing.

## Recipes (data_element_builder + data_element_tool)

Ids are `{component, element}` objects copied verbatim from a query result.

- **Pill / badge text** (Block rejects `set_text`): build `BY_CUSTOM_TAG div` with `set_style ["pill"]` and one child `BY_CUSTOM_TAG span` carrying `set_text`; then `remove_element` the old pill.
- **Heading with accent word**: `set_text` the Heading with the plain prefix (trailing space) — this wipes existing accent children — then builder-append `BY_CUSTOM_TAG em` with `set_style` on the site's accent class (e.g. `bc--accent`) and `set_text`. Inline tags `em`/`strong`/`span` honor builder `set_text`.
- **Plain paragraph**: build `{"type":"Paragraph"}` with no children, then `data_element_tool > set_text` on the returned id.
- **Mixed-format paragraph** ("**Best for:** text"): build Paragraph with children `BY_CUSTOM_TAG strong` + `BY_CUSTOM_TAG span`, each with `set_text`; query `children_depth: -1` and `remove_element` the first `String` child (lorem).
- **Bullet list**: `BY_CUSTOM_TAG ul` with `BY_CUSTOM_TAG li` children (each `set_text`) yields a real `List`/`ListItem` tree, but 3 default `ListItem`s are prepended — query and remove them; if `li` text did not land, `set_text` each `ListItem` id.
- **Variant swap**: `set_style` with the full desired list (`["pill"]` drops `is-new`; `["button","primary"]` changes a button) — omitted classes are removed.
- **Button copy + target**: `set_text` on the Link element, then `set_link` (`page` + id from `list_pages`, or `url` + literal).

## Verification

- `get_current_page` id matches the `pageId` you pass to `data_element_tool`.
- Post-build `query_elements` shows your text as `String` children and no lorem/placeholder nodes.
- Selected element on canvas is the one you edited.
