import { normalizeSession } from "./shared/session-url.js";

const PROTOCOL = "1.3";
const DESKTOP_WIDTH = 1600;
const NAV_BREAKPOINTS = [
  { name: "tablet", width: 768, height: 1024 },
  { name: "mobile", width: 390, height: 844 },
];

const desktopLock = { tabId: null, attached: false };

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

chrome.runtime.onInstalled.addListener(() => {
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(() => {});
});

chrome.runtime.onStartup.addListener(() => {
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(() => {});
});

function tabSend(tabId, message) {
  return chrome.tabs.sendMessage(tabId, message);
}

async function inject(tabId) {
  for (let attempt = 0; attempt < 5; attempt += 1) {
    try {
      const pong = await tabSend(tabId, { type: "HC_PING" });
      if (pong?.ok) return { ok: true, reused: true };
    } catch { /* inject below */ }
    try {
      await chrome.scripting.insertCSS({
        target: { tabId },
        files: ["content/capture.css"],
      });
      await chrome.scripting.executeScript({
        target: { tabId },
        files: ["content/targeting.js", "content/nav-breakpoints.js", "content/component-names.js", "content/paper-sections.js", "content/tag-overlays.js", "content/capture.js"],
      });
      return { ok: true, reused: false };
    } catch (error) {
      if (attempt === 4) throw error;
      await sleep(350);
    }
  }
  return { ok: true };
}

function attach(tabId) {
  return new Promise((resolve, reject) => {
    chrome.debugger.attach({ tabId }, PROTOCOL, () => {
      const error = chrome.runtime.lastError;
      if (error && !/already attached/i.test(error.message || "")) reject(new Error(error.message));
      else resolve();
    });
  });
}

function detach(tabId) {
  return new Promise((resolve) => {
    chrome.debugger.detach({ tabId }, () => resolve());
  });
}

function cdp(tabId, method, params = {}) {
  return new Promise((resolve, reject) => {
    chrome.debugger.sendCommand({ tabId }, method, params, (result) => {
      const error = chrome.runtime.lastError;
      if (error) reject(new Error(error.message));
      else resolve(result);
    });
  });
}

async function hoverPair(tabId, captureId) {
  let attachedHere = false;
  try {
    const locked = desktopLock.attached && desktopLock.tabId === tabId;
    if (!locked) {
      await attach(tabId);
      attachedHere = true;
    }
    await cdp(tabId, "Input.dispatchMouseEvent", {
      type: "mouseMoved",
      x: 2,
      y: 2,
      buttons: 0,
      pointerType: "mouse",
    });
    await sleep(280);
    const prepared = await tabSend(tabId, { type: "HC_PREPARE_TARGET", captureId });
    if (!prepared?.ok) throw new Error(prepared?.error || "Target is no longer visible");
    const fallbackPoint = prepared.point;
    await cdp(tabId, "Input.dispatchMouseEvent", {
      type: "mouseMoved",
      x: 2,
      y: 2,
      buttons: 0,
      pointerType: "mouse",
    });
    await sleep(220);
    const before = await tabSend(tabId, {
      type: "HC_SERIALIZE_TARGET",
      captureId,
      state: "default",
    });
    if (!before?.ok) throw new Error(before?.error || "Default state could not be serialized");
    const point = before.point || fallbackPoint;
    await cdp(tabId, "Input.dispatchMouseEvent", {
      type: "mouseMoved",
      x: point.x,
      y: point.y,
      buttons: 0,
      pointerType: "mouse",
    });
    await sleep(850);
    const after = await tabSend(tabId, {
      type: "HC_SERIALIZE_TARGET",
      captureId,
      state: "hover",
    });
    if (!after?.ok) throw new Error(after?.error || "Hover state could not be serialized");
    return {
      ok: true,
      capture: {
        ...before.capture,
        mode: "hover",
        defaultHtml: before.capture.html,
        hoverHtml: after.capture.html,
        html: undefined,
      },
    };
  } finally {
    if (attachedHere) await detach(tabId);
  }
}

async function autoHover(tabId) {
  const listed = await tabSend(tabId, { type: "HC_AUTO_TARGETS", mode: "hover" });
  const targets = listed?.targets || [];
  const captures = [];
  for (const target of targets.slice(0, 8)) {
    const result = await hoverPair(tabId, target.captureId);
    if (result.ok) captures.push(result.capture);
  }
  return { ok: true, captures, scanned: targets.length };
}

