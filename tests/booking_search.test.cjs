const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const vm = require('node:vm');
const source = readFileSync('src/campus_asset_concierge/static/locker_bookings.js', 'utf8');

function harness() {
  const nodes = {};
  const errors = [];
  const requests = [];
  let timer;
  let address;
  function node(key, textContent = '') {
    return {
      textContent, value: '', listeners: {}, attributes: {},
      addEventListener(type, callback) { this.listeners[type] = callback; },
      setAttribute(key, value) { this.attributes[key] = value; },
      removeAttribute(key) { delete this.attributes[key]; },
      replaceWith(value) { nodes[key] = value; },
    };
  }
  for (const key of ['booking-results', 'booking-list-title', 'booking-search-feedback',
    'booking-search', 'booking-status', '.booking-stats', '.booking-search', '.refresh-button']) {
    nodes[key] = node(key);
  }
  nodes['.booking-search'].action = 'http://localhost/locker/bookings';
  nodes['booking-status'].value = 'all';
  vm.runInNewContext(source, {
    document: { getElementById: key => nodes[key], querySelector: key => nodes[key] },
    setTimeout(callback) { timer = callback; }, clearTimeout() { timer = null; },
    AbortController, URL, URLSearchParams,
    FormData: class {
      *[Symbol.iterator]() {
        yield ['q', nodes['booking-search'].value];
        yield ['status', nodes['booking-status'].value];
      }
    },
    fetch(url, options) {
      return new Promise((resolve, reject) => requests.push({ url, options, resolve, reject }));
    },
    DOMParser: class {
      parseFromString(title) {
        return {
          getElementById: key => node(key, key === 'booking-list-title' ? title : ''),
          querySelector: key => node(key),
        };
      }
    },
    history: { replaceState(_state, _unused, url) { address = url; } },
    errorBox: { hidden: true }, showError: message => errors.push(message),
  });
  return {
    nodes, requests, errors, get address() { return address; },
    type(value, isComposing = false) {
      nodes['booking-search'].value = value;
      nodes['booking-search'].listeners.input({ isComposing });
    },
    flush() { const callback = timer; timer = null; return callback?.(); },
  };
}

test('typing is debounced, updates rows and URL, and preserves the search field', async () => {
  const app = harness();
  const input = app.nodes['booking-search'];
  app.type('p'); app.type('projector');
  assert.equal(app.requests.length, 0);
  const done = app.flush();
  assert.equal(app.requests.length, 1);
  assert.equal(app.requests[0].url.searchParams.get('q'), 'projector');
  app.requests[0].resolve({ ok: true, text: async () => 'All bookings (2)' });
  await done;
  assert.equal(app.nodes['booking-search'], input);
  assert.equal(input.value, 'projector');
  assert.equal(app.nodes['booking-search-feedback'].textContent, 'All bookings (2)');
  assert.equal(app.address.searchParams.get('q'), 'projector');
});

test('an older response cannot replace newer search results', async () => {
  const app = harness();
  app.type('old'); const old = app.flush();
  app.type('new'); const latest = app.flush();
  assert.equal(app.requests[0].options.signal.aborted, true);
  app.requests[1].resolve({ ok: true, text: async () => 'Latest results' });
  await latest;
  app.requests[0].resolve({ ok: true, text: async () => 'Stale results' });
  await old;
  assert.equal(app.nodes['booking-list-title'].textContent, 'Latest results');
});

test('failed searches retain the previous rows and show an error', async () => {
  const app = harness();
  const previous = app.nodes['booking-results'];
  app.type('projector'); const done = app.flush();
  app.requests[0].resolve({ ok: false });
  await done;
  assert.equal(app.nodes['booking-results'], previous);
  assert.equal(previous.attributes['aria-busy'], undefined);
  assert.equal(app.errors.length, 1);
});

test('status changes search automatically and composition waits until typing finishes', async () => {
  const app = harness();
  app.type('unfinished', true);
  assert.equal(app.flush(), undefined);
  app.nodes['booking-status'].value = 'completed';
  app.nodes['booking-status'].listeners.change();
  const done = app.flush();
  assert.equal(app.requests[0].url.searchParams.get('status'), 'completed');
  app.requests[0].resolve({ ok: true, text: async () => 'Completed bookings (0)' });
  await done;
});

test('new booking rows use the shared load and dialog actions', () => {
  const clicks = [];
  const requests = [];
  let opened = false;
  const dialog = {
    querySelector: () => ({ hidden: false }), showModal() { opened = true; },
  };
  vm.runInNewContext(readFileSync('src/campus_asset_concierge/static/locker.js', 'utf8'), {
    document: {
      getElementById: key => key === 'sidebar-toggle' ? null : key === 'new-dialog' ? dialog : { hidden: true },
      querySelector: () => null, querySelectorAll: () => [],
      addEventListener(type, callback) { if (type === 'click') clicks.push(callback); },
    },
    fetch(url) { requests.push(url); return new Promise(() => {}); },
  });
  const loadButton = { dataset: { post: '/reservations/new/load' }, disabled: false };
  const viewButton = { dataset: { openDialog: 'new-dialog' } };
  for (const callback of clicks) {
    callback({ target: { closest: selector => selector === '[data-post]' ? loadButton : null } });
    callback({ target: { closest: selector => selector === '[data-open-dialog]' ? viewButton : null } });
  }
  assert.deepEqual(requests, ['/reservations/new/load']);
  assert.equal(opened, true);
});
