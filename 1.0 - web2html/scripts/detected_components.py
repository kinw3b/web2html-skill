"""Legacy detect-and-apply DOM cleanup. Not a pipeline step.

3.2 uses author-faq.py and author-nav-dropdown.py (and author-nav-drawer.py
for the burger). Do not call this instead of those scripts.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from token_utilities import dumps, ensure_stylesheet_link

FAQ_ROOT_SEL = (
    "#faq-section",
    "[data-paper-section='faq-section']",
    "[id*='faq-section']",
    "section[data-paper-name*='faq']",
)
FAQ_ITEM_SEL = "[data-faq-item], [data-component='FaqRow'], [data-action='toggle-faq']"

FAQ_CSS = """/* Detected FAQ — written only when FAQ exists. Pitfall #79 */
[data-faq-item] {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  width: 100%;
  height: fit-content;
  box-sizing: border-box;
}
[data-faq-item][role="button"] {
  /* inner <button data-action="toggle-faq"> is the control */
}
[data-action="toggle-faq"] {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-6, 24px);
  width: 100%;
  appearance: none;
  background: none;
  border: none;
  padding: 0;
  margin: 0;
  cursor: pointer;
  font: inherit;
  color: inherit;
  text-align: inherit;
}
[data-faq-answer] {
  width: 100%;
  box-sizing: border-box;
}
[data-faq-item][data-open="false"] [data-faq-answer] {
  display: none;
}
[data-faq-item][data-open="true"] [data-faq-answer] {
  display: block;
  width: 100%;
}
[data-faq-icon] {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
"""

FAQ_JS = """
  // Detect only: no FAQ hooks → do nothing. Bind the button, never the card.
  var faq = document.getElementById("faq-section")
    || document.querySelector("[data-paper-section='faq-section']")
    || document.querySelector("[data-faq-item]");
  if (faq) {
    var items = faq.querySelectorAll("[data-faq-item]");
    if (items.length) {
      function setFaqOpen(item, open) {
        item.setAttribute("data-open", open ? "true" : "false");
        var button = item.querySelector("[data-action=\\"toggle-faq\\"]");
        if (button) button.setAttribute("aria-expanded", open ? "true" : "false");
        var answer = item.querySelector("[data-faq-answer]");
        if (answer) answer.setAttribute("aria-hidden", open ? "false" : "true");
      }
      items.forEach(function (item, index) {
        var button = item.querySelector("[data-action=\\"toggle-faq\\"]");
        var answer = item.querySelector("[data-faq-answer]");
        if (item.getAttribute("role") === "button" && button) {
          item.removeAttribute("role");
          item.removeAttribute("tabindex");
        }
        if (answer) answer.id = answer.id || ("faq-a-" + index);
        if (button) {
          if (!button.id) button.id = "faq-q-" + index;
          if (answer) button.setAttribute("aria-controls", answer.id);
          button.addEventListener("click", function () {
            var open = item.getAttribute("data-open") === "true";
            items.forEach(function (other) {
              if (other !== item) setFaqOpen(other, false);
            });
            setFaqOpen(item, !open);
          });
          button.addEventListener("keydown", function (event) {
            if (event.key !== "Enter" && event.key !== " ") return;
            if (button.tagName === "BUTTON") return;
            event.preventDefault();
            button.click();
          });
        }
        if (!item.hasAttribute("data-open")) {
          setFaqOpen(item, index === 0);
        } else {
          setFaqOpen(item, item.getAttribute("data-open") === "true");
        }
      });
    }
  }
"""

MAIN_JS_SHELL = """(function () {
  "use strict";

  var nav = document.getElementById("nav")
    || document.querySelector("[data-nav-toggle]")
    && document.querySelector("nav, header");

  function mqMobile() {
    return window.matchMedia("(max-width: 768px)").matches;
  }

  function setDropdown(open) {
    if (!nav) return;
    nav.classList.toggle("is-dropdown-open", open);
    var trigger = nav.querySelector("[data-nav-dropdown-trigger]");
    if (trigger) trigger.setAttribute("aria-expanded", open ? "true" : "false");
  }

  function setNavOpen(open) {
    if (!nav) return;
    nav.classList.toggle("is-nav-open", open);
    var toggle = nav.querySelector("[data-nav-toggle]");
    if (toggle) {
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    }
    if (open) setDropdown(false);
  }

  if (nav) {
    var trigger = nav.querySelector("[data-nav-dropdown-trigger]");
    var panel = nav.querySelector("[data-nav-dropdown-panel]");
    if (panel && !panel.id) panel.id = "nav-dropdown";
    if (trigger) {
      trigger.setAttribute("role", "button");
      trigger.setAttribute("aria-haspopup", "true");
      trigger.setAttribute("aria-controls", "nav-dropdown");
      trigger.setAttribute("tabindex", "0");
      trigger.setAttribute("aria-expanded", "false");
      trigger.addEventListener("click", function (event) {
        event.preventDefault();
        if (mqMobile()) return;
        setDropdown(!nav.classList.contains("is-dropdown-open"));
      });
      trigger.addEventListener("keydown", function (event) {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          trigger.click();
        }
      });
      trigger.addEventListener("mouseenter", function () {
        if (!mqMobile()) setDropdown(true);
      });
    }
    if (panel) {
      panel.addEventListener("mouseenter", function () {
        if (!mqMobile()) setDropdown(true);
      });
    }
    nav.addEventListener("mouseleave", function () {
      if (!mqMobile()) setDropdown(false);
    });
    var toggle = nav.querySelector("[data-nav-toggle]");
    if (toggle) {
      toggle.addEventListener("click", function (event) {
        event.preventDefault();
        setNavOpen(!nav.classList.contains("is-nav-open"));
      });
    }
    document.addEventListener("click", function (event) {
      if (!nav.contains(event.target)) {
        setDropdown(false);
        setNavOpen(false);
      }
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        setDropdown(false);
        setNavOpen(false);
      }
    });
    window.addEventListener("resize", function () {
      if (!mqMobile()) setNavOpen(false);
      else setDropdown(false);
    });
  }
FAQ_PLACEHOLDER
})();
"""


def has_faq_hooks(html: str) -> bool:
    low = html.lower()
    return bool(
        "faq-section" in low
        or "data-faq-item" in low
        or 'data-component="faqrow"' in low
        or "data-action=\"toggle-faq\"" in low
        or "data-action='toggle-faq'" in low
    )


def find_faq_root(soup):
    for sel in FAQ_ROOT_SEL:
        el = soup.select_one(sel)
        if el is not None:
            return el
    hit = soup.select_one(FAQ_ITEM_SEL)
    if hit is None:
        return None
    node = hit
    for _ in range(12):
        parent = getattr(node, "parent", None)
        if parent is None or not getattr(parent, "name", None):
            break
        node = parent
        if node.name in {"section", "main", "article"}:
            return node
    return hit


def find_faq_items(root) -> list:
    from bs4 import Tag

    items = [el for el in root.select("[data-faq-item]") if isinstance(el, Tag)]
    if items:
        return items
    found = []
    for btn in root.select('[data-component="FaqRow"], [data-action="toggle-faq"]'):
        if not isinstance(btn, Tag):
            continue
        card = btn
        painted = None
        for _ in range(10):
            card = card.parent
            if not isinstance(card, Tag):
                break
            st = card.get("style") or ""
            if "border-radius" in st and "background-color" in st:
                painted = card
                break
        if painted is None:
            painted = btn.parent if isinstance(btn.parent, Tag) else btn
        if painted not in found:
            painted["data-faq-item"] = painted.get("data-faq-item") or ""
            found.append(painted)
    return found


def _question_text(item) -> str:
    ans = item.find(attrs={"data-faq-answer": True})
    ans_text = ans.get_text(" ", strip=True) if ans else ""
    btn = item.find(attrs={"data-action": "toggle-faq"})
    if btn is not None:
        for t in btn.stripped_strings:
            if t and t != ans_text:
                return t
    for t in item.stripped_strings:
        if not t:
            continue
        if ans_text and t in ans_text:
            continue
        if len(t) > 2:
            return t
    return ""


def _answer_text(item) -> str:
    ans = item.find(attrs={"data-faq-answer": True})
    if ans is not None:
        return ans.get_text(" ", strip=True)
    for p in item.find_all("p"):
        t = p.get_text(" ", strip=True)
        if len(t) > 40:
            return t
    return ""


def _icon_html(item, soup):
    icon = item.find(attrs={"data-faq-icon": True})
    if icon is not None:
        return icon
    for svg in item.find_all("svg"):
        wrap = soup.new_tag("span")
        wrap["data-faq-icon"] = ""
        wrap.append(svg.extract())
        return wrap
    return None


def _merge_class(el, *names: str) -> None:
    existing = el.get("class") or []
    if isinstance(existing, str):
        existing = existing.split()
    merged = list(existing)
    for n in names:
        if n and n not in merged:
            merged.append(n)
    if merged:
        el["class"] = merged


def _strip_width_85(style: str) -> str:
    style = re.sub(r"width\s*:\s*85%\s*;?", "width: 100%;", style or "")
    style = re.sub(r"width\s*:\s*round\(\s*85%\s*,[^)]*\)\s*;?", "width: 100%;", style)
    return style.strip().strip(";")


def restructure_faq_item(item, soup, captured_answer: str, index: int) -> None:
    from bs4 import Tag

    question = _question_text(item)
    answer = _answer_text(item) or captured_answer
    icon = _icon_html(item, soup)
    if icon is not None:
        icon.extract()
    existing_btn = item.find(attrs={"data-action": "toggle-faq"})

    item["data-faq-item"] = item.get("data-faq-item") or ""
    if not item.has_attr("data-open"):
        item["data-open"] = "true" if index == 0 else "false"
    if item.get("role") == "button":
        del item["role"]
    if item.has_attr("tabindex"):
        del item["tabindex"]
    if item.has_attr("id") and str(item.get("id", "")).startswith("faq-q-"):
        del item["id"]
    _merge_class(item, "flex", "flex-col", "w-full", "h-min")
    st = _strip_width_85(item.get("style") or "")
    if st:
        item["style"] = st
    elif item.has_attr("style"):
        del item["style"]

    item.clear()

    if isinstance(existing_btn, Tag) and existing_btn.get("data-action") == "toggle-faq":
        btn = soup.new_tag("button")
        btn.attrs.update({k: v for k, v in existing_btn.attrs.items() if k != "style"})
    else:
        btn = soup.new_tag("button")
    btn["type"] = "button"
    btn["data-action"] = "toggle-faq"
    btn["data-component"] = btn.get("data-component") or "FaqRow"
    btn["aria-expanded"] = "true" if item.get("data-open") == "true" else "false"
    btn["id"] = f"faq-q-{index}"
    label = soup.new_tag("span")
    label.string = question
    btn.append(label)
    if icon is not None:
        btn.append(icon)
    item.append(btn)

    ans = soup.new_tag("div")
    ans["data-faq-answer"] = ""
    ans["id"] = f"faq-a-{index}"
    _merge_class(ans, "w-full")
    ans["style"] = "width: 100%"
    p = soup.new_tag("p")
    p.string = answer
    ans.append(p)
    item.append(ans)
    btn["aria-controls"] = ans["id"]


def apply_detected_components(html: str) -> tuple[str, dict]:
    """Restructure FAQ when present. No-op otherwise. Does not write files."""
    info = {"faq": False, "faq_items": 0, "cloned_answers": 0}
    if not has_faq_hooks(html):
        return html, info
    from bs4 import BeautifulSoup, Tag

    soup = BeautifulSoup(html, "html.parser")
    root = find_faq_root(soup)
    if root is None:
        return html, info
    items = find_faq_items(root)
    if not items:
        return html, info
    captured = ""
    for item in items:
        captured = _answer_text(item) or captured
    cloned = 0
    for i, item in enumerate(items):
        if not isinstance(item, Tag):
            continue
        before = _answer_text(item)
        restructure_faq_item(item, soup, captured, i)
        if not before and captured:
            cloned += 1
    info.update({"faq": True, "faq_items": len(items), "cloned_answers": cloned})
    return dumps(soup, html), info


def patch_faq_width_css(css: str) -> str:
    css = re.sub(
        r"(#faq-section\s+\[data-faq-answer\][^{]*\{[^}]*?)width\s*:\s*85%",
        r"\1width: 100%",
        css,
    )
    css = re.sub(r"width\s*:\s*85%", "width: 100%", css)
    return css


def ensure_faq_css(rebuild_dir: Path, html: str) -> str:
    hover = rebuild_dir / "css" / "hover.css"
    if hover.is_file():
        text = patch_faq_width_css(hover.read_text(encoding="utf-8"))
        if "[data-action=\"toggle-faq\"]" not in text or "width: 100%" not in text:
            if "/* Detected FAQ" not in text:
                text = text.rstrip() + "\n\n" + FAQ_CSS
        hover.write_text(text, encoding="utf-8")
        return html
    dest = rebuild_dir / "css" / "detected-components.css"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(FAQ_CSS, encoding="utf-8")
    return ensure_stylesheet_link(html, "css/detected-components.css")


def _replace_faq_js_block(text: str) -> str:
    marker = "Bind the button, never the card"
    if text.count(marker) == 1 and "item.setAttribute(\"role\"" not in text:
        return text
    pattern = re.compile(
        r"\n\s*// Detect only:.*?\n\}\)\(\);\s*$"
        r"|\n  if \(faq\) \{.*?\n  \}\s*\n\}\)\(\);\s*$",
        re.S,
    )
    if pattern.search(text):
        return pattern.sub("\n" + FAQ_JS + "\n})();\n", text, count=1)
    if text.rstrip().endswith("})();"):
        return text.rstrip()[:-5] + FAQ_JS + "\n})();\n"
    return text.rstrip() + "\n" + FAQ_JS


def ensure_main_js(rebuild_dir: Path, *, faq: bool) -> None:
    path = rebuild_dir / "js" / "main.js"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not faq:
        if not path.is_file():
            return
        return
    if path.is_file():
        text = path.read_text(encoding="utf-8")
        # Drop nested role=button on the card if an inner button exists.
        text = _replace_faq_js_block(text)
        path.write_text(text, encoding="utf-8")
        return
    shell = MAIN_JS_SHELL.replace("FAQ_PLACEHOLDER", FAQ_JS)
    path.write_text(shell, encoding="utf-8")


def ensure_assets(html_path: Path, html: str, info: dict) -> str:
    rebuild_dir = html_path.parent
    if info.get("faq"):
        html = ensure_faq_css(rebuild_dir, html)
        ensure_main_js(rebuild_dir, faq=True)
        if "js/main.js" not in html:
            tag = '<script src="js/main.js" defer></script>'
            if "</body>" in html:
                html = html.replace("</body>", f"  {tag}\n</body>", 1)
            else:
                html += "\n" + tag
    return html


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path)
    ap.add_argument("-o", "--output", type=Path)
    args = ap.parse_args(argv)
    html = args.input.read_text(encoding="utf-8")
    out, info = apply_detected_components(html)
    dest = args.output or args.input
    dest.parent.mkdir(parents=True, exist_ok=True)
    out = ensure_assets(dest, out, info)
    dest.write_text(out, encoding="utf-8")
    if info["faq"]:
        print(
            f"faq: {info['faq_items']} rows "
            f"(cloned answers: {info['cloned_answers']}) → {dest}"
        )
    else:
        print(f"faq: no-op → {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
