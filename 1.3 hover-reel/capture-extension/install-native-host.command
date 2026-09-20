#!/bin/sh
# Install the Paper Capture Tool native-messaging bridge.
#
#   double-click                              # Finder: prompts "Press Return" at the end
#   sh install-native-host.command --quiet    # scripted (install-skills.sh / capture-doctor)
#
# Writes ~/Library/Application Support/Paper Capture Tool/{host.mjs,semantics.mjs,run-paper-capture-host}
# and a NativeMessagingHosts manifest for EVERY Chromium-family browser found on
# this Mac (Chrome, Brave, Chromium, Edge, Arc). Finder launches with a bare PATH,
# so node is looked up in the usual install spots, not just `command -v`.
# A missing manifest, a dead node path, or a stale host.mjs all surface in the
# side panel as OFFLINE (web2html Pitfall #217).
set -eu

EXTENSION_ID="ecicfkapebfbpdgfaiadgfcghkpgmbem"
HOST_NAME="com.kreativepro.paper_capture"
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
QUIET=""
for arg in "$@"; do
  case "$arg" in
    --quiet|-q) QUIET=1 ;;
  esac
done

fail() {
  printf '%s\n' "$1" >&2
  if [ -z "$QUIET" ]; then printf '%s' "Press Return to close…"; read _unused; fi
  exit 1
}

# --- locate node -----------------------------------------------------------
# Order: explicit override, PATH, then common install locations. Finder's PATH
# is /usr/bin:/bin:/usr/sbin:/sbin, which has none of these.
find_node() {
  if [ -n "${PAPER_CAPTURE_NODE:-}" ] && [ -x "${PAPER_CAPTURE_NODE}" ]; then
    printf '%s' "$PAPER_CAPTURE_NODE"; return 0
  fi
  cand=$(command -v node 2>/dev/null || true)
  if [ -n "$cand" ]; then printf '%s' "$cand"; return 0; fi
  for cand in \
    /opt/homebrew/bin/node \
    /usr/local/bin/node \
    /opt/local/bin/node \
    "$HOME/.volta/bin/node" \
    "$HOME/.local/bin/node" \
    "$HOME/.hermes/node/bin/node" \
    /usr/bin/node; do
    if [ -x "$cand" ]; then printf '%s' "$cand"; return 0; fi
  done
  # nvm / fnm / n: newest installed version
  for base in "$HOME/.nvm/versions/node" "$HOME/.local/share/fnm/node-versions" "$HOME/n/n/versions/node" /usr/local/n/versions/node; do
    if [ -d "$base" ]; then
      cand=$(ls -1 "$base" 2>/dev/null | sort -t. -k1,1n -k2,2n -k3,3n | tail -n 1)
      for sub in "bin/node" "installation/bin/node"; do
        if [ -n "$cand" ] && [ -x "$base/$cand/$sub" ]; then printf '%s' "$base/$cand/$sub"; return 0; fi
      done
    fi
  done
  return 1
}

NODE_BIN=$(find_node || true)
if [ -z "$NODE_BIN" ]; then
  fail "Node.js 18 or newer is required for the Paper bridge. Install Node.js (brew install node), then run this installer again. Set PAPER_CAPTURE_NODE=/path/to/node to point at a specific binary."
fi
# Resolve symlinks so the launcher does not die when ~/.local/bin/node is repointed.
RESOLVED=$("$NODE_BIN" -p "require('fs').realpathSync(process.execPath)" 2>/dev/null || true)
if [ -n "$RESOLVED" ] && [ -x "$RESOLVED" ]; then NODE_BIN="$RESOLVED"; fi

NODE_MAJOR=$("$NODE_BIN" -p "process.versions.node.split('.')[0]")
if [ "$NODE_MAJOR" -lt 18 ]; then
  fail "Node.js 18 or newer is required (found $("$NODE_BIN" -v) at $NODE_BIN)."
fi

# --- bridge files ------------------------------------------------------------
INSTALL_DIR="$HOME/Library/Application Support/Paper Capture Tool"
HOST_COPY="$INSTALL_DIR/host.mjs"
SEMANTICS_COPY="$INSTALL_DIR/semantics.mjs"
LAUNCHER="$INSTALL_DIR/run-paper-capture-host"

