/**
 * RUN EVERY COMPONENT'S SCRIPT AGAINST ITS OWN MARKUP.
 *
 * Reading the source was not enough, and I know that because I wrote a
 * reading test first and its mutation SURVIVED. It searched for
 * getElementById('bCut'); the bug that killed the frame used
 * getElementById(id) with the id coming from an array — invisible to a
 * regex, fatal at runtime.
 *
 * So this executes. A fake DOM knows only the ids that are really in the
 * markup and returns null for anything else, which is exactly what a
 * browser does. If a component reaches for something that is not there,
 * this throws here instead of in Baba's hands.
 *
 * Two failures this would have caught:
 *   v101  a label constant declared in the wrong component file
 *   v121  buttons removed, their ids left in a forEach
 * Both silently removed half a feature and neither failed a test.
 *
 *     node tests/gastest/test_components.js
 */

const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..', '..');
let passed = 0, failed = 0;

function check(name, cond, detail) {
  if (cond) { passed++; console.log('  ok   ' + name); }
  else { failed++; console.log('  FAIL ' + name + (detail ? '  — ' + detail : '')); }
}

function fakeDom(ids) {
  const made = {};
  const el = (id) => {
    if (made[id]) return made[id];
    const style = {};
    const node = {
      id, style, className: '', textContent: '', value: '', disabled: false,
      hidden: false, dataset: {},
      classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
      addEventListener() {}, removeEventListener() {}, focus() {}, blur() {},
      select() {}, setSelectionRange() {}, click() {},
      appendChild() {}, removeChild() {}, remove() {},
      setAttribute() {}, getAttribute() { return null; },
      removeAttribute() {}, insertBefore() {}, contains() { return false; },
      closest() { return null; }, matches() { return false; },
      firstElementChild: null, parentElement: null, children: [],
      innerHTML: '', innerText: '',
      getBoundingClientRect: () => ({ x: 0, y: 0, width: 100, height: 20 }),
      querySelector: () => el(id + '_q'), querySelectorAll: () => [],
      scrollWidth: 100, clientWidth: 100, scrollHeight: 100,
      selectionStart: 0, selectionEnd: 0,
      set onclick(v) {}, get onclick() { return null; },
      // EVERY node answers getContext. A canvas is a normal element to
      // getElementById, and the two frames that draw a scope reach for
      // its context straight away — my first harness gave getContext
      // only to querySelector results, so both scopes threw and the
      // failure was mine, not theirs.
      getContext: () => new Proxy({}, { get: () => () => ({}) }),
      width: 300, height: 60,
    };
    made[id] = node;
    return node;
  };

  const doc = {
    getElementById: (id) => (ids.has(id) ? el(id) : null),
    querySelector: () => el('_qs'),
    querySelectorAll: () => [],
    createElement: () => el('_new'),
    addEventListener() {}, removeEventListener() {},
    body: el('_body'), documentElement: el('_html'),
    // A frame that asks for a canvas gets one that answers everything.
    hidden: false,
  };
  el('_qs').getContext = () => ctx();
  el('_new').getContext = () => ctx();
  function ctx() {
    return new Proxy({}, { get: () => () => {} });
  }
  return doc;
}

