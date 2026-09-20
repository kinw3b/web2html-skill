// Visible capture cursor + HUD. Playwright's mouse is a CDP event stream —
// Chrome does not draw an OS pointer for it. This overlay is moved by
// __hrCursor.move() (not DOM mousemove) so a person watching the window can
// see what A/6 is targeting. Host/hud ids start with x-paper- so url-to-paper's
// serializer skips them.

export const CURSOR_TAG = "x-paper-cursor";
export const HUD_TAG = "x-paper-cursor-hud";

export function formatHud({ phase, current, total, label, text } = {}) {
  if (text) return String(text);
  const bits = ["hover-reel"];
  if (current != null && total != null && Number(total) > 0) {
    bits.push(`${Number(current)}/${Number(total)}`);
  }
  if (phase) bits.push(String(phase));
  if (label && String(label) !== String(phase || "")) bits.push(String(label));
  return bits.join(" · ");
}

export function bootVisibleCursor() {
  const TAG = "x-paper-cursor";
  const BOX = "x-paper-cursor-box";
  const HUD = "x-paper-cursor-hud";
  const mount = () => {
    if (
      document.querySelector(TAG) &&
      document.querySelector(BOX) &&
      document.querySelector(HUD) &&
      window.__hrCursor
    ) {
      return window.__hrCursor;
    }
    document.querySelector(TAG)?.remove();
    document.querySelector(BOX)?.remove();
    document.querySelector(HUD)?.remove();
    const host = document.createElement(TAG);
    host.id = "x-paper-cursor";
    host.setAttribute("aria-hidden", "true");
    host.style.cssText = [
      "position:fixed",
      "left:0",
      "top:0",
      "z-index:2147483647",
      "pointer-events:none",
      "width:0",
      "height:0",
    ].join(";");
    host.innerHTML = `
      <div data-hr="spot" style="
        position:absolute;left:-14px;top:-14px;width:28px;height:28px;
        border:3px solid #E11D2E;border-radius:999px;background:rgba(225,29,46,.18);
        box-shadow:0 0 0 6px rgba(225,29,46,.12), 0 8px 18px rgba(0,0,0,.28);
      "></div>
      <svg data-hr="arrow" width="28" height="28" viewBox="0 0 24 24" style="position:absolute;left:-2px;top:-2px;filter:drop-shadow(0 1px 2px rgba(0,0,0,.55))">
        <path d="M4 3 L20 12 L13 13.5 L16.5 21.5 L13.5 23 L10 15 L4 18 Z" fill="#111" stroke="#fff" stroke-width="1.4" stroke-linejoin="round"/>
      </svg>
      <div data-hr="label" style="
        position:absolute;left:22px;top:-10px;max-width:280px;
        padding:4px 8px;border-radius:6px;background:#111;color:#fff;
        font:600 12px/1.2 Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
        white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
        box-shadow:0 6px 16px rgba(0,0,0,.28);display:none;
      "></div>
      <div data-hr="mark" hidden style="
        position:absolute;left:20px;top:-16px;width:28px;height:28px;
        display:none;align-items:center;justify-content:center;
        border-radius:999px;background:#fff;color:#111;
        font:700 11px/1 Inter,ui-sans-serif,system-ui,sans-serif;
        box-shadow:0 4px 14px rgba(0,0,0,.35);
        pointer-events:none;
      ">01</div>
      <div data-hr="hold" hidden style="
        position:absolute;left:18px;top:-4px;display:none;align-items:center;
        pointer-events:none;
      ">
        <div style="
          width:92px;height:8px;border-radius:999px;background:#fff;
          box-shadow:0 2px 10px rgba(0,0,0,.35);overflow:hidden;
        ">
          <div data-hr="hold-fill" style="width:0;height:100%;background:#E11D2E;"></div>
        </div>
      </div>
    `;
    const box = document.createElement(BOX);
    box.id = "x-paper-cursor-box";
    box.setAttribute("aria-hidden", "true");
    box.style.cssText = [
      "position:fixed",
      "left:0",
      "top:0",
      "width:0",
      "height:0",
      "z-index:2147483646",
      "pointer-events:none",
      "border:2px solid #E11D2E",
      "background:rgba(225,29,46,.06)",
      "display:none",
    ].join(";");
    const hud = document.createElement(HUD);
    hud.id = "x-paper-cursor-hud";
    hud.setAttribute("aria-hidden", "true");
    hud.style.cssText = [
      "position:fixed",
      "left:16px",
      "bottom:16px",
      "z-index:2147483647",
      "pointer-events:none",
      "max-width:70vw",
      "padding:7px 14px",
      "border-radius:999px",
      "background:rgba(18,18,24,.92)",
      "color:#fff",
      'font:400 12px/1.4 Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
      "letter-spacing:0.2px",
      "white-space:nowrap",
      "overflow:hidden",
      "text-overflow:ellipsis",
      "border:1px solid rgba(255,255,255,.12)",
      "box-shadow:0 2px 12px rgba(0,0,0,.35)",
      "display:block",
      "visibility:visible",
    ].join(";");
    hud.textContent = "hover-reel · running";
    const root = document.documentElement || document.body;
    root.appendChild(box);
    root.appendChild(host);
    root.appendChild(hud);
    const label = host.querySelector("[data-hr=label]");
    const arrow = host.querySelector("[data-hr=arrow]");
    const hold = host.querySelector("[data-hr=hold]");
    const holdFill = host.querySelector("[data-hr=hold-fill]");
    const mark = host.querySelector("[data-hr=mark]");
    const pos = { x: 0, y: 0 };
    let lockEl = null;
    const move = (x, y) => {
      pos.x = Math.round(Number(x) || 0);
      pos.y = Math.round(Number(y) || 0);
      host.style.transform = `translate(${pos.x}px, ${pos.y}px)`;
    };
    const aim = (text) => {
      const t = String(text || "").trim();
      label.textContent = t;
      label.style.display = t && !lockEl ? "block" : "none";
    };
    const setHold = (progress) => {
      if (!hold || !holdFill) return;
      if (progress == null || Number.isNaN(Number(progress))) {
        hold.hidden = true;
        hold.style.display = "none";
        if (arrow) arrow.style.display = "";
        return;
      }
      const p = Math.min(1, Math.max(0, Number(progress)));
      hold.hidden = false;
      hold.style.display = "flex";
      holdFill.style.width = `${Math.round(p * 100)}%`;
      if (arrow) arrow.style.display = "none";
      if (label) label.style.display = "none";
    };
    const setClickMark = (n) => {
      if (!mark) return;
      const step = Number(n);
      if (!step) {
        mark.hidden = true;
        mark.style.display = "none";
        return;
      }
      mark.textContent = String(step).padStart(2, "0");
      mark.hidden = false;
      mark.style.display = "flex";
    };
    const lock = (el) => {
      lockEl = el && el.nodeType === 1 ? el : null;
      ring(lockEl);
    };
    const showHud = (info = {}) => {
      const bits = ["hover-reel"];
      if (info.text) {
        hud.textContent = String(info.text);
      } else {
        if (info.current != null && info.total != null && Number(info.total) > 0) {
          bits.push(`${Number(info.current)}/${Number(info.total)}`);
        }
        if (info.phase) bits.push(String(info.phase));
        if (info.label && String(info.label) !== String(info.phase || "")) bits.push(String(info.label));
        hud.textContent = bits.join(" · ");
      }
      hud.style.display = "block";
      hud.style.visibility = "visible";
    };
    const ring = (el) => {
      if (!el || el === host || el === box || el === hud || host.contains(el) || el.nodeType !== 1) {
        box.style.display = "none";
        return;
      }
      const r = el.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) {
        box.style.display = "none";
        return;
      }
      box.style.display = "block";
      box.style.left = `${Math.round(r.left - 3)}px`;
      box.style.top = `${Math.round(r.top - 3)}px`;
      box.style.width = `${Math.round(r.width + 6)}px`;
      box.style.height = `${Math.round(r.height + 6)}px`;
    };
    document.addEventListener("mousemove", (e) => {
      move(e.clientX, e.clientY);
      if (lockEl) {
        ring(lockEl);
        return;
      }
      const t = document.elementFromPoint(e.clientX, e.clientY);
      ring(t && t.closest && (t.closest(TAG) || t.closest(BOX) || t.closest(HUD)) ? null : t);
    }, true);
    window.__hrCursor = { move, aim, ring, lock, setHold, setClickMark, showHud, host, box, hud, pos };
    return window.__hrCursor;
  };
  mount();
  if (!window.__hrCursorWatch) {
    window.__hrCursorWatch = new MutationObserver(() => {
      if (
        !document.querySelector(TAG) ||
        !document.querySelector(BOX) ||
        !document.querySelector(HUD)
      ) {
        mount();
      }
    });
    window.__hrCursorWatch.observe(document.documentElement, { childList: true, subtree: true });
  }
  const remount = () => { try { mount(); } catch { /* document tearing down */ } };
  if (!window.__hrCursorNav) {
    window.__hrCursorNav = true;
    document.addEventListener("DOMContentLoaded", remount);
    window.addEventListener("pageshow", remount);
  }
  return window.__hrCursor;
}

