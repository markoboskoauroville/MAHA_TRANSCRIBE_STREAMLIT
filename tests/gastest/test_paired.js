/* TEST 1 — the mechanism alone. No network, no Streamlit, no UI.
 *
 * Runs the REAL apps_script/Code.gs inside the fake runtime and checks
 * the paired archive: text stored beside audio, deleted with it, and the
 * sheet index kept honest about both.
 *
 *   node tests/gastest/test_paired.js
 */

'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');
const gas = require('./fakegas');

const ROOT = 'ROOTFOLDER123';
const SRC = path.join(__dirname, '..', '..', 'apps_script', 'Code.gs');

function loadScript(mutate) {
  let src = fs.readFileSync(SRC, 'utf8');
  // Substitute BY PATTERN, not by replacing a CHANGE_ME placeholder.
  // A harness that swaps the placeholder silently misses on a real
  // filled-in file, and then every signed check runs against the wrong
  // secret — 17 passed / 22 failed on a file that was perfect (§46).
  src = src.replace(/^var SHEETS_TOKEN = '[^']*';/m, "var SHEETS_TOKEN = 'TOK';");
  src = src.replace(/^var DRIVE_SECRET = '[^']*';/m, "var DRIVE_SECRET = 'SEC';");
  src = src.replace(/^var DRIVE_ROOT_ID = '[^']*';/m,
                    "var DRIVE_ROOT_ID = '" + ROOT + "';");
  if (mutate) src = mutate(src);

  const ctx = vm.createContext({
    DriveApp: gas.DriveApp, SpreadsheetApp: gas.SpreadsheetApp,
    Utilities: gas.Utilities, ContentService: gas.ContentService,
    Date, Math, String, Number, JSON, Object, Array, console, require,
  });
  vm.runInContext(src, ctx, { filename: 'Code.gs' });
  return ctx;
}

let pass = 0, fail = 0;
const results = [];
function check(name, cond, detail) {
  if (cond) { pass++; results.push('  ok   ' + name); }
  else { fail++; results.push('  FAIL ' + name + (detail ? '  — ' + detail : '')); }
}

function post(ctx, body) {
  body.token = body.token === undefined ? 'TOK' : body.token;
  const out = ctx.doPost({ postData: { contents: JSON.stringify(body) } });
  return JSON.parse(out.getContent());
}

function b64(s) { return Buffer.from(s).toString('base64'); }

function fresh() {
  gas.resetWorld(ROOT);
  const ctx = loadScript();
  ctx.setupDrive();
  return ctx;
}

function recRows(ctx) {
  const s = gas.SS.getSheetByName('recordings');
  return s ? s.rows : [];
}

// ---------------------------------------------------------------------
// A. the pair is created together
// ---------------------------------------------------------------------
{
  const ctx = fresh();
  const put = post(ctx, { what: 'audio_put', user: 'baba', rec_id: 'r1',
                          part: 0, data: b64('AUDIOBYTES') });
  check('A1 audio stored, file_id returned', put.ok && !!put.file_id);

  const reg = post(ctx, { what: 'audio_reg', user: 'baba', rec_id: 'r1',
                          seconds: 12, parts: 1, folder_id: put.folder_id,
                          language: 'hr' });
  check('A2 registered', reg.ok === true);

  const txt = post(ctx, { what: 'text_put', user: 'baba', rec_id: 'r1',
                          text: 'Dobar dan, ovo je transkript.' });
  check('A3 text stored, file_id returned', txt.ok && !!txt.file_id);
  check('A4 chars reported', txt.chars === 29, 'got ' + txt.chars);

  const folder = ctx.recFolder_('baba', 'r1');
  const names = [];
  const it = folder.getFiles();
  while (it.hasNext()) names.push(it.next().getName());
  check('A5 BOTH files in ONE folder',
        names.includes('part_0000.flac') && names.includes('text.txt'),
        names.join(','));

  const list = post(ctx, { what: 'audio_list', user: 'baba' });
  check('A6 list says has_text', list.recordings[0].has_text === true);
  check('A7 list carries chars', list.recordings[0].chars === 29);

  const got = post(ctx, { what: 'text_get', user: 'baba', rec_id: 'r1' });
  check('A8 text round trips exactly',
        got.ok && got.text === 'Dobar dan, ovo je transkript.', got.text);
}

