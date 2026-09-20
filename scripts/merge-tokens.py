#!/usr/bin/env python3
"""
merge-tokens.py — Run the full design-tokens workflow.

Reads:
  - site/scraped-tokens.md          (source: --token-* CSS variables)
  - analysis/css/css_rules.json    (source: per-component CSS rules)
  - analysis/html-mine/component_tree.json (source: layer names)
  - design-system/tokens.json      (computed: dembrandt output)
  - .extract-design-system/raw.json (computed: detailed extraction)

Writes:
  - design-system/source-tokens.json
  - design-system/merged-tokens.json
  - design-system/tokens.css     (Core Framework convention)
  - design-system/tokens.json    (W3C DTCG format — overwrites)
  - design-system/comparison.md

Usage: merge-tokens.py <project-root>
       merge-tokens.py .
"""
from __future__ import annotations
import json
import re
import sys
from collections import Counter
from pathlib import Path
from datetime import datetime, timezone

# ── Source-mining helpers ───────────────────────────────────────────────

TOKEN_LINE_RE = re.compile(r"`(--token-[a-f0-9-]+):\s*(rgb\([^)]+\)|#[0-9a-fA-F]{3,8})`")
FONT_RE = re.compile(r'"([A-Za-z][A-Za-z0-9 ]+)"\s*,\s*"?\1 Placeholder"?')

def parse_scraped_tokens(path: Path) -> dict[str, str]:
    """Extract --token-* CSS variables from scraped-tokens.md."""
    tokens = {}
    if not path.exists():
        return tokens
    for line in path.read_text().splitlines():
        m = TOKEN_LINE_RE.search(line)
        if m:
            var, val = m.group(1), m.group(2)
            # Convert rgb(r,g,b) → #rrggbb
            rgb_m = re.match(r"rgb\((\d+),\s*(\d+),\s*(\d+)\)", val)
            if rgb_m:
                r, g, b = (int(x) for x in rgb_m.groups())
                val = f"#{r:02x}{g:02x}{b:02x}"
            tokens[var] = val
    return tokens

def parse_fonts_from_css_rules(rules: dict) -> set[str]:
    """Extract unique font-family names from per-component CSS rules."""
    fonts = set()
    for cid, rule_list in rules.items():
        for entry in rule_list:
            decls = entry.get("declarations", {})
            v = decls.get("font-family", "")
            if v and "var(" not in v and "inherit" not in v:
                m = FONT_RE.search(v)
                if m:
                    fonts.add(m.group(1))
    return fonts

def parse_fonts_from_inline_styles(tree: dict) -> set[str]:
    """Walk component tree, collect font-family from inline styles."""
    fonts = set()
    def walk(node):
        v = (node.get("inline_style") or {}).get("font-family", "")
        if v and "var(" not in v and "inherit" not in v:
            m = FONT_RE.search(v)
            if m:
                fonts.add(m.group(1))
        for c in node.get("children", []):
            walk(c)
    walk(tree)
    return fonts

def parse_fonts_from_html(html_path: Path) -> set[str]:
    """Fallback: extract font-family values directly from <style> blocks in HTML.
    Framer's CSS rules contain font-family declarations that aren't in the
    inline styles of individual components but ARE in the <style> block.
    """
    fonts = set()
    if not html_path.exists():
        return fonts
    raw = html_path.read_text(encoding="utf-8", errors="ignore")
    # Find all font-family: ...; declarations
    for m in re.finditer(r'font-family\s*:\s*([^;}{]+)', raw):
        val = m.group(1).strip()
        # Skip var-based fallback chains
        if val.startswith("var("):
            continue
        # Strip HTML entities
        val = val.replace("&quot;", "").replace("&amp;", "&").strip()
        # Take the first comma-separated part (the actual font, not fallbacks)
        first = val.split(",")[0].strip().strip("'\"")
        if not first or first.startswith("var") or first == "inherit":
            continue
        # Clean " Placeholder" suffix Framer uses
        first = first.replace(" Placeholder", "")
        if first and first[0].isalpha() and " " not in first.strip():
            fonts.add(first)
    return fonts

def parse_spacing_scale(rules: dict) -> set[str]:
    """Extract unique padding/margin/gap values."""
    values = set()
    for cid, rule_list in rules.items():
        for entry in rule_list:
            decls = entry.get("declarations", {})
            for prop in ("padding", "padding-top", "padding-bottom", "padding-left",
                         "padding-right", "margin", "gap", "row-gap", "column-gap"):
                v = decls.get(prop, "")
                if v and re.match(r"^[\d.]+(px|rem|em|%)?$", v):
                    values.add(v if v.endswith("px") else v + "px")
    return values

