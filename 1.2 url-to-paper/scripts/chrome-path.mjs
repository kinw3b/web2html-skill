// Resolve a usable Chromium from the Playwright cache.
// Override with PW_CHROME=/path/to/binary (required on most Linux agents).
import { existsSync, readdirSync } from "node:fs";
import { join } from "node:path";

export function resolveChrome() {
  if (process.env.PW_CHROME) {
    if (!existsSync(process.env.PW_CHROME)) {
      throw new Error(`PW_CHROME set but not found: ${process.env.PW_CHROME}`);
    }
    return process.env.PW_CHROME;
  }

  const homes = [
    join(process.env.HOME || "", "Library/Caches/ms-playwright"),
    join(process.env.HOME || "", ".cache/ms-playwright"),
    process.env.PLAYWRIGHT_BROWSERS_PATH || "",
  ].filter(Boolean);

  const cache = homes.find((p) => existsSync(p));
  if (!cache) {
    throw new Error(
      `No Playwright cache found. Set PW_CHROME=/path/to/chrome or run: npx playwright install chromium`,
    );
  }

  // Newest revision first.
  const builds = readdirSync(cache)
    .filter((d) => /^chromium(-\d+)?$/.test(d) || /^chromium_headless_shell-\d+$/.test(d))
    .sort((a, b) => {
      const na = parseInt((a.match(/(\d+)/) || [])[1] || "0", 10);
      const nb = parseInt((b.match(/(\d+)/) || [])[1] || "0", 10);
      return nb - na;
    });

  const candidates = [
    // macOS
    "chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
    "chrome-mac/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
    "chrome-mac-arm64/Chromium.app/Contents/MacOS/Chromium",
    "chrome-mac/Chromium.app/Contents/MacOS/Chromium",
    // Linux
    "chrome-linux64/chrome",
    "chrome-linux/chrome",
    "chromium-linux64/chrome",
    "chromium-linux/chrome",
  ];

  for (const build of builds) {
    for (const rel of candidates) {
      const p = join(cache, build, rel);
      if (existsSync(p)) return p;
    }
  }

  throw new Error(
    `No Chromium binary under ${cache}. Set PW_CHROME=/path/to/chrome or run: npx playwright install chromium`,
  );
}

const SYSTEM_CHROME_CANDIDATES = [
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/usr/bin/google-chrome",
  "/usr/bin/google-chrome-stable",
  "/usr/bin/chromium",
  "/usr/bin/chromium-browser",
];

/**
 * Launch options for chromium.launch().
 *
 * visible: true  → real Google Chrome when available, windowed.
 * visible: false → cached Playwright Chromium, headless.
 */
export function launchOptions({ visible = false } = {}) {
  if (!visible) {
    return { executablePath: resolveChrome(), headless: true };
  }

  const systemChrome = SYSTEM_CHROME_CANDIDATES.find((p) => existsSync(p));
  if (systemChrome && systemChrome.startsWith("/Applications/")) {
    // `channel` makes Playwright drive the installed Chrome rather than its
    // own Chromium build — this is what puts a real Chrome window on screen.
    return {
      channel: "chrome",
      headless: false,
      args: ["--window-size=1620,1100", "--window-position=40,40"],
    };
  }

  if (systemChrome) {
    return {
      executablePath: systemChrome,
      headless: false,
      args: ["--window-size=1620,1100", "--window-position=40,40", "--no-sandbox"],
    };
  }

  console.error(
    "· System Chrome not found — falling back to cached Chromium (still visible).",
  );
  return {
    executablePath: resolveChrome(),
    headless: false,
    args: ["--window-size=1620,1100", "--window-position=40,40"],
  };
}