// ---------------------------------------------------------------------
// B. Croatian diacritics survive the round trip
// ---------------------------------------------------------------------
{
  const ctx = fresh();
  post(ctx, { what: 'audio_put', user: 'baba', rec_id: 'r2', part: 0,
              data: b64('A') });
  post(ctx, { what: 'audio_reg', user: 'baba', rec_id: 'r2', parts: 1 });
  const hr = 'ČčĆćŠšŽžĐđ — Idem u šumu, čekaj me.';
  post(ctx, { what: 'text_put', user: 'baba', rec_id: 'r2', text: hr });
  const got = post(ctx, { what: 'text_get', user: 'baba', rec_id: 'r2' });
  check('B1 Croatian diacritics intact', got.text === hr, got.text);
}

// ---------------------------------------------------------------------
// C. they die together
// ---------------------------------------------------------------------
{
  const ctx = fresh();
  const put = post(ctx, { what: 'audio_put', user: 'baba', rec_id: 'r3',
                          part: 0, data: b64('AUDIO') });
  post(ctx, { what: 'audio_reg', user: 'baba', rec_id: 'r3', parts: 1,
              folder_id: put.folder_id });
  post(ctx, { what: 'text_put', user: 'baba', rec_id: 'r3', text: 'gone soon' });

  check('C1 row exists before delete', recRows(ctx).length === 2);

  const del = post(ctx, { what: 'audio_del', user: 'baba', rec_id: 'r3' });
  check('C2 delete reports ok', del.ok === true);

  const folder = ctx.recFolder_('baba', 'r3');
  let n = 0;
  const it = folder.getFiles();
  while (it.hasNext()) { it.next(); n++; }
  check('C3 NO files left — audio and text both gone', n === 0, 'left ' + n);

  check('C4 sheet row removed too', recRows(ctx).length === 1);

  const got = post(ctx, { what: 'text_get', user: 'baba', rec_id: 'r3' });
  check('C5 text_get refuses after delete', got.ok === false);
}

// ---------------------------------------------------------------------
// D. retranscribe replaces, never accumulates
// ---------------------------------------------------------------------
{
  const ctx = fresh();
  post(ctx, { what: 'audio_put', user: 'baba', rec_id: 'r4', part: 0,
              data: b64('A') });
  post(ctx, { what: 'audio_reg', user: 'baba', rec_id: 'r4', parts: 1 });
  post(ctx, { what: 'text_put', user: 'baba', rec_id: 'r4', text: 'first pass' });
  post(ctx, { what: 'text_put', user: 'baba', rec_id: 'r4', text: 'second pass, better' });

  const folder = ctx.recFolder_('baba', 'r4');
  let n = 0;
  const it = folder.getFilesByName('text.txt');
  while (it.hasNext()) { it.next(); n++; }
  check('D1 exactly ONE text.txt after two writes', n === 1, 'found ' + n);

  const got = post(ctx, { what: 'text_get', user: 'baba', rec_id: 'r4' });
  check('D2 newest text wins', got.text === 'second pass, better', got.text);

  const list = post(ctx, { what: 'audio_list', user: 'baba' });
  check('D3 chars updated to the new length',
        list.recordings[0].chars === 19, 'got ' + list.recordings[0].chars);
}

// ---------------------------------------------------------------------
// E. re-registering must not wipe the text flags
// ---------------------------------------------------------------------
{
  const ctx = fresh();
  post(ctx, { what: 'audio_put', user: 'baba', rec_id: 'r5', part: 0,
              data: b64('A') });
  post(ctx, { what: 'audio_reg', user: 'baba', rec_id: 'r5', parts: 1 });
  post(ctx, { what: 'text_put', user: 'baba', rec_id: 'r5', text: 'keep me' });
  post(ctx, { what: 'audio_reg', user: 'baba', rec_id: 'r5', parts: 1,
              language: 'en' });

  const list = post(ctx, { what: 'audio_list', user: 'baba' });
  check('E1 has_text survives a re-register',
        list.recordings[0].has_text === true);
  check('E2 chars survive a re-register',
        list.recordings[0].chars === 7, 'got ' + list.recordings[0].chars);
  check('E3 the re-register still applied its own change',
        list.recordings[0].language === 'en');
  check('E4 still exactly one row', recRows(ctx).length === 2);
}

