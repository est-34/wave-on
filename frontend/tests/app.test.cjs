const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../js/app.js'), 'utf8');
function app(fetch) {
  const elements = new Map();
  const element = id => {
    if (!elements.has(id)) elements.set(id, {textContent: '', innerHTML: '', dataset: {}, hidden: true,
      disabled: false, setAttribute() {}, removeAttribute() {},
      classList: {remove() {}, add() {}, toggle() {}},
      open: false, close() { this.open = false; }, showModal() { this.open = true; }, querySelectorAll: () => []});
    return elements.get(id);
  };
  const context = vm.createContext({fetch, document: {getElementById: element, addEventListener() {}, querySelectorAll: () => []}, window: {}});
  vm.runInContext(source, context);
  return {element, run: code => vm.runInContext(code, context)};
}
const state = {counts: {observations: 2, learned_memories: 0, pending_suggestions: 0},
  suggestions: [], memories: [], events: [], threshold: 3,
  candidates: [{context_scope: 'presentation', observation_count: 2}]};
test('dashboard failure remains visible until recovery and displays external 2/3 progress', async () => {
  let failed = true;
  const ui = app(async () => { if (failed) throw Error('offline'); return {ok: true, status: 200, json: async () => state}; });
  await assert.rejects(ui.run('refreshDashboard()'));
  assert.equal(ui.element('dashboardConnection').hidden, false);
  failed = false;
  await ui.run('refreshDashboard()');
  assert.equal(ui.element('dashboardConnection').hidden, true);
  assert.equal(ui.element('learningProgress').textContent, '2/3');
});
test('concurrent refresh shares one request; unchanged suggestions preserve user edits', async () => {
  let calls = 0;
  const ui = app(async () => { calls++; return {ok: true, status: 200, json: async () => state}; });
  await Promise.all([ui.run('refreshDashboard()'), ui.run('refreshDashboard()')]);
  assert.equal(calls, 1);
  ui.element('suggestionContent').innerHTML = 'user selection';
  await ui.run('refreshDashboard()');
  assert.equal(ui.element('suggestionContent').innerHTML, 'user selection');
});
test('FAILED overlay includes error, context and confidence without success status', () => {
  const ui = app();
  ui.run(`showActionOverlay({intent:'NEXT_SLIDE', confidence:0.9, execution:{status:'FAILED', error_message:'blocked'}})`);
  assert.equal(ui.element('actionOverlay').dataset.status, 'failed');
  assert.match(ui.element('overlayConfidence').textContent, /발표.*90%.*blocked/);
});

function syntheticFrame(width, height, blockX) {
  const frame = new Uint8ClampedArray(width * height * 4);
  for (let offset = 3; offset < frame.length; offset += 4) frame[offset] = 255;
  for (let y = 18; y < 34; y++) {
    for (let x = blockX; x < blockX + 16; x++) {
      const offset = ((y * width) + x) * 4;
      frame[offset] = frame[offset + 1] = frame[offset + 2] = 230;
    }
  }
  return frame;
}

test('browser camera motion analysis identifies horizontal movement without retaining frames', () => {
  const ui = app();
  const width = 96;
  const height = 54;
  const motion = ui.run(`detectHorizontalMotion(${JSON.stringify([...syntheticFrame(width, height, 28)])}, ${JSON.stringify([...syntheticFrame(width, height, 32)])}, ${width}, ${height})`);
  assert.equal(motion.direction, 'right');
  assert.equal(ui.run(`detectHorizontalMotion(${JSON.stringify([...syntheticFrame(width, height, 28)])}, ${JSON.stringify([...syntheticFrame(width, height, 28)])}, ${width}, ${height})`), null);
});

test('analyzeMotionField reports the ratio and centroid of the pixels that changed', () => {
  const ui = app();
  const width = 96;
  const height = 54;
  const field = ui.run(`analyzeMotionField(${JSON.stringify([...syntheticFrame(width, height, 28)])}, ${JSON.stringify([...syntheticFrame(width, height, 60)])}, ${width}, ${height}, 20)`);
  assert.ok(field.ratio > 0);
  assert.ok(field.centroidX > 27 && field.centroidX < 76);
  assert.equal(ui.run(`analyzeMotionField(null, ${JSON.stringify([...syntheticFrame(width, height, 28)])}, ${width}, ${height}, 20)`), null);
});

