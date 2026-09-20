// Small, dependency-free image geometry helpers for Paper source-shot frames.
//
// Paper can parse a data-URI image before its intrinsic dimensions are ready.
// `height:auto` then produces a real layer whose measured height is 0.  Stage P
// knows the bytes it is embedding, so read the dimensions before writing and
// pin both the image and its containing frame to explicit pixel geometry.

const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
const JPEG_SOF = new Set([
  0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7,
  0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf,
]);

const finitePositive = (value) => Number.isFinite(value) && value > 0;

/** Return intrinsic pixel dimensions for PNG/JPEG buffers, or null. */
export function readImageDimensions(buffer) {
  if (!Buffer.isBuffer(buffer) || buffer.length < 24) return null;

  if (buffer.subarray(0, 8).equals(PNG_SIGNATURE) && buffer.length >= 24) {
    const width = buffer.readUInt32BE(16);
    const height = buffer.readUInt32BE(20);
    return finitePositive(width) && finitePositive(height) ? { width, height, format: "png" } : null;
  }

  if (buffer[0] !== 0xff || buffer[1] !== 0xd8) return null;
  let offset = 2;
  while (offset + 3 < buffer.length) {
    if (buffer[offset] !== 0xff) {
      offset++;
      continue;
    }
    while (offset < buffer.length && buffer[offset] === 0xff) offset++;
    if (offset >= buffer.length) break;
    const marker = buffer[offset++];
    if (marker === 0xd9 || marker === 0xda) break;
    if (marker === 0x01 || (marker >= 0xd0 && marker <= 0xd8)) continue;
    if (offset + 1 >= buffer.length) break;
    const length = buffer.readUInt16BE(offset);
    if (length < 2 || offset + length > buffer.length) break;
    if (JPEG_SOF.has(marker) && length >= 7) {
      const height = buffer.readUInt16BE(offset + 3);
      const width = buffer.readUInt16BE(offset + 5);
      return finitePositive(width) && finitePositive(height) ? { width, height, format: "jpeg" } : null;
    }
    offset += length;
  }
  return null;
}
/** Scale an image to a Paper frame width while preserving its source ratio. */
export function scaledImageDimensions(buffer, targetWidth) {
  const intrinsic = readImageDimensions(buffer);
  if (!intrinsic || !finitePositive(targetWidth)) return null;
  return {
    ...intrinsic,
    displayWidth: Math.round(targetWidth),
    displayHeight: Math.max(1, Math.round(targetWidth * intrinsic.height / intrinsic.width)),
  };
}
