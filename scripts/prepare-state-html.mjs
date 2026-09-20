// Make a captured default/hover fragment safe for Paper and for the rebuild.
//
// Stage P already runs flattenDecorativeAbs before write_html, so desktop
// lander buttons land as native `border` / `background-image`. A/6 used to
// write the raw serializer tree: Framer hover pills keep a pointer-events
// none overlay for the stroke, and text-swap animations serialize both
// label copies. Those become floating Rectangles and stacked type in Paper,
// then leak into get_jsx.
//
//   prepareStateHtml(html, normalizePaperRootOpts)

import {
  isFaqKind,
  isFluidPairKind,
  normalizePaperRoot,
  prepareFaqStateHtml,
  prepareFluidPairHtml,
} from './component-state-utils.mjs';
import { importSibling } from './skill-paths.mjs';
import { trim } from './trim-styles.mjs';

const { collapseAnimatedLabelStacks, flattenDecorativeAbs, stripAbsolutePaintFill } = await importSibling(
  'url-to-paper',
  'scripts/flatten-decorative-abs.mjs',
);

export function prepareStateHtml(html, opts = {}) {
  const locked = normalizePaperRoot(html, opts);
  const flat = flattenDecorativeAbs(locked);
  const labels = collapseAnimatedLabelStacks(flat.html);
  let out = trim(labels.html);
  if (isFaqKind(opts.kind, opts.mode)) out = prepareFaqStateHtml(out);
  else if (isFluidPairKind(opts.kind, opts.mode)) out = prepareFluidPairHtml(out, opts);
  else if (/^(buttons|footer)$/i.test(String(opts.kind || ''))) {
    const stripped = stripAbsolutePaintFill(out);
    out = stripped.html;
    flat.removed.push(...stripped.removed);
  }
  return {
    html: out,
    removed: flat.removed,
    collapsed: labels.collapsed,
  };
}
