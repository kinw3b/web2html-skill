(() => {
  // Tags overlays must ride the live element. A page-fixed box that copies
  // getBoundingClientRect once will drift on zoom, visualViewport pan,
  // Framer transform-scroll, and any resize away from the 1600 lander.
  // Scan identity is the serializer pc-id path, never those leftover coords.
  const VOID_TAGS = new Set([
    "AREA", "BASE", "BR", "COL", "EMBED", "HR", "IMG", "INPUT", "LINK",
    "META", "PARAM", "SOURCE", "TRACK", "WBR",
  ]);
  const SEMANTIC_TAGS = new Set([
    "H1", "H2", "H3", "H4", "H5", "H6", "P", "UL", "OL", "IMG", "A", "BUTTON", "FORM",
  ]);
  const DESKTOP_WIDTH = 1600;

  function isToolChrome(node) {
    if (!node) return false;
    const tag = String(node.tagName || "");
    if (/^X-PAPER-/i.test(tag)) return true;
    if (typeof node.hasAttribute === "function" && node.hasAttribute("data-paper-tool")) return true;
    if (typeof node.closest === "function" && node.closest("x-paper-capture-root")) return true;
    return false;
  }

  function computedPosition(element, style) {
    const inline = String(element?.style?.position || "").trim();
    if (inline) return inline;
    if (style) return String(style);
    if (typeof getComputedStyle === "function" && element) {
      try { return getComputedStyle(element).position; } catch { /* jsdom / detached */ }
    }
    return "static";
  }

  function canAttach(element, style) {
    if (!element || VOID_TAGS.has(String(element.tagName || "").toUpperCase())) return false;
    if (isToolChrome(element)) return false;
    return /^(relative|absolute|fixed|sticky)$/i.test(computedPosition(element, style));
  }

  function viewportRect(element, view) {
    const rect = typeof element.getBoundingClientRect === "function"
      ? element.getBoundingClientRect()
      : { left: 0, top: 0, width: 0, height: 0 };
    const vv = view || (typeof visualViewport !== "undefined" ? visualViewport : null);
    return {
      left: Number(rect.left || 0) + (Number(vv?.offsetLeft) || 0),
      top: Number(rect.top || 0) + (Number(vv?.offsetTop) || 0),
      width: Number(rect.width || 0),
      height: Number(rect.height || 0),
    };
  }

  function applyOverlayBox(overlay, rect) {
    if (!overlay?.style || !rect) return overlay;
    overlay.style.left = `${Math.round(rect.left)}px`;
    overlay.style.top = `${Math.round(rect.top)}px`;
    overlay.style.width = `${Math.round(rect.width)}px`;
    overlay.style.height = `${Math.round(rect.height)}px`;
    return overlay;
  }

  function attachOutline(element, outline, fallbackRoot) {
    if (!outline) return "none";
    if (canAttach(element)) {
      outline.dataset.attached = "host";
      outline.style.left = "";
      outline.style.top = "";
      outline.style.width = "";
      outline.style.height = "";
      element.append(outline);
      return "host";
    }
    outline.dataset.attached = "overlay";
    fallbackRoot?.append(outline);
    return "overlay";
  }

  function pcIdFor(sectionId, path) {
    const id = String(sectionId || "01").padStart(2, "0");
    return `pc-${id}-${path}`;
  }

  function walkLayerIds(root, sectionId, opts = {}) {
    const skip = opts.skip || isToolChrome;
    const tags = opts.semanticTags || SEMANTIC_TAGS;
    const out = [];
    if (!root) return out;
    (function visit(el, path) {
      if (!el || skip(el)) return;
      const tagName = String(el.tagName || "");
      if (tags.has(tagName.toUpperCase()) || tags.has(tagName)) {
        out.push({
          pcId: pcIdFor(sectionId, path),
          path,
          sectionId: String(sectionId || "01").padStart(2, "0"),
          tag: tagName.toLowerCase(),
          element: el,
        });
      }
      const children = el.children ? [...el.children] : [];
      children.forEach((child, index) => {
        if (skip(child)) return;
        visit(child, `${path}.${index}`);
      });
    })(root, "0");
    return out;
  }

  globalThis.PaperCaptureTags = {
    VOID_TAGS,
    SEMANTIC_TAGS,
    DESKTOP_WIDTH,
    isToolChrome,
    canAttach,
    viewportRect,
    applyOverlayBox,
    attachOutline,
    pcIdFor,
    walkLayerIds,
  };
})();