test('camera open-palm tracker needs a sustained still, frame-filling object and re-arms once it leaves', () => {
  const ui = app();
  const filling = { ratio: 0.5 };
  const still = { ratio: 0.01 };
  for (let i = 0; i < 4; i += 1) {
    assert.equal(ui.run(`trackOpenPalm(${JSON.stringify(filling)}, ${JSON.stringify(still)}, ${i})`), null);
  }
  const detected = ui.run(`trackOpenPalm(${JSON.stringify(filling)}, ${JSON.stringify(still)}, 4)`);
  assert.equal(detected.coverage, 0.5);
  // Continuing to hold the palm up must not keep re-firing every frame.
  assert.equal(ui.run(`trackOpenPalm(${JSON.stringify(filling)}, ${JSON.stringify(still)}, 5)`), null);
  // Lowering the hand drops background coverage and re-arms detection.
  ui.run(`trackOpenPalm(${JSON.stringify({ ratio: 0.05 })}, ${JSON.stringify(still)}, 6)`);
  for (let i = 0; i < 4; i += 1) ui.run(`trackOpenPalm(${JSON.stringify(filling)}, ${JSON.stringify(still)}, ${i})`);
  assert.ok(ui.run(`trackOpenPalm(${JSON.stringify(filling)}, ${JSON.stringify(still)}, 4)`));
});

test('camera circle tracker recognizes a full loop of the moving centroid but not a quarter turn', () => {
  const ui = app();
  const pointAt = (fraction) => ({
    ratio: 0.05,
    centroidX: 40 + (Math.cos(fraction * Math.PI * 2) * 10),
    centroidY: 30 + (Math.sin(fraction * Math.PI * 2) * 10),
  });
  let result = null;
  for (let i = 0; i <= 3; i += 1) {
    result = ui.run(`trackCircleMotion(${JSON.stringify(pointAt(i / 12))}, ${i * 100})`);
  }
  assert.equal(result, null);
  for (let i = 4; i <= 11; i += 1) {
    result = ui.run(`trackCircleMotion(${JSON.stringify(pointAt(i / 12))}, ${i * 100})`);
  }
  assert.ok(result);
  assert.equal(result.durationMs, 1100);
});

test('input transaction ignores overlapping operations and releases after failure', async () => {
  const ui = app();
  let finish;
  const pending = new Promise(resolve => { finish = resolve; });
  // Expose a delayed request through the existing request helper.
  const delayed = app(async () => { await pending; return {ok: true, status: 204}; });
  const first = delayed.run('withInputBusy(() => request("/test"))');
  assert.equal(delayed.run('inputBusy'), true);
  assert.equal(await delayed.run('withInputBusy(() => { throw Error("overlap"); })'), undefined);
  finish();
  await first;
  assert.equal(delayed.run('inputBusy'), false);
  await assert.rejects(ui.run('withInputBusy(() => { throw Error("offline"); })'), /offline/);
  assert.equal(ui.run('inputBusy'), false);
  ui.run('demoModeEnabled = false');
  await ui.run('withInputBusy(() => {})');
  assert.equal(ui.element('resetButton').disabled, true);
});

test('camera preserves an observation awaiting a teaching action', async () => {
  let calls = 0;
  const ui = app(async () => { calls++; throw Error('unexpected request'); });
  ui.run('lastObservation = {id: 42}');
  await ui.run('submitCameraGesture("swipe", "left", 430, 1, 1)');
  assert.equal(calls, 0);
  assert.equal(ui.run('lastObservation.id'), 42);
});

