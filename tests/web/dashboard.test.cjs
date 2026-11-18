const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const page = fs.readFileSync(path.join(__dirname, '../../apps/web/index.html'), 'utf8');
const script = page.match(/<script>([\s\S]*)<\/script>/)[1];

function dashboard(fetch) {
  const elements = new Map();
  const listeners = new Map();
  const document = {
    getElementById(id) {
      if (!elements.has(id)) {
        const autoOption = {};
        elements.set(id, {
          autoOption,
          textContent: '',
          innerHTML: '',
          style: {},
          classList: { add() {}, remove() {} },
          querySelector: () => autoOption,
        });
      }
      return elements.get(id);
    },
    addEventListener(name, listener) { listeners.set(name, listener); },
  };
  const context = vm.createContext({
    document,
    window: { addEventListener() {}, confirm: () => true },
    setTimeout() {},
    fetch,
    URL,
  });
  vm.runInContext(script, context);
  return { context, get: id => document.getElementById(id), listeners };
}

function overview(tiktok = {}) {
  return {
    platforms: { instagram: { mode: 'DRAFT' }, tiktok: { mode: 'DRAFT', badge: 'Awaiting review' } },
    accounts: { tiktok: { connected: false, pilot_verified: false, ...tiktok } },
    emergency_stop: { active: false },
    kpis: {},
    budget: {
      total_spend_gbp: 0, hosting_fixed_gbp: 0, storage_fixed_gbp: 0, ai_variable_spend_gbp: 0,
      ai_monthly_subcap_gbp: 5, hard_monthly_ceiling_gbp: 30, estimated_cost_per_1000_replies_gbp: 0,
    },
    health: { webhook_latency_ms: {}, safety_invariants: {} },
  };
}

test('provider failures remain visible without fabricating connection or sync results', async () => {
  const calls = [];
  const ui = dashboard(async (endpoint, request) => {
    calls.push([endpoint, request]);
    if (endpoint === '/api/v1/overview') return { status: 200, ok: true, json: async () => overview() };
    return { status: 502, ok: false, json: async () => ({ error: 'TikTok provider unavailable' }) };
  });
  assert.equal(await ui.context.fetchOverview(), true);
  assert.equal(ui.get('ttSyncBtn').disabled, true);
  assert.equal(ui.get('ttModeSelect').autoOption.disabled, true);
  await ui.context.runTikTokAction('verify');
  assert.equal(calls[1][0], '/api/v1/tiktok/verify');
  assert.equal(calls[1][1].body, '{}');
  assert.equal(calls[1][1].cache, 'no-store');
  assert.equal(ui.get('toast').textContent, 'TikTok provider unavailable');
  assert.match(ui.get('ttActionResult').textContent, /could not be confirmed/);
  assert.equal(ui.get('ttSyncBtn').disabled, true);
  assert.equal(ui.get('tiktokPilotCard').hidden, true);
});

test('pilot display is read-only until an owner selects a stored draft, then enables SAFE_AUTO from server proof', async () => {
  const endpoints = [];
  const candidate = { video_id: '123', comment_id: '456', reply_candidate: 'I liked this too <3' };
  const ui = dashboard(async (endpoint, request) => {
    endpoints.push(endpoint);
    if (endpoint === '/api/v1/overview') return { status: 200, ok: true, json: async () => overview() };
    if (endpoint === '/api/v1/tiktok/verify') return {
      status: 200, ok: true, json: async () => ({
        overview: overview({ connected: true, can_request_pilot: true, pilot_candidates: [candidate] }),
      }),
    };
    assert.equal(endpoint, '/api/v1/tiktok/pilot');
    assert.deepEqual(JSON.parse(request.body), { video_id: '123', comment_id: '456' });
    return {
      status: 200, ok: true, json: async () => ({
        overview: overview({ connected: true, pilot_verified: true, can_request_pilot: true, auto_replies_sent: 1 }),
      }),
    };
  });
  await ui.context.fetchOverview();
  await ui.context.runTikTokAction('verify');
  assert.deepEqual(endpoints, ['/api/v1/overview', '/api/v1/tiktok/verify']);
  assert.match(ui.get('tiktokPilotCandidates').innerHTML, /I liked this too &lt;3/);
  assert.equal(ui.get('tiktokPilotCard').hidden, false);
  assert.equal(ui.get('ttModeSelect').autoOption.disabled, true);
  await ui.context.runTikTokAction('pilot', { video_id: '123', comment_id: '456' });
  assert.equal(ui.get('tiktokPilotCard').hidden, true);
  assert.equal(ui.get('ttModeSelect').autoOption.disabled, false);
  assert.match(ui.get('ttActionResult').textContent, /confirmed the pilot reply/);
});

test('social content stays text and copied drafts do not supply inline handlers', async () => {
  const unsafe = "'><img src=x onerror=alert(1)>";
  const state = overview();
  state.comments = [{
    platform: 'tiktok', commenter_pseudonym: 'Viewer', post_id: '123', category: 'question',
    text_redacted: unsafe, reply_candidate: unsafe, response_status: 'SENT', audit_trail: [unsafe],
  }];
  state.creator_notifications = [{
    platform: 'tiktok', creator_display_name: unsafe, post_url: 'javascript:alert(1)',
    post_title: unsafe, draft_suggestions: [unsafe],
  }];
  const ui = dashboard(async () => ({ status: 200, ok: true, json: async () => state }));
  await ui.context.fetchOverview();
  const inbox = ui.get('commentsListContainer').innerHTML;
  const friends = ui.get('friendsNotificationsContainer').innerHTML;
  assert.match(inbox, /Posting unverified/);
  for (const html of [inbox, friends]) {
    assert.doesNotMatch(html, /<img|javascript:|onclick=/);
    assert.match(html, /&lt;img/);
    assert.match(html, /data-copy=/);
  }
  assert.equal(ui.context.platformPostUrl('https://www.tiktok.com/@creator/video/1', 'tiktok'), 'https://www.tiktok.com/@creator/video/1');
  assert.equal(ui.context.platformPostUrl('https://tiktok.com.example/@creator/video/1', 'tiktok'), '');
});
