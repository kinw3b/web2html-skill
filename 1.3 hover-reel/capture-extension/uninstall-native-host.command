#!/bin/sh
# Remove the Paper Capture Tool native-messaging bridge from every Chromium-family
# browser the installer writes to (Chrome, Brave, Chromium, Edge, Arc).
#   sh uninstall-native-host.command --quiet   # no "Press Return"
set -eu

HOST_NAME="com.kreativepro.paper_capture"
INSTALL_DIR="$HOME/Library/Application Support/Paper Capture Tool"
SUPPORT="$HOME/Library/Application Support"
QUIET=""
for arg in "$@"; do
  case "$arg" in
    --quiet|-q) QUIET=1 ;;
  esac
done

for rel in \
  "Google/Chrome/NativeMessagingHosts" \
  "BraveSoftware/Brave-Browser/NativeMessagingHosts" \
  "Chromium/NativeMessagingHosts" \
  "Microsoft Edge/NativeMessagingHosts" \
  "Arc/User Data/NativeMessagingHosts"; do
  m="$SUPPORT/$rel/$HOST_NAME.json"
  if [ -f "$m" ]; then rm -f "$m"; printf '  removed %s\n' "$m"; fi
done
if [ -d "$INSTALL_DIR" ]; then mv "$INSTALL_DIR" "$HOME/.Trash/Paper Capture Tool $(date +%Y%m%d-%H%M%S)"; fi

printf '\n%s\n' "✓ Paper Capture Tool bridge removed."
printf '%s\n' "Remove the unpacked extension from chrome://extensions to finish."
if [ -z "$QUIET" ]; then
  printf '%s' "Press Return to close…"
  read _unused
fi
