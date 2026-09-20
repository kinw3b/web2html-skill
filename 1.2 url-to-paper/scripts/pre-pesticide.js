// Pre-pesticide HUD, injected into the *live* page before Stage P capture.
//
// Smart sibling of rebuild qa-overlay (end-of-build Pesticide outlines).
// This one inventories the live DOM so we can compare semantics, tags,
// images, and forms against Paper after import.
//
// EVERY element created here is `x-paper-` prefixed. The serializer skips
// any element whose tagName or id starts with "x-paper-", so the HUD must
// not leak into write_html. Rename anything and it will start appearing
// inside the imported Paper artboard.
//
// Injected as a source string; defines window.__xPaperPrePesticide.

(() => {
  if (window.__xPaperPrePesticide) return;

  const HUD_TAG = "x-paper-prepesticide";
  const HUD_ID = "x-paper-prepesticide";
  const HUD_STYLE_ID = "x-paper-prepesticide-css";
  const HUD_OUTLINE_ID = "x-paper-prepesticide-outline";
  const LANDMARKS = ["header", "nav", "main", "section", "footer", "form", "img", "a", "button", "h1", "h2", "h3"];

  let hud = null;
  let shadow = null;
  let outline = null;
  let styleEl = null;
  let hoverEl = null;
  let pinned = false;
  let raf = 0;
  let twPrefix = "";
  let lastRecord = null;
  let bound = false;

  function isSkip(el) {
    if (!el || el.nodeType !== 1) return true;
    const tag = el.tagName.toLowerCase();
    if (tag.startsWith("x-paper-") || (el.id && el.id.startsWith("x-paper-"))) return true;
    if (el.closest && (el.closest(HUD_TAG) || el.closest("x-paper-hud"))) return true;
    return false;
  }

  function slugify(text, fallback) {
    const s = String(text || "")
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

  function paperType(el) {
    const tag = el.tagName.toLowerCase();
    if (tag === "img") return "Image";
    if (tag === "svg" || el.closest?.("svg") === el || tag === "svg") return "SVG";
    if (tag === "svg") return "SVG";
    const text = (el.textContent || "").replace(/\s+/g, " ").trim();
    if (["h1", "h2", "h3", "h4", "h5", "h6", "p", "span", "a", "button", "label", "li"].includes(tag) && text) {
      return "Text";
    }
    return "Frame";
  }

  function paintRole(el) {
    const tag = el.tagName.toLowerCase();
    if (el.getAttribute("aria-hidden") === "true") return "decorative";
    const role = el.getAttribute("role") || "";
    if (role === "presentation" || role === "none") return "decorative";
    if (el.getAttribute("data-decorative") === "true") return "decorative";
    if (tag === "img") {
      const alt = el.getAttribute("alt");
      const w = el.naturalWidth || 0;
      const h = el.naturalHeight || 0;
      if (alt === "" && w * h > 0 && w * h < 80 * 80) return "decorative";
      return "content";
    }
    if (tag === "svg") {
      const titled = el.querySelector("title");
      const r = el.getBoundingClientRect();
      if (!titled && r.width * r.height < 80 * 80) return "decorative";
      return titled ? "content" : "decorative";
    }
    return "content";
  }

  function sectionSlug(el) {
    const detected = (typeof window.__xPaperDetectSections === "function" && window.__xPaperDetectSections()) || [];
    for (const s of detected) {
      try {
        const node = document.querySelector(s.selector);
        if (node && (node === el || node.contains(el))) return s.name;
      } catch {
        /* ignore bad selectors */
      }
    }
    let n = el;
    while (n && n.nodeType === 1) {
      const tag = n.tagName.toLowerCase();
      if (["header", "section", "footer", "nav", "main"].includes(tag) || n.getAttribute("data-framer-name")) {
        const framer = n.getAttribute("data-framer-name");
        if (framer) return slugify(framer, tag);
        if (n.id) return slugify(n.id, tag);
        const heading = n.querySelector("h1, h2, h3");
        if (heading && heading.textContent.trim()) return slugify(heading.textContent, tag);
        return slugify(tag, "section");
      }
      n = n.parentElement;
    }
    return "page";
  }

  function rgbToHex(v) {
    const m = String(v).match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/i);
    if (!m) return String(v).replace(/\s+/g, "");
    const h = (n) => Number(n).toString(16).padStart(2, "0");
    return `#${h(m[1])}${h(m[2])}${h(m[3])}`;
  }

  function tailwindOf(el) {
    const p = twPrefix;
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    const cls = [];
    if (r.width) cls.push(`${p}w-[${Math.round(r.width)}px]`);
    if (r.height) cls.push(`${p}h-[${Math.round(r.height)}px]`);
    if (cs.display === "flex") {
      cls.push(`${p}flex`);
      if (cs.flexDirection === "column") cls.push(`${p}flex-col`);
      if (cs.alignItems === "center") cls.push(`${p}items-center`);
      if (cs.alignItems === "flex-end") cls.push(`${p}items-end`);
      if (cs.justifyContent === "center") cls.push(`${p}justify-center`);
      if (cs.justifyContent === "space-between") cls.push(`${p}justify-between`);
      const gap = parseFloat(cs.gap);
      if (gap) cls.push(`${p}gap-[${Math.round(gap)}px]`);
    }
    const radius = parseFloat(cs.borderRadius);
    if (radius) cls.push(radius >= 999 ? `${p}rounded-full` : `${p}rounded-[${Math.round(radius)}px]`);
    if (cs.backgroundColor && cs.backgroundColor !== "rgba(0, 0, 0, 0)" && cs.backgroundColor !== "transparent") {
      cls.push(`${p}bg-[${rgbToHex(cs.backgroundColor)}]`);
    }
    if (cs.color) cls.push(`${p}text-[${rgbToHex(cs.color)}]`);
    const fs = parseFloat(cs.fontSize);
    if (fs) cls.push(`${p}text-[${Math.round(fs)}px]`);
    if (cs.fontWeight && cs.fontWeight !== "400" && cs.fontWeight !== "normal") {
      cls.push(`${p}font-[${cs.fontWeight}]`);
    }
    return cls.join(" ");
  }

  function inspect(el) {
    const tag = el.tagName.toLowerCase();
    const classes = el.classList ? Array.from(el.classList).filter((c) => c && !c.startsWith("x-paper-") && !c.startsWith("qa-")) : [];
    const img = tag === "img" ? el : el.querySelector && el.querySelector("img");
    const record = {
      tag,
      id: el.id || "",
      classes,
      framerName: el.getAttribute("data-framer-name") || "",
      role: el.getAttribute("role") || "",
      text: (el.textContent || "").replace(/\s+/g, " ").trim().slice(0, 80),
      landmark: LANDMARKS.includes(tag),
      landmarkKind: LANDMARKS.includes(tag) ? tag : "",
      paperType: paperType(el),
      paintRole: paintRole(el),
      sectionSlug: sectionSlug(el),
      bbox: {
        x: Math.round(el.getBoundingClientRect().left + window.scrollX),
        y: Math.round(el.getBoundingClientRect().top + window.scrollY),
        w: Math.round(el.getBoundingClientRect().width),
        h: Math.round(el.getBoundingClientRect().height),
      },
      tailwind: tailwindOf(el),
    };
    if (img) {
      record.img = {
        src: img.currentSrc || img.src || "",
        alt: img.getAttribute("alt") ?? "",
        w: img.naturalWidth || 0,
        h: img.naturalHeight || 0,
      };
    }
    const bits = [
      `slug=${record.sectionSlug}`,
      `type=${record.paperType}`,
      `role=${record.paintRole}`,
      `tag=${record.tag}`,
    ];
    if (record.framerName) bits.push(`framer=${record.framerName}`);
    if (record.img?.src) bits.push(`img=${record.img.src}`);
    record.paperRow = bits.join("  ");
    return record;
  }

  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text).catch(() => fallbackCopy(text));
    }
    fallbackCopy(text);
    return Promise.resolve();
  }

  function fallbackCopy(text) {
    const ta = document.createElement("x-paper-prepesticide-copy");
    ta.id = "x-paper-prepesticide-copy";
    ta.textContent = text;
    ta.setAttribute("contenteditable", "true");
    ta.style.cssText = "position:fixed;left:-9999px;top:0";
    document.documentElement.appendChild(ta);
    const range = document.createRange();
    range.selectNodeContents(ta);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
    try {
      document.execCommand("copy");
    } catch {
      /* ignore */
    }
    sel.removeAllRanges();
    ta.remove();
  }

  function ensureStyle() {
    if (styleEl) return;
    styleEl = document.createElement("style");
    styleEl.id = HUD_STYLE_ID;
    styleEl.textContent = `
      html[data-x-paper-prepesticide="on"] body { outline: 1px solid #2980b9; }
      html[data-x-paper-prepesticide="on"] article { outline: 1px solid #3498db; }
      html[data-x-paper-prepesticide="on"] nav { outline: 1px solid #0088c3; }
      html[data-x-paper-prepesticide="on"] aside { outline: 1px solid #33a0ce; }
      html[data-x-paper-prepesticide="on"] section { outline: 1px solid #66b8da; }
      html[data-x-paper-prepesticide="on"] header { outline: 1px solid #99cfe7; }
      html[data-x-paper-prepesticide="on"] footer { outline: 1px solid #cce7f3; }
      html[data-x-paper-prepesticide="on"] h1 { outline: 1px solid #162544; }
      html[data-x-paper-prepesticide="on"] h2 { outline: 1px solid #314e6e; }
      html[data-x-paper-prepesticide="on"] h3 { outline: 1px solid #3e5e85; }
      html[data-x-paper-prepesticide="on"] main { outline: 1px solid #2f4f90; }
      html[data-x-paper-prepesticide="on"] div { outline: 1px solid #036cdb; }
      html[data-x-paper-prepesticide="on"] p { outline: 1px solid #ac050b; }
      html[data-x-paper-prepesticide="on"] ul,
      html[data-x-paper-prepesticide="on"] ol,
      html[data-x-paper-prepesticide="on"] li { outline: 1px solid #d90416; }
      html[data-x-paper-prepesticide="on"] button { outline: 1px solid #da8301; }
      html[data-x-paper-prepesticide="on"] form,
      html[data-x-paper-prepesticide="on"] input,
      html[data-x-paper-prepesticide="on"] textarea,
      html[data-x-paper-prepesticide="on"] select { outline: 1px solid #fca600; }
      html[data-x-paper-prepesticide="on"] img,
      html[data-x-paper-prepesticide="on"] svg { outline: 1px solid #22746b; }
      html[data-x-paper-prepesticide="on"] a { outline: 1px solid #ff62ab; }
      html[data-x-paper-prepesticide="on"] span { outline: 1px solid #cc2643; }
      html[data-x-paper-prepesticide="on"] ${HUD_TAG},
      html[data-x-paper-prepesticide="on"] ${HUD_TAG} *,
      html[data-x-paper-prepesticide="on"] #${HUD_OUTLINE_ID} { outline: none !important; }
    `;
    document.documentElement.appendChild(styleEl);
    document.documentElement.setAttribute("data-x-paper-prepesticide", "on");
  }

  function ensure() {
    if (hud) return;
    ensureStyle();

    hud = document.createElement(HUD_TAG);
    hud.id = HUD_ID;
    hud.style.cssText = [
      "position:fixed",
      "right:16px",
      "top:16px",
      "z-index:2147483647",
      "pointer-events:auto",
    ].join(";");
    shadow = hud.attachShadow({ mode: "open" });
    shadow.innerHTML = `
      <style>
        :host { all: initial; }
        .card {
          font: 500 12px/1.4 ui-sans-serif, -apple-system, system-ui, sans-serif;
          color: #f4f1ea;
          background: rgba(17,19,24,0.96);
          backdrop-filter: blur(12px);
          border: 1px solid rgba(255,255,255,0.12);
          border-radius: 12px;
          padding: 12px 14px;
          width: min(380px, 92vw);
          box-shadow: 0 12px 32px rgba(0,0,0,0.4);
          max-height: calc(100vh - 32px);
          overflow: auto;
        }
        .kicker { font: 650 10px/1.2 ui-monospace, monospace; letter-spacing: 0.06em; text-transform: uppercase; color: #ecd046; }
        .sub { margin: 4px 0 10px; font-size: 11px; opacity: 0.6; }
        dl { margin: 0; display: grid; gap: 5px; }
        .row { display: grid; grid-template-columns: 72px 1fr; gap: 8px; }
        dt { margin: 0; color: #9aa8b5; font-weight: 600; font-size: 10px; text-transform: uppercase; letter-spacing: 0.04em; }
        dd { margin: 0; color: #7ec8ff; word-break: break-word; font: 500 11px/1.35 ui-monospace, SFMono-Regular, Menlo, monospace; }
        dd.yes { color: #ecd046; }
        .actions { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
        button {
          appearance: none;
          border: 1px solid #4a5560;
          background: #2a3038;
          color: #f4f1ea;
          border-radius: 6px;
          padding: 5px 8px;
          font: 600 11px/1 system-ui, sans-serif;
          cursor: pointer;
        }
        button:hover { border-color: #ecd046; color: #ecd046; }
        .hint { margin-top: 8px; font-size: 10px; opacity: 0.5; }
      </style>
      <div class="card">
        <div class="kicker">pre-pesticide · live</div>
        <div class="sub">Hover a node. Click to pin. Copy Tailwind or the Paper row.</div>
        <dl>
          <div class="row"><dt>tag</dt><dd data-k="tag">—</dd></div>
          <div class="row"><dt>id</dt><dd data-k="id">—</dd></div>
          <div class="row"><dt>class</dt><dd data-k="classes">—</dd></div>
          <div class="row"><dt>framer</dt><dd data-k="framer">—</dd></div>
          <div class="row"><dt>role</dt><dd data-k="role">—</dd></div>
          <div class="row"><dt>text</dt><dd data-k="text">—</dd></div>
          <div class="row"><dt>img</dt><dd data-k="img">—</dd></div>
          <div class="row"><dt>landmark</dt><dd data-k="landmark">—</dd></div>
          <div class="row"><dt>paper</dt><dd data-k="paper">—</dd></div>
          <div class="row"><dt>tailwind</dt><dd data-k="tailwind">—</dd></div>
        </dl>
        <div class="actions">
          <button type="button" data-act="tw">Copy Tailwind v3</button>
          <button type="button" data-act="paper">Copy Paper row</button>
          <button type="button" data-act="prefix">tw- prefix</button>
          <button type="button" data-act="pin">Pin</button>
        </div>
        <div class="hint">Serializer skips x-paper-* · not the rebuild Outlines overlay</div>
      </div>
    `;
    document.documentElement.appendChild(hud);

    outline = document.createElement("x-paper-prepesticide-outline");
    outline.id = HUD_OUTLINE_ID;
    outline.style.cssText = [
      "position:absolute",
      "z-index:2147483646",
      "pointer-events:none",
      "border-radius:2px",
      "outline:2px solid #00d1ff",
      "outline-offset:1px",
      "background:color-mix(in oklab, #00d1ff 10%, transparent)",
      "opacity:0",
      "top:0",
      "left:0",
    ].join(";");
    document.documentElement.appendChild(outline);

    shadow.querySelector('[data-act="tw"]').addEventListener("click", (e) => {
      e.stopPropagation();
      if (lastRecord) copyText(lastRecord.tailwind || "");
    });
    shadow.querySelector('[data-act="paper"]').addEventListener("click", (e) => {
      e.stopPropagation();
      if (lastRecord) copyText(lastRecord.paperRow || "");
    });
    shadow.querySelector('[data-act="prefix"]').addEventListener("click", (e) => {
      e.stopPropagation();
      twPrefix = twPrefix ? "" : "tw-";
      e.currentTarget.textContent = twPrefix ? "tw- on" : "tw- prefix";
      if (hoverEl) paint(hoverEl);
    });
    shadow.querySelector('[data-act="pin"]').addEventListener("click", (e) => {
      e.stopPropagation();
      pinned = !pinned;
      e.currentTarget.textContent = pinned ? "Pinned" : "Pin";
    });
  }

  function fill(record) {
    lastRecord = record;
    const q = (k) => shadow && shadow.querySelector(`[data-k="${k}"]`);
    const set = (k, v, cls) => {
      const n = q(k);
      if (!n) return;
      n.textContent = v || "—";
      n.classList.toggle("yes", !!cls);
    };
    set("tag", record.tag);
    set("id", record.id);
    set("classes", record.classes.join(" ") || "—");
    set("framer", record.framerName);
    set("role", record.role);
    set("text", record.text);
    set(
      "img",
      record.img
        ? `${record.img.w}×${record.img.h}  ${record.img.alt || "(no alt)"}  ${record.img.src}`
        : "—",
    );
    set("landmark", record.landmark ? record.landmarkKind : "no", record.landmark);
    set("paper", `${record.sectionSlug} · ${record.paperType} · ${record.paintRole}`);
    set("tailwind", record.tailwind);
  }

  function placeOutline(el) {
    if (!outline) return;
    const r = el.getBoundingClientRect();
    outline.style.top = `${r.top + window.scrollY}px`;
    outline.style.left = `${r.left + window.scrollX}px`;
    outline.style.width = `${r.width}px`;
    outline.style.height = `${r.height}px`;
    outline.style.opacity = "1";
  }

  function paint(el) {
    if (isSkip(el)) return;
    hoverEl = el;
    const record = inspect(el);
    fill(record);
    placeOutline(el);
  }

  function onMove(e) {
    if (pinned) return;
    if (raf) return;
    raf = requestAnimationFrame(() => {
      raf = 0;
      const t = e.target;
      if (!t || isSkip(t)) return;
      paint(t);
    });
  }

  function onClick(e) {
    if (isSkip(e.target)) return;
    if (e.target.closest && e.target.closest(HUD_TAG)) return;
    e.preventDefault();
    e.stopPropagation();
    paint(e.target);
    pinned = true;
    const btn = shadow && shadow.querySelector('[data-act="pin"]');
    if (btn) btn.textContent = "Pinned";
  }

  function inventory() {
    const skip = isSkip;
    const tagOf = (el) => String(el.tagName || "").toLowerCase();
    const bbox = (el) => {
      const r = el.getBoundingClientRect();
      return {
        x: Math.round(r.left + window.scrollX),
        y: Math.round(r.top + window.scrollY),
        w: Math.round(r.width),
        h: Math.round(r.height),
      };
    };
    const counts = (root) => {
      const c = { img: 0, a: 0, button: 0, form: 0, h: 0, svg: 0 };
      for (const el of root.querySelectorAll("img, a, button, form, h1, h2, h3, h4, h5, h6, svg")) {
        if (skip(el)) continue;
        const t = tagOf(el);
        if (t === "img") c.img += 1;
        else if (t === "a") c.a += 1;
        else if (t === "button") c.button += 1;
        else if (t === "form") c.form += 1;
        else if (/^h[1-6]$/.test(t)) c.h += 1;
        else if (t === "svg") c.svg += 1;
      }
      return c;
    };

    const detectedNow = typeof window.__xPaperDetectSections === "function" ? window.__xPaperDetectSections() : [];
    const sectionEls = [];
    const seen = new Map();
    const push = (el, hint = {}) => {
      if (!el || skip(el)) return;
      let slug = hint.name || hint.slug;
      if (!slug) {
        const heading = el.querySelector && el.querySelector("h1, h2, h3");
        slug = slugify(
          el.getAttribute("data-framer-name") || el.id || heading?.textContent || tagOf(el),
          "section",
        );
      }
      if (seen.has(slug)) {
        const n = seen.get(slug) + 1;
        seen.set(slug, n);
        slug = `${slug}-${n}`;
      } else seen.set(slug, 1);
      sectionEls.push({ el, slug, selector: hint.selector || "", chrome: !!hint.chrome });
    };
    for (const s of detectedNow) {
      let el = null;
      try {
        el = document.querySelector(s.selector);
      } catch {
        el = null;
      }
      push(el, s);
    }
    if (!sectionEls.length) {
      const cands = [...document.querySelectorAll("header, nav, section, footer, [data-framer-name]")].filter((el) => {
        if (skip(el) || tagOf(el) === "main") return false;
        return true;
      });
      const roots = cands.filter((el) => !cands.some((o) => o !== el && o.contains(el)));
      for (const el of roots) push(el);
    }

    const sectionOf = (el) => {
      let n = el;
      while (n && n.nodeType === 1) {
        const hit = sectionEls.find((s) => s.el === n);
        if (hit) return hit.slug;
        n = n.parentElement;
      }
      for (const s of sectionEls) {
        if (s.el.contains(el)) return s.slug;
      }
      return "page";
    };

    const cssUrls = (value) => {
      if (!value || value === "none") return [];
      const out = [];
      const re = /url\(\s*(['"]?)([^'")]+)\1\s*\)/gi;
      let m;
      while ((m = re.exec(String(value)))) out.push(m[2]);
      return out;
    };
    const bgSrc = (el) => {
      const style = el.getAttribute("style") || "";
      const fromStyle = style.match(/background-image\s*:\s*([^;]+)/i);
      if (fromStyle) {
        const urls = cssUrls(fromStyle[1]);
        if (urls[0]) return urls[0];
      }
      try {
        const urls = cssUrls(getComputedStyle(el).backgroundImage);
        if (urls[0]) return urls[0];
      } catch {
        /* ignore */
      }
      return "";
    };

    const sections = sectionEls.map((s) => ({
      slug: s.slug,
      tag: tagOf(s.el),
      framerName: s.el.getAttribute("data-framer-name") || "",
      bbox: bbox(s.el),
      childCounts: counts(s.el),
      selector: s.selector,
      chrome: s.chrome,
    }));
    const images = [...document.images]
      .filter((el) => !skip(el))
      .map((el) => ({
        src: el.currentSrc || el.src || "",
        alt: el.getAttribute("alt") ?? "",
        w: el.naturalWidth || 0,
        h: el.naturalHeight || 0,
        section: sectionOf(el),
        via: "img",
      }));
    for (const el of document.querySelectorAll("*")) {
      if (skip(el) || tagOf(el) === "img") continue;
      const src = bgSrc(el);
      if (!src) continue;
      const box = bbox(el);
      images.push({
        src,
        alt: el.getAttribute("aria-label") || el.getAttribute("data-framer-name") || "",
        w: box.w,
        h: box.h,
        section: sectionOf(el),
        via: "background",
      });
    }
    const forms = [...document.querySelectorAll("form")]
      .filter((el) => !skip(el))
      .map((el) => ({
        id: el.id || "",
        name: el.getAttribute("name") || "",
        action: el.getAttribute("action") || "",
        method: (el.getAttribute("method") || "get").toLowerCase(),
        fields: el.querySelectorAll("input, textarea, select, button").length,
        section: sectionOf(el),
        bbox: bbox(el),
      }));
    const landmarks = [...document.querySelectorAll("header, nav, main, section, footer, form, img, a, button, h1, h2, h3, [role='banner'], [role='navigation'], [role='main'], [role='contentinfo']")]
      .filter((el) => !skip(el))
      .map((el) => ({
        tag: tagOf(el),
        id: el.id || "",
        framerName: el.getAttribute("data-framer-name") || "",
        role: el.getAttribute("role") || "",
        section: sectionOf(el),
        bbox: bbox(el),
      }));

    const hud = document.querySelector(HUD_TAG) || document.getElementById(HUD_ID);
    return {
      hudTag: hud ? hud.tagName.toLowerCase() : HUD_TAG,
      hudId: hud ? hud.id : HUD_ID,
      sections,
      images,
      forms,
      landmarks,
    };
  }

  window.__xPaperPrePesticide = {
    HUD_TAG,
    HUD_ID,
    inventory,
    init({ prefix = "" } = {}) {
      twPrefix = prefix || "";
      ensure();
      if (!bound) {
        document.addEventListener("pointermove", onMove, true);
        document.addEventListener("click", onClick, true);
        bound = true;
      }
    },
    inspect,
    paint,
    setPrefix(p) {
      twPrefix = p || "";
    },
    hide() {
      if (hud) hud.style.visibility = "hidden";
      if (outline) outline.style.visibility = "hidden";
    },
    // Hide the inspect card only. Pesticide outlines stay on so per-section
    // SOURCE shots still show the live DOM boxes.
    hideCard() {
      if (hud) hud.style.visibility = "hidden";
      if (outline) outline.style.opacity = "0";
    },
    show() {
      if (hud) hud.style.visibility = "visible";
      if (outline) outline.style.visibility = "visible";
    },
    destroy() {
      document.removeEventListener("pointermove", onMove, true);
      document.removeEventListener("click", onClick, true);
      bound = false;
      document.documentElement.removeAttribute("data-x-paper-prepesticide");
      hud?.remove();
      outline?.remove();
      styleEl?.remove();
      hud = shadow = outline = styleEl = hoverEl = lastRecord = null;
      pinned = false;
    },
  };
})();
