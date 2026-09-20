# Paper Capture Tool · Chrome extension

This is the live **1.3** Capture Tool: a Manifest V3 Chrome extension. It
runs in your normal browser as a side panel and uses a small local bridge
to wait for real Paper write receipts. Use it after **1.2** has written
1600 / 768 / 390 and passed geometry. One session walks Nav → Hover →
Multi → Single → Done and sends navbar and buttons back to Paper.

## Install on macOS

1. Unzip the package somewhere you will keep it.
2. Run the bridge installer. `./scripts/install-skills.sh` in the web2html
   checkout does this for you; standalone, double-click
   `install-native-host.command` (right-click → **Open** if macOS blocks it) or
   `sh install-native-host.command --quiet`. It needs Node.js 18+, looks in
   Homebrew / nvm / volta / `~/.local/bin` as well as `PATH` (Finder launches
   with a bare PATH), pins the resolved binary, writes a native-messaging
   manifest for **every** Chromium browser found (Chrome, Brave, Chromium,
   Edge, Arc), and PINGs the host before reporting success.
   `PAPER_CAPTURE_NODE=/path/to/node` overrides the lookup.
3. Fully quit and reopen the browser.
4. Open `chrome://extensions`.
5. Turn **Developer mode** on.
6. Click **Load unpacked** and select **this** unzipped folder — the folder
   that contains `manifest.json` (`capture-extension/`). Do not select the
   parent `1.3 hover-reel` package. Chrome remembers that path; loading the
   parent (or keeping an old copy after a rename) leaves Record talking
   to a stale inject.
7. If you renamed or moved the folder, click **Remove** on the existing
   Paper Capture Tool card, then **Load unpacked** again. Refresh follows the
   previous path.
8. Pin **Paper Capture Tool** to the Chrome toolbar.

The installable GitHub copy is [paper-bridge](https://github.com/kinw3b/paper-bridge).
Bump `manifest.json` `version` here, copy this folder into that checkout, then
tag **that** repo (`git tag -a 1.2.23`). Chrome Load unpacked should point at
`~/Documents/Extensions/Paper-Bridge`, not this nested `capture-extension/`
path, or the toolbar keeps a stale 1.2.19.

The package has a fixed development extension ID:
`ecicfkapebfbpdgfaiadgfcghkpgmbem`. The installer grants native bridge access
only to that extension ID. Session prefill comes from the source tab URL,
not from a `chrome-extension://` page.

## Run the first test

1. Open Paper Desktop and the Paper file that already contains (or should
   contain) the `Navigation`, `Buttons`, and `Components` frames.
2. `pipeline-progress.py mark <project> --step 1.4 --status active` opens the
   source URL with `?paperFileId=…&projectRoot=…` appended so the side panel
   reads them off the live tab. `pipeline-progress.py open-capture <project>`
   re-opens it.
3. Click the **Paper Capture Tool** toolbar icon. The side panel opens.
4. Paste the Paper file ID and the absolute project folder **only if they
   are empty**. Then click
   **Start capture**. The extension creates missing review frames, but never
   creates a Design Library.
5. In **Navbar + Dropdowns**, leave `Navbar` selected and click **Record**.
   Hover begins on the exact DOM node under the pointer. Press **↑** to climb
   one parent or **↓** to move back toward the original node, then click the
   wrapper you actually want. Auto deliberately selects the first full navbar.
   The serialized component contains only that selected root and its real
   descendants—no synthetic context frame. SVG symbol references and computed
   borders/outlines are preserved for Paper.
6. Wait while Capture Tool opens a short-lived 768 popup, then a 390 popup,
   rematches the desktop Navbar, and sends all three versions to
   `Navigation`. Continue unlocks only after Paper confirms Desktop, Tablet,
   and Mobile. The progress card shows capture/confirmation state and `n/3`;
   the locked button displays its wait, then unlocks automatically at `3/3`.
   A failed width says Retry needed. If Record errors with
   **Receiving end does not exist**, the source tab lost its capture script:
   refresh the page, click **Start capture**, then Record again.
7. If the page has a dropdown, select `Dropdown`:
   - Record the closed state.
   - Open the dropdown normally on the page.
   - For a hover-open menu, keep the pointer on the page and press **R** so the
     menu does not close; then click the open menu wrapper to record state two.
8. Click **Continue** and test Hover, Multi-state, then Single. Nav and Hover
   stay locked to the **1600** desktop lander at zoom 100% (Pitfall #150).
9. Click **Done** on Single. It writes
   `source-site/components/capture-extension-session.json` and
   `human-hover-done.json`, then keeps the panel open.
   Semantic tags come from 1.2 `layer-ids.json`; 2.2.a applies that map.
   Type **Continue** in agent chat when you are ready for Design Library.

## Auto mode

- Navbar: chooses the first visible navigation landmark.
- Hover: walks up to eight unique visible controls with trusted Chrome pointer
  events and skips repeated list/grid patterns.
- Single: chooses the first visible exact object candidate.
- Dropdown and Multi-state remain manual because an extension should not invent
  or guess a component's open state.

## What gets written

- Paper `Navigation`: the selected desktop Navbar, its automatic 768 and 390
  responsive matches, and any dropdown pairs.
- Paper `Buttons`: default/hover pairs.
- Paper `Components`: Multi-state and Single receipts.
- Confirmed-take wrappers and state cells hug the intrinsic serialized content
  size instead of inheriting the review-board width.
- Disk `source-site/components/home/*`: Paper-ready HTML and manifests.
- Disk `source-site/components/human-hover-done.json`: the 1.3 hard-stop receipt.

## Troubleshooting

- **Offline / Native host not found:** run
  `python3 $SKILLS/web2html/scripts/pipeline-progress.py capture-doctor` — it
  names the missing manifest / dead node path / stale host and prints the
  fix. Then rerun `install-native-host.command`, fully quit and reopen the
  browser, and reload the extension. Brave / Edge / Arc each need their own
  manifest; the installer writes all of them.
- **Paper unavailable:** keep Paper Desktop open and verify the file ID. The
  default endpoint is `http://127.0.0.1:29979/mcp`.
- **Debugger already attached:** close DevTools on the source tab. Capture Tool
  keeps the debugger attached so the page stays at 1600 CSS pixels. Hover uses
  that same session; 768/390 Navbar capture uses it on short-lived popups.
- **1600 lock failed:** reload this unpacked folder, rerun
  `install-native-host.command`, then Start capture again. Do not pinch-zoom
  or leave Chrome at 80%/125%.
- **File URL:** enable **Allow access to file URLs** on the extension details
  page if the source is a local `file://` page.
- **Red failed take:** no green check was issued. Fix Paper or the bridge and
  click **Retry**; the take ID is idempotent.

To remove the bridge, double-click `uninstall-native-host.command`, then remove
the unpacked extension from `chrome://extensions`.
