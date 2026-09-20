// Section detection, shared by capture.mjs (--list-sections) and
// capture-sections.mjs (the visible per-section loop).
//
// Injected as a source string; defines window.__xPaperDetectSections().
//
// Returns [{ selector, name, w, h, top }] in document order.
// Per-viewport only. Do not reuse another width's flex-wrap / column
// count. Box metrics (icon size, container w/h, gap) come from the
// live inventory at this width (Pitfall #75).
//
// Selectors are nth-child paths rather than data attributes ON PURPOSE: the
// serializer captures every attribute it finds, so marking the DOM would leak
// the markers into the imported HTML.

(() => {
  if (window.__xPaperDetectSections) return;

  function cssPath(el) {
    const parts = [];
    let node = el;
    while (node && node.nodeType === 1 && node !== document.body) {
      const parent = node.parentElement;
      if (!parent) break;
      const idx = Array.prototype.indexOf.call(parent.children, node) + 1;
      parts.unshift(`${node.tagName.toLowerCase()}:nth-child(${idx})`);
      node = parent;
    }
    return `body > ${parts.join(" > ")}`;
  }

  function slug(text, fallback) {
    const s = (text || "")
      .trim()
      .toLowerCase()
      .replace(/['’"]/g, "")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .split("-")
      .slice(0, 5)
      .join("-")
      .slice(0, 40);
    return s || fallback;
  }

  function nameFor(el, i, isLast) {
    const tag = el.tagName.toLowerCase();
    const framerName = el.getAttribute("data-framer-name");
    if (framerName) return slug(framerName, `section-${i + 1}`);

    // Structural tags win over content — a <footer> is a footer regardless of
    // what text happens to sit in it.
    if (tag === "footer") return "footer";
    if (tag === "nav") return "nav";

    // Last content band is the footer. Do not slug it from a heading or
    // street address (Fluxy "Marketing solution that just makes sense").
    if (isLast && i > 0) return "footer";

    const heading = el.querySelector("h1, h2, h3");

    const anyHeading = heading || el.querySelector("h4, h5, h6");
    if (anyHeading && anyHeading.textContent.trim()) {
      return slug(anyHeading.textContent, `section-${i + 1}`);
    }

    const aria = el.getAttribute("aria-label");
    if (aria) return slug(aria, `section-${i + 1}`);

    // No heading and no label — positional is clearer than guessing from body
    // copy, which produces names like "officegermany-785-15h-street".
    return `section-${i + 1}`;
  }

  window.__xPaperDetectSections = function detectSections() {
    const pageWidth = document.documentElement.scrollWidth;
    const vw = window.innerWidth;
    const minWidth = Math.min(pageWidth * 0.9, vw * 0.85);

    function isSkippable(c) {
      if (!c || c.nodeType !== 1) return true;
      const tag = c.tagName.toLowerCase();
      if (tag.startsWith("x-paper-")) return true;
      if (["script", "style", "link", "meta", "noscript"].includes(tag)) return true;
      if (c.closest && c.closest("x-paper-hud")) return true;
      return false;
    }

    // Framer pages: walk down to the first container with >=3 full-width,
    // in-flow, tall children (same heuristic as scrape-web.sh). Scoring
    // every node by kid-count prefers floating "Buy Template" overlays.
    function fwTall(parent) {
      return Array.from(parent.children).filter((c) => {
        if (isSkippable(c)) return false;
        const r = c.getBoundingClientRect();
        const s = window.getComputedStyle(c);
        if (s.display === "none" || s.visibility === "hidden") return false;
        if (s.position === "fixed" || s.position === "sticky") return false;
        return r.width >= vw * 0.7 && c.scrollHeight >= 200;
      });
    }

    let best = null;
    const queue = [document.body];
    while (queue.length) {
      const n = queue.shift();
      if (!n || isSkippable(n)) continue;
      const fw = fwTall(n);
      if (fw.length >= 3) {
        best = n;
        break;
      }
      for (const c of Array.from(n.children)) {
        if (isSkippable(c)) continue;
        const r = c.getBoundingClientRect();
        if (r.width >= vw * 0.7 && c.scrollHeight >= 400) queue.push(c);
      }
    }

    const seen = new Map();
    const out = [];
    let kids = best ? fwTall(best) : [];

    // Named Framer layers as a second pass when the stack is thin (inner pages
    // that are one wrapper + footer, or breakpoint variants).
    if (kids.length < 3) {
      const named = Array.from(document.querySelectorAll("[data-framer-name]")).filter((el) => {
        if (isSkippable(el)) return false;
        const s = window.getComputedStyle(el);
        if (s.display === "none" || s.visibility === "hidden") return false;
        if (s.position === "fixed" || s.position === "sticky") return false;
        const r = el.getBoundingClientRect();
        if (r.width < vw * 0.55 || el.scrollHeight < 180) return false;
        return true;
      });
      const roots = named.filter((el) => !named.some((o) => o !== el && o.contains(el)));
      if (roots.length > kids.length) kids = roots;
    }

    if (!kids.length) {
      return [{ selector: "body", name: "page", w: pageWidth, h: document.body.scrollHeight, top: 0 }];
    }

    kids.forEach((el, i) => {
      const r = el.getBoundingClientRect();
      let name = nameFor(el, i, i === kids.length - 1);
      // De-duplicate names so Paper layer names stay unique.
      if (seen.has(name)) {
        const n = seen.get(name) + 1;
        seen.set(name, n);
        name = `${name}-${n}`;
      } else {
        seen.set(name, 1);
      }
      out.push({
        selector: cssPath(el),
        name,
        w: Math.round(r.width),
        h: Math.round(r.height),
        top: Math.round(r.top + window.scrollY),
      });
    });

    // Chrome (nav, header, menu bars) often lives OUTSIDE the <main> section
    // container, so it never enters `out` and Paper misses the menu.
    // Fixed/sticky bars always qualify. Relative/absolute/static Framer top
    // bars also qualify when they look like nav (data-framer-name matching
    // Nav Bar / Navbar / Navigation / Header, or <nav>/<header> tags).
    // Pair with capture fullpage/chrome screenshots for QA even if serialize fails.
    const covered = new Set(out.map((s) => s.selector));
    const chrome = [];
    const looksLikeNavName = (raw) => {
      const n = String(raw || "").trim().toLowerCase();
      if (!n) return false;
      return (
        /\bnav\s*bars?\b/.test(n) ||
        /\bnavbars?\b/.test(n) ||
        /\bnavigation\b/.test(n) ||
        /\bheaders?\b/.test(n) ||
        n === "nav" ||
        n === "nav bar" ||
        n === "nav-bar"
      );
    };
    for (const el of document.body.querySelectorAll("header, nav, [role='navigation'], [data-framer-name]")) {
      if (el.closest("x-paper-hud") || (el.tagName && el.tagName.toLowerCase().startsWith("x-paper-"))) continue;
      // Skip if already a section child we captured
      if (out.some((s) => {
        try { return document.querySelector(s.selector) === el || document.querySelector(s.selector)?.contains(el); }
        catch { return false; }
      })) continue;
      const st = window.getComputedStyle(el);
      const pos = st.position;
      const tag = el.tagName.toLowerCase();
      const framerName = el.getAttribute("data-framer-name") || "";
      const isFixedSticky = pos === "fixed" || pos === "sticky";
      const isNavTag = tag === "nav" || tag === "header" || el.getAttribute("role") === "navigation";
      const isNamedNav = looksLikeNavName(framerName);
      // Non-fixed chrome only when it looks like a top nav/header.
      if (!isFixedSticky && !(isNavTag || isNamedNav)) continue;
      if (!isFixedSticky && pos !== "relative" && pos !== "absolute" && pos !== "static") continue;
      const r = el.getBoundingClientRect();
      if (r.width < minWidth * 0.85 || r.height < 36 || r.height > window.innerHeight * 0.55) continue;
      // Relative/static/absolute bars must sit near the top of the page.
      if (!isFixedSticky && r.top + window.scrollY > 120) continue;
      const sel = cssPath(el);
      if (covered.has(sel)) continue;
      covered.add(sel);
      let name = tag === "nav" ? "nav" : tag === "header" ? "header" : "site-chrome";
      if (isNamedNav && name === "site-chrome") name = "nav";
      if (seen.has(name)) {
        const n = seen.get(name) + 1;
        seen.set(name, n);
        name = `${name}-${n}`;
      } else {
        seen.set(name, 1);
      }
      chrome.push({
        selector: sel,
        name,
        w: Math.round(r.width),
        h: Math.round(r.height),
        top: Math.round(r.top + window.scrollY),
        chrome: true,
      });
    }
    // Also: direct body children that are fixed full-width bars (Framer often wraps nav in a div)
    for (const el of document.body.children) {
      if (!el || el.nodeType !== 1) continue;
      if (el.tagName.toLowerCase().startsWith("x-paper-")) continue;
      const st = window.getComputedStyle(el);
      if (st.position !== "fixed" && st.position !== "sticky") continue;
      const r = el.getBoundingClientRect();
      if (r.width < minWidth * 0.85 || r.height < 36 || r.height > 200) continue;
      if (r.top > 80) continue; // top bar only
      const sel = cssPath(el);
      if (covered.has(sel)) continue;
      // Skip if any chrome entry already contains this
      if (chrome.some((c) => {
        try {
          const n = document.querySelector(c.selector);
          return n && (n === el || n.contains(el) || el.contains(n));
        } catch { return false; }
      })) continue;
      covered.add(sel);
      let name = "site-chrome";
      if (seen.has(name)) {
        const n = seen.get(name) + 1;
        seen.set(name, n);
        name = `${name}-${n}`;
      } else {
        seen.set(name, 1);
      }
      chrome.push({
        selector: sel,
        name,
        w: Math.round(r.width),
        h: Math.round(r.height),
        top: Math.round(r.top + window.scrollY),
        chrome: true,
      });
    }

    // Storm 2026-08: Framer wraps one menu as <header><header><nav>.
    // Emitting all three stacks three navbars in Paper. Keep the outermost
    // chrome node only — descendants share the same visual slot.
    const collapsed = chrome.filter((a) => {
      return !chrome.some((b) => {
        if (a === b) return false;
        try {
          const ea = document.querySelector(a.selector);
          const eb = document.querySelector(b.selector);
          return ea && eb && eb.contains(ea) && eb !== ea;
        } catch {
          return b.selector && a.selector && a.selector.startsWith(`${b.selector} > `);
        }
      });
    });

    return collapsed.length ? [...collapsed, ...out] : out;
  };
})();