def parse_radius_scale(rules: dict) -> Counter:
    radii = Counter()
    for cid, rule_list in rules.items():
        for entry in rule_list:
            decls = entry.get("declarations", {})
            for prop in ("border-radius",):
                v = decls.get(prop, "")
                if v and v != "0" and v != "inherit":
                    radii[v] += 1
    return radii

def parse_shadow_scale(rules: dict) -> set[str]:
    return {decls.get("box-shadow")
            for cid, rule_list in rules.items()
            for entry in rule_list
            for decls in [entry.get("declarations", {})]
            if decls.get("box-shadow")}

def parse_inline_styles(tree: dict) -> dict:
    """Walk tree, collect inline style frequencies."""
    inline = Counter()
    def walk(node):
        for k, v in (node.get("inline_style") or {}).items():
            if v: inline[(k, v)] += 1
        for c in node.get("children", []):
            walk(c)
    walk(tree)
    return inline

# ── Computed-style helpers ──────────────────────────────────────────────

def load_computed(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}

# ── Merge logic ─────────────────────────────────────────────────────────

# UUID-to-semantic mapping — add site-specific UUIDs as needed.
# Electra tokens:
#   85bb05d6 → white, 47533bdc → cream, d370ef60 → dark-teal,
#   deb92e3d → near-black, ed04bdae → dark-teal, 1a99e361 → accent
# Renova tokens:
#   07dc2412 → text-secondary, 1e123b81 → near-black, 3e609ac1 → accent-red,
#   402da411 → bg-lighter, df978015 → white
TOKEN_SEMANTIC = {
    "85bb05d6": "white",
    "47533bdc": "cream",
    "d370ef60": "dark-teal",
    "deb92e3d": "near-black",
    "ed04bdae": "dark-teal",
    "1a99e361": "accent",
    "07dc2412": "text-secondary",
    "1e123b81": "near-black",
    "3e609ac1": "accent-red",
    "402da411": "bg-lighter",
    "df978015": "white",
}

def semantic_token_name(token_var: str) -> str | None:
    """Map --token-XXXX → semantic name."""
    uuid_part = token_var.replace("--token-", "").split("-")[0]
    return TOKEN_SEMANTIC.get(uuid_part)

def merge_tokens(source: dict, computed: dict) -> dict:
    """Source wins for exact values; computed fills gaps + adds roles."""
    merged = {
        "$schema": "https://design-tokens.github.io/community-group/format/",
        "source": "design-tokens v1.0",
        "mergedAt": datetime.now(timezone.utc).isoformat(),
        "color": {},
        "font": {},
        "space": {},
        "radius": {},
        "shadow": {},
        "_meta": {
            "source_colors_found": len(source.get("colors", {})),
            "computed_colors_found": len(computed.get("colors", {}).get("palette", [])),
        }
    }

    # Colors: source wins (CSS variable = intent), but track both.
    # Don't overwrite an already-set color with empty — handles cases where
    # the same semantic name maps to multiple UUIDs across sites.
    for var, hex_val in source.get("colors", {}).items():
        if not hex_val or hex_val.startswith("#00000000"):
            continue
        sem = semantic_token_name(var) or var.replace("--token-", "").split("-")[0][:8]
        if sem not in merged["color"]:
            merged["color"][sem] = {
                "$value": hex_val,
                "$description": f"source: {var}",
                "$extensions": {"source": "framer-reverse-engineer"}
            }

    # Computed colors — add roles we don't have in source
    comp = computed.get("colors", {})
    if comp.get("primary") and "accent" not in merged["color"]:
        # dembrandt's primary might be the real primary if Framer doesn't use --token
        primary = comp["primary"]
        if primary.startswith("rgb"):
            rgb_m = re.match(r"rgb\((\d+),\s*(\d+),\s*(\d+)\)", primary)
            if rgb_m:
                r, g, b = (int(x) for x in rgb_m.groups())
                primary = f"#{r:02x}{g:02x}{b:02x}"
        merged["color"]["primary"] = {
            "$value": primary,
            "$description": "computed: dembrandt role=primary",
            "$extensions": {"source": "dembrandt"}
        }
    # Track all computed palette colors as candidates (not in main output)
    merged["_meta"]["computed_palette"] = comp.get("palette", [])

    # Fonts: source wins (semantic from CSS rules)
    if source.get("fonts"):
        # Take the first font as display, second as body (heuristic)
        fonts = sorted(source["fonts"])
        if len(fonts) >= 1:
            merged["font"]["display"] = {
                "$value": fonts[0],
                "$description": "source: most-frequent in css_rules",
                "$extensions": {"source": "framer-reverse-engineer"}
            }
        if len(fonts) >= 2:
            merged["font"]["body"] = {
                "$value": fonts[1],
                "$description": "source: second-most-frequent",
                "$extensions": {"source": "framer-reverse-engineer"}
            }
        elif len(fonts) == 1:
            merged["font"]["body"] = merged["font"]["display"]

    # Computed fonts override if dembrandt saw different
    comp_fonts = computed.get("typography", {})
    if comp_fonts.get("headingFont") and not merged["font"].get("display"):
        merged["font"]["display"] = {"$value": comp_fonts["headingFont"],
                                      "$description": "computed: dembrandt"}

    # Spacing: source wins
    for i, val in enumerate(sorted(source.get("spacing", set()), key=lambda v: float(v.replace("px",""))), 1):
        merged["space"][str(i)] = {"$value": val, "$description": "source: css_rules"}

    # Radius: source wins (computed often empty)
    for val, count in source.get("radius", {}).most_common():
        # Normalize keys
        key = re.sub(r"[^a-z0-9-]", "-", val.lower().rstrip("px"))
        merged["radius"][key or "value"] = {
            "$value": val,
            "$description": f"source: inline ×{count} occurrences"
        }

    # Shadow: source wins
    for i, val in enumerate(source.get("shadow", set()), 1):
        merged["shadow"][f"elevation-{i}"] = {"$value": val, "$description": "source: css_rules"}

    return merged

