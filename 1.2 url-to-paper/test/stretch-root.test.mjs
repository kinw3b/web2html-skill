import test from 'node:test';
import assert from 'node:assert/strict';
import * as stretchRoot from '../scripts/stretch-root.mjs';

test('stretch-root can be imported without contacting Paper', async () => {
  process.env.PAPER_MCP = 'http://127.0.0.1:1/mcp';
  await assert.doesNotReject(
    import('../scripts/stretch-root.mjs'),
  );
});

test('true top-level full-bleed section roots keep width 100%', () => {
  assert.equal(typeof stretchRoot.stretchStylesForNode, 'function');
  assert.deepEqual(stretchRoot.stretchStylesForNode({
    isSectionRoot: true,
    measuredWidth: 1600,
    rootWidth: 1600,
  }), { width: '100%' });
});

test('nested full-bleed children use parent-aware Fill styles', () => {
  assert.deepEqual(stretchRoot.stretchStylesForNode({
    parentStyle: { display: 'flex', flexDirection: 'row' },
    childStyle: {},
    measuredWidth: 1600,
    rootWidth: 1600,
  }), { flexGrow: '1' });
  assert.deepEqual(stretchRoot.stretchStylesForNode({
    parentStyle: { display: 'flex', flexDirection: 'column' },
    childStyle: {},
    measuredWidth: 1600,
    rootWidth: 1600,
  }), { alignSelf: 'stretch' });
});

test('site containers keep max width and stay centered', () => {
  const want = { width: '100%', maxWidth: '1280px', alignSelf: 'center' };
  assert.deepEqual(stretchRoot.stretchStylesForNode({
    parentStyle: { display: 'flex', flexDirection: 'row' },
    childStyle: {},
    measuredWidth: 1280,
    rootWidth: 1600,
    siblingCount: 1,
  }), want);
  assert.deepEqual(stretchRoot.stretchStylesForNode({
    parentStyle: { display: 'flex', flexDirection: 'column' },
    childStyle: {},
    measuredWidth: 1320,
    rootWidth: 1600,
    siblingCount: 1,
  }), { width: '100%', maxWidth: '1320px', alignSelf: 'center' });
});

test('nested hugged controls retain intrinsic sizing', () => {
  assert.deepEqual(stretchRoot.stretchStylesForNode({
    parentStyle: { display: 'flex', flexDirection: 'row' },
    childStyle: { width: 'fit-content', flexGrow: '0' },
    measuredWidth: 1280,
    rootWidth: 1600,
    siblingCount: 1,
  }), {});
});
