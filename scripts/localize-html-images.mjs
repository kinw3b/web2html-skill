#!/usr/bin/env node
// Rewrite remote <img src> / CSS url() / data:image backgrounds to local
// Paper assets.
//
// Why: Stage P serializer emits https://framerusercontent.com/… URLs,
// Framer `data:framer/asset-reference,<hash>.png` on 768/390, and
// wordmarks as background-image: url('data:image/svg+xml…'). Paper
// fetches remote URLs at write_html (fetcher race / CDN 404), cannot
// load asset-reference, and cannot keep large CSS data URIs as image
// fills — all three become the grey broken-image placeholder while the
// write still reports success.
// Paper's local contract is paper-asset:// + an absolute path. Empty
// background-image boxes (footer logo) become an inline SVG or <img>.
//
// Resolution order per http(s) URL:
//   1. rebuild/images/<basename> or source-site/assets/<basename>
//      (1.1 light scrape — images + Latin fonts only)
//   2. capture/assets/<basename> (previous download)
//   3. download into capture/assets/ and copy into rebuild/images/
//
// Usage (library):
//   import { localizeHtml } from "./localize-html-images.mjs";
//   const { html, mapped } = await localizeHtml(raw, { projectRoot });
//
// Usage (CLI):
//   node localize-html-images.mjs --dir capture/home-desktop
//                                 [--project <root>] [--no-download]

import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, writeFileSync, existsSync, copyFileSync } from "node:fs";
import { basename, extname, join, resolve } from "node:path";

