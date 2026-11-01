import assert from 'node:assert/strict';
import { test } from 'node:test';
import { mentioned } from '../src/localize.js';

test('the longest part name in a question wins', () => {
  const e = { parts: [{ id: 'hub', name: 'Rotor hub', aliases: ['rotor'] }, { id: 'tail', name: 'Tail rotor' }, { id: 'mast', name: 'Mast', aliases: [] }] };
  assert.equal(mentioned(e, 'Why does a helicopter need a tail rotor?').id, 'tail');
  assert.equal(mentioned(e, 'What does the rotor do?').id, 'hub');
  assert.equal(mentioned(e, 'hello'), undefined);
});