function run(name) {
  const file = path.join(ROOT, name, 'index.html');
  const src = fs.readFileSync(file, 'utf8');

  const ids = new Set();
  for (const m of src.matchAll(/id="([A-Za-z0-9_-]+)"/g)) ids.add(m[1]);

  const script = src.split('<script>')[1] ? src.split('<script>')[1].split('</script>')[0] : '';
  check(name + ': has a script', script.length > 0);

  const document = fakeDom(ids);
  const listeners = [];
  const window = {
    document,
    parent: { postMessage() {} },
    addEventListener(t, fn) { listeners.push([t, fn]); },
    removeEventListener() {},
    requestAnimationFrame() { return 1; },
    cancelAnimationFrame() {},
    setInterval() { return 1; }, clearInterval() {},
    setTimeout() { return 1; }, clearTimeout() {},
    AudioContext: function () { return new Proxy({}, { get: () => () => ({}) }); },
    navigator: { mediaDevices: { getUserMedia: async () => ({}) } },
    MediaRecorder: function () { return new Proxy({}, { get: () => () => {} }); },
    FileReader: function () { return { readAsDataURL() {}, result: '' }; },
    Blob: function () { return { size: 0, type: '' }; },
    location: { href: '' }, localStorage: { getItem() { return null; }, setItem() {}, removeItem() {} },
    Audio: function () { return new Proxy({}, { get: () => () => {} }); },
    Image: function () { return new Proxy({}, { get: () => () => {} }); },
    URL: { createObjectURL: () => 'blob:x', revokeObjectURL() {} },
    fetch: async () => ({ ok: true, json: async () => ({}) }),
    Uint8Array, Float32Array, Number, Math, Date, JSON, String, Array,
    Object, console,
  };
  window.window = window;

  // NAMED ACCESS ON WINDOW. A browser exposes every element with an id
  // as a global of that name, and cassette_frontend uses it — `bFile`
  // with no lookup at all. Emulating it is what makes this harness
  // realistic rather than merely strict; without it the deck failed
  // here while working perfectly in Baba's hands, which is the wrong
  // kind of red.
  // ONLY the ids the script uses BARE. Passing every id as a parameter
  // collides with a script's own `const pad = ...` when an element is
  // also called pad — a SyntaxError that says nothing about the app.
  // A name counts as bare if it appears without a getElementById around
  // it and is never declared.
  const declared = new Set(
    [...script.matchAll(/\b(?:var|let|const|function)\s+([A-Za-z_$][\w$]*)/g)]
      .map((m) => m[1]));
  const named = [...ids].filter((id) =>
    !declared.has(id) && new RegExp('\\b' + id + '\\b').test(script));
  const namedVals = named.map((id) => document.getElementById(id));

  const fn = new Function(...named, 'window', 'document', 'navigator', 'MediaRecorder',
                          'FileReader', 'Blob', 'AudioContext', 'localStorage',
                          'requestAnimationFrame', 'cancelAnimationFrame',
                          'setInterval', 'clearInterval', 'setTimeout',
                          'clearTimeout', 'location', 'Audio', 'Image', 'URL',
                          'fetch',
                          '"use strict";' + script);
  try {
    fn(...namedVals, window, document, window.navigator, window.MediaRecorder,
       window.FileReader, window.Blob, window.AudioContext, window.localStorage,
       window.requestAnimationFrame, window.cancelAnimationFrame,
       window.setInterval, window.clearInterval, window.setTimeout,
       window.clearTimeout, window.location, window.Audio, window.Image,
       window.URL, window.fetch);
    check(name + ': THE SCRIPT RUNS without reaching for anything missing', true);
  } catch (e) {
    check(name + ': THE SCRIPT RUNS without reaching for anything missing',
          false, e.message);
    return;
  }

  // And a render message must not throw either — that is where labels
  // and arguments arrive, and where v121's dead lookups were waiting.
  const render = { data: { type: 'streamlit:render', args: {
    text: 'proba', scale: 1.0, source: 'mic',
    labels: { rec: 'rec', stop: 'stop', pause: 'pause',
              cut: 'cut', line: 'line' },
    sources: [{ id: 'mic', label: 'microphone' }],
  } } };
  try {
    for (const [type, fn2] of listeners) if (type === 'message') fn2(render);
    check(name + ': a render message does not throw', true);
  } catch (e) {
    check(name + ': a render message does not throw', false, e.message);
  }
}

console.log('COMPONENTS, EXECUTED\n');
for (const d of fs.readdirSync(ROOT)) {
  if (d.endsWith('_frontend') && fs.existsSync(path.join(ROOT, d, 'index.html'))) {
    run(d);
  }
}

console.log('\n' + passed + ' passed, ' + failed + ' failed');
process.exit(failed ? 1 : 0);
