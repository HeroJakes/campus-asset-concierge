const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const vm = require('node:vm');

function setup() {
  class Node {
    constructor(tag = 'div') { this.tag = tag; this.children = []; this.listeners = {}; this.style = {}; this.dataset = {}; this.value = ''; this.disabled = false; }
    set textContent(value) { this.text = value; this.children = []; }
    get textContent() { return (this.text || '') + this.children.map(child => child.textContent).join(''); }
    appendChild(child) { child.parent = this; this.children.push(child); return child; }
    addEventListener(type, handler) { this.listeners[type] = handler; }
    setAttribute(name, value) { this[name] = value; }
    focus() { this.focused = true; }
    remove() { this.parent.children = this.parent.children.filter(child => child !== this); }
    closest() { return this.className?.includes('assistant-row') ? this : this.parent.closest(); }
  }
  const nodes = Object.fromEntries(['assistant-log', 'assistant-form', 'assistant-input', 'assistant-send'].map(id => [id, new Node()]));
  const quick = new Node('button'); quick.dataset.prompt = 'Check my pickups';
  const clock = new Node('time'); clock.textContent = '2026-11-07 · 11:01'; clock.dateTime = '2026-11-07T11:01:00+08:00';
  const requests = [];
  const context = vm.createContext({
    document: {
      getElementById: id => nodes[id] || { content: { cloneNode: () => new Node('svg') } },
      createElement: tag => new Node(tag), querySelector: () => clock,
      querySelectorAll: () => [quick],
    },
    fetch: (url, options) => new Promise((resolve, reject) => requests.push({ url, options, resolve, reject })),
  });
  vm.runInContext(readFileSync('src/campus_asset_concierge/static/locker_assistant.js', 'utf8'), context);
  const all = (node = nodes['assistant-log']) => [node, ...node.children.flatMap(child => all(child))];
  return { nodes, quick, requests, all,
    submit(text) { nodes['assistant-input'].value = text; nodes['assistant-form'].listeners.submit({ preventDefault() {} }); },
    offer(data) { context.fixture = data; vm.runInContext('addOfferCard(fixture)', context); },
  };
}
const flush = () => new Promise(resolve => setImmediate(resolve));

test('quick actions fill the composer without sending a request', () => {
  const ui = setup(); ui.quick.listeners.click();
  assert.equal(ui.nodes['assistant-input'].value, 'Check my pickups');
  assert.equal(ui.nodes['assistant-input'].focused, true);
  assert.equal(ui.requests.length, 0);
});

test('chat waits for a reply, prevents duplicate sends, and renders text safely', async () => {
  const ui = setup(); ui.submit('Book a kit'); ui.submit('Duplicate');
  assert.equal(ui.requests.length, 1);
  assert.equal(ui.requests[0].url, '/assistant/chat');
  ui.requests[0].resolve({ ok: true, json: async () => ({ reply: '<script>example</script>', offer: null }) });
  await flush();
  assert.equal(ui.nodes['assistant-send'].disabled, false);
  assert.ok(ui.nodes['assistant-log'].textContent.includes('<script>example</script>'));
  assert.equal(ui.all().some(node => node.tag === 'script'), false);
  assert.ok(ui.all().some(node => node.tag === 'time' && node.textContent === '11:01'));
  assert.equal(ui.all().some(node => node.className === 'assistant-typing'), false);
});

test('offer confirmation stays human-driven and can retry after a rejected confirmation', async () => {
  const ui = setup();
  ui.offer({ id: 'offer/1', asset_id: 'projector-b', pickup_location: 'Campus Loan Desk', pickup_at: '2026-11-07T14:00', due_at: '2026-11-07T16:00' });
  const confirm = ui.all().find(node => node.tag === 'button' && node.textContent.includes('Confirm booking'));
  const change = ui.all().find(node => node.textContent === 'Change request');
  change.listeners.click();
  assert.ok(ui.nodes['assistant-input'].value.includes('change my request'));
  assert.equal(ui.requests.length, 0);
  let click = confirm.listeners.click();
  assert.equal(ui.requests[0].url, '/reservation-offers/offer%2F1/confirm');
  ui.requests[0].resolve({ ok: false, json: async () => ({ detail: 'Offer expired' }) }); await click;
  assert.equal(confirm.disabled, false);
  assert.ok(ui.nodes['assistant-log'].textContent.includes('Offer expired'));
  click = confirm.listeners.click(); ui.requests[1].resolve({ ok: true }); await click;
  assert.ok(ui.nodes['assistant-log'].textContent.includes('Booked ✓'));
  assert.ok(ui.all().some(node => node.tag === 'a' && node.href === '/locker'));
  assert.equal(ui.all().includes(confirm), false);
  assert.equal(ui.all().includes(change), false);
});

test('network failure removes typing and allows the next message', async () => {
  const ui = setup(); ui.submit('Hello'); ui.requests[0].reject(new Error('offline')); await flush();
  assert.ok(ui.nodes['assistant-log'].textContent.includes('Network error'));
  assert.equal(ui.all().some(node => node.className === 'assistant-typing'), false);
  ui.submit('Try again'); assert.equal(ui.requests.length, 2);
  ui.requests[1].resolve({ ok: true, json: async () => ({ reply: 'Hello', offer: null }) }); await flush();
  assert.equal(ui.nodes['assistant-send'].disabled, false);
});
