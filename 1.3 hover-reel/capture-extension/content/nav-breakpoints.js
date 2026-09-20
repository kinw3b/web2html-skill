(() => {
  const MIN_SCORE = 6;

  function norm(value) {
    return String(value || "").toLowerCase().replace(/\s+/g, " ").trim();
  }

  function classes(value) {
    if (Array.isArray(value)) return value.filter(Boolean).map(String);
    return String(value || "").split(/\s+/).filter(Boolean);
  }

  function breakpointSpecs() {
    return [
      { name: "tablet", width: 768, height: 1024 },
      { name: "mobile", width: 390, height: 844 },
    ];
  }

  function fingerprintNav(source = {}) {
    const get = (name) => typeof source.getAttribute === "function"
      ? source.getAttribute(name) || ""
      : source[name] || "";
    return {
      tag: norm(source.tagName || source.tag),
      id: String(source.id || get("id")),
      framerName: String(get("data-framer-name") || source.framerName || ""),
      role: String(get("role") || source.role || ""),
      aria: String(get("aria-label") || source.aria || ""),
      classes: classes(typeof source.className === "string" ? source.className : source.classes || get("class")),
      text: norm(source.innerText || source.textContent || source.text).slice(0, 80),
    };
  }

  const STOP_WORDS = new Set([
    "all", "pages", "page", "home", "menu", "about", "pricing", "sign", "in",
    "get", "started", "now", "the", "and", "for", "our",
  ]);

  function compactBand(row = {}) {
    const rect = row.rect || {};
    const viewport = row.viewport || {};
    const vw = Number(viewport.width || 0);
    const vh = Number(viewport.height || 0);
    const width = Number(rect.width || 0);
    const height = Number(rect.height || 0);
    const top = Number(rect.top || 0);
    return vw > 0 && vh > 0
      && top <= Math.min(180, vh * 0.25)
      && width >= vw * 0.45
      && height >= 24
      && height <= Math.min(280, vh * 0.32);
  }

  function brandToken(text) {
    return norm(text).split(" ").find((word) => word.length >= 4 && !STOP_WORDS.has(word)) || "";
  }

  function identityScore(row = {}, fp = {}) {
    let score = 0;
    if (fp.framerName && row.framerName && norm(fp.framerName) === norm(row.framerName)) score += 12;
    if (fp.id && row.id && fp.id === row.id) score += 10;
    if (fp.role && row.role && norm(fp.role) === norm(row.role)) score += 2;
    if (fp.tag && row.tag && norm(fp.tag) === norm(row.tag)) score += 1;
    if (fp.aria && row.aria && norm(fp.aria) === norm(row.aria)) score += 3;
    const wanted = new Set(classes(fp.classes).map(norm).filter((name) => name.length >= 8 || /^framer-[a-z0-9]{5,}$/i.test(name)));
    score += Math.min(4, classes(row.classes).map(norm).filter((name) => wanted.has(name)).length);
    const textNeedle = norm(fp.text).slice(0, 12);
    if (textNeedle && norm(row.text).includes(textNeedle)) score += 2;
    const brand = brandToken(fp.text);
    if (brand && norm(row.text).includes(brand)) score += 6;
    return score;
  }

  function validBand(row = {}, fp = {}) {
    if (!compactBand(row)) return false;
    const vw = Number(row.viewport?.width || 0);
    const navLinks = Number(row.navLinkCount || 0);
    const hasDesktopCore = Boolean(row.hasLogo) && navLinks >= 2
      && (Boolean(row.hasCta) || Boolean(row.hasDropdown) || navLinks >= 3);
    const hasDesktopFallback = navLinks >= 3 && (Boolean(row.hasCta) || Boolean(row.hasDropdown));
    const hasMobileCore = Boolean(row.hasLogo) && Boolean(row.hasMenuButton);
    const narrow = vw > 0 && vw <= 900;
    const namedBreakpoint = /(phone|tablet|mobile)/i.test(String(row.framerName || ""));
    const hasNamedCore = narrow && namedBreakpoint && (Boolean(row.hasLogo) || Boolean(row.hasMenuButton) || Boolean(row.hasCta));
    const hasRematchCore = Boolean(fp && (fp.framerName || fp.id || fp.text || (fp.classes || []).length))
      && narrow
      && (hasMobileCore || identityScore(row, fp) >= 6);
    return hasDesktopCore || hasDesktopFallback || hasMobileCore || hasNamedCore || hasRematchCore;
  }

  function scoreNavCandidate(row = {}, fp = {}) {
    if (!validBand(row, fp)) return -Infinity;
    let score = identityScore(row, fp);
    const identity = `${row.tag || ""} ${row.role || ""} ${row.framerName || ""} ${row.id || ""}`;
    if (/(header|navbar|navigation|menubar|banner|\bnav\b)/i.test(identity)) score += 4;
    if (/(phone|tablet|mobile|burger)/i.test(row.framerName || "")) score += 8;
    if (row.hasLogo) score += 4;
    if (row.hasMenuButton) score += 4;
    if (row.hasCta) score += 3;
    if (row.hasDropdown) score += 2;
    score += Math.min(5, Number(row.navLinkCount || 0));
    score += Math.min(3, Number(row.interactiveCount || 0));
    if (Number(row.rect?.top || 0) <= 120) score += 2;
    score -= Math.min(4, Number(row.rect?.height || 0) / Math.max(1, Number(row.viewport?.height || 1)) * 12);
    return score;
  }

  function pickNavCandidate(rows = [], fp = {}, minimum = MIN_SCORE) {
    let best = null;
    for (const row of rows) {
      const score = scoreNavCandidate(row, fp);
      if (score >= minimum && (!best || score > best.score)) best = { ...row, score };
    }
    return best;
  }

  globalThis.PaperCaptureNavBreakpoints = {
    MIN_SCORE,
    breakpointSpecs,
    fingerprintNav,
    pickNavCandidate,
    scoreNavCandidate,
    validBand,
  };
})();
