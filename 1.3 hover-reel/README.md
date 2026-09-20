# Hover Reel

## Paper Capture Tool extension preview

The installable Capture Tool now lives at `capture-extension/`. It is a
Manifest V3 side-panel extension for the primary Chrome browser, with
**Navbar + Dropdowns first**, followed by **Hover**, **Multi-state**,
and **Single**. Its local native-messaging bridge waits for a Paper
node ID before the panel shows `✓ added to Paper`; **Done** exists only on Single
and writes `source-site/components/human-hover-done.json`. The Done screen
stays open and tells the user to type **Continue** in agent chat when they
are ready for Design Library + Tokens.

Build the developer ZIP with:

```sh
npm run package:extension
```

See `capture-extension/README.md` for the macOS bridge installer and Chrome
Developer mode steps. This extension is the **only** 1.3 capture path.
`capture-session.mjs` is now step **1.2** only: a headless collect of
1600 / 768 / 390 onto Paper, the three review-frame seeds, and the geometry
postflight. It opens no window and mounts no HUD. Navbar
breakpoint rematching is now built in: one confirmed desktop selection produces
inactive 768 and 390 captures and automatically parks all three in Navigation.
Auto Navbar selection now climbs from logo/link/CTA/menu evidence to the
smallest compact common parent; announcement bars and hero/document shells are
rejected before serialization, and the same evidence gate rematches 768/390.
Auto exposes a hover/focus tooltip explaining that it scans the entire page on
all steps. Recording instructions sit above one full-width action button with
short mode-specific copy.
The three-breakpoint progress card stays hidden until that manual desktop
Navbar capture occurs, then follows the background confirmations.
Tags are not a 1.3 rail step. `capture/home-desktop/layer-ids.json` from 1.2
is the pc-id + tag census; 2.2.a applies that map. Capture Tool does not Scan,
write `qa/layer-ids-enrich.json`, or rename `home-desktop`.

`scripts/capture-site-component-states.mjs` is the **automated / CI** hunter for
A/6 state pairs. It refuses to run without `--auto` or `--headless`, because
human-led capture is 1.3 in the extension. When it does run headed, a drawn
pointer travels to each control so you can watch; if the pointer never moves,
the run is broken — fix the overlay rather than capture blind.

## Repo layout

```
1.3 hover-reel/
  capture-extension/      the 1.3 Capture Tool (load this folder unpacked)
    manifest.json
    service-worker.js     capture orchestration + native bridge messaging
    sidepanel/            the Capture Tool panel (UI source of truth)
    content/              targeting, nav breakpoints, capture, session-from-url
    bridge/host.mjs       native messaging host → disk + Paper MCP
    install-native-host.command
  scripts/
    capture-session.mjs   step 1.2: headless collect + board seed + postflight
    run-paper-phase.mjs   the 1.2 collect itself (no window, no HUD; clips 1600/768/390)
    capture-*-states.mjs  automated / CI component hunters
  test/
    validate.mjs          manifest/file/syntax/message-drift checks
    capture-extension*.test.mjs
```

## Testing

```sh
npm test                    # node --test — utils, extension, bridge, targeting
npm run package:extension   # build the developer ZIP for capture-extension/
```

One-time setup for the Playwright-backed capture scripts:

```sh
npm i && npx playwright install chromium
```

## Caveats

- **Close DevTools on the target tab** — only one debugger can attach, and the
  Capture Tool needs it.
- Chrome shows a **"Paper Capture Tool started debugging this browser"** infobar
  during a capture. That is expected and clears when the session ends.
- **Cross-origin iframes are skipped** — capture only sees the top document
  (and open shadow roots).
- **Keep your mouse off the page during a hover take** — real pointer movement
  contaminates the recorded hover state.

## Privacy

Everything stays local. The extension talks only to its own native bridge on
stdio, and the bridge only talks to Paper Desktop on localhost — the installer
and the bridge both refuse a non-localhost Paper endpoint. Captures are written
under the project folder you point the session at. No analytics, no telemetry,
no third-party network calls.
