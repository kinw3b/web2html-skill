// Paper Snapshot 0.3.12 (lidfahaahiogmnlccifabccgplofocck), ported from
// Paper-Bridge content/paper-snapshot.js @ fda64f2 (0.3.8 base) plus the
// 0.3.12 upstream deltas: throttled frame yield, positioned-element baseline
// resets, canvas/video PNG rasterization, in-page reduced-motion emulation,
// and ::before/::after content:url() images. Keep the computed-style diff.
// 1.2-only layer-name / sidecar / dryRun / AbortController stay in fe().
function svgHrefId(href) {
  const raw = String(href || "").trim();
  if (!raw) return "";
  const urlFn = raw.match(/url\(\s*['"]?#([^)'"]+)/i);
  if (urlFn) {
    try { return decodeURIComponent(urlFn[1]); } catch { return urlFn[1]; }
  }
  if (raw.includes("#")) {
    const hash = raw.slice(raw.lastIndexOf("#") + 1);
    if (!hash) return "";
    try { return decodeURIComponent(hash); } catch { return hash; }
  }
  if (/^[A-Za-z_][\w.-]*$/.test(raw)) return raw;
  return "";
}
function elementId(element) {
  if (typeof element?.id === "string") return element.id;
  return element?.getAttribute?.("id") || "";
}
function htmlHost(element) {
  let node = element;
  while (node && !(node instanceof HTMLElement)) {
    const parent = node.parentElement;
    if (!parent) break;
    node = parent;
  }
  return node || element;
}
function useHref(element) {
  try {
    const animated = element.href && typeof element.href === "object"
      ? (element.href.baseVal || element.href.animVal)
      : "";
    return animated
      || element.getAttribute("href")
      || element.getAttributeNS?.("http://www.w3.org/1999/xlink", "href")
      || element.getAttribute("xlink:href")
      || "";
  } catch {
    return element.getAttribute?.("href") || "";
  }
}
function findById(id, source) {
  if (!id) return null;
  const usable = (node) => Boolean(node) && node !== source && !node.contains?.(source);
  const root = source.getRootNode?.() || source.ownerDocument;
  try {
    if (root instanceof Document || root instanceof ShadowRoot) {
      const hit = root.getElementById(id);
      if (usable(hit)) return hit;
    }
  } catch { /* closed tree */ }
  try {
    const hit = source.ownerDocument.getElementById(id);
    if (usable(hit)) return hit;
  } catch { /* no document */ }
  const queue = [source.ownerDocument];
  const seen = new Set();
  let selector = "";
  try { selector = `[id="${CSS.escape(id)}"]`; } catch { selector = ""; }
  while (queue.length) {
    const tree = queue.shift();
    if (!tree || seen.has(tree)) continue;
    seen.add(tree);
    try {
      if (typeof tree.getElementById === "function") {
        const hit = tree.getElementById(id);
        if (usable(hit)) return hit;
      }
      const match = selector ? tree.querySelector?.(selector) : null;
      if (usable(match)) return match;
      for (const node of tree.querySelectorAll?.("*") || []) {
        if (node.shadowRoot) queue.push(node.shadowRoot);
      }
    } catch { /* skip */ }
  }
  return null;
}
function isCheckVisible(element) {
  if (typeof element.checkVisibility === "function") {
    try { return element.checkVisibility(); } catch { return true; }
  }
  try {
    const style = window.getComputedStyle(element);
    return style.display !== "none" && style.visibility !== "hidden";
  } catch {
    return true;
  }
}
// In-flow Framer appear leftovers (`opacity: 0` + translateY) must not land
// in Paper as 0% blending. Absolute/fixed overlays stay as-is (dropped later).
function restEntranceStyles(r) {
  if (!r || typeof r !== "object") return r;
  const pos = String(r.position || "");
  if (pos === "absolute" || pos === "fixed") return r;
  const op = parseFloat(r.opacity);
  const t = String(r.transform || r.translate || "");
  const zero = Number.isFinite(op) && op < 0.05;
  const mid = Number.isFinite(op) && op < 0.99
    && (/translate(?:3d|X|Y|Z)?\(/i.test(t) || /matrix\(/.test(t));
  if (!zero && !mid) return r;
  r.opacity = "1";
  if (r.transform && r.transform !== "none") r.transform = "none";
  if (r.translate && r.translate !== "none") r.translate = "none";
  if (r.filter && /blur\(/i.test(r.filter)) r.filter = "none";
  return r;
}

async function fe(n, opts = {}) {
  // ---- Paper layer names (lean 1.2) ----
  // Do not stamp generated pc-* path trees as layer-name. Keep the name the
  // scrape / HTML already has, or omit and let Paper name the layer.
  const idPrefix = String(opts.idPrefix ?? ""),
    layerIds = [];
  function pcId(path) {
    return `pc-${idPrefix}${path}`;
  }
  function isPcPathName(name) {
    return /^pc-[a-z0-9]+(?:-[0-9.ab~]+)*$/i.test(String(name || "").trim());
  }
  function paperLayerName(el) {
    const existing = el.getAttribute?.("layer-name") || "";
    if (existing && !isPcPathName(existing)) return existing;
    const framer = el.getAttribute?.("data-framer-name") || "";
    if (framer && !isPcPathName(framer)) return framer;
    return "";
  }
  const h = new Set([
      "area",
      "base",
      "br",
      "col",
      "embed",
      "hr",
      "img",
      "input",
      "link",
      "meta",
      "param",
      "source",
      "track",
      "wbr",
    ]),
    u = ["display", "appearance", "box-sizing"],
    i = document.getElementsByTagName("x-paper-toast")[0],
    f = Array.from(window.getComputedStyle(document.body));
  // 0.3.12: canvas/video elements found during the dry run, rasterized to
  // PNG data URIs between passes so they emit as real <img> layers.
  const rasterCache = new Map();
  // 0.3.12: yield to the browser at most every 16ms (and never while the tab
  // is hidden) instead of once per node — big speed win on large pages.
  const yieldEveryMs = 16;
  let lastYield = performance.now();
  async function yieldFrame() {
    if (document.hidden || performance.now() - lastYield < yieldEveryMs) return;
    await new Promise((done) => {
      let settled = false;
      const finish = () => {
        if (settled) return;
        settled = true;
        cancelAnimationFrame(raf);
        document.removeEventListener("visibilitychange", onVis);
        lastYield = performance.now();
        done();
      };
      const onVis = () => {
        if (document.hidden) finish();
      };
      const raf = requestAnimationFrame(finish);
      document.addEventListener("visibilitychange", onVis);
    });
  }
  let l = 0,
    b = 0;
  f.push(
    "aspect-ratio",
    "paint-order",
    "text-underline-offset",
    "text-decoration-thickness",
    "transform-box",
    "-webkit-text-stroke-color",
    "-webkit-text-stroke-width",
  );
  // 0.3.12: force-apply `prefers-reduced-motion: reduce` CSS across all
  // stylesheets (incl. @import, adopted sheets, shadow roots) and finish any
  // running CSS transitions. Framer often ignores the emulated media query;
  // this makes the reduce rules unconditional for the capture. Returns a
  // cleanup function that restores the original adopted sheets.
  function emulateReducedMotion() {
    const undos = [],
      rmRe = /\(\s*prefers-reduced-motion\s*(?::\s*reduce\s*)?\)/i,
      roots = [document];
    function classifyMedia(mediaList) {
      const kept = [];
      for (const q of Array.from(mediaList)) {
        if (/^(only\s+)?not\b/i.test(q.trim()) || !rmRe.test(q)) continue;
        const flat = q.replace(/\([^()]*\)/g, "");
        if (flat.includes("(") || flat.includes(")") || /\bor\b/i.test(flat)) continue;
        const rest = q
          .replace(rmRe, "")
          .split(/\s+and\s+/i)
          .map((part) => part.trim())
          .filter((part) => part !== "");
        kept.push(rest.join(" and "));
      }
      return kept.length === 0
        ? { kind: "unaffected" }
        : kept.includes("")
          ? { kind: "unconditional" }
          : { kind: "conditional", mediaText: kept.join(", ") };
    }
    function wrap(cssText, stack) {
      let out = cssText;
      for (let i = stack.length - 1; i >= 0; i--) out = `${stack[i]} { ${out} }`;
      return out;
    }
    function collect(sheetOrRules, stack, out, seen) {
      let rules;
      if (sheetOrRules instanceof CSSStyleSheet) {
        if (seen.has(sheetOrRules)) return;
        seen.add(sheetOrRules);
        try {
          rules = sheetOrRules.cssRules;
        } catch {
          return; // cross-origin
        }
      } else rules = sheetOrRules;
      for (const rule of Array.from(rules)) {
        if (typeof CSSImportRule < "u" && rule instanceof CSSImportRule) {
          if (rule.styleSheet) collect(rule.styleSheet, stack, out, seen);
          continue;
        }
        if (typeof CSSMediaRule < "u" && rule instanceof CSSMediaRule) {
          const mediaText = rule.media.mediaText,
            cls = classifyMedia(rule.media);
          if (cls.kind !== "unaffected") {
            const body = Array.from(rule.cssRules, (r) => r.cssText).join("\n");
            if (body) {
              let text = body;
              if (cls.kind === "conditional") text = `@media ${cls.mediaText} { ${text} }`;
              out.push(wrap(text, stack));
            }
            continue;
          }
          collect(rule.cssRules, [...stack, `@media ${mediaText}`], out, seen);
          continue;
        }
        if (!("cssRules" in rule)) continue;
        const brace = rule.cssText.indexOf("{");
        if (brace === -1) continue;
        const prelude = rule.cssText.slice(0, brace).trim(),
          lower = prelude.toLowerCase();
        if (
          lower.startsWith("@supports") ||
          lower.startsWith("@container") ||
          lower.startsWith("@scope")
        )
          collect(rule.cssRules, [...stack, prelude], out, seen);
        else if (lower.startsWith("@layer")) collect(rule.cssRules, stack, out, seen);
      }
    }
    function undoAll() {
      for (const undo of undos) undo();
    }
    try {
      const patched = [];
      while (roots.length > 0) {
        const root = roots.shift(),
          extracted = [],
          seen = new WeakSet(),
          sheets = [];
        if (root.styleSheets) sheets.push(...root.styleSheets);
        if (root.adoptedStyleSheets) sheets.push(...root.adoptedStyleSheets);
        for (const sheet of sheets) collect(sheet, [], extracted, seen);
        if (extracted.length > 0) {
          const overlay = new CSSStyleSheet();
          overlay.replaceSync(extracted.join("\n"));
          const prev = root.adoptedStyleSheets ? [...root.adoptedStyleSheets] : [];
          root.adoptedStyleSheets = [...prev, overlay];
          undos.push(() => {
            root.adoptedStyleSheets = prev;
          });
          patched.push(root);
        }
        for (const el of root.querySelectorAll("*"))
          if (el.shadowRoot) roots.push(el.shadowRoot);
      }
      if (typeof CSSTransition < "u")
        for (const root of patched)
          for (const anim of root.getAnimations())
            if (anim instanceof CSSTransition) anim.finish();
    } catch (err) {
      undoAll();
      throw err;
    }
    return undoAll;
  }
  // 0.3.12: rasterize the canvas/video elements collected during the dry run.
  async function rasterizeCaptured(signal) {
    if (rasterCache.size === 0 || signal.aborted) return;
    await new Promise((done) => {
      const raf = requestAnimationFrame(run),
        timer = setTimeout(run, 100);
      function run() {
        cancelAnimationFrame(raf);
        clearTimeout(timer);
        const jobs = Array.from(rasterCache.keys(), async (el) => {
          try {
            const canvas = toCanvas(el);
            if (!canvas) return;
            const blob = await new Promise((r) => canvas.toBlob(r, "image/png"));
            if (!blob || signal.aborted) return;
            const dataUrl = await new Promise((r, j) => {
              const reader = new FileReader();
              reader.onload = () => r(reader.result);
              reader.onerror = () => j(reader.error);
              reader.readAsDataURL(blob);
            });
            rasterCache.set(el, dataUrl);
          } catch { /* tainted canvas etc. — skip */ }
        });
        Promise.all(jobs).then(finish);
      }
      function finish() {
        cancelAnimationFrame(raf);
        clearTimeout(timer);
        signal.removeEventListener("abort", finish);
        done();
      }
      signal.addEventListener("abort", finish);
    });
  }
  function toCanvas(el) {
    const canvas =
      el instanceof HTMLCanvasElement ? el : document.createElement("canvas");
    if (el instanceof HTMLVideoElement) {
      if (el.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) return;
      canvas.width = el.videoWidth;
      canvas.height = el.videoHeight;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.drawImage(el, 0, 0);
    }
    return canvas;
  }
  function a(e) {
    if (e === null || !i) {
      const o = i?.shadowRoot;
      if (o && i) {
        const r = o.querySelector(".toast__progress");
        r
          ? (r.classList.add("no-transition"),
            i.style.setProperty("--x-paper-progress", "0"),
            requestAnimationFrame(() => {
              (r.classList.remove("no-transition"),
                i?.style.removeProperty("--x-paper-progress"));
            }))
          : i.style.removeProperty("--x-paper-progress");
      } else i && i.style.removeProperty("--x-paper-progress");
      (i?.style.removeProperty("--x-paper-suffix"),
        i?.style.removeProperty("--x-paper-suffix-width"));
      return;
    }
    if (!i) return;
    const t = Math.min(Math.ceil((e / b) * 100), 100);
    b > 50
      ? (i.style.setProperty("--x-paper-progress", t.toString()),
        b > 100 &&
          (i.style.setProperty("--x-paper-suffix", `"${t.toString()}%"`),
          i.style.setProperty("--x-paper-suffix-width", "48px")))
      : i.style.removeProperty("--x-paper-suffix-width");
  }
  function d(e) {
    return (
      [
        "matrix(0, 0, 0, 1, 0, 0)",
        "matrix(0, 0, 0, 0, 0, 0)",
        "scaleX(0)",
        "scale(0)",
        "scaleY(0)",
      ].includes(e.transform || "") &&
      ["absolute", "fixed"].includes(e.position || "")
    );
  }
  function P(e) {
    let t = e.parentElement;
    for (; t;) {
      if (t instanceof SVGElement) return !0;
      t = t.parentElement;
    }
    return !1;
  }
  function m(e) {
    return Object.entries(e)
      .map(([t, o]) => `${t}: ${o};`)
      .join(" ");
  }
  function x(e) {
    return e
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }
  function I(e) {
    return e.replaceAll("&", "&amp;").replaceAll('"', "&quot;");
  }
  // 0.3.12: pseudo-element `content` can mix strings and url() images.
  function parseContent(content) {
    if (!content) return [];
    const primary = content.split(" / ")[0],
      parts = [];
    for (const g of primary.matchAll(/url\(\s*(['"]?)(.*?)\1\s*\)|(['"])(.*?)\3/g))
      if (g[0].startsWith("url(")) {
        if (g[2]) parts.push({ kind: "url", url: g[2] });
      } else parts.push({ kind: "text", text: g[4] });
    return parts;
  }
  // 0.3.12: emit a ::before/::after as <img> when its content is a single
  // url(), a styled <div> of text and inline <img>s otherwise.
  function pseudoHtml(styles) {
    const parts = parseContent(styles.content);
    delete styles.content;
    const css = m(styles),
      first = parts[0];
    if (parts.length === 1 && first && first.kind === "url")
      return `<img src="${I(first.url)}" style="${I(css)}">`;
    let inner = "";
    for (const part of parts)
      inner += part.kind === "url" ? `<img src="${I(part.url)}">` : x(part.text);
    return `<div style="${I(css)}">${inner}</div>`;
  }
  function F(e) {
    if (!e) return "";
    let t = e.parentElement;
    if (
      (!t &&
        e.parentNode instanceof ShadowRoot &&
        e.parentNode.host instanceof Element &&
        (t = e.parentNode.host),
      t)
    ) {
      const o = window.getComputedStyle(t).backgroundColor;
      return o && o !== "rgba(0, 0, 0, 0)" && o !== "transparent" ? o : F(t);
    }
    return "";
  }
  function q(e) {
    const t = [document];
    for (; t.length > 0;) {
      const o = t.shift(),
        r = o.querySelector(e);
      if (r) return r;
      for (const g of o.querySelectorAll("*"))
        g.shadowRoot && t.push(g.shadowRoot);
    }
    return null;
  }
  function $(e, { isRoot: t = !1, pseudo: o } = {}) {
    const r = {},
      g = new Map();
    if (o) {
      const y = window.getComputedStyle(e, o);
      for (const c of f) g.set(c, y.getPropertyValue(c));
    } else {
      const y = e.computedStyleMap?.(),
        c = window.getComputedStyle(e);
      for (const S of f) {
        const T = y?.get(S);
        if (T) g.set(S, T.toString());
        else {
          const O = c.getPropertyValue(S);
          O && g.set(S, O);
        }
      }
    }
    const L = new Map(),
      s = document.createElement("link");
    if (
      ((s.textContent = e.textContent),
      s.style.setProperty("background-color", "transparent", "important"),
      s.style.setProperty("border-color", "hotpink", "important"),
      s.style.setProperty("border-radius", "0", "important"),
      s.style.setProperty("border-width", "0px", "important"),
      s.style.setProperty("border-style", "none", "important"),
      s.style.setProperty("box-shadow", "none", "important"),
      s.style.setProperty("fill", "black", "important"),
      s.style.setProperty("font-size", "1px", "important"),
      s.style.setProperty("font-weight", "400", "important"),
      s.style.setProperty("height", "auto", "important"),
      s.style.setProperty("margin", "0", "important"),
      s.style.setProperty("overflow", "visible", "important"),
      // 0.3.12: neutralize positioning + transforms on the baseline so
      // positioned/transformed elements emit those properties in the diff.
      s.style.setProperty("position", "static", "important"),
      s.style.setProperty("top", "auto", "important"),
      s.style.setProperty("right", "auto", "important"),
      s.style.setProperty("bottom", "auto", "important"),
      s.style.setProperty("left", "auto", "important"),
      s.style.setProperty("inset", "auto", "important"),
      s.style.setProperty("transform", "none", "important"),
      s.style.setProperty("translate", "none", "important"),
      s.style.setProperty("rotate", "none", "important"),
      s.style.setProperty("scale", "none", "important"),
      s.style.setProperty("padding", "0", "important"),
      s.style.setProperty("text-align", "initial", "important"),
      s.style.setProperty("width", "auto", "important"),
      s.style.setProperty("z-index", "auto", "important"),
      t &&
        ((s.style.color = "hotpink"),
        (s.style.lineHeight = "0.1234"),
        (s.style.fontFamily = '"Papyrus"'),
        (s.style.listStyleType = "initial")),
      e.parentElement?.lastElementChild === e
        ? e.insertAdjacentElement("afterend", s)
        : e.insertAdjacentElement("beforebegin", s),
      o)
    ) {
      const y = window.getComputedStyle(s, o);
      for (const c of f) L.set(c, y.getPropertyValue(c));
    } else {
      const y = s.computedStyleMap?.(),
        c = window.getComputedStyle(s);
      for (const S of f) {
        const T = y?.get(S);
        if (T) L.set(S, T.toString());
        else {
          const O = c.getPropertyValue(S);
          O && L.set(S, O);
        }
      }
    }
    s.remove();
    for (const y of f) {
      const c = g.get(y),
        S = L.get(y);
      c &&
        !c.startsWith("--") &&
        (c !== S || u.includes(y)) &&
        (r[y] = c.replaceAll('"', "'"));
    }
    if (t) {
      const y = e.getBoundingClientRect(),
        c = Math.ceil(y.width) + "px",
        S = Math.ceil(y.height) + "px";
      (y.width > 200 ||
        y.height > 200 ||
        r.width?.includes("%") ||
        r.height?.includes("%")) &&
        ((r.width = c), (r.height = S));
    }
    if (
      (t &&
        e instanceof Element &&
        (!g.get("background-color") ||
          g.get("background-color") === "rgba(0, 0, 0, 0)") &&
        (r["background-color"] = F(e)),
      r["scrollbar-gutter"]?.includes("stable") && e instanceof HTMLElement)
    ) {
      const y = parseFloat(g.get("border-left-width") || "0"),
        c = parseFloat(g.get("border-right-width") || "0"),
        S = e.offsetWidth - e.clientWidth - y - c;
      if (S > 0) {
        const T = r["scrollbar-gutter"].includes("both"),
          O = g.get("direction") || "ltr",
          C = parseFloat(r["padding-right"] || "0"),
          w = parseFloat(r["padding-left"] || "0");
        O === "rtl"
          ? ((r["padding-left"] = w + S + "px"),
            T && (r["padding-right"] = C + S + "px"))
          : ((r["padding-right"] = C + S + "px"),
            T && (r["padding-left"] = w + S + "px"));
      }
    }
    return ((o === "::after" || o === "::before") && !r.content) ||
      Object.keys(r).length === 0
      ? {}
      : restEntranceStyles(r);
  }
  function R(e) {
    const t = e.textContent;
    if (!t) return "";
    if (e.parentElement) {
      const g = window.getComputedStyle(e.parentElement).whiteSpace;
      if (g === "pre" || g === "pre-wrap") return t;
      if (g === "pre-line") return t.replace(/[\t\f\r ]+/g, " ");
    }
    const o = t.replace(/[\t\n\r\f ]+/g, " ").replace(/^ | $/g, "");
    if (o) {
      const g = /^[\t\n\r\f ]*/.exec(t)[0].length,
        L = /[\t\n\r\f ]*$/.exec(t)[0].length;
      let s = !1,
        H = !1;
      if (g > 0) {
        const y = document.createRange();
        (y.setStart(e, 0),
          y.setEnd(e, g),
          (s = y.getBoundingClientRect().width > 0));
      }
      if (L > 0) {
        const y = document.createRange();
        (y.setStart(e, t.length - L),
          y.setEnd(e, t.length),
          (H = y.getBoundingClientRect().width > 0));
      }
      return (s ? " " : "") + o + (H ? " " : "");
    }
    const r = document.createRange();
    return (r.selectNode(e), r.getBoundingClientRect().width === 0 ? "" : " ");
  }
  async function E(
    e,
    {
      abortSignal: t,
      dryRun: o = !1,
      __isRoot: r = !0,
      __processedNodes: g = 0,
      __path: ie = "0",
    } = {},
  ) {
    if (t?.aborted) return { html: "", processedNodes: 0 };
    if ((o || a(g + 1), !(e instanceof Element || e instanceof SVGElement))) {
      if (o) return { html: "", processedNodes: 1 };
      if (e instanceof Text) {
        const v = R(e);
        return { html: x(v), processedNodes: 1 };
      }
      return { html: "", processedNodes: 1 };
    }
    const L = e.tagName.toLowerCase(),
      s = window.getComputedStyle(e),
      H = ["absolute", "fixed"].includes(s.position),
      y =
        !!e.parentElement &&
        ["block", "inline-block"].includes(
          window.getComputedStyle(e.parentElement).display,
        ),
      c = parseFloat(s.height) === 0 || parseFloat(s.width) === 0,
      S =
        parseFloat(s.paddingTop) > 0 ||
        parseFloat(s.paddingRight) > 0 ||
        parseFloat(s.paddingBottom) > 0 ||
        parseFloat(s.paddingLeft) > 0,
      T = s.overflowX !== "visible" && s.overflowY !== "visible",
      O = c && (H || y) && !S && T,
      C = s.display === "none",
      w =
        e.parentElement ??
        (e.parentNode instanceof ShadowRoot ? e.parentNode : null),
      // 0.3.12: also drop opacity-0 only-children (modal/menu shells left in
      // the DOM at opacity 0). In-flow appear leftovers are still rest-painted
      // upstream of this via settlePainted, so live opacity is 1 for those.
      J = s.opacity === "0" && (H || w?.childElementCount === 1),
      B = L.startsWith("x-paper-") || elementId(e).startsWith("x-paper-"),
      se = ["script", "style", "meta", "link", "noscript"].includes(L) || B,
      Q = !(s.display === "contents") && !P(e) && !isCheckVisible(e),
      re = Q && !C && s.contentVisibility !== "hidden";
    if (O || C || J || se || Q)
      return (re && !o && l++, { html: "", processedNodes: 1 });
    let K = 1;
    const z = [];
    let k = {};
    const ae = !(e instanceof SVGElement) || e instanceof SVGGraphicsElement;
    if (!o && ae) {
      const v = $(e, { pseudo: "::before" });
      if (Object.keys(v).length && !d(v)) z.push(pseudoHtml(v));
      k = $(e, { isRoot: r });
    }
    const U = e.getAttributeNames().map((v) => [v, e.getAttribute(v) || ""]),
      ee = e.shadowRoot
        ? Array.from(e.shadowRoot.childNodes)
        : Array.from(e.childNodes);
    // 0.3.12: canvas/video subtrees are replaced by a rasterized <img>.
    if (e instanceof HTMLCanvasElement || e instanceof HTMLVideoElement)
      ee.length = 0;
    let oe = 0;
    for (let v = 0; v < ee.length; v++) {
      const A = ee[v],
        N = [];
      // Index over ELEMENT children only, so the path matches a plain
      // parent.children walk at Tags-scan time. Dropped (invisible) elements
      // still consume their index — that is what keeps the two walks aligned.
      const ne = A instanceof Element ? `${ie}.${oe++}` : null;
      if (A instanceof HTMLSlotElement)
        N.push(...A.assignedNodes({ flatten: !0 }));
      else if (A instanceof SVGElement && A.tagName.toLowerCase() === "use") {
        const W = svgHrefId(useHref(A)),
          j = findById(W, A);
        if (j)
          if (["symbol", "svg"].includes(j.tagName.toLowerCase())) {
            const de = new Set(["viewBox", "preserveAspectRatio"]);
            for (const V of j.getAttributeNames())
              if (!["id", "class", "style"].includes(V))
                if (de.has(V)) {
                  const te = U.findIndex(([pe]) => pe === V);
                  (te >= 0 && U.splice(te, 1), U.push([V, j.getAttribute(V)]));
                } else if (!U.some(([pe]) => pe === V)) U.push([V, j.getAttribute(V)]);
            N.push(...Array.from(j.childNodes));
          } else N.push(j);
      } else if (e instanceof HTMLSelectElement) {
        const D = e.options[e.selectedIndex];
        D && z.push(`<option selected>${x(D.textContent || "")}</option>`);
      } else A && N.push(A);
      if (N.length)
        for (let ue = 0; ue < N.length; ue++) {
          const D = N[ue];
          o || (await yieldFrame());
          // <slot> / <use> expand one child into several; keep each unique.
          const G = ne === null ? `${ie}.x${v}` : ue === 0 ? ne : `${ne}~${ue}`;
          const W = await E(D, {
            abortSignal: t,
            dryRun: o,
            __isRoot: !1,
            __processedNodes: g + K,
            __path: G,
          });
          ((K += W.processedNodes), o || z.push(W.html));
        }
    }
    if (o) {
      // Dry run registers canvas/video for rasterization between passes.
      if (e instanceof HTMLCanvasElement || e instanceof HTMLVideoElement)
        rasterCache.set(e, void 0);
      return { html: "", processedNodes: K };
    }
    const Y = $(e, { pseudo: "::after" });
    if (Object.keys(Y).length && !d(Y)) z.push(pseudoHtml(Y));
    const M = [];
    if (
      e instanceof HTMLImageElement &&
      (M.push(["src", e.src]), !k.width && !k.height)
    ) {
      const v = window.getComputedStyle(e);
      ((k.width = v.width), (k.height = v.height));
    }
    if (e instanceof HTMLInputElement) {
      if (
        (e.value && M.push(["value", e.value]),
        e.type && M.push(["type", e.type]),
        (e.checked || e.defaultChecked) && M.push(["checked", "true"]),
        e.placeholder)
      ) {
        const v = $(e, { pseudo: "::placeholder" });
        (M.push(["placeholder", e.placeholder]),
          M.push(["data-paper-placeholder-styles", m(v)]));
      }
    } else if (
      e instanceof HTMLTextAreaElement &&
      (e.value && z.unshift(x(e.value)), e.placeholder)
    ) {
      const v = $(e, { pseudo: "::placeholder" });
      (M.push(["placeholder", e.placeholder]),
        M.push(["data-paper-placeholder-styles", m(v)]));
    }
    const ce = [
        "table",
        "thead",
        "tbody",
        "tfoot",
        "tr",
        "td",
        "th",
        "caption",
        "colgroup",
        "col",
      ],
      le = ["body"];
    let X = [...ce, ...le].includes(L) ? "div" : L;
    // 0.3.12: emit rasterized canvas/video as a real <img> layer.
    if (e instanceof HTMLCanvasElement || e instanceof HTMLVideoElement) {
      const dataUrl = rasterCache.get(e);
      if (dataUrl?.startsWith("data:image/png;base64,")) {
        X = "img";
        M.push(["src", dataUrl]);
        if (k.width === void 0 || k.width === "auto") k.width = s.width;
        if (k.height === void 0 || k.height === "auto") k.height = s.height;
      }
    }
    if (
      (X !== L && M.push(["paper-snapshot-original-tag", e.tagName]),
      e instanceof SVGElement)
    ) {
      const v = window.getComputedStyle(e);
      ((k.width === void 0 || k.width === "auto") && (k.width = v.width),
        (k.height === void 0 || k.height === "auto") && (k.height = v.height),
        U.forEach(([A, N]) => {
          if (!(["class", "style", "display", "overflow"].includes(A) || !N)) {
            if (["fill", "stroke", "color"].includes(A)) {
              let D = k[A];
              if ((!D || D.toLowerCase() === "currentcolor") && N.toLowerCase() === "currentcolor") {
                D = k.color || v[A] || v.color;
              }
              if (D && D.toLowerCase() !== "currentcolor") N = D;
            }
            (M.push([A, N]), !["width", "height"].includes(A) && delete k[A]);
          }
        }));
    }
    if (
      (Object.keys(k).length > 0 &&
        ((k.width || k.height) && ((k.width ??= "auto"), (k.height ??= "auto")),
        M.push(["style", m(k)])),
      P(e) || (isCheckVisible(e) && k.display !== "contents"))
    ) {
      // Do not grow a pc-id tree in Paper. Drop generated path ids; keep a
      // scrape name when the HTML already has one; otherwise let Paper name it.
      for (let di = M.length - 1; di >= 0; di--) {
        if (M[di][0] === "layer-name" && isPcPathName(M[di][1])) M.splice(di, 1);
      }
      if (!P(e)) {
        const G = pcId(ie),
          me = e.getBoundingClientRect(),
          ye = (e.textContent || "").replace(/\s+/g, " ").trim(),
          rawClass =
            (e.getAttribute && e.getAttribute("class")) ||
            (typeof e.className === "string" ? e.className : "") ||
            "",
          keyClass = rawClass
            .trim()
            .split(/\s+/)
            .filter((t) => t === "framer-text" || t.startsWith("framer-styles-preset-")),
          paperName = paperLayerName(e);
        if (paperName && !M.some(([attr]) => attr === "layer-name")) {
          M.unshift(["layer-name", paperName]);
        }
        layerIds.push({
            pcId: G,
            path: ie,
            tag: L,
            class: rawClass,
            classes: keyClass,
            role: e.getAttribute?.("role") || "",
            "data-framer-name": e.getAttribute?.("data-framer-name") || "",
            text: ye.slice(0, 120),
            alt: e.getAttribute?.("alt") || "",
            href: e.getAttribute?.("href") || "",
            src: e instanceof HTMLImageElement ? e.src : "",
            pageX: Math.round(me.x + window.scrollX),
            pageY: Math.round(me.y + window.scrollY),
            w: Math.round(me.width),
            h: Math.round(me.height),
          });
      }
      const v = `<${X} ${M.map(([D, W]) => `${D}="${I(W)}"`).join(" ")}>`,
        A = h.has(X) ? "" : `</${X}>`;
      return { html: `${v}${z.join("")}${A}`, processedNodes: K };
    }
    return { html: z.join(""), processedNodes: K };
  }
  const p = htmlHost(q(n));
  if (p) {
    let e = function (o) {
      o.key === "Escape" &&
        (o.preventDefault(), o.stopPropagation(), t.abort());
    };
    const t = new AbortController();
    window.addEventListener("keydown", e, { capture: !0 });
    let undoReducedMotion = null;
    try {
      try {
        undoReducedMotion = emulateReducedMotion();
      } catch (err) {
        console.warn("Paper: reduced motion emulation failed, capturing as-is.", err);
      }
      (a(null),
        (b = (await E(p, { dryRun: !0 })).processedNodes),
        a(0),
        await new Promise((g) => setTimeout(g, 500)),
        await rasterizeCaptured(t.signal));
      (layerIds.length = 0);
      const r = await E(p, { abortSignal: t.signal });
      return t.signal.aborted
        ? { status: "aborted" }
        : l > 0
          ? r.html === ""
            ? {
                status: "error",
                error:
                  "Your selection could not be captured, try selecting something else.",
              }
            : {
                status: "success",
                html: r.html,
                ids: layerIds,
                warning: "Some elements were unable to be captured.",
              }
          : { status: "success", html: r.html, ids: layerIds };
    } finally {
      (window.removeEventListener("keydown", e, { capture: !0 }),
        undoReducedMotion && undoReducedMotion(),
        p.removeAttribute("data-paper-element-picker"));
    }
  }
  return { status: "error", error: "Your selection could not be captured." };
}
