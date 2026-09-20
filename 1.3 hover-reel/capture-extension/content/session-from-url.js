// Reads this run's Paper session off the source URL that the pipeline stamped.
//
// This runs at document_start on every http(s) page, so the query string is
// untrusted input: any site could link with these params and try to repoint the
// capture session at another folder or Paper file. Validate here, hand the
// result to the service worker (the single place that writes storage), and let
// the native bridge re-check projectRoot and pin the endpoint to localhost.
(() => {
  const PAPER_FILE_ID = /^[A-Za-z0-9][A-Za-z0-9._-]{7,63}$/;
  const LOCAL_HOSTS = new Set(["127.0.0.1", "localhost", "::1", "[::1]"]);

  function plausibleRoot(root) {
    if (!root.startsWith("/") || root.length > 4096) return false;
    return !root.split("/").includes("..");
  }

  function localEndpoint(endpoint) {
    if (!endpoint) return true;
    try {
      const url = new URL(endpoint);
      if (url.protocol !== "http:" && url.protocol !== "https:") return false;
      return LOCAL_HOSTS.has(url.hostname);
    } catch {
      return false;
    }
  }

  function readSession(href) {
    let url;
    try { url = new URL(href); } catch { return null; }
    const hash = new URLSearchParams(url.hash.startsWith("#") ? url.hash.slice(1) : url.hash);
    const read = (name) => (url.searchParams.get(name) || hash.get(name) || "").trim();

    const paperFileId = read("paperFileId");
    const projectRoot = read("projectRoot");
    const paperEndpoint = read("paperEndpoint");
    if (!paperFileId && !projectRoot) return null;
    if (paperFileId && !PAPER_FILE_ID.test(paperFileId)) return null;
    if (projectRoot && !plausibleRoot(projectRoot)) return null;
    if (!localEndpoint(paperEndpoint)) return null;

    const session = { paperFileId, projectRoot, captureAutostart: true };
    if (paperEndpoint) session.paperEndpoint = paperEndpoint;
    return session;
  }

  const session = readSession(location.href);
  if (!session) return;
  chrome.runtime
    .sendMessage({ type: "HC_SESSION_FROM_PAGE", session })
    .catch(() => { /* worker asleep — the panel re-reads the tab URL on open */ });
})();
