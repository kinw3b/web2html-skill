(function () {
  var KEY = "qa-outlines";

  function showPolishChip() {
    try {
      var q = new URLSearchParams(location.search).get("qa-review");
      if (q === "final") return true;
      var raw = (location.hash || "").replace(/^#/, "");
      if (!raw) return false;
      if (raw.indexOf("qa-review=final") === 0) return true;
      return new URLSearchParams(raw).get("qa-review") === "final";
    } catch (e) {
      return false;
    }
  }

  var MODES = ["off", "on", "tags", "mono"];
  var hoverEl = null;
  var labelEl = null;
  var inspectEl = null;
  var pinned = false;
  var raf = 0;
  var POS_KEY = "qa-inspector-pos";
  var dragging = false;
  var dragOffX = 0;
  var dragOffY = 0;
  var collapsed = false;
  var TAG_SEL = "h1,h2,h3,h4,h5,h6,a,p,button,aside,article,main,section,header,footer,nav";
  var tagLayer = null;
  var tagRaf = 0;
  var walkStack = [];
  var copyTimer = 0;

  function forcedMode() {
    try {
      var q = new URLSearchParams(location.search).get("qa-outlines");
      if (q && MODES.indexOf(q) !== -1) return q;
      var raw = (location.hash || "").replace(/^#/, "");
      if (!raw) return null;
      if (raw.indexOf("qa-outlines=") === 0) {
        var h = raw.slice("qa-outlines=".length).split("&")[0];
        if (h && MODES.indexOf(h) !== -1) return h;
      }
      var fromHash = new URLSearchParams(raw).get("qa-outlines");
      if (fromHash && MODES.indexOf(fromHash) !== -1) return fromHash;
    } catch (e) {}
    return null;
  }

  function bootMode() {
    var forced = forcedMode();
    if (forced) {
      try { localStorage.setItem(KEY, forced); } catch (e) {}
      return forced;
    }
    return null;
  }

  function mode() {
    var boot = bootMode();
    if (boot) return boot;
    try {
      return localStorage.getItem(KEY) || "tags";
    } catch (e) {
      return "tags";
    }
  }

  function isMobile() {
    return window.matchMedia("(max-width: 767px)").matches;
  }

  function skipClass(c) {
    return !c || c.indexOf("qa-") === 0;
  }

  function classListOf(el) {
    if (!el.classList || !el.classList.length) return [];
    var out = [];
    for (var i = 0; i < el.classList.length; i++) {
      if (!skipClass(el.classList[i])) out.push(el.classList[i]);
    }
    return out;
  }

  function ident(el) {
    if (!el || el.nodeType !== 1) return "";
    var tag = el.tagName.toLowerCase();
    var out = tag;
    if (el.id) out += "#" + el.id;
    var cls = classListOf(el);
    if (cls.length) out += "." + cls.slice(0, 4).join(".");
    var attrs = [
      "data-component",
      "data-paper-section",
      "data-paper-node",
      "data-prop",
      "data-action",
      "data-nav-toggle",
      "data-faq-row",
    ];
    for (var a = 0; a < attrs.length; a++) {
      var v = el.getAttribute(attrs[a]);
      if (v) out += "[" + attrs[a] + '="' + v + '"]';
    }
    return out;
  }

  function cssPath(el) {
    if (!el || el === document.documentElement) return "html";
    if (el.id) return "#" + el.id;
    var bits = [];
    var n = el;
    var depth = 0;
    while (n && n.nodeType === 1 && n !== document.documentElement && depth < 5) {
      var piece = n.tagName.toLowerCase();
      if (n.id) {
        bits.unshift("#" + n.id);
        break;
      }
      var cls = classListOf(n);
      if (cls.length) piece += "." + cls[0];
      else if (n.getAttribute("data-component")) {
        piece += '[data-component="' + n.getAttribute("data-component") + '"]';
      } else if (n.getAttribute("data-paper-section")) {
        piece += '[data-paper-section="' + n.getAttribute("data-paper-section") + '"]';
      }
      bits.unshift(piece);
      n = n.parentElement;
      depth++;
    }
    return bits.join(" > ");
  }

  function domPath(el) {
    var bits = [];
    var n = el;
    while (n && n.nodeType === 1) {
      var piece = n.tagName.toLowerCase();
      if (n.id) piece += "#" + n.id;
      var cls = classListOf(n);
      if (cls.length) piece += "." + cls.join(".");
      bits.unshift(piece);
      n = n.parentElement;
    }
    return bits.join(" → ");
  }

  function isQaChrome(el) {
    return !!(el && el.closest && el.closest("[data-qa-chrome]"));
  }

  function isWalkable(el) {
    if (!el || el.nodeType !== 1) return false;
    var tag = el.tagName;
    if (tag === "HTML" || tag === "BODY") return false;
    if (isQaChrome(el)) return false;
    return true;
  }

  function pickHtml(el) {
    var clone = el.cloneNode(true);
    var kill = clone.querySelectorAll(
      "[data-qa-chrome], .qa-overlay, .qa-inspector, .qa-overlay-label, .qa-tag-layer, script"
    );
    for (var i = 0; i < kill.length; i++) {
      if (kill[i].parentNode) kill[i].parentNode.removeChild(kill[i]);
    }
    if (clone.hasAttribute && clone.hasAttribute("data-qa-hover")) {
      clone.removeAttribute("data-qa-hover");
    }
    var html = clone.outerHTML || "";
    if (html.length > 1200) html = html.slice(0, 1200) + "…";
    return html;
  }

  function copyPromptText(el) {
    var parts = (location.pathname || "").split("/");
    var file = parts[parts.length - 1] || "index.html";
    var cls = classListOf(el);
    var line = el.getAttribute("data-src-line") || "—";
    return [
      "QA overlay pick",
      "file: " + file,
      "selector: " + cssPath(el),
      "dom: " + domPath(el),
      "tag: " + ident(el),
      "id: " + (el.id || "—"),
      "classes: " + (cls.length ? cls.join(" ") : "—"),
      "line: " + line,
      "html:",
      pickHtml(el),
    ].join("\n");
  }

  function markCopied(btn) {
    if (!btn) return;
    btn.classList.add("is-copied");
    var isIcon = btn.classList.contains("qa-inspector-copyicon");
    var prev = btn.getAttribute("data-qa-copy-label") || (isIcon ? "" : btn.textContent);
    if (!isIcon) {
      btn.setAttribute("data-qa-copy-label", prev === "Copied" ? "Copy" : prev);
      btn.textContent = "Copied";
    }
    if (copyTimer) clearTimeout(copyTimer);
    copyTimer = setTimeout(function () {
      btn.classList.remove("is-copied");
      if (!isIcon) btn.textContent = btn.getAttribute("data-qa-copy-label") || "Copy";
      copyTimer = 0;
    }, 1000);
  }

  function inlineClone(src, dst) {
    var cs = window.getComputedStyle(src);
    var props = [
      "display","position","top","left","right","bottom","width","height","min-width","min-height",
      "max-width","max-height","box-sizing","margin","padding","border","border-radius","background",
      "background-color","background-image","background-size","background-position","color","font",
      "font-size","font-family","font-weight","font-style","line-height","letter-spacing","text-align",
      "text-transform","white-space","overflow","object-fit","object-position","align-items",
      "justify-content","flex-direction","flex-wrap","gap","grid-template-columns","opacity",
      "box-shadow","transform","z-index"
    ];
    for (var i = 0; i < props.length; i++) {
      dst.style.setProperty(props[i], cs.getPropertyValue(props[i]));
    }
    dst.style.margin = "0";
    dst.style.position = "static";
    dst.style.inset = "auto";
    dst.style.transform = "none";
    var sc = src.children;
    var dc = dst.children;
    for (var j = 0; j < sc.length && j < dc.length; j++) inlineClone(sc[j], dc[j]);
  }

  function rasterizeEl(el, done) {
    var r = el.getBoundingClientRect();
    var w = Math.max(1, Math.round(r.width));
    var h = Math.max(1, Math.round(r.height));
    if (window.html2canvas) {
      window.html2canvas(el, {
        backgroundColor: null,
        scale: 2,
        useCORS: true,
        logging: false,
        ignoreElements: function (n) {
          return !!(n && n.getAttribute && n.getAttribute("data-qa-chrome"));
        },
      }).then(function (canvas) {
        canvas.toBlob(function (blob) { done(blob); }, "image/png");
      }).catch(function () { done(null); });
      return;
    }
    try {
      var clone = el.cloneNode(true);
      if (clone.removeAttribute) clone.removeAttribute("data-qa-hover");
      inlineClone(el, clone);
      clone.style.width = w + "px";
      clone.style.height = h + "px";
      var wrap = document.createElement("div");
      wrap.setAttribute("xmlns", "http://www.w3.org/1999/xhtml");
      wrap.style.width = w + "px";
      wrap.style.height = h + "px";
      wrap.style.background = window.getComputedStyle(el).backgroundColor || "#fff";
      wrap.appendChild(clone);
      var xml = new XMLSerializer().serializeToString(wrap);
      var svg =
        '<svg xmlns="http://www.w3.org/2000/svg" width="' + w + '" height="' + h + '">' +
        '<foreignObject width="100%" height="100%">' + xml + "</foreignObject></svg>";
      var url = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml;charset=utf-8" }));
      var img = new Image();
      img.onload = function () {
        var c = document.createElement("canvas");
        c.width = w * 2;
        c.height = h * 2;
        var ctx = c.getContext("2d");
        ctx.scale(2, 2);
        ctx.drawImage(img, 0, 0);
        URL.revokeObjectURL(url);
        c.toBlob(function (blob) { done(blob); }, "image/png");
      };
      img.onerror = function () {
        URL.revokeObjectURL(url);
        done(null);
      };
      img.src = url;
    } catch (e) {
      done(null);
    }
  }

  function screenshotPick(el, btn) {
    if (!el || el.nodeType !== 1) return;
    var hover = el.getAttribute("data-qa-hover");
    if (hover) el.removeAttribute("data-qa-hover");
    rasterizeEl(el, function (blob) {
      if (hover) el.setAttribute("data-qa-hover", hover);
      if (!blob) {
        if (btn) {
          var prev = btn.textContent;
          btn.textContent = "Failed";
          setTimeout(function () { btn.textContent = prev; }, 1200);
        }
        return;
      }
      function finish(ok) {
        if (btn) {
          var prev = btn.textContent;
          btn.textContent = ok ? "Copied" : "Saved";
          setTimeout(function () { btn.textContent = prev; }, 1200);
        }
      }
      if (navigator.clipboard && window.ClipboardItem) {
        navigator.clipboard.write([new ClipboardItem({ "image/png": blob })]).then(
          function () { finish(true); },
          function () {
            downloadBlob(blob, el);
            finish(false);
          }
        );
      } else {
        downloadBlob(blob, el);
        finish(false);
      }
    });
  }

  function downloadBlob(blob, el) {
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = (el.id || el.tagName.toLowerCase() || "element") + ".png";
    a.setAttribute("data-qa-chrome", "true");
    document.body.appendChild(a);
    a.click();
    setTimeout(function () {
      URL.revokeObjectURL(a.href);
      a.remove();
    }, 500);
  }

  function writeClipboard(text, done) {
    function fallback() {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("data-qa-chrome", "true");
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      var ok = false;
      try {
        ok = document.execCommand("copy");
      } catch (e) {}
      document.body.removeChild(ta);
      done(ok);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(
        function () {
          done(true);
        },
        fallback
      );
    } else fallback();
  }

  function copyPick(el, btn) {
    if (!el || el.nodeType !== 1) return;
    writeClipboard(copyPromptText(el), function (ok) {
      if (ok) markCopied(btn);
    });
  }

  function ensureLabel() {
    if (labelEl) return labelEl;
    labelEl = document.createElement("div");
    labelEl.className = "qa-overlay-label";
    labelEl.setAttribute("data-qa-chrome", "true");
    labelEl.setAttribute("hidden", "");
    document.body.appendChild(labelEl);
    return labelEl;
  }

  function loadPos() {
    try {
      var raw = localStorage.getItem(POS_KEY);
      if (!raw) return null;
      var o = JSON.parse(raw);
      return o && typeof o === "object" ? o : null;
    } catch (e) {
      return null;
    }
  }

  function savePos() {
    if (!inspectEl) return;
    try {
      var r = inspectEl.getBoundingClientRect();
      localStorage.setItem(
        POS_KEY,
        JSON.stringify({
          left: Math.round(r.left),
          top: Math.round(r.top),
          collapsed: collapsed,
        })
      );
    } catch (e) {}
  }

  function clampPos(left, top) {
    var w = inspectEl.offsetWidth || 280;
    var h = inspectEl.offsetHeight || 48;
    var pad = 8;
    left = Math.min(Math.max(pad, left), Math.max(pad, window.innerWidth - w - pad));
    top = Math.min(Math.max(pad, top), Math.max(pad, window.innerHeight - h - pad));
    return { left: left, top: top };
  }

  function applyPos(left, top) {
    var p = clampPos(left, top);
    inspectEl.style.left = p.left + "px";
    inspectEl.style.top = p.top + "px";
    inspectEl.style.right = "auto";
    inspectEl.classList.add("is-moved");
  }

  function setCollapsed(next) {
    collapsed = !!next;
    if (inspectEl) {
      inspectEl.classList.toggle("is-collapsed", collapsed);
      var btn = inspectEl.querySelector(".qa-inspector-collapse");
      if (btn) {
        btn.setAttribute("aria-expanded", collapsed ? "false" : "true");
        btn.textContent = collapsed ? "Expand" : "Collapse";
      }
    }
    savePos();
  }

  function bindInspectorChrome(box) {
    var bar = box.querySelector(".qa-inspector-bar");
    box.querySelector(".qa-inspector-pin").addEventListener("click", function (e) {
      e.stopPropagation();
      setPinned(!pinned);
    });
    box.querySelector(".qa-inspector-collapse").addEventListener("click", function (e) {
      e.stopPropagation();
      setCollapsed(!collapsed);
    });
    box.querySelector(".qa-inspector-parent").addEventListener("click", function (e) {
      e.stopPropagation();
      walkParent();
    });
    box.querySelector(".qa-inspector-child").addEventListener("click", function (e) {
      e.stopPropagation();
      walkChild();
    });
    var copyBtn = box.querySelector(".qa-inspector-copyicon");
    if (copyBtn) {
      copyBtn.addEventListener("click", function (e) {
        e.stopPropagation();
        copyPick(hoverEl, e.currentTarget);
      });
    }
    var shotBtn = box.querySelector(".qa-inspector-shot");
    if (shotBtn) {
      shotBtn.addEventListener("click", function (e) {
        e.stopPropagation();
        screenshotPick(hoverEl, e.currentTarget);
      });
    }
    bar.addEventListener("pointerdown", function (e) {
      if (e.button !== 0) return;
      if (e.target.closest && e.target.closest("button")) return;
      var r = box.getBoundingClientRect();
      dragging = true;
      dragOffX = e.clientX - r.left;
      dragOffY = e.clientY - r.top;
      box.classList.add("is-dragging");
      try {
        bar.setPointerCapture(e.pointerId);
      } catch (err) {}
      e.preventDefault();
    });
    bar.addEventListener("pointermove", function (e) {
      if (!dragging) return;
      applyPos(e.clientX - dragOffX, e.clientY - dragOffY);
    });
    function endDrag() {
      if (!dragging) return;
      dragging = false;
      box.classList.remove("is-dragging");
      savePos();
    }
    bar.addEventListener("pointerup", endDrag);
    bar.addEventListener("pointercancel", endDrag);
    window.addEventListener("resize", function () {
      if (!box.hasAttribute("hidden") && box.classList.contains("is-moved")) {
        var r = box.getBoundingClientRect();
        applyPos(r.left, r.top);
      }
    });
    var saved = loadPos();
    if (saved) {
      if (typeof saved.left === "number" && typeof saved.top === "number") applyPos(saved.left, saved.top);
      if (saved.collapsed) setCollapsed(true);
    }
  }

  function ensureInspector() {
    if (inspectEl) return inspectEl;
    inspectEl = document.createElement("aside");
    inspectEl.className = "qa-inspector";
    inspectEl.setAttribute("data-qa-chrome", "true");
    inspectEl.setAttribute("hidden", "");
    inspectEl.innerHTML =
      '<div class="qa-inspector-bar">' +
      '<span class="qa-inspector-tip">drag to move · ↑ ↓ parent/child</span>' +
      '<button type="button" class="qa-inspector-collapse" aria-expanded="true">Collapse</button>' +
      '<button type="button" class="qa-inspector-pin" aria-pressed="false" aria-label="Pin">Pin</button>' +
      "</div>" +
      '<div class="qa-inspector-actions">' +
      '<button type="button" class="qa-inspector-parent" aria-label="Parent" title="Parent (↑)">↑</button>' +
      '<button type="button" class="qa-inspector-child" aria-label="Child" title="Child (↓)">↓</button>' +
      '<button type="button" class="qa-inspector-shot" title="Screenshot selected element">Screenshot</button>' +
      '<button type="button" class="qa-inspector-copyicon" title="Copy selector for chat" aria-label="Copy selector">' +
      '<svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true"><rect x="5" y="5" width="9" height="9" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.4"/><rect x="2" y="2" width="9" height="9" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.4"/></svg>' +
      "</button>" +
      "</div>" +
      "<dl>" +
      '<div><dt>node</dt><dd data-k="node">—</dd></div>' +
      '<div><dt>id</dt><dd data-k="id">—</dd></div>' +
      '<div><dt>classes</dt><dd data-k="classes">—</dd></div>' +
      '<div><dt>DOM</dt><dd data-k="dom">—</dd></div>' +
      "</dl>";
    document.body.appendChild(inspectEl);
    bindInspectorChrome(inspectEl);
    return inspectEl;
  }

  function setPinned(next) {
    pinned = !!next;
    var pin = inspectEl && inspectEl.querySelector(".qa-inspector-pin");
    if (pin) {
      pin.setAttribute("aria-pressed", pinned ? "true" : "false");
      pin.textContent = pinned ? "Pinned" : "Pin";
    }
    if (inspectEl) inspectEl.classList.toggle("is-pinned", pinned);
  }

  function fillInspector(el) {
    var box = ensureInspector();
    box.querySelector('[data-k="node"]').textContent = el.tagName.toLowerCase();
    box.querySelector('[data-k="id"]').textContent = el.id || "—";
    var cls = classListOf(el);
    box.querySelector('[data-k="classes"]').textContent = cls.length ? cls.join(" ") : "—";
    box.querySelector('[data-k="dom"]').textContent = domPath(el);
    box.removeAttribute("hidden");
    var tip = box.querySelector(".qa-inspector-tip");
    if (tip) {
      tip.textContent = collapsed
        ? el.tagName.toLowerCase() + (el.id ? "#" + el.id : "")
        : "drag to move · ↑ ↓ parent/child";
    }
  }

  function hideInspector() {
    if (inspectEl) inspectEl.setAttribute("hidden", "");
    setPinned(false);
  }

  function clearHover() {
    if (hoverEl) hoverEl.removeAttribute("data-qa-hover");
    hoverEl = null;
    walkStack = [];
    if (labelEl) {
      labelEl.setAttribute("hidden", "");
      labelEl.textContent = "";
    }
    hideInspector();
  }

  function selectNode(t) {
    if (!t || t.nodeType !== 1) return;
    if (isQaChrome(t)) return;
    if (hoverEl && hoverEl !== t) hoverEl.removeAttribute("data-qa-hover");
    hoverEl = t;
    t.setAttribute("data-qa-hover", "true");
    placeLabel(t);
  }

  function walkParent() {
    if (mode() === "off" || !hoverEl) return;
    var p = hoverEl.parentElement;
    while (p && !isWalkable(p)) {
      if (!p.parentElement || p.tagName === "HTML") return;
      p = p.parentElement;
    }
    if (!p || !isWalkable(p)) return;
    walkStack.push(hoverEl);
    selectNode(p);
  }

  function walkChild() {
    if (mode() === "off" || !hoverEl || !walkStack.length) return;
    var child = walkStack.pop();
    if (child && hoverEl.contains(child)) selectNode(child);
  }

  function placeLabel(el, rebuild) {
    fillInspector(el);
    if (isMobile()) {
      if (labelEl) labelEl.setAttribute("hidden", "");
      return;
    }
    var lab = ensureLabel();
    if (rebuild !== false) {
      var name = ident(el);
      var path = cssPath(el);
      lab.innerHTML = "";
      var a = document.createElement("b");
      a.textContent = name;
      lab.appendChild(a);
      if (path && path !== name) {
        var s = document.createElement("span");
        s.textContent = path;
        lab.appendChild(s);
      }
      var copyBtn = document.createElement("button");
      copyBtn.type = "button";
      copyBtn.className = "qa-overlay-copy";
      copyBtn.textContent = "Copy";
      copyBtn.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        copyPick(el, copyBtn);
      });
      lab.appendChild(copyBtn);
    }
    lab.removeAttribute("hidden");
    var r = el.getBoundingClientRect();
    var pad = 6;
    var lw = lab.offsetWidth;
    var lh = lab.offsetHeight;
    var top = r.top - lh - 4;
    if (top < pad) top = r.bottom + 4;
    if (top + lh > window.innerHeight - pad) top = Math.max(pad, r.top + 4);
    var left = r.left;
    if (left + lw > window.innerWidth - pad) left = window.innerWidth - lw - pad;
    if (left < pad) left = pad;
    lab.style.top = Math.round(top) + "px";
    lab.style.left = Math.round(left) + "px";
  }

  function inspectTarget(t) {
    if (mode() === "off") return;
    if (!t || t.nodeType !== 1) return;
    if (isQaChrome(t)) return;
    if (pinned) return;
    if (t === hoverEl) {
      placeLabel(t, false);
      return;
    }
    walkStack = [];
    selectNode(t);
  }

  function ensureTagLayer() {
    if (tagLayer) return tagLayer;
    tagLayer = document.createElement("div");
    tagLayer.className = "qa-tag-layer";
    tagLayer.setAttribute("data-qa-chrome", "true");
    document.body.appendChild(tagLayer);
    return tagLayer;
  }

  function clearTagLabels() {
    if (tagLayer) tagLayer.innerHTML = "";
  }

  function syncTagLabels() {
    if (mode() !== "tags") {
      clearTagLabels();
      return;
    }
    var layer = ensureTagLayer();
    var nodes = document.querySelectorAll(TAG_SEL);
    var html = "";
    var vw = window.innerWidth;
    var vh = window.innerHeight;
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      if (el.closest && el.closest("[data-qa-chrome]")) continue;
      var cs = window.getComputedStyle(el);
      if (cs.display === "contents" || cs.display === "none" || cs.visibility === "hidden") continue;
      var r = el.getBoundingClientRect();
      if (r.width < 4 || r.height < 4) continue;
      if (r.bottom < 0 || r.right < 0 || r.top > vh || r.left > vw) continue;
      var tag = el.tagName.toLowerCase();
      var top = Math.max(2, Math.round(r.top) + 2);
      var left = Math.round(r.right) - 2;
      html +=
        '<span class="qa-tag-chip" data-tag="' +
        tag +
        '" style="top:' +
        top +
        "px;left:" +
        left +
        'px">' +
        tag +
        "</span>";
    }
    layer.innerHTML = html;
  }

  function scheduleTagLabels() {
    if (tagRaf) return;
    tagRaf = requestAnimationFrame(function () {
      tagRaf = 0;
      syncTagLabels();
    });
  }

  function apply(next) {
    var html = document.documentElement;
    if (next === "off") {
      html.removeAttribute("data-qa-outlines");
      clearHover();
      clearTagLabels();
    } else html.setAttribute("data-qa-outlines", next);
    try {
      localStorage.setItem(KEY, next);
    } catch (e) {}
    var btn = document.getElementById("qa-outline-toggle");
    if (btn) {
      btn.setAttribute("aria-pressed", next === "off" ? "false" : "true");
      var labels = { off: "Outlines", on: "Outlines · on", tags: "Outlines · tags", mono: "Outlines · mono" };
      btn.textContent = labels[next] || "Outlines";
    }
    scheduleTagLabels();
  }

  function cycle() {
    var i = MODES.indexOf(mode());
    apply(MODES[(i + 1) % MODES.length]);
  }

  function mount() {
    if (document.getElementById("qa-outline-toggle")) {
      apply(mode());
      return;
    }
    var wrap = document.createElement("div");
    wrap.className = "qa-overlay";
    wrap.setAttribute("data-qa-chrome", "true");
    var btn = document.createElement("button");
    btn.id = "qa-outline-toggle";
    btn.type = "button";
    var isMac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent || "");
    btn.title = isMac
      ? "Cycle outlines: off / all / tags / mono (Option+O). Tags = headings, a, p, button, aside, article, main, section, header, footer, nav. ↑ ↓ parent/child."
      : "Cycle outlines: off / all / tags / mono (Alt+O). Tags = headings, a, p, button, aside, article, main, section, header, footer, nav. ↑ ↓ parent/child.";
    btn.addEventListener("click", cycle);
    var kbd = document.createElement("kbd");
    kbd.textContent = isMac ? "⌥O" : "Alt+O";
    wrap.appendChild(btn);
    wrap.appendChild(kbd);
    if (showPolishChip()) {
      document.documentElement.setAttribute("data-qa-review", "final");
      var polish = document.createElement("a");
      polish.id = "qa-polish-report";
      polish.className = "qa-polish";
      polish.href = "polish-report.html";
      polish.textContent = "Polish 3.1–3.3";
      polish.title = "C/3.1 impeccable · 3.2 design-taste · 3.3 emil report";
      wrap.appendChild(polish);
    }
    document.body.appendChild(wrap);
    ensureInspector();
    apply(mode());
    window.addEventListener("scroll", scheduleTagLabels, true);
    window.addEventListener("resize", scheduleTagLabels);
  }

  document.addEventListener(
    "pointermove",
    function (e) {
      if (raf) return;
      raf = requestAnimationFrame(function () {
        raf = 0;
        inspectTarget(e.target);
      });
    },
    true
  );

  document.addEventListener(
    "click",
    function (e) {
      if (mode() === "off") return;
      if (e.target.closest && e.target.closest("[data-qa-chrome]")) return;
      inspectTarget(e.target);
      setPinned(!pinned);
    },
    true
  );

  function isTyping(e) {
    var t = e.target;
    if (!t) return false;
    var tag = (t.tagName || "").toLowerCase();
    if (tag === "input" || tag === "textarea" || tag === "select") return true;
    if (t.isContentEditable) return true;
    return false;
  }

  document.addEventListener(
    "keydown",
    function (e) {
      var letterO = e.code === "KeyO" || e.key === "o" || e.key === "O" || e.key === "ø" || e.key === "Ø";
      if (e.altKey && letterO && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        cycle();
        return;
      }
      if (mode() === "off" || isTyping(e) || e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === "ArrowUp" || e.key === "[" || e.code === "BracketLeft") {
        e.preventDefault();
        walkParent();
      } else if (e.key === "ArrowDown" || e.key === "]" || e.code === "BracketRight") {
        e.preventDefault();
        walkChild();
      }
    },
    true
  );

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();
