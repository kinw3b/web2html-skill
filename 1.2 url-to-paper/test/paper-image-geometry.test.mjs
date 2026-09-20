import test from 'node:test';
import assert from 'node:assert/strict';
import { readImageDimensions, scaledImageDimensions } from '../scripts/paper-image-geometry.mjs';

test('reads PNG dimensions and produces explicit Paper geometry', () => {
  const png = Buffer.alloc(24);
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]).copy(png, 0);
  png.writeUInt32BE(1600, 16);
  png.writeUInt32BE(9404, 20);
  assert.deepEqual(readImageDimensions(png), { width: 1600, height: 9404, format: 'png' });
  assert.deepEqual(scaledImageDimensions(png, 800), {
    width: 1600, height: 9404, format: 'png', displayWidth: 800, displayHeight: 4702,
  });
});

test('reads JPEG SOF dimensions', () => {
  const jpeg = Buffer.from([
    0xff, 0xd8,
    0xff, 0xc0, 0x00, 0x11, 0x08,
    0x03, 0x20, 0x06, 0x40,
    0x01, 0x01, 0x11, 0x00, 0x02, 0x11, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  ]);
  assert.deepEqual(readImageDimensions(jpeg), { width: 1600, height: 800, format: 'jpeg' });
});

test('refuses unknown image bytes instead of allowing height:auto to collapse', () => {
  assert.equal(readImageDimensions(Buffer.from('not an image')), null);
  assert.equal(scaledImageDimensions(Buffer.from('not an image'), 1600), null);
});