test('teaching exposes repeat input, then a pending suggestion hides it', async () => {
  let pending = false;
  const ui = app(async url => ({ok: true, status: 200, json: async () => url.endsWith('/teachings')
    ? {progress_current: pending ? 3 : 1, progress_required: 3, suggestion: pending ? {status: 'PENDING'} : null}
    : state}));
  ui.run('lastObservation = {id: 42}; lastGestureLabel = "오른쪽 손짓"; lastGestureButton = {}');
  await ui.run('teachAction("NEXT_SLIDE", "powerpoint")');
  assert.equal(ui.element('repeatGesture').hidden, false);
  assert.match(ui.element('repeatGesture').textContent, /오른쪽 손짓/);
  assert.equal(ui.run('lastObservation'), null);
  pending = true;
  // Avoid the notification timer in this minimal DOM harness.
  ui.run('showToast = () => {}; lastObservation = {id: 43}');
  await ui.run('teachAction("NEXT_SLIDE", "powerpoint")');
  assert.equal(ui.element('repeatGesture').hidden, true);
});

test('simulation result explicitly says the real app was not controlled', () => {
  const ui = app();
  ui.run('showActionOverlay({intent: "NEXT_SLIDE", confidence: 0.9, execution: {status: "SIMULATED"}})');
  assert.match(ui.element('overlayConfidence').textContent, /시뮬레이션.*실제 앱/);
});

test('approved context shows learned memories instead of zero learning progress', async () => {
  const ui = app(async () => ({ok: true, status: 200, json: async () => ({...state,
    candidates: [], memories: [{gesture_key: 'swipe:right', context_scope: 'presentation', confidence: 0.9, intent: 'NEXT_SLIDE'}]})}));
  await ui.run('refreshDashboard()');
  assert.equal(ui.element('learningProgress').textContent, '기억 1개');
});

test('learning panels appear only when actionable and empty memory links to learning', () => {
  const ui = app();
  ui.run('renderSuggestions([], [])');
  assert.equal(ui.element('suggestionPanel').hidden, true);
  assert.equal(ui.element('confirmationControls').hidden, true);
  ui.run('renderSuggestions([{id: 1, suggested_intent: "NEXT_SLIDE", confidence: 0.9}], [])');
  assert.equal(ui.element('suggestionPanel').hidden, false);
  assert.equal(ui.element('confirmationControls').hidden, false);
  ui.run('renderSuggestions([], []); renderMemories([]); renderInterpretations([])');
  assert.match(ui.element('memoryList').innerHTML, /href="#workspace-task"/);
  assert.match(ui.element('interpretationList').innerHTML, /href="#workspace-task"/);
  ui.run('updateTeachingCard("행동 선택", "설명")');
  assert.equal(ui.element('teachingCard').hidden, false);
});

test('accept and reject suggestions both clear stale teaching and explain the next step', async () => {
  for (const decision of ['ACCEPTED', 'REJECTED']) {
    const ui = app(async url => ({ok: true, status: url.endsWith('/responses') ? 204 : 200, json: async () => state}));
    ui.run('lastObservation = {id: 42}; lastGestureButton = {};');
    await ui.run(`respondSuggestion(1, '${decision}')`);
    assert.equal(ui.run('lastObservation'), null);
    assert.equal(ui.element('teachingCard').hidden, true);
    assert.equal(ui.element('repeatGesture').hidden, true);
    assert.equal(ui.element('suggestionPanel').hidden, true);
    assert.match(ui.element('stageDescription').textContent, decision === 'ACCEPTED' ? /다시 입력.*시뮬레이션/ : /다시 알려/);
  }
});


test('connection retry restores bootstrap configuration before loading the dashboard', async () => {
  const calls = [];
  const ui = app(async url => {
    calls.push(url);
    return {ok: true, status: 200, json: async () => url.endsWith('/demo/bootstrap')
      ? {intent_labels: {NEXT_SLIDE: '다음 슬라이드'}, auto_execution_threshold: 0.6, os_actions_enabled: false, demo_mode: true}
      : state};
  });
  await ui.run('loadWorkspace()');
  assert.deepEqual(calls, ['/api/v1/demo/bootstrap', '/api/v1/dashboard?user_id=demo-user']);
  assert.equal(ui.run('intentLabel("NEXT_SLIDE")'), '다음 슬라이드');
  assert.equal(ui.element('dashboardConnection').hidden, true);
});