const IMAGE_HOST = /framerusercontent\.com|images\.unsplash\.com|cdn\.|cloudinary|imgix/i;
const IMAGE_EXT = /\.(png|jpe?g|webp|avif|gif|svg)(\?|$)/i;
const URL_RE = /https?:\/\/[^"')\s]+/g;

export function isImageUrl(url) {
  try {
    const u = new URL(url);
    return IMAGE_EXT.test(u.pathname) || IMAGE_HOST.test(u.hostname);
  } catch {
    return false;
  }
}

export function paperAssetSrc(absPath) {
  const abs = resolve(absPath);
  return abs.startsWith("/") ? `paper-asset://${abs}` : `paper-asset:///${abs}`;
}

function candidates(url, dirs) {
  let name;
  try { name = basename(new URL(url).pathname); } catch { return []; }
  if (!name) return [];
  const stem = name.replace(extname(name), "");
  const extras = [".png", ".jpg", ".jpeg", ".webp", ".avif", ".gif", ".svg"];
  const names = [name, ...extras.map((e) => stem + e)];
  const out = [];
  for (const dir of dirs) {
    for (const n of names) out.push(join(dir, n));
  }
  return out;
}

async function download(url, dest) {
  const res = await fetch(url, { redirect: "follow" });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  const buf = Buffer.from(await res.arrayBuffer());
  mkdirSync(resolve(dest, ".."), { recursive: true });
  writeFileSync(dest, buf);
  return buf.length;
}

function extractQuotedDataUris(html) {
  const out = [];
  let i = 0;
  while (true) {
    const start = html.indexOf("data:image/", i);
    if (start < 0) break;
    const before = html.slice(Math.max(0, start - 10), start);
    const qMatch = before.match(/(['"])$/);
    if (!qMatch) {
      i = start + 11;
      continue;
    }
    const end = html.indexOf(qMatch[1], start);
    if (end < 0) break;
    out.push(html.slice(start, end));
    i = end + 1;
  }
  return [...new Set(out)];
}

function dataUriToBuffer(uri) {
  const comma = uri.indexOf(",");
  if (comma < 0) return null;
  const meta = uri.slice(5, comma);
  const payload = uri.slice(comma + 1);
  const mime = meta.split(";")[0] || "application/octet-stream";
  const isB64 = /;base64/i.test(meta);
  let buf;
  try {
    buf = isB64
      ? Buffer.from(payload, "base64")
      : Buffer.from(decodeURIComponent(payload), "utf8");
  } catch {
    return null;
  }
  const ext = mime.includes("svg")
    ? ".svg"
    : mime.includes("png")
      ? ".png"
      : mime.includes("jpeg") || mime.includes("jpg")
        ? ".jpg"
        : mime.includes("webp")
          ? ".webp"
          : mime.includes("gif")
            ? ".gif"
            : ".bin";
  return { buf, ext, mime };
}

function writeDataUri(uri, destDir, rebuildDir) {
  const parsed = dataUriToBuffer(uri);
  if (!parsed) return null;
  const hash = createHash("sha1").update(parsed.buf).digest("hex").slice(0, 12);
  const name = `data-${hash}${parsed.ext}`;
  const dest = join(destDir, name);
  if (!existsSync(dest)) writeFileSync(dest, parsed.buf);
  const rebuildCopy = join(rebuildDir, name);
  if (!existsSync(rebuildCopy)) copyFileSync(dest, rebuildCopy);
  return dest;
}

function stripBgImageProps(style) {
  return style
    .replace(/background-image:\s*url\((?:'[^']+'|"[^"]+"|[^)]+)\)\s*;?/gi, "")
    .replace(/background-size:\s*[^;]+;?/gi, "")
    .replace(/background-repeat:\s*[^;]+;?/gi, "")
    .replace(/background-position(?:-x|-y)?:\s*[^;]+;?/gi, "")
    .replace(/image-rendering:\s*[^;]+;?/gi, "")
    .replace(/;\s*;/g, ";")
    .trim();
}

function promoteEmptyBackgroundImages(html, paperSrcToLocal) {
  return html.replace(
    /<(a|div|span)(\s[^>]*?)\s*>\s*<\/\1>/gi,
    (full, tag, attrs) => {
      const srcMatch = attrs.match(
        /background-image:\s*url\(\s*(['"]?)(paper-asset:[^'"]+)\1\s*\)/i,
      );
      if (!srcMatch) return full;
      const src = srcMatch[2];
      const styleMatch = attrs.match(/style="([^"]*)"/i);
      if (!styleMatch) return full;
      const newStyle = stripBgImageProps(styleMatch[1]);
      const newAttrs = attrs.replace(/style="[^"]*"/i, `style="${newStyle}"`);
      const local = paperSrcToLocal.get(src);
      if (local && extname(local).toLowerCase() === ".svg") {
        const svg = readFileSync(local, "utf8")
          .replace(/<\?xml[^?]*\?>/i, "")
          .trim();
        const withFit = svg.replace(
          /<svg\b/i,
          '<svg style="display:block;width:100%;height:100%"',
        );
        return `<${tag}${newAttrs}>${withFit}</${tag}>`;
      }
      return `<${tag}${newAttrs}><img src="${src}" alt="" style="display:block;width:100%;height:100%;object-fit:contain" /></${tag}>`;
    },
  );
}

// Framer tablet/mobile captures often emit
// `data:framer/asset-reference,<hash>.png?originalFilename=…` instead of
// https://framerusercontent.com/images/<hash>.png. Paper cannot fetch that
// scheme, so the slot lands as an empty Rectangle. Resolve the hash against
// the same local files desktop already downloaded.
const ASSET_REF_RE = /data:framer\/asset-reference,([^?"')\s]+)(?:\?[^"')\s]*)?/gi;

export function rewriteFramerAssetReferences(html, searchDirs, acc = {}) {
  const mapped = acc.mapped || [];
  const missing = acc.missing || [];
  const seen = acc.seen || new Map();
  const dirs = (searchDirs || []).map((d) => resolve(d));

  const out = String(html).replace(ASSET_REF_RE, (full, file) => {
    const name = decodeURIComponent(String(file || "").replace(/&amp;/g, "&"));
    if (!name) return full;
    if (seen.has(full)) return seen.get(full);
    const hit = dirs.map((d) => join(d, name)).find((p) => existsSync(p));
    if (!hit) {
      missing.push({ url: full, error: "framer asset-reference not on disk" });
      return full;
    }
    const src = paperAssetSrc(hit);
    seen.set(full, src);
    mapped.push({ url: full, local: hit, paperSrc: src, kind: "framer-asset-reference" });
    return src;
  });
  return out;
}

export async function localizeHtml(html, opts = {}) {
  const projectRoot = resolve(opts.projectRoot || process.cwd());
  const cacheDir = resolve(opts.cacheDir || join(projectRoot, "capture/assets"));
  const rebuildDir = resolve(opts.rebuildDir || join(projectRoot, "rebuild/images"));
  const searchDirs = (opts.searchDirs || [
    join(projectRoot, "rebuild/images"),
    join(projectRoot, "source-site/assets"),
    cacheDir,
  ]).map((d) => resolve(d));
  const allowDownload = opts.download !== false;
  mkdirSync(cacheDir, { recursive: true });
  mkdirSync(rebuildDir, { recursive: true });

  const mapped = [];
  const missing = [];
  const seen = new Map();
  html = rewriteFramerAssetReferences(html, searchDirs, { mapped, missing, seen });
  const urls = [...new Set(html.match(URL_RE) || [])].filter(isImageUrl);
  const dataUris = extractQuotedDataUris(html);

  for (const uri of dataUris) {
    const local = writeDataUri(uri, cacheDir, rebuildDir);
    if (!local) {
      missing.push({ url: uri.slice(0, 48), error: "bad data URI" });
      continue;
    }
    seen.set(uri, paperAssetSrc(local));
    mapped.push({ url: uri.slice(0, 48) + "…", local, paperSrc: seen.get(uri), kind: "data-uri" });
  }

  for (const url of urls) {
    if (seen.has(url)) continue;
    const hit = candidates(url, searchDirs).find((p) => existsSync(p));
    let local = hit || null;
    if (!local && allowDownload) {
      let name;
      try { name = basename(new URL(url).pathname); } catch { name = `img-${mapped.length}`; }
      const dest = join(cacheDir, name);
      try {
        await download(url, dest);
        local = dest;
        const rebuildCopy = join(rebuildDir, name);
        if (!existsSync(rebuildCopy)) copyFileSync(dest, rebuildCopy);
      } catch (err) {
        missing.push({ url, error: err.message.split("\n")[0] });
        continue;
      }
    }
    if (!local) {
      missing.push({ url, error: "not on disk and download disabled" });
      continue;
    }
    seen.set(url, paperAssetSrc(local));
    mapped.push({ url, local, paperSrc: seen.get(url) });
  }

  let out = html;
  for (const [url, src] of seen) {
    out = out.split(url).join(src);
  }
  const paperSrcToLocal = new Map(mapped.map((m) => [m.paperSrc, m.local]));
  out = promoteEmptyBackgroundImages(out, paperSrcToLocal);
  out = remapUnavailableFonts(out);
  return { html: out, mapped, missing, remote: urls.length + dataUris.length };
}

// Paper cannot load General Sans / Clash Grotesk. The serializer also
// bakes weight into the family name ("General Sans Semibold") and omits
// font-weight, so write_html falls back to system-ui Regular. Satoshi
// Bold is the closest installed display face (no 600 on Satoshi).
function remapUnavailableFonts(html) {
  return html
    .replace(
      /font-family:\s*'General Sans Semibold',\s*sans-serif/gi,
      "font-family: Satoshi, sans-serif; font-weight: 700",
    )
    .replace(
      /font-family:\s*Inter-Medium,\s*Inter,\s*sans-serif/gi,
      "font-family: Inter, sans-serif",
    )
    .replace(
      /font-family:\s*Inter-SemiBold,\s*Inter,\s*sans-serif/gi,
      "font-family: Inter, sans-serif",
    );
}

// ---- CLI (only when this file is the entrypoint with --dir) ----
if (process.argv[1]?.endsWith("localize-html-images.mjs") && process.argv.includes("--dir")) {
  const argv = process.argv.slice(2);
  const arg = (name, fallback) => {
    const i = argv.indexOf(`--${name}`);
    return i >= 0 && argv[i + 1] ? argv[i + 1] : fallback;
  };
  const dir = arg("dir");
  if (!dir) {
    console.error("usage: localize-html-images.mjs --dir capture/home-desktop [--project <root>]");
    process.exit(1);
  }
  const projectRoot = resolve(arg("project", process.cwd()));
  const { readdirSync } = await import("node:fs");
  const files = readdirSync(resolve(dir)).filter((f) => f.endsWith(".html"));
  const summary = { files: 0, mapped: 0, missing: [] };
  for (const f of files) {
    const path = join(resolve(dir), f);
    const raw = readFileSync(path, "utf8");
    const { html, mapped, missing } = await localizeHtml(raw, {
      projectRoot,
      download: !argv.includes("--no-download"),
    });
    if (mapped.length) writeFileSync(path, html, "utf8");
    summary.files++;
    summary.mapped += mapped.length;
    summary.missing.push(...missing);
    if (mapped.length || missing.length) {
      console.error(`· ${f}: ${mapped.length} localized, ${missing.length} missing`);
    }
  }
  const ledgerPath = join(projectRoot, "capture/assets/ledger.json");
  mkdirSync(join(projectRoot, "capture/assets"), { recursive: true });
  writeFileSync(ledgerPath, JSON.stringify(summary, null, 2));
  console.log(JSON.stringify({ dir: resolve(dir), ...summary, ledger: ledgerPath }, null, 1));
  if (summary.missing.length) process.exit(2);
}