export async function installVisibleCursor(page) {
  await page.addInitScript(bootVisibleCursor);
  const remount = async () => {
    try { await page.evaluate(bootVisibleCursor); } catch { /* document not ready */ }
  };
  await remount();
  if (!page.__hrCursorHooks) {
    page.__hrCursorHooks = true;
    page.on("load", () => { remount(); });
    page.on("framenavigated", (frame) => {
      if (frame === page.mainFrame()) remount();
    });
  }
}

export async function showCursorLabel(page, label) {
  try {
    await page.evaluate((text) => {
      if (!window.__hrCursor) return;
      window.__hrCursor.aim(String(text || ""));
    }, label || "");
  } catch {
    /* page gone */
  }
}

export async function showHud(page, info = {}) {
  try {
    await page.evaluate((payload) => {
      const boot = window.__hrCursor || null;
      if (!boot || !boot.hud) return;
      boot.showHud(payload || {});
    }, {
      phase: info.phase || "",
      current: info.current,
      total: info.total,
      label: info.label || "",
      text: info.text || "",
    });
  } catch {
    /* page gone */
  }
}

export async function movePointer(page, x, y, { steps = 18, label } = {}) {
  if (label != null) await showCursorLabel(page, label);
  const n = Math.max(8, Number(steps) || 18);
  const tx = Number(x);
  const ty = Number(y);
  // Drive the drawn pointer ourselves — page.mouse.move often does not fire
  // DOM mousemove, so the overlay would otherwise sit still.
  const overlay = page.evaluate(async ({ x, y, steps }) => {
    const api = window.__hrCursor;
    if (!api || typeof api.move !== "function") return;
    const x0 = Number(api.pos?.x);
    const y0 = Number(api.pos?.y);
    const fromX = Number.isFinite(x0) ? x0 : x;
    const fromY = Number.isFinite(y0) ? y0 : y;
    for (let i = 1; i <= steps; i++) {
      const t = i / steps;
      api.move(fromX + (x - fromX) * t, fromY + (y - fromY) * t);
      await new Promise((r) => setTimeout(r, 16));
    }
  }, { x: tx, y: ty, steps: n }).catch(() => {});
  await Promise.all([
    overlay,
    page.mouse.move(tx, ty, { steps: n }),
  ]);
}
