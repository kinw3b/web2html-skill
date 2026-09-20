// Capture HUD, injected into the page so the user can watch the capture happen.
//
// EVERY element created here is `x-paper-` prefixed on purpose. The serializer
// skips any element whose tagName or id starts with "x-paper-", so the overlay
// excludes itself from the capture for free. Rename anything and it will start
// appearing inside the imported Paper artboard.
//
// Injected as a source string; defines window.__xPaperOverlay.

(() => {
  if (window.__xPaperOverlay) return;

  const ACCENT = "oklch(0.7 0.15 258)";
  const DONE = "oklch(0.72 0.17 150)";

  let hud = null;
  let shadow = null;
  let outline = null;
  let total = 0;

  function ensure() {
    if (hud) return;

    hud = document.createElement("x-paper-hud");
    hud.style.cssText = [
      "position:fixed",
      "right:24px",
      "top:24px",
      "z-index:2147483647",
      "pointer-events:none",
    ].join(";");
    shadow = hud.attachShadow({ mode: "open" });
    shadow.innerHTML = `
      <style>
        :host { all: initial; }
        .card {
          font: 500 13px/1.4 ui-sans-serif, -apple-system, "SF Pro Text", system-ui, sans-serif;
          color: #fff;
          background: rgba(17,19,24,0.94);
          -webkit-backdrop-filter: blur(12px);
          backdrop-filter: blur(12px);
          border: 1px solid rgba(255,255,255,0.10);
          border-radius: 12px;
          padding: 14px 16px;
          min-width: 270px;
          box-shadow: 0 12px 32px rgba(0,0,0,0.35);
        }
        .row { display: flex; align-items: center; gap: 8px; }
        .dot {
          width: 8px; height: 8px; border-radius: 50%;
          background: ${ACCENT};
          box-shadow: 0 0 0 0 ${ACCENT};
          animation: pulse 1.4s ease-out infinite;
          flex: 0 0 auto;
        }
        .dot.done { background: ${DONE}; animation: none; }
        @keyframes pulse {
          0%   { box-shadow: 0 0 0 0 color-mix(in oklab, ${ACCENT} 70%, transparent); }
          70%  { box-shadow: 0 0 0 7px transparent; }
          100% { box-shadow: 0 0 0 0 transparent; }
        }
        .label { letter-spacing: 0.01em; }
        .count { margin-left: auto; opacity: 0.6; font-variant-numeric: tabular-nums; }
        .name {
          margin-top: 8px;
          font-size: 15px;
          font-weight: 600;
          letter-spacing: -0.01em;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          max-width: 260px;
        }
        .track {
          margin-top: 10px;
          height: 4px;
          border-radius: 999px;
          background: rgba(255,255,255,0.12);
          overflow: hidden;
        }
        .bar {
          height: 100%;
          width: 0%;
          border-radius: 999px;
          background: ${ACCENT};
          transition: width 260ms cubic-bezier(0.4, 0, 0.2, 1);
        }
        .bar.done { background: ${DONE}; }
        .meta {
          margin-top: 7px;
          font-size: 11px;
          opacity: 0.55;
          font-variant-numeric: tabular-nums;
        }
      </style>
      <div class="card">
        <div class="row">
          <span class="dot"></span>
          <span class="label">capturing</span>
          <span class="count">0/0</span>
        </div>
        <div class="name">—</div>
        <div class="track"><div class="bar"></div></div>
        <div class="meta">0 KB</div>
      </div>
    `;
    document.documentElement.appendChild(hud);

    // Separate element so it can be positioned in document space independently.
    outline = document.createElement("x-paper-capture-outline");
    outline.id = "x-paper-capture-outline";
    outline.style.cssText = [
      "position:absolute",
      "z-index:2147483646",
      "pointer-events:none",
      "border-radius:4px",
      `outline:2px solid ${ACCENT}`,
      "outline-offset:2px",
      "background:color-mix(in oklab, " + ACCENT + " 8%, transparent)",
      "transition:opacity 200ms ease",
      "opacity:0",
      "top:0",
      "left:0",
    ].join(";");
    document.documentElement.appendChild(outline);
  }

  const q = (sel) => shadow && shadow.querySelector(sel);

  window.__xPaperOverlay = {
    init(count) {
      ensure();
      total = count;
      const c = q(".count");
      if (c) c.textContent = `0/${count}`;
    },

    section(index, name, bytesSoFar) {
      ensure();
      const c = q(".count");
      const n = q(".name");
      const b = q(".bar");
      const m = q(".meta");
      if (c) c.textContent = `${index}/${total}`;
      if (n) n.textContent = name;
      if (b) b.style.width = `${Math.round((index / Math.max(total, 1)) * 100)}%`;
      if (m) m.textContent = `${(bytesSoFar / 1024).toFixed(0)} KB`;
    },

    // Position the outline over an element, in document coordinates so it
    // stays put while the page scrolls.
    highlight(selector) {
      ensure();
      const el = document.querySelector(selector);
      if (!el || !outline) return;
      const r = el.getBoundingClientRect();
      outline.style.top = `${r.top + window.scrollY}px`;
      outline.style.left = `${r.left + window.scrollX}px`;
      outline.style.width = `${r.width}px`;
      outline.style.height = `${r.height}px`;
      outline.style.opacity = "1";
    },

    clearHighlight() {
      if (outline) outline.style.opacity = "0";
    },

    // Hide HUD + outline for Playwright element screenshots. The serializer
    // already skips x-paper-* nodes, but element screenshots still composite
    // overlapping fixed layers ("capturing N/M") into the JPEG.
    hide() {
      ensure();
      if (hud) hud.style.visibility = "hidden";
      if (outline) outline.style.visibility = "hidden";
    },

    show() {
      ensure();
      if (hud) hud.style.visibility = "visible";
      if (outline) outline.style.visibility = "visible";
    },

    finish(bytes) {
      ensure();
      const d = q(".dot");
      const l = q(".label");
      const b = q(".bar");
      const m = q(".meta");
      if (d) d.classList.add("done");
      if (l) l.textContent = "captured";
      if (b) { b.classList.add("done"); b.style.width = "100%"; }
      if (m) m.textContent = `${(bytes / 1024).toFixed(0)} KB total`;
      this.clearHighlight();
    },

    destroy() {
      hud?.remove();
      outline?.remove();
      hud = shadow = outline = null;
    },
  };
})();
