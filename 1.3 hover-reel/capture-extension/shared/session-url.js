export const EXTENSION_ID = "ecicfkapebfbpdgfaiadgfcghkpgmbem";
export const SESSION_PARAM = "paper-capture";

function clean(value) {
  return String(value || "").trim();
}

// A session can arrive from a page URL, so every field is untrusted input.
// The bridge re-checks projectRoot and pins the endpoint to localhost, but
// reject obvious junk here so a hostile link cannot quietly repoint a run.
const PAPER_FILE_ID = /^[A-Za-z0-9][A-Za-z0-9._-]{7,63}$/;
const LOCAL_HOSTS = new Set(["127.0.0.1", "localhost", "::1", "[::1]"]);

export function isPlausiblePaperFileId(value) {
  return PAPER_FILE_ID.test(clean(value));
}

export function isPlausibleProjectRoot(value) {
  const root = clean(value);
  if (!root.startsWith("/")) return false;              // absolute POSIX path only
  if (root.length > 4096) return false;
  if (/\0/.test(root)) return false;
  return !root.split("/").includes("..");                // no traversal segments
}

export function isLocalPaperEndpoint(value) {
  const endpoint = clean(value);
  if (!endpoint) return true;                            // absent → bridge default
  let url;
  try { url = new URL(endpoint); } catch { return false; }
  if (url.protocol !== "http:" && url.protocol !== "https:") return false;
  return LOCAL_HOSTS.has(url.hostname);
}

export function normalizeSession(raw) {
  if (!raw || typeof raw !== "object") return null;
  const session = {
    paperFileId: clean(raw.paperFileId || raw.fileId),
    projectRoot: clean(raw.projectRoot),
    paperEndpoint: clean(raw.paperEndpoint),
  };
  if (session.paperFileId && !isPlausiblePaperFileId(session.paperFileId)) return null;
  if (session.projectRoot && !isPlausibleProjectRoot(session.projectRoot)) return null;
  if (!isLocalPaperEndpoint(session.paperEndpoint)) return null;
  if (!session.paperFileId && !session.projectRoot) return null;
  return session;
}

export function parseHref(href) {
  let url;
  try {
    url = new URL(href);
  } catch {
    return null;
  }

  const hash = new URLSearchParams(url.hash.startsWith("#") ? url.hash.slice(1) : url.hash);
  const fromFields = normalizeSession({
    paperFileId: url.searchParams.get("paperFileId") || hash.get("paperFileId"),
    projectRoot: url.searchParams.get("projectRoot") || hash.get("projectRoot"),
    paperEndpoint: url.searchParams.get("paperEndpoint") || hash.get("paperEndpoint"),
  });
  if (fromFields) return fromFields;

  const packed = url.searchParams.get(SESSION_PARAM) || hash.get(SESSION_PARAM);
  if (!packed) return null;
  try {
    return normalizeSession(JSON.parse(decodeURIComponent(packed)));
  } catch {
    return null;
  }
}

export function buildPageUrl(baseUrl, session) {
  const next = normalizeSession(session);
  if (!next) throw new Error("paperFileId or projectRoot is required");
  const url = new URL(baseUrl);
  if (next.paperFileId) url.searchParams.set("paperFileId", next.paperFileId);
  if (next.projectRoot) url.searchParams.set("projectRoot", next.projectRoot);
  const hash = new URLSearchParams();
  if (next.paperFileId) hash.set("paperFileId", next.paperFileId);
  if (next.projectRoot) hash.set("projectRoot", next.projectRoot);
  url.hash = hash.toString();
  return url.href;
}