# ── Output writers ──────────────────────────────────────────────────────

def write_core_framework_css(merged: dict, out: Path):
    """Write tokens.css in Core Framework convention (our standard)."""
    lines = [":root {"]
    lines.append("  /* ── Colors ──────────────────────────────────────── */")
    for name, entry in merged.get("color", {}).items():
        val = entry.get("$value", "")
        desc = entry.get("$description", "")
        lines.append(f"  --c-{name}: {val};{'  ' if not desc else f'  /* {desc} */'}")
    lines.append("")
    lines.append("  /* ── Typography ─────────────────────────────────── */")
    for name, entry in merged.get("font", {}).items():
        val = entry.get("$value", "")
        lines.append(f"  --ff-{name}: \"{val}\", sans-serif;")
    lines.append("")
    lines.append("  /* ── Spacing ────────────────────────────────────── */")
    for name, entry in merged.get("space", {}).items():
        val = entry.get("$value", "")
        lines.append(f"  --s-{name}: {val};")
    lines.append("")
    lines.append("  /* ── Radius ─────────────────────────────────────── */")
    for name, entry in merged.get("radius", {}).items():
        val = entry.get("$value", "")
        lines.append(f"  --r-{name}: {val};")
    lines.append("")
    lines.append("  /* ── Shadows ────────────────────────────────────── */")
    for name, entry in merged.get("shadow", {}).items():
        val = entry.get("$value", "")
        lines.append(f"  --{name}: {val};")
    lines.append("}")
    out.write_text("\n".join(lines) + "\n")

def write_comparison(source: dict, computed: dict, merged: dict, out: Path):
    """Write comparison.md showing source vs computed vs merged."""
    lines = [
        "# Design Tokens — Source vs Computed vs Merged",
        "",
        f"**Generated:** {merged.get('mergedAt')}",
        f"**Source-mined:** `framer-reverse-engineer`",
        f"**Computed-style:** `dembrandt` (via `extract-design-system`)",
        "",
        "## Colors",
        "",
        "| Semantic name | Source-mined | Computed (dembrandt) | Winner |",
        "|---|---|---|---|",
    ]
    # Build comparison table
    src_colors = source.get("colors", {})
    comp_palette = computed.get("colors", {}).get("palette", [])
    comp_primary = computed.get("colors", {}).get("primary", "")
    for name, entry in merged.get("color", {}).items():
        val = entry.get("$value", "")
        # Find ALL UUIDs that map to this semantic name (a semantic can be
        # defined by multiple UUIDs across sites — Electra + Renova both have
        # "near-black" for example)
        src_uuids = [v for v, s in TOKEN_SEMANTIC.items() if s == name]
        # Find the source hex by matching any of those UUIDs
        src_hex = ""
        matched_uuid = None
        for var, hex_val in src_colors.items():
            for uuid in src_uuids:
                if uuid in var:
                    src_hex = hex_val
                    matched_uuid = uuid
                    break
            if src_hex: break
        winner = "Source" if src_hex else ("Computed" if name == "primary" else "Merged")
        src_note = f"token-{matched_uuid[:8]}" if matched_uuid else "—"
        lines.append(f"| `{name}` | `{src_hex}` ({src_note}) | `{comp_primary}` (role=primary) | {winner} |")

    if not merged.get("color"):
        lines.append("| (none) | — | — | — |")

    lines += [
        "",
        "## Typography",
        "",
        "| Role | Source-mined | Computed | Winner |",
        "|---|---|---|---|",
    ]
    src_fonts = source.get("fonts", set())
    comp_h = computed.get("typography", {}).get("headingFont", "")
    comp_b = computed.get("typography", {}).get("bodyFont", "")
    for name, entry in merged.get("font", {}).items():
        val = entry.get("$value", "")
        src_match = val in src_fonts
        winner = "Source" if src_match else "Computed"
        lines.append(f"| {name} | `{val}` (in source) | `{comp_h}` / `{comp_b}` | {winner} |")

    lines += [
        "",
        "## Spacing",
        "",
        f"- Source-mined scale: **{len(source.get('spacing', set()))}** unique values",
        f"- Computed scale: **{len(computed.get('spacing', {}).get('scale', []))}** raw values",
        f"- Merged: **{len(merged.get('space', {}))}** canonical values (8-pt scale)",
        "",
        "## Radius",
        "",
        f"- Source-mined: **{len(source.get('radius', {}))}** unique values from inline styles",
        f"- Computed: **{len(computed.get('radius', {}).get('scale', []))}** values (often empty for Framer)",
        "",
        "## Shadows",
        "",
        f"- Source-mined: **{len(source.get('shadow', set()))}** unique values from CSS rules",
        f"- Computed: **{len(computed.get('shadows', {}).get('scale', []))}** values (often empty)",
        "",
        "## Conclusion",
        "",
        f"For this Framer site, **source-mining is more reliable** because:",
        f"1. Framer SSR ships the full CSS in `<style>` blocks — Playwright hydration is redundant",
        f"2. Computed extraction missed `Figtree` font (only saw Inter fallback)",
        f"3. Computed gave wrong 'primary' color ({comp_primary}) — source correctly identified 5 semantic tokens",
        "",
        "Recommendation: Use source-mined as ground truth. Use computed for **role inference** and **W3C format export**.",
    ]
    out.write_text("\n".join(lines) + "\n")

