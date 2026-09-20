// Live page → content sections only (hero = 01). Used by Capture Tool.

import { reviewSequenceSections } from "./review-sequence.mjs";
import { paperSectionName } from "./section-ids.mjs";
import { settlePageLoad, settlePainted } from "./settle-page.mjs";

export function unwrapSerializer(result) {
  if (!result) return { status: "error", html: "", ids: [], error: "empty" };
  if (typeof result === "string") return { status: "success", html: result, ids: [] };
  const html = result.html || "";
  const status = result.status || (html ? "success" : "error");
  return {
    status,
    html,
    ids: Array.isArray(result.ids) ? result.ids : [],
    error: result.error || (html ? "" : "empty capture"),
  };
}

export function contentWalkFromDetect(raw = []) {
  const rows = reviewSequenceSections((raw || []).map((s, i) => ({
    id: s.id || String(i + 1).padStart(2, "0"),
    slug: s.name || s.slug || `section-${i + 1}`,
    name: s.name || s.slug,
    selector: s.selector || "",
    top: s.top ?? 0,
    height: s.h ?? s.height ?? 0,
    h: s.h ?? s.height ?? 0,
    chrome: Boolean(s.chrome),
    w: s.w,
  })));
  return rows.map((s) => ({
    ...s,
    paperName: s.paperName || paperSectionName(s, { desktop: true }),
  }));
}

export async function serializeSelector(page, serializerSrc, selector, opts = {}) {
  await settlePainted(page, selector);
  const expr = `(async () => {
    ${serializerSrc}
    return await fe(${JSON.stringify(selector)}, ${JSON.stringify(opts)});
  })()`;
  try {
    return unwrapSerializer(await page.evaluate(expr));
  } catch (error) {
    return { status: "error", html: "", ids: [], error: String(error.message || error).split("\n")[0] };
  }
}

export async function settleLivePage(page) {
  await page.evaluate(async () => {
    const step = window.innerHeight * 0.8;
    const max = Math.min(document.body.scrollHeight || 0, 20_000);
    for (let y = 0; y < max; y += step) {
      window.scrollTo(0, y);
      await new Promise((r) => setTimeout(r, 150));
    }
    window.scrollTo(0, 0);
    await new Promise((r) => setTimeout(r, 400));
  });
  await settlePageLoad(page);
}

export async function detectRawSections(page, detectSrc) {
  await page.evaluate(detectSrc);
  const raw = await page.evaluate("window.__xPaperDetectSections()");
  return Array.isArray(raw) ? raw : [];
}

export function navSelectorHint() {
  return "nav, header, [role=navigation]";
}