function sameOrigin(tabUrl, expectedUrl) {
  try {
    return new URL(tabUrl).origin === new URL(expectedUrl).origin;
  } catch {
    return Boolean(tabUrl && expectedUrl && String(tabUrl).startsWith(String(expectedUrl)));
  }
}

function waitForTabComplete(tabId, expectedUrl, timeout = 45000) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => finish(new Error("Responsive Navbar tab timed out")), timeout);
    const finish = (error) => {
      clearTimeout(timer);
      chrome.tabs.onUpdated.removeListener(onUpdated);
      if (error) reject(error);
      else resolve();
    };
    const ready = (tab) => {
      if (!tab || tab.status !== "complete") return false;
      const href = tab.url || "";
      if (!href || href === "about:blank" || href.startsWith("chrome:")) return false;
      return !expectedUrl || sameOrigin(href, expectedUrl);
    };
    const onUpdated = (updatedId, change, tab) => {
      if (updatedId !== tabId || change.status !== "complete") return;
      if (ready(tab)) finish();
    };
    chrome.tabs.onUpdated.addListener(onUpdated);
    chrome.tabs.get(tabId).then((tab) => {
      if (ready(tab)) finish();
    }).catch(finish);
  });
}

async function pageSize(tabId) {
  const [shot] = await chrome.scripting.executeScript({
    target: { tabId },
    func: () => ({ width: innerWidth, height: innerHeight }),
  });
  return shot?.result || { width: 0, height: 0 };
}

async function releaseDesktopLock() {
  const tabId = desktopLock.tabId;
  desktopLock.tabId = null;
  desktopLock.attached = false;
  if (Number.isInteger(tabId)) await detach(tabId);
}

async function lockDesktopViewport(tabId) {
  try {
    const tab = await chrome.tabs.get(tabId);
    if (Number.isInteger(tab.windowId)) {
      await chrome.windows.update(tab.windowId, { state: "maximized" }).catch(() => {});
    }
    await chrome.tabs.setZoom(tabId, 1).catch(() => {});
    if (chrome.tabs.setZoomSettings) {
      await chrome.tabs.setZoomSettings(tabId, { mode: "disabled", scope: "per-tab" }).catch(() => {});
    }
    await attach(tabId);
    desktopLock.tabId = tabId;
    desktopLock.attached = true;
    const size = await pageSize(tabId);
    const view = await lockViewport(tabId, {
      width: DESKTOP_WIDTH,
      height: Math.max(900, Number(size.height) || 900),
    });
    return {
      ok: true,
      width: Number(view.width) || DESKTOP_WIDTH,
      height: Number(view.height) || 0,
      contractWidth: DESKTOP_WIDTH,
      zoom: 1,
    };
  } catch (error) {
    await releaseDesktopLock();
    throw error;
  }
}

async function lockViewport(tabId, spec) {
  const metrics = {
    width: spec.width,
    height: spec.height,
    screenWidth: spec.width,
    screenHeight: spec.height,
    deviceScaleFactor: 1,
    mobile: spec.width <= 768,
  };
  let last = { width: 0, height: 0 };
  for (let attempt = 0; attempt < 8; attempt += 1) {
    await cdp(tabId, "Emulation.setDeviceMetricsOverride", metrics);
    await sleep(450);
    last = await pageSize(tabId);
    if (Math.abs(Number(last.width) - spec.width) <= 48) {
      await sleep(900);
      return last;
    }
  }
  throw new Error(`Viewport stayed at ${last.width}×${last.height}, wanted ${spec.width}×${spec.height}`);
}

async function captureNavBreakpoint(url, fingerprint, spec) {
  const previous = await chrome.windows.getLastFocused().catch(() => null);
  const win = await chrome.windows.create({
    url,
    type: "popup",
    focused: true,
    width: spec.width,
    height: spec.height + 80,
    left: 24,
    top: 24,
  });
  const tabId = win.tabs?.[0]?.id || (await chrome.tabs.query({ windowId: win.id }))[0]?.id;
  if (!tabId) throw new Error(`Navbar ${spec.width} window had no tab`);
  let attached = false;
  try {
    await waitForTabComplete(tabId, url);
    await attach(tabId);
    attached = true;
    await lockViewport(tabId, spec);
    await inject(tabId);
    const result = await tabSend(tabId, {
      type: "HC_CAPTURE_NAV_BREAKPOINT",
      fingerprint,
      spec,
    });
    if (!result?.ok || !result.capture) {
      throw new Error(result?.error || `Navbar ${spec.width} capture failed`);
    }
    return result.capture;
  } finally {
    if (attached) await detach(tabId);
    await chrome.windows.remove(win.id).catch(() => {});
    if (previous?.id) await chrome.windows.update(previous.id, { focused: true }).catch(() => {});
  }
}

