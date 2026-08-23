/**
 * THE NOTEBOOK IN DRIVE.
 *
 * Baba: "to survive between sessions, notes should be saved in the same
 * location where audio files are saved, and a simple text file as a
 * backup in Google Drive."
 *
 * v140 put them in the browser, which fixed the reload but leaves them
 * on one device. This is the durable half: one notes.txt in the
 * person's own folder, beside their recordings, readable without the
 * app.
 *
 *     node tests/gastest/test_notes_drive.js
 */
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const gas = require('./fakegas');

const ROOT = 'ROOTFOLDER123';
const SRC = path.join(__dirname, '..', '..', 'apps_script', 'Code.gs');

// THE SAME LOADER AS test_paired.js, and for the same reason written
// there: substitute BY PATTERN, never by replacing a CHANGE_ME
// placeholder, or the harness silently misses on a real filled-in file
// and every check runs against the wrong secret.
function fresh() {
  let src = fs.readFileSync(SRC, 'utf8');
  src = src.replace(/^var SHEETS_TOKEN = '[^']*';/m, "var SHEETS_TOKEN = 'TOK';");
  src = src.replace(/^var DRIVE_SECRET = '[^']*';/m, "var DRIVE_SECRET = 'SEC';");
  src = src.replace(/^var DRIVE_ROOT_ID = '[^']*';/m,
                    "var DRIVE_ROOT_ID = '" + ROOT + "';");
  gas.resetWorld(ROOT);
  const ctx = vm.createContext({
    DriveApp: gas.DriveApp, SpreadsheetApp: gas.SpreadsheetApp,
    Utilities: gas.Utilities, ContentService: gas.ContentService,
    MimeType: { PLAIN_TEXT: 'text/plain' },
    Date, Math, String, Number, JSON, Object, Array, console, require,
  });
  vm.runInContext(src, ctx, { filename: 'Code.gs' });
  ctx.setupDrive();
  return ctx;
}

let passed = 0, failed = 0;
function check(name, cond, detail) {
  if (cond) { passed++; console.log('  ok   ' + name); }
  else { failed++; console.log('  FAIL ' + name + (detail ? '  — ' + detail : '')); }
}

console.log('THE NOTEBOOK IN DRIVE\n');

const ctx = fresh();

// --- writing ----------------------------------------------------------
let out = ctx.notesPut_({ user: 'emina', text: '[{"id":"n1","text":"prva"}]' });
check('1 a notebook is written', out.ok === true, JSON.stringify(out));

const root = gas.DRIVE.roots[ROOT];
const userFolder = root.getFoldersByName('emina');
check('2 IN THE PERSON\'S OWN FOLDER, beside their recordings — not '
      + 'inside one of them', userFolder.hasNext());

const folder = root.getFoldersByName('emina').next();
const files = [];
const it = folder.getFilesByName('notes.txt');
while (it.hasNext()) files.push(it.next());
check('3 as a plain notes.txt', files.length === 1, files.length);
check('4 holding the notebook', files[0].getBlob().getDataAsString()
      === '[{"id":"n1","text":"prva"}]');

// --- reading back -----------------------------------------------------
out = ctx.notesGet_({ user: 'emina' });
check('5 and it reads back exactly', out.ok === true
      && out.text === '[{"id":"n1","text":"prva"}]', JSON.stringify(out));

// --- replaced whole, never duplicated ---------------------------------
ctx.notesPut_({ user: 'emina', text: 'DRUGO' });
const files2 = [];
const it2 = folder.getFilesByName('notes.txt');
while (it2.hasNext()) files2.push(it2.next());
check('6 A SECOND SAVE REPLACES, it does not add a second file — two '
      + 'notes.txt would leave no answer to which one is the notebook',
      files2.length === 1, files2.length);
check('7 with the new contents',
      ctx.notesGet_({ user: 'emina' }).text === 'DRUGO');

// --- a duplicate is cleaned up ----------------------------------------
//
// The check above passes whether or not the tidy-up loop exists,
// because a single existing file goes down the setContent path and the
// loop never runs. Its mutation survived until this was written.
//
// Two notes.txt CAN happen: Drive allows same-named files in one
// folder, and a half-finished write or a hand-copied file leaves one.
// Then there is no answer to which is the notebook.
folder.createFile('notes.txt', 'STRAY', 'text/plain');
ctx.notesPut_({ user: 'emina', text: 'JEDINO' });
const files3 = [];
const it3 = folder.getFilesByName('notes.txt');
while (it3.hasNext()) files3.push(it3.next());
check('7b A DUPLICATE IS TRASHED, so exactly one file is the notebook',
      files3.length === 1, files3.length);
check('7c and the one that survives is the one just written',
      ctx.notesGet_({ user: 'emina' }).text === 'JEDINO',
      ctx.notesGet_({ user: 'emina' }).text);

// --- somebody with no notes yet ---------------------------------------
out = ctx.notesGet_({ user: 'marinko' });
check('8 NO NOTEBOOK IS NOT AN ERROR. Somebody who has never made a '
      + 'note must read as "nothing yet", not as a fault',
      out.ok === true && out.text === null, JSON.stringify(out));

// --- one person cannot read another's ----------------------------------
ctx.notesPut_({ user: 'marinko', text: 'MARINKO' });
check('9 EACH PERSON HAS THEIR OWN, in their own folder',
      ctx.notesGet_({ user: 'emina' }).text === 'JEDINO'
      && ctx.notesGet_({ user: 'marinko' }).text === 'MARINKO',
      ctx.notesGet_({ user: 'emina' }).text);

// --- a name cannot climb out -------------------------------------------
out = ctx.notesPut_({ user: '../../etc', text: 'x' });
check('10 a name that tries to climb out is scrubbed, not obeyed',
      !root.getFoldersByName('..').hasNext(), 'a .. folder exists');
out = ctx.notesPut_({ user: '', text: 'x' });
check('11 and an empty name is refused outright',
      out.ok === false, JSON.stringify(out));

// --- the doPost door ---------------------------------------------------
const src = require('fs').readFileSync(
  path.join(__dirname, '..', '..', 'apps_script', 'Code.gs'), 'utf8');
check('12 both are reachable through doPost, or the app cannot call them',
      src.indexOf("'notes_put'") > 0 && src.indexOf("'notes_get'") > 0);

console.log('\n' + passed + ' passed, ' + failed + ' failed');
process.exit(failed ? 1 : 0);
