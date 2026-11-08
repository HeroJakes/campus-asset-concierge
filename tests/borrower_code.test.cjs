const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const vm = require('node:vm');

function keypad() {
  const listeners = {};
  const cells = { hidden: true, children: Array.from({ length: 6 }, () => ({
    textContent: '', classList: { toggle() {} },
  })) };
  const entry = { classList: { add() {} }, querySelector: () => cells };
  const input = {
    value: '', selectionStart: 0, closest: () => entry,
    addEventListener: (type, handler) => { listeners[type] = handler; },
  };
  vm.runInNewContext(readFileSync('src/campus_asset_concierge/static/locker_borrower.js', 'utf8'), {
    document: { querySelectorAll: () => [input] },
  });
  return { input, cells, listeners, displayed: () => cells.children.map(cell => cell.textContent).join('') };
}

test('code entry keeps leading zeros, shows typing and deletion, and strips non-digits', () => {
  const k = keypad();
  assert.equal(k.cells.hidden, false);
  k.input.value = '0012';
  k.listeners.input();
  assert.equal(k.displayed(), '0012––');
  k.input.value = '001';
  k.listeners.input();
  assert.equal(k.displayed(), '001–––');
  k.input.value = '0a1234567';
  k.listeners.input();
  assert.equal(k.input.value, '012345');
  assert.equal(k.displayed(), '012345');
});

test('pasting a full or spaced code fills all six cells without losing leading zeros', () => {
  const k = keypad();
  let prevented = false;
  k.listeners.paste({ clipboardData: { getData: () => '00 12-34' }, preventDefault() { prevented = true; } });
  assert.equal(prevented, true);
  assert.equal(k.input.value, '001234');
  assert.equal(k.displayed(), '001234');
});