async function captureNavBreakpoints(url, fingerprint) {
  if (!url || !fingerprint) throw new Error("Desktop Navbar fingerprint is missing");
  const captures = [];
  const errors = [];
  for (const spec of NAV_BREAKPOINTS) {
    chrome.runtime.sendMessage({
      type: "HC_NAV_BREAKPOINT_PROGRESS", breakpoint: spec.name, phase: "capturing",
    }).catch(() => {});
    try {
      captures.push(await captureNavBreakpoint(url, fingerprint, spec));
      chrome.runtime.sendMessage({
        type: "HC_NAV_BREAKPOINT_PROGRESS", breakpoint: spec.name, phase: "captured",
      }).catch(() => {});
    } catch (error) {
      errors.push(`${spec.width}: ${error.message}`);
      chrome.runtime.sendMessage({
        type: "HC_NAV_BREAKPOINT_PROGRESS", breakpoint: spec.name, phase: "failed",
      }).catch(() => {});
    }
  }
  return { ok: errors.length === 0, captures, errors };
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || typeof message.type !== "string") return false;

  if (message.type === "HC_SESSION_FROM_PAGE") {
    // Page-supplied — validate before it reaches storage. A rejected session is
    // not an error the page should be able to distinguish, so answer the same
    // shape either way.
    const session = normalizeSession(message.session);
    if (!session) {
      sendResponse({ ok: false, error: "Session parameters were rejected" });
      return true;
    }
    const stored = {
      paperFileId: session.paperFileId || "",
      projectRoot: session.projectRoot || "",
      captureAutostart: true,
    };
    if (session.paperEndpoint) stored.paperEndpoint = session.paperEndpoint;
    const tabId = sender.tab?.id;
    const windowId = sender.tab?.windowId;
    chrome.storage.local.set(stored).then(() => {
      const openPanel = Number.isInteger(tabId)
        ? chrome.sidePanel.open({ tabId })
        : Number.isInteger(windowId)
          ? chrome.sidePanel.open({ windowId })
          : Promise.resolve();
      openPanel.catch(() => {}).finally(() => sendResponse({ ok: true }));
    }, (error) => {
      sendResponse({ ok: false, error: error.message });
    });
    return true;
  }

  if (message.type === "HC_INJECT") {
    inject(message.tabId).then(sendResponse, (error) => {
      sendResponse({ ok: false, error: error.message });
    });
    return true;
  }

  if (message.type === "HC_HOVER_TARGET") {
    const tabId = sender.tab?.id;
    if (!tabId) return false;
    hoverPair(tabId, message.captureId).then((result) => {
      chrome.runtime.sendMessage({ type: "HC_TAKE_READY", ...result }).catch(() => {});
    }, (error) => {
      chrome.runtime.sendMessage({
        type: "HC_TAKE_READY",
        ok: false,
        error: error.message,
      }).catch(() => {});
    });
    sendResponse({ ok: true });
    return false;
  }

  if (message.type === "HC_AUTO_HOVER") {
    autoHover(message.tabId).then(sendResponse, (error) => {
      sendResponse({ ok: false, error: error.message });
    });
    return true;
  }

  if (message.type === "HC_LOCK_DESKTOP_VIEWPORT") {
    lockDesktopViewport(message.tabId).then(sendResponse, (error) => {
      sendResponse({ ok: false, error: error.message, contractWidth: DESKTOP_WIDTH });
    });
    return true;
  }

  if (message.type === "HC_RELEASE_VIEWPORT") {
    releaseDesktopLock().then(() => sendResponse({ ok: true }), (error) => {
      sendResponse({ ok: false, error: error.message });
    });
    return true;
  }

  if (message.type === "HC_CAPTURE_NAV_BREAKPOINTS") {
    captureNavBreakpoints(message.url, message.fingerprint).then(sendResponse, (error) => {
      sendResponse({ ok: false, captures: [], errors: [error.message] });
    });
    return true;
  }

  if (message.type === "HC_CLOSE_PANEL") {
    const tabId = message.tabId;
    if (typeof chrome.sidePanel.close === "function" && Number.isInteger(tabId)) {
      chrome.sidePanel.close({ tabId }).catch(() => {});
    }
    sendResponse({ ok: true });
    return false;
  }

  return false;
});
