// Append one Hover take onto FRAME Hover States (stack below last row).
// Never wipe siblings already on that board.

import { parksOnHoverStates } from "./component-state-utils.mjs";
import { parkOneHoverOnBoard } from "./park-capture-boards.mjs";

export async function parkOneHoverOnSource(opts = {}) {
  const { kind = "buttons", captureMethod = "", type } = opts;
  if (!parksOnHoverStates(kind, { captureMethod, type })) {
    return { written: false, reason: "not hover" };
  }
  return parkOneHoverOnBoard(opts);
}
