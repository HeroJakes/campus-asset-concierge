const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const vm = require('node:vm');

function setup(storage = new Map(), username = 'borrower-a') {
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
    querySelectorAll() { return this.children.filter(child => child.className?.includes('assistant-row')); }
  }
  const nodes = Object.fromEntries(['assistant-log', 'assistant-form', 'assistant-input', 'assistant-send', 'assistant-clear', 'assistant-history-status'].map(id => [id, new Node()]));
  nodes['assistant-log'].dataset.username = username;
  const quick = new Node('button'); quick.dataset.prompt = 'Check my pickups';
  const clock = new Node('time'); clock.textContent = '2026-11-07 · 11:01'; clock.dateTime = '2026-11-07T11:01:00+08:00';
  const requests = [];
  const context = vm.createContext({
    localStorage: { getItem: key => storage.get(key) || null, setItem: (key, value) => storage.set(key, value) },
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

test('thinking has three animated dots and model bold stays safe', async () => {
  const ui = setup(); ui.submit('Hello');
  const dots = ui.all().find(node => node.className === 'assistant-typing');
  assert.equal(dots.children.length, 3);
  assert.equal(dots['aria-label'], 'MiMi is thinking');
  ui.requests[0].resolve({ ok: true, json: async () => ({ reply: '**Projector A** <img src=x onerror=alert(1)>', offer: null }) });
  await flush();
  assert.ok(ui.all().some(node => node.tag === 'strong' && node.textContent === 'Projector A'));
  assert.equal(ui.all().some(node => node.tag === 'img'), false);
});

test('history survives reload, stays per borrower, and clear removes saved context', async () => {
  const storage = new Map(); const ui = setup(storage);
  ui.submit('Book a kit');
  ui.requests[0].resolve({ ok: true, json: async () => ({ reply: 'What time?', offer: null }) });
  await flush();
  const restored = setup(storage);
  assert.ok(restored.nodes['assistant-log'].textContent.includes('What time?'));
  assert.equal(setup(storage, 'borrower-b').nodes['assistant-log'].textContent, '');
  restored.submit('At noon');
  assert.equal(JSON.parse(restored.requests[0].options.body).messages.length, 3);
  restored.requests[0].resolve({ ok: true, json: async () => ({ reply: 'Okay', offer: null }) });
  await flush();
  restored.nodes['assistant-clear'].listeners.click();
  assert.equal(setup(storage).nodes['assistant-log'].textContent, '');
});

test('restored offers cannot submit an old confirmation', async () => {
  const storage = new Map(); const ui = setup(storage); ui.submit('Book');
  ui.requests[0].resolve({ ok: true, json: async () => ({ reply: 'Here is an offer', offer: { id: 'old', asset_id: 'projector-b' } }) });
  await flush();
  const restored = setup(storage);
  assert.ok(restored.nodes['assistant-log'].textContent.includes('Ask for a fresh offer'));
  assert.equal(restored.all().some(node => node.tag === 'button' && node.textContent.includes('Confirm booking')), false);
});

test('history storage failure does not stop sending', () => {
  const ui = setup({ get() { throw new Error('blocked'); }, set() { throw new Error('blocked'); } });
  ui.submit('Hello');
  assert.equal(ui.requests.length, 1);
  assert.ok(ui.nodes['assistant-history-status'].textContent.includes('could not be saved'));
});

test('saved conversations stay within the API context limit', () => {
  const storage = new Map();
  storage.set('campus-assistant-v1:borrower-a', JSON.stringify(Array.from({ length: 100 }, (_, i) => ({
    role: i % 2 ? 'model' : 'user', text: 'x'.repeat(3000),
  }))));
  const ui = setup(storage); ui.submit('Continue');
  const messages = JSON.parse(ui.requests[0].options.body).messages;
  assert.ok(messages.length <= 40);
  assert.equal(messages[0].role, 'user');
  assert.ok(messages.every(message => message.text.length <= 2000));
});