// ---------------------------------------------------------------------
// F. the ugly cases
// ---------------------------------------------------------------------
{
  const ctx = fresh();

  let r = post(ctx, { what: 'text_put', user: 'baba', rec_id: 'nope',
                      text: 'x' });
  check('F1 text_put on a recording that does not exist is refused',
        r.ok === false, JSON.stringify(r));

  r = post(ctx, { what: 'text_get', user: 'baba', rec_id: 'nope' });
  check('F2 text_get on a missing recording is refused', r.ok === false);

  post(ctx, { what: 'audio_put', user: 'baba', rec_id: 'r6', part: 0,
              data: b64('A') });
  post(ctx, { what: 'audio_reg', user: 'baba', rec_id: 'r6', parts: 1 });

  r = post(ctx, { what: 'text_get', user: 'baba', rec_id: 'r6' });
  check('F3 audio with no text yet says so', r.ok === false, JSON.stringify(r));

  r = post(ctx, { what: 'text_put', user: 'baba', rec_id: 'r6', text: '' });
  check('F4 empty text is accepted', r.ok === true);
  const list = post(ctx, { what: 'audio_list', user: 'baba' });
  check('F5 empty text sets has_text FALSE, not TRUE',
        list.recordings[0].has_text === false);

  const big = 'x'.repeat(120000);
  post(ctx, { what: 'text_put', user: 'baba', rec_id: 'r6', text: big });
  const got = post(ctx, { what: 'text_get', user: 'baba', rec_id: 'r6' });
  check('F6 a 120,000-char transcript survives — past any sheet-cell limit',
        got.ok && got.text.length === 120000,
        got.ok ? String(got.text.length) : got.error);

  r = post(ctx, { what: 'text_put', user: 'baba', rec_id: 'r6', text: 'x',
                  token: 'WRONG' });
  check('F7 bad token cannot write text', r.ok === false && r.error === 'bad token');

  r = post(ctx, { what: 'text_get', user: 'baba', rec_id: 'r6', token: 'WRONG' });
  check('F8 bad token cannot read text', r.ok === false && r.error === 'bad token');

  r = post(ctx, { what: 'text_put', user: '', rec_id: 'r6', text: 'x' });
  check('F9 missing user is refused', r.ok === false);

  // Another user must not reach it: safeName_ + per-user folder means a
  // different user resolves to a different folder entirely.
  r = post(ctx, { what: 'text_get', user: 'emina', rec_id: 'r6' });
  check('F10 another user cannot read this text', r.ok === false);
}

// ---------------------------------------------------------------------
// G. the upgrade from the version before
// ---------------------------------------------------------------------
{
  gas.resetWorld(ROOT);
  const ctx = loadScript();
  // Build an OLD eight-column sheet by hand, exactly as v85 left it.
  const s = gas.SS.insertSheet('recordings');
  s.appendRow(['user', 'rec_id', 'created', 'seconds', 'parts',
               'folder_id', 'language', 'note']);
  s.appendRow(['baba', 'old1', new Date(), 30, 1, 'fid', 'hr', '']);

  check('G1 starts at 8 columns', s.getLastColumn() === 8);

  // Any call that touches recSheet_ must widen it.
  post(ctx, { what: 'audio_list', user: 'baba' });
  ctx.recSheet_(gas.SS);
  check('G2 migrated to 10 columns', s.getLastColumn() === 10,
        'got ' + s.getLastColumn());
  check('G3 new headers are the right ones',
        s._cell(1, 9) === 'has_text' && s._cell(1, 10) === 'chars');

  const list = post(ctx, { what: 'audio_list', user: 'baba' });
  check('G4 the pre-existing row still reads correctly',
        list.recordings[0].rec_id === 'old1' &&
        list.recordings[0].seconds === 30 &&
        list.recordings[0].language === 'hr');
  check('G5 an old row reports has_text FALSE, not undefined',
        list.recordings[0].has_text === false);

  // And text can then be added to that old recording.
  post(ctx, { what: 'audio_put', user: 'baba', rec_id: 'old1', part: 0,
              data: b64('A') });
  const t = post(ctx, { what: 'text_put', user: 'baba', rec_id: 'old1',
                        text: 'added later' });
  check('G6 text can be added to a pre-existing recording', t.ok === true);
  const l2 = post(ctx, { what: 'audio_list', user: 'baba' });
  check('G7 the old row now says has_text', l2.recordings[0].has_text === true);
}

