const { strict: assert } = require('node:assert');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const { test } = require('node:test');
const vm = require('node:vm');

const webRoot = join(__dirname, '..', '..', 'apps', 'web');
const source = readFileSync(join(webRoot, 'sw.js'), 'utf8');

function startWorker({ network = async () => new Response('online'), oldKeys = [] } = {}) {
  const registrations = new Map();
  const cached = new Map();
  const deleted = [];
  const register = (type, handler) => registrations.set(type, handler);
  const origin = 'https://ann.example';
  const fallback = new Response('offline');
  let claiming = false;

  vm.runInNewContext(source, {
    URL,
    Response,
    fetch: network,
    caches: {
      open: async () => ({
        addAll: async (paths) => {
          for (const path of paths) cached.set(path, fallback);
        },
        match: async (path) => cached.get(path),
      }),
      keys: async () => oldKeys,
      delete: async (key) => deleted.push(key),
    },
    self: {
      addEventListener: register,
      location: { origin },
      clients: { claim: async () => { claiming = true; } },
      skipWaiting: async () => {},
    },
  });

  const lifecycle = (type) => new Promise((resolve) => {
    registrations.get(type)({ waitUntil: resolve });
  });
  function request(path, { method = 'GET', mode = 'navigate', from = origin } = {}) {
    let response;
    registrations.get('fetch')({
      request: { url: new URL(path, from).href, method, mode },
      respondWith: (result) => { response = result; },
    });
    return response;
  }
  return { cached, deleted, lifecycle, request, wasClaimed: () => claiming };
}

test('install manifest references correctly sized PNG icons', () => {
  const manifest = JSON.parse(readFileSync(join(webRoot, 'manifest.json'), 'utf8'));
  assert.equal(manifest.display, 'standalone');
  assert.equal(manifest.start_url, '/');
  assert.deepEqual(
    manifest.icons.map(({ sizes, purpose }) => [sizes, purpose]),
    [['192x192', 'any'], ['512x512', 'any'], ['512x512', 'maskable']],
  );
  for (const icon of manifest.icons) {
    assert.equal(icon.type, 'image/png');
    const image = readFileSync(join(webRoot, icon.src), null);
    assert.equal(image.subarray(0, 8).toString('hex'), '89504e470d0a1a0a');
    const [width, height] = icon.sizes.split('x').map(Number);
    assert.equal(image.readUInt32BE(16), width);
    assert.equal(image.readUInt32BE(20), height);
  }
});

test('worker replaces its old cache and only caches public offline files', async () => {
  const worker = startWorker({ oldKeys: ['ann-reveals-ai-manager-v4', 'unrelated-app'] });
  await worker.lifecycle('install');
  await worker.lifecycle('activate');
  assert.deepEqual([...worker.cached.keys()], [
    '/offline.html', '/icons/icon-192.png', '/icons/icon-512.png', '/icons/icon-512-maskable.png',
  ]);
  assert.deepEqual(worker.deleted, ['ann-reveals-ai-manager-v4']);
  assert.equal(worker.wasClaimed(), true);
});

test('offline navigation has a fallback, while APIs and authentication still use the network', async () => {
  const offline = startWorker({ network: async () => { throw new Error('network unavailable'); } });
  await offline.lifecycle('install');
  assert.equal(await (await offline.request('/')).text(), 'offline');
  assert.equal(offline.request('/api/v1/overview'), undefined);
  assert.equal(offline.request('/api/v1/overview', { method: 'POST' }), undefined);
  assert.equal(offline.request('/login'), undefined);
  assert.equal(offline.request('/', { from: 'https://another.example' }), undefined);

  const unauthorized = startWorker({ network: async () => new Response(null, { status: 401 }) });
  await unauthorized.lifecycle('install');
  assert.equal((await unauthorized.request('/')).status, 401);
});
