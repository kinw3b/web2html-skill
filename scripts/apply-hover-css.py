#!/usr/bin/env python3
"""3.2 — write rebuild/css/hover.css from the 1.3 source-CSS button hover receipt.

  python3 apply-hover-css.py .

Reads qa/button-hover.json (1.3). Writes rebuild/css/hover.css, links it from
rebuild/index-polish.html, and records qa/button-hover-css.json.

Does not invent hover. Bare a:hover / button:hover is not a CTA recipe.
Does not mutate rebuild/index.html.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from html import unescape
from pathlib import Path

WRITER = "apply-hover-css.py"
HOVER_HREF = "css/hover.css"
LIBRARY_CLASS = re.compile(r"\b(btn-[a-z0-9-]+|pill|text-link|navbar-link)\b", re.I)
CONTROL_RE = re.compile(r"<(a|button)\b([^>]*)>(.*?)</\1>", re.I | re.S)
TOKEN_RE = re.compile(r"(--[a-z0-9-]+)\s*:\s*([^;}{]+)", re.I)
VAR_RE = re.compile(r"var\((--[a-z0-9-]+)", re.I)
LABEL_PREFIX = re.compile(
    r"^(primary|secondary|ghost|outline|button|cta|pill|nav|link)\s*[-–—:]\s*",
    re.I,
)


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)


def read_json(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def _key(label: str) -> str:
    text = LABEL_PREFIX.sub("", str(label or ""))
    return re.sub(r"\s+", " ", unescape(text)).strip().casefold()


def text_of(inner: str) -> str:
    stripped = re.sub(r"<script[\s\S]*?</script>", " ", inner, flags=re.I)
    stripped = re.sub(r"<style[\s\S]*?</style>", " ", stripped, flags=re.I)
    stripped = re.sub(r"<[^>]+>", " ", stripped)
    return _key(stripped)


def token_values(css: str) -> dict[str, str]:
    names: dict[str, str] = {}
    colors: dict[str, str] = {}
    for match in TOKEN_RE.finditer(css or ""):
        name = match.group(1)
        value = match.group(2).strip()
        names[name] = value
        compact = re.sub(r"\s+", "", value).casefold()
        if compact:
            colors.setdefault(compact, f"var({name})")
    return {"names": names, "colors": colors}


def usable_value(value: str, token_names: dict[str, str]) -> str | None:
    raw = (value or "").strip()
    if not raw:
        return None
    vars_in = VAR_RE.findall(raw)
    if vars_in and not all(name in token_names for name in vars_in):
        return None
    return raw


def maybe_token(value: str, colors: dict[str, str]) -> str:
    compact = re.sub(r"\s+", "", value).casefold()
    return colors.get(compact, value)


def find_control(html: str, label: str) -> re.Match[str] | None:
    key = _key(label)
    if not key:
        return None
    exact = None
    fuzzy = None
    for match in CONTROL_RE.finditer(html):
        text = text_of(match.group(3))
        if text == key:
            exact = match
            break
        if text and (key in text or text in key) and fuzzy is None:
            fuzzy = match
    return exact or fuzzy


def class_attr(attrs: str) -> str:
    return re.search(r'\bclass=["\']([^"\']*)', attrs or "", re.I).group(1) if re.search(
        r'\bclass=["\']([^"\']*)', attrs or "", re.I
    ) else ""


def library_class_of(attrs: str, fallback: str) -> str:
    found = LIBRARY_CLASS.search(class_attr(attrs))
    if found:
        return found.group(1).lower()
    return (fallback or "btn-primary").lower()


def add_class(html: str, match: re.Match[str], cls: str) -> str:
    tag, attrs, inner = match.group(1), match.group(2), match.group(3)
    current = class_attr(attrs)
    if re.search(rf"\b{re.escape(cls)}\b", current):
        return html
    if current:
        new_attrs = re.sub(
            r'(\bclass=["\'])([^"\']*)',
            lambda m: f"{m.group(1)}{m.group(2)} {cls}",
            attrs,
            count=1,
            flags=re.I,
        )
    else:
        new_attrs = attrs + f' class="{cls}"'
    replacement = f"<{tag}{new_attrs}>{inner}</{tag}>"
    return html[: match.start()] + replacement + html[match.end() :]


def section_prefix(section_name: str, section_id: str, conflict: bool) -> str:
    if not conflict:
        return ""
    slug = re.sub(r"[^a-z0-9]+", "-", (section_name or "").casefold()).strip("-")
    if slug:
        return f"#{slug} "
    if section_id:
        return f'[data-section="{section_id}"] '
    return ""


def rule_css(class_name: str, decls: dict, colors: dict[str, str], prefix: str) -> str:
    body = []
    color = ""
    for prop, value in decls.items():
        mapped = maybe_token(value, colors)
        body.append(f"  {prop}: {mapped};")
        if prop in {"color", "-webkit-text-fill-color"}:
            color = mapped
    lines = [f"{prefix}.{class_name}:hover {{", *body, "}"]
    if color:
        lines.extend(
            [
                f"{prefix}.{class_name}:hover p,",
                f"{prefix}.{class_name}:hover span {{",
                f"  color: {color};",
                f"  -webkit-text-fill-color: {color};",
                "}",
            ]
        )
    return "\n".join(lines)


def ensure_link(html: str) -> str:
    if "css/hover.css" in html:
        return html
    tag = f'<link rel="stylesheet" href="{HOVER_HREF}" />'
    for needle in (
        'href="css/tokens.css" />',
        'href="css/tokens.css"/>',
        'href="css/tokens.css">',
        "href='css/tokens.css'>",
    ):
        if needle in html:
            return html.replace(needle, f"{needle}\n  {tag}", 1)
    if "</head>" in html:
        return html.replace("</head>", f"  {tag}\n</head>", 1)
    return tag + "\n" + html


def hover_receipt_ok(payload: dict) -> bool:
    return (
        payload.get("ok") is True
        and payload.get("writer") == WRITER
        and isinstance(payload.get("applied"), list)
        and isinstance(payload.get("skipped"), list)
    )


def apply_hover_css(root: Path) -> dict:
    root = root.resolve()
    polish = root / "rebuild" / "index-polish.html"
    if not polish.is_file():
        raise FileNotFoundError("need rebuild/index-polish.html — 3.1 seeds it")

    source = read_json(root / "qa" / "button-hover.json", {})
    recipes = source.get("applied") if isinstance(source.get("applied"), list) else []
    html = polish.read_text(encoding="utf-8")
    tokens_css = ""
    tokens_path = root / "rebuild" / "css" / "tokens.css"
    if tokens_path.is_file():
        tokens_css = tokens_path.read_text(encoding="utf-8")
    tokens = token_values(tokens_css)

    by_class: dict[str, list[dict]] = {}
    for row in recipes:
        name = str(row.get("className") or "btn-primary")
        by_class.setdefault(name, []).append(row)

    applied = []
    skipped = list(source.get("skipped") or []) if isinstance(source.get("skipped"), list) else []
    blocks = [
        "/* 1.3 source CSS button hover — authored at 3.2. Do not invent UA-blue link hover. */"
    ]
    html_out = html
    files: list[str] = []

    if not recipes:
        skipped = skipped or [
            {
                "finding": "button hover",
                "reason": "1.3 found no source CSS :hover paint on pulled buttons",
            }
        ]
    else:
        for row in recipes:
            label = row.get("label") or "button"
            decls_in = row.get("declarations") or {}
            decls = {}
            for prop, value in decls_in.items():
                usable = usable_value(str(value), tokens["names"])
                if usable:
                    decls[prop] = usable
            if not decls:
                skipped.append({"label": label, "reason": "hover decls used unknown source variables"})
                continue
            match = find_control(html_out, label)
            if match is None:
                skipped.append({"label": label, "reason": "no matching control on index-polish.html"})
                continue
            class_name = library_class_of(match.group(2), str(row.get("className") or "btn-primary"))
            html_out = add_class(html_out, match, class_name)
            conflict = len(by_class.get(str(row.get("className") or class_name), [])) > 1
            prefix = section_prefix(str(row.get("sectionName") or ""), str(row.get("sectionId") or ""), conflict)
            blocks.append(
                f"/* {label} · {row.get('sectionId') or ''} · {row.get('sourceSelector') or ''} */"
            )
            blocks.append(rule_css(class_name, decls, tokens["colors"], prefix))
            applied.append(
                {
                    "label": label,
                    "className": class_name,
                    "selector": f"{prefix}.{class_name}:hover",
                    "sectionId": row.get("sectionId") or "",
                }
            )

    css_dir = root / "rebuild" / "css"
    css_dir.mkdir(parents=True, exist_ok=True)
    css_path = css_dir / "hover.css"
    existing = css_path.read_text(encoding="utf-8") if css_path.is_file() else ""
    faq_keep = ""
    marker = existing.find("/* Detected FAQ")
    if marker >= 0:
        faq_keep = "\n\n" + existing[marker:].rstrip() + "\n"
    if applied:
        css_path.write_text("\n\n".join(blocks) + "\n" + faq_keep, encoding="utf-8")
        html_out = ensure_link(html_out)
        files.append("rebuild/css/hover.css")
        if html_out != html or "css/hover.css" not in html:
            polish.write_text(html_out, encoding="utf-8")
            if "rebuild/index-polish.html" not in files:
                files.append("rebuild/index-polish.html")
    elif not css_path.is_file():
        css_path.write_text(
            "/* 3.2 — no source CSS button hover to apply */\n",
            encoding="utf-8",
        )

    linked = polish.is_file() and "css/hover.css" in polish.read_text(encoding="utf-8")
    ok = True
    if recipes and not applied:
        ok = False

    receipt = {
        "ok": ok,
        "writer": WRITER,
        "applied": applied,
        "skipped": skipped,
        "files": files,
        "linked": linked,
    }
    dest = root / "qa" / "button-hover-css.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path, nargs="?", default=Path("."))
    args = ap.parse_args(argv)
    try:
        receipt = apply_hover_css(args.root)
    except FileNotFoundError as exc:
        fail(str(exc))
        return 2
    print(json.dumps(receipt, indent=2))
    if not hover_receipt_ok(receipt):
        fail("qa/button-hover-css.json is not a valid 3.2 hover receipt")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
