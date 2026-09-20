// Wait until fonts, animations, and entrance opacity have settled, then
// snap leftover Framer appear tweens to rest paint.
//
// Serializer used to keep in-flow `opacity: 0` + `translate(0px, 28px)`
// nodes (not absolute / only-child), so Paper imported them at 0% blending.
// Source-section shots only waited 80ms after scrollIntoView, so FAQ/footer
// clips landed mid-fade. Call after load AND immediately before each
// section serialize/screenshot — IntersectionObserver can retrigger.
//
// All waits are bounded.

const timeout = (ms) => new Promise((r) => setTimeout(r, ms));

/** In-flow appear leftover (Framer/GSAP). Overlays stay hidden. */
export function isEntrancePaint(style = {}) {
  const display = String(style.display || "");
  const visibility = String(style.visibility || "");
  if (display === "none" || visibility === "hidden") return false;
  const position = String(style.position || "");
  if (position === "absolute" || position === "fixed") return false;
  const op = parseFloat(style.opacity);
  if (!Number.isFinite(op) || op >= 0.99) return false;
  if (op < 0.05) return true;
  const transform = String(style.transform || style.translate || "");
  return /translate(?:3d|X|Y|Z)?\(/i.test(transform) || /matrix\(/.test(transform);
}

/** Serializer catch: write rest paint instead of Paper 0% blending. */
export function restEntranceStyles(r) {
  if (!r || typeof r !== "object") return r;
  if (!isEntrancePaint(r)) return r;
  const out = { ...r, opacity: "1" };
  if (out.transform && out.transform !== "none") out.transform = "none";
  if (out.translate && out.translate !== "none") out.translate = "none";
  if (out.filter && /blur\(/i.test(out.filter)) out.filter = "none";
  return out;
}

/** Browser-side. Self-contained for Playwright `page.evaluate`. */
export function applyRestPaint(sel = "body") {
  const root = (typeof sel === "string" ? document.querySelector(sel) : sel) || document.body;
  if (!root) return { forced: 0 };

  const isEntrancePaint = (style) => {
    const display = String(style.display || "");
    const visibility = String(style.visibility || "");
    if (display === "none" || visibility === "hidden") return false;
    const position = String(style.position || "");
    if (position === "absolute" || position === "fixed") return false;
    const op = parseFloat(style.opacity);
    if (!Number.isFinite(op) || op >= 0.99) return false;
    if (op < 0.05) return true;
    const transform = String(style.transform || style.translate || "");
    return /translate(?:3d|X|Y|Z)?\(/i.test(transform) || /matrix\(/.test(transform);
  };

  const hiddenUi = (el) => {
    if (el.hidden || el.getAttribute("hidden") != null) return true;
    if (el.getAttribute("aria-hidden") === "true") return true;
    if (el.closest("[aria-hidden='true']")) return true;
    if (el.closest("dialog:not([open])")) return true;
    if (el.closest("details:not([open])") && !el.closest("summary")) return true;
    return false;
  };

  try {
    const anims = typeof root.getAnimations === "function"
      ? root.getAnimations({ subtree: true })
      : [];
    for (const anim of anims) {
      try { anim.finish(); } catch { /* infinite / already finished */ }
    }
  } catch { /* no WAAPI */ }

  let forced = 0;
  const nodes = [root, ...root.querySelectorAll("*")];
  for (const el of nodes) {
    if (!(el instanceof Element) || hiddenUi(el)) continue;
    const s = getComputedStyle(el);
    if (!isEntrancePaint({
      opacity: s.opacity,
      transform: s.transform,
      translate: s.translate,
      position: s.position,
      display: s.display,
      visibility: s.visibility,
    })) continue;
    el.style.setProperty("transition", "none", "important");
    el.style.setProperty("animation", "none", "important");
    el.style.setProperty("opacity", "1", "important");
    el.style.setProperty("transform", "none", "important");
    el.style.setProperty("translate", "none", "important");
    if (/blur\(/i.test(s.filter || "")) el.style.setProperty("filter", "none", "important");
    forced += 1;
  }
  return { forced };
}

export async function settlePainted(page, selector = "body", { extraMs = 80 } = {}) {
  await page.evaluate(async (sel) => {
    const wait = (ms) => new Promise((r) => setTimeout(r, ms));
    const root = document.querySelector(sel) || document.body;
    await Promise.race([document.fonts?.ready ?? Promise.resolve(), wait(5_000)]);

    const anims = typeof root.getAnimations === "function"
      ? root.getAnimations({ subtree: true })
      : [];
    if (anims.length) {
      await Promise.race([
        Promise.all(anims.map((a) => a.finished.catch(() => {}))),
        wait(4_000),
      ]);
    }

    const start = Date.now();
    while (Date.now() - start < 2_000) {
      let leftover = false;
      for (const el of root.querySelectorAll("*")) {
        const s = getComputedStyle(el);
        if (s.display === "none" || s.visibility === "hidden") continue;
        if (s.position === "absolute" || s.position === "fixed") continue;
        const op = parseFloat(s.opacity);
        if (Number.isFinite(op) && op < 0.05) {
          leftover = true;
          break;
        }
      }
      if (!leftover) break;
      await wait(100);
    }
  }, selector);

  await page.evaluate(applyRestPaint, selector);
  if (extraMs) await timeout(extraMs);
}

export async function settlePageLoad(page) {
  await page.evaluate(async () => {
    const wait = (ms) => new Promise((r) => setTimeout(r, ms));
    await Promise.race([document.fonts?.ready ?? Promise.resolve(), wait(5_000)]);
    const pending = Array.from(document.images).filter((i) => !i.complete);
    await Promise.race([
      Promise.all(pending.map((i) => new Promise((r) => { i.onload = i.onerror = r; }))),
      wait(8_000),
    ]);
  });
  await settlePainted(page, "body", { extraMs: 120 });
}
