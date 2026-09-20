(() => {
  // Paper numbers 01 from the first content band (hero). Compact nav/header
  // chrome is 00. Framer paints later bands as <header> — those stay 01+.
  const api = {
    isCompactChrome(root, opts = {}) {
      if (!root) return false;
      const tag = String(root.tagName || "").toLowerCase();
      const role = String(root.getAttribute?.("role") || "").toLowerCase();
      if (tag === "nav" || role === "navigation" || role === "menubar") return true;
      if (tag !== "header" && role !== "banner") return false;
      const rect = typeof root.getBoundingClientRect === "function"
        ? root.getBoundingClientRect()
        : { height: Number(root.height || 0), top: Number(root.top || 0) };
      const scrollY = Number(opts.scrollY || 0);
      const height = Number(rect.height || root.height || 0);
      const top = Number(rect.top || 0) + scrollY;
      return height > 0 && height <= 96 && top <= 80;
    },

    normalizeCensus(sections = []) {
      return (sections || [])
        .map((section, index) => ({
          id: String(section.id || String(index + 1).padStart(2, "0")).padStart(2, "0"),
          slug: section.slug || section.name || section.label || "",
          top: Number(section.top ?? section.bbox?.y ?? section.y),
          h: Number(section.height ?? section.h ?? section.bbox?.h ?? 0),
        }))
        .filter((section) => Number.isFinite(section.top))
        .sort((a, b) => a.top - b.top);
    },

    matchCensus(pageY, sections = []) {
      const rows = api.normalizeCensus(sections);
      if (!rows.length) return null;
      const y = Number(pageY);
      if (!Number.isFinite(y)) return null;
      const first = rows[0];
      if (y < first.top) return { id: "00", label: "header", source: "paper-chrome" };
      const inside = rows.find((section) => (
        y >= section.top && (section.h <= 0 || y < section.top + section.h)
      ));
      const hit = inside || rows.filter((section) => section.top <= y).pop() || first;
      return { id: hit.id, label: hit.slug || hit.id, source: "paper" };
    },

    contentBands(roots, opts = {}) {
      const list = [...(roots || [])];
      let start = 0;
      while (start < list.length && api.isCompactChrome(list[start], opts)) start += 1;
      return { chrome: list.slice(0, start), bands: list.slice(start) };
    },

    assignFromBands(element, bands, opts = {}) {
      const getTop = opts.getTop || ((node) => {
        const rect = node.getBoundingClientRect?.() || { top: 0 };
        return Number(rect.top) + Number(opts.scrollY || 0);
      });
      if (!bands.length) return { id: "01", label: "page", source: "dom" };
      let index = bands.findIndex((root) => root === element || root.contains?.(element));
      if (index < 0) {
        const top = getTop(element);
        if (top < getTop(bands[0])) return { id: "00", label: "header", source: "dom-chrome" };
        for (let cursor = bands.length - 1; cursor >= 0; cursor -= 1) {
          if (getTop(bands[cursor]) <= top) {
            index = cursor;
            break;
          }
        }
        if (index < 0) index = 0;
      }
      return {
        id: String(index + 1).padStart(2, "0"),
        label: bands[index]?.slug || bands[index]?.label || `section-${index + 1}`,
        source: "dom",
        root: bands[index],
      };
    },
  };
  globalThis.PaperCaptureSections = api;
})();
