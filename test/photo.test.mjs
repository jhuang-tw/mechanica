// SAM 3.1 returns every instance of a prompt ("rear wheel" also traced the front one on a real photo, 2026-11-01): one mask per part
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { oneMask } from '../src/photo.js';

const front = { bounds: { left: 302, top: 211, right: 489, bottom: 393 }, confidence: 0.9 }, rear = { bounds: { left: 54, top: 210, right: 216, bottom: 380 }, confidence: 0.8 };
const res = { frame: { w: 512, h: 512 }, masks: [front, rear] };
test('the mask that fits the box Muse gave wins', () => assert.deepEqual(oneMask(res, [0.1, 0.4, 0.43, 0.75]), [rear]));
test('without a box, the most confident mask', () => assert.deepEqual(oneMask(res), [front]));
test('a single mask stays', () => assert.deepEqual(oneMask({ masks: [rear] }, [0.6, 0, 1, 1]), [rear]));