// ---------------------------------------------------------------------
// H. MUTATIONS — a test that has never failed is a rumour
// ---------------------------------------------------------------------
const mutations = [
  ['text dispatch removed',
   (s) => s.replace("if (body.what === 'text_put')   return json(putText_(body));", '')],
  ['replace-before-write removed (two text.txt could accumulate)',
   (s) => s.replace(/var old = folder\.getFilesByName\(TEXT_NAME\);\n\s*while \(old\.hasNext\(\)\) old\.next\(\)\.setTrashed\(true\);/,
                    '')],
  ['setTextFlags_ never called',
   (s) => s.replace('setTextFlags_(user, recId, chars > 0, chars);', '')],
  ['deleteRec_ stops trashing files',
   (s) => s.replace('while (files.hasNext()) files.next().setTrashed(true);', '')],
  ['register wipes the text flags',
   (s) => s.replace('if (body.has_text === undefined) {', 'if (false) {')],
  ['migration removed',
   (s) => s.replace(/if \(have < REC_HEADERS\.length\) \{/, 'if (false) {')],
];

const mutResults = [];
mutations.forEach(([name, fn]) => {
  let caught = false;
  try {
    gas.resetWorld(ROOT);
    const ctx = loadScript(fn);
    // Start from an OLD eight-column sheet, not a fresh one. setupDrive()
    // creates the tab already at ten columns, so the migration branch was
    // never reached and its mutation survived — the scenario has to
    // contain the thing being mutated or the mutation proves nothing.
    const s0 = gas.SS.insertSheet('recordings');
    s0.appendRow(['user', 'rec_id', 'created', 'seconds', 'parts',
                  'folder_id', 'language', 'note']);
    const put = post(ctx, { what: 'audio_put', user: 'baba', rec_id: 'm1',
                            part: 0, data: b64('A') });
    post(ctx, { what: 'audio_reg', user: 'baba', rec_id: 'm1', parts: 1,
                folder_id: put.folder_id });
    post(ctx, { what: 'text_put', user: 'baba', rec_id: 'm1', text: 'hello' });
    post(ctx, { what: 'text_put', user: 'baba', rec_id: 'm1', text: 'hello2' });
    post(ctx, { what: 'audio_reg', user: 'baba', rec_id: 'm1', parts: 1 });

    const list = post(ctx, { what: 'audio_list', user: 'baba' });
    const row = list.recordings[0] || {};
    const folder = ctx.recFolder_('baba', 'm1');
    let nText = 0;
    const it = folder.getFilesByName('text.txt');
    while (it.hasNext()) { it.next(); nText++; }

    // Hold the SAME folder object across the delete. Re-resolving it
    // afterwards calls recFolder_, which creates a fresh empty folder
    // when the real one is trashed — so the count came back 0 whatever
    // deleteRec_ did, and the mutation survived against a test that was
    // measuring a folder that had only just been created.
    const folderBefore = ctx.recFolder_('baba', 'm1');
    post(ctx, { what: 'audio_del', user: 'baba', rec_id: 'm1' });
    let leftover = 0;
    const it2 = folderBefore.getFiles();
    while (it2.hasNext()) { it2.next(); leftover++; }

    const healthy = row.has_text === true && row.chars === 6 &&
                    nText === 1 && leftover === 0 &&
                    gas.SS.getSheetByName('recordings').getLastColumn() === 10;
    caught = !healthy;
  } catch (err) {
    caught = true;
  }
  if (caught) { pass++; mutResults.push('  ok   caught: ' + name); }
  else { fail++; mutResults.push('  FAIL survived: ' + name); }
});

console.log('PAIRED ARCHIVE — Test 1, mechanism alone\n');
console.log(results.join('\n'));
console.log('\nMUTATIONS (each must be caught)\n');
console.log(mutResults.join('\n'));
console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