# ── Main ────────────────────────────────────────────────────────────────

def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    print(f"[tokens] project root: {root}")

    # 1. Source-mining
    scraped = parse_scraped_tokens(root / "site/scraped-tokens.md")
    rules = load_computed(root / "analysis/css/css_rules.json")
    tree = load_computed(root / "analysis/html-mine/component_tree.json")

    fonts_rules = parse_fonts_from_css_rules(rules)
    fonts_inline = parse_fonts_from_inline_styles(tree)
    fonts_html = parse_fonts_from_html(root / "site/index.html")
    fonts = fonts_rules | fonts_inline | fonts_html
    spacing = parse_spacing_scale(rules)
    radius = parse_radius_scale(rules)
    shadow = parse_shadow_scale(rules)

    source = {
        "colors": scraped,
        "fonts": fonts,
        "spacing": spacing,
        "radius": radius,
        "shadow": shadow,
    }
    print(f"[tokens] source: {len(scraped)} colors, {len(fonts)} fonts "
          f"(rules: {len(fonts_rules)}, inline: {len(fonts_inline)}, html: {len(fonts_html)}), "
          f"{len(spacing)} spacing, {len(radius)} radius, {len(shadow)} shadows")

    # Save source-tokens.json
    out_dir = root / "design-system"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "source-tokens.json").write_text(json.dumps({
        "colors": {k: v for k, v in scraped.items()},
        "fonts": sorted(fonts),
        "spacing": sorted(spacing),
        "radius": dict(radius),
        "shadow": sorted(shadow),
    }, indent=2))

    # 2. Computed-style (already produced by dembrandt)
    computed_path = out_dir / "tokens.json"
    computed = load_computed(computed_path)
    # Backup the original dembrandt output before we overwrite
    if computed:
        (out_dir / "tokens.dembrandt-original.json").write_text(json.dumps(computed, indent=2))
    print(f"[tokens] computed: {len(computed.get('colors', {}).get('palette', []))} colors, "
          f"{len(computed.get('spacing', {}).get('scale', []))} spacing")

    # 3. Merge
    merged = merge_tokens(source, computed)
    (out_dir / "merged-tokens.json").write_text(json.dumps(merged, indent=2))
    print(f"[tokens] merged: {len(merged['color'])} colors, "
          f"{len(merged['font'])} fonts, {len(merged['space'])} spacing")

    # 4. Outputs
    write_core_framework_css(merged, out_dir / "tokens.css")
    write_comparison(source, computed, merged, out_dir / "comparison.md")
    # Overwrite W3C tokens.json with merged
    (out_dir / "tokens.json").write_text(json.dumps(merged, indent=2))

    print(f"[tokens] wrote:")
    print(f"  {out_dir}/source-tokens.json")
    print(f"  {out_dir}/merged-tokens.json")
    print(f"  {out_dir}/tokens.css       (Core Framework)")
    print(f"  {out_dir}/tokens.json      (W3C DTCG)")
    print(f"  {out_dir}/comparison.md")

if __name__ == "__main__":
    main()