mkdir -p "$INSTALL_DIR"
cp "$SCRIPT_DIR/bridge/host.mjs" "$HOST_COPY"
cp "$SCRIPT_DIR/bridge/semantics.mjs" "$SEMANTICS_COPY"
chmod 700 "$HOST_COPY" "$SEMANTICS_COPY"

{
  printf '%s\n' '#!/bin/sh'
  printf 'exec "%s" "%s"\n' "$NODE_BIN" "$HOST_COPY"
} > "$LAUNCHER"
chmod 700 "$LAUNCHER"

# --- one manifest per installed Chromium-family browser ----------------------
SUPPORT="$HOME/Library/Application Support"
written=0
emit_manifest() {
  dir="$1"
  mkdir -p "$dir"
  {
    printf '%s\n' '{'
    printf '  "name": "%s",\n' "$HOST_NAME"
    printf '%s\n' '  "description": "Paper Capture Tool local bridge",'
    printf '  "path": "%s",\n' "$LAUNCHER"
    printf '%s\n' '  "type": "stdio",'
    printf '  "allowed_origins": ["chrome-extension://%s/"]\n' "$EXTENSION_ID"
    printf '%s\n' '}'
  } > "$dir/$HOST_NAME.json"
}
write_manifest() {
  app="$1"; rel="$2"
  if [ ! -d "/Applications/$app.app" ] && [ ! -d "$HOME/Applications/$app.app" ]; then return 0; fi
  emit_manifest "$SUPPORT/$rel"
  printf '  %s -> %s\n' "$app" "$SUPPORT/$rel/$HOST_NAME.json"
  written=$((written + 1))
}

printf '%s\n' "Native host manifests:"
write_manifest "Google Chrome"  "Google/Chrome/NativeMessagingHosts"
write_manifest "Brave Browser"  "BraveSoftware/Brave-Browser/NativeMessagingHosts"
write_manifest "Chromium"       "Chromium/NativeMessagingHosts"
write_manifest "Microsoft Edge" "Microsoft Edge/NativeMessagingHosts"
write_manifest "Arc"            "Arc/User Data/NativeMessagingHosts"

if [ "$written" -eq 0 ]; then
  # No browser found — still write Chrome's so a later Chrome install works.
  emit_manifest "$SUPPORT/Google/Chrome/NativeMessagingHosts"
  printf '  %s\n' "(no Chromium browser found in /Applications — wrote the Chrome manifest anyway)"
fi

# --- smoke test: the launcher must answer PING ---------------------------------
if ! "$NODE_BIN" -e '
const { spawn } = require("child_process");
const p = spawn(process.argv[1], [], { stdio: ["pipe", "pipe", "inherit"] });
const body = Buffer.from(JSON.stringify({ requestId: "install", type: "PING" }));
const head = Buffer.alloc(4); head.writeUInt32LE(body.length, 0);
let out = Buffer.alloc(0);
const t = setTimeout(() => { p.kill(); process.exit(1); }, 5000);
p.stdout.on("data", (d) => {
  out = Buffer.concat([out, d]);
  if (out.length >= 4 && out.length >= 4 + out.readUInt32LE(0)) {
    clearTimeout(t); p.kill();
    process.exit(out.toString("utf8", 4).includes("\"ok\":true") ? 0 : 1);
  }
});
p.stdin.write(Buffer.concat([head, body]));
' "$LAUNCHER"; then
  fail "The bridge launcher did not answer PING. node: $NODE_BIN — check that it runs."
fi

printf '\n%s\n' "✓ Paper Capture Tool bridge installed."
printf '%s\n' "node:         $NODE_BIN"
printf '%s\n' "Extension ID: $EXTENSION_ID"
printf '%s\n' "Fully quit and reopen the browser, open chrome://extensions, turn on Developer mode,"
printf '%s\n' "choose Load unpacked, and select:"
printf '  %s\n' "$SCRIPT_DIR"
if [ -z "$QUIET" ]; then
  printf '\n%s' "Press Return to close…"
  read _unused
fi
