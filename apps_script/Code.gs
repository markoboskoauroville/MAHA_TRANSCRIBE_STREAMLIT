/**
 * ═══════════════════════════════════════════════════════════════════
 *  TTT-LLL — THE APPS SCRIPT.  This is the whole thing.
 * ═══════════════════════════════════════════════════════════════════
 *
 *  ONE FILE. There is no base script and no additions. There used to be
 *  three files that had to be combined in the right order with two edits
 *  made by hand, and combining them wrongly left the Drive functions
 *  unreachable — every function present, nothing routed to any of them.
 *  One file cannot be assembled wrongly.
 *
 *  DO NOT SPLIT THIS UP AGAIN. Anything new belongs in here.
 *
 *  Edit it on your Mac and send it with `clasp push` — see SETUP.md,
 *  which walks through clasp from nothing. Pasting into the browser
 *  still works, but then paste the WHOLE file, never a part of it.
 *
 * ───────────────────────────────────────────────────────────────────
 *  WHAT YOU FILL IN
 * ───────────────────────────────────────────────────────────────────
 *
 *  EVERYTHING is in one block a little further down, between two thick
 *  boxes. Nothing below that block ever needs touching. You do not have
 *  to read or scroll through the rest of this file.
 *
 *  Three that matter:
 *      SHEETS_TOKEN      -> Streamlit secrets as SHEETS_TOKEN
 *      DRIVE_SECRET   -> Streamlit secrets as DRIVE_SECRET
 *      DRIVE_ROOT_ID     -> only for audio storage; leave it otherwise
 *
 *  Two you may want:
 *      KNOWN_USERS       -> who gets a tab on day one
 *      KEY_PROVIDERS     -> which k_ key tabs get made
 *
 *  Two you probably never will:
 *      LINK_SECONDS, MAX_PART_BYTES
 *
 *  MAKE THE SECRETS YOURSELF:   openssl rand -base64 33
 *  Run it twice, once for each. Never paste a secret into a chat, an
 *  email or a screenshot — a message cannot be unsent, and text in a
 *  chat log cannot be deleted afterwards. If one ever lands in a
 *  message, replace it rather than hope.
 *
 *  THERE ARE NO API KEYS IN THIS FILE, and none should ever be added.
 *  Groq, Speechify, Anthropic and AssemblyAI keys live in the k_ tabs of
 *  the spreadsheet, where the app reads them through doGet.
 *
 * ───────────────────────────────────────────────────────────────────
 *  AFTER PASTING — in this order
 * ───────────────────────────────────────────────────────────────────
 *
 *  1. Run  setup()        once  — user tabs, Summary, Daily
 *  2. Run  setupConfig()  once  — settings tab and the k_ key tabs
 *  3. Run  setupDrive()   once  — recordings tab; it checks your folder
 *                                 id and refuses if the two secrets
 *                                 match. Skip if not using Drive yet.
 *  4. Deploy > Manage deployments > pencil > New version > Deploy
 *
 *  STEP 4 IS NOT OPTIONAL. Saving the editor changes nothing that the
 *  app can see; only a NEW VERSION is published. An old deployment will
 *  keep answering with the old code and look like your edits did
 *  nothing.
 *
 *  5. Put SHEETS_URL (the /exec address), SHEETS_TOKEN and DRIVE_SECRET
 *     into Streamlit secrets.
 *
 * ───────────────────────────────────────────────────────────────────
 *  PRIVACY, BY DESIGN
 * ───────────────────────────────────────────────────────────────────
 *
 *  No text ever leaves the app. Not what was transcribed, not what was
 *  translated, not what was read. This script sees only: which user,
 *  what kind of action, how big it was, which engine, and when. There
 *  is deliberately no field for content, so none can be sent even by
 *  accident.
 */

// ╔═══════════════════════════════════════════════════════════════════╗
// ║                                                                   ║
// ║   EVERYTHING YOU FILL IN IS IN THIS ONE BLOCK.                    ║
// ║   Nothing below it needs to be touched, ever.                     ║
// ║                                                                   ║
// ╚═══════════════════════════════════════════════════════════════════╝

// ─── 1 ─── THE SHARED TOKEN ──────────────────────────────────────────
// A long random string, so strangers cannot write to your sheet or read
// your keys. The SAME string goes into Streamlit secrets as
// SHEETS_TOKEN. Nothing works until the two match.
//
// Make it yourself:   openssl rand -base64 33
//
// IF IT EVER APPEARS IN A MESSAGE, A SCREENSHOT OR A LOG, REPLACE IT.
// It unlocks doGet, which hands back every API key in the k_ tabs. A
// message cannot be unsent.
var SHEETS_TOKEN = 'CHANGE_ME_to_a_long_random_string';


// ─── 2 ─── THE DOWNLOAD SECRET ───────────────────────────────────────
// A DIFFERENT long random string. The same one goes into Streamlit
// secrets as DRIVE_SECRET. Run the openssl line a second time.
//
// It must not equal SHEETS_TOKEN, and setupDrive() refuses to run if it
// does. The reason: the token above unlocks your settings AND your API
// keys, while a download link is the part most likely to end up in a log
// somewhere. Losing one must never cost you the other.
var DRIVE_SECRET = 'CHANGE_ME_to_a_different_long_random_string';


// ─── 3 ─── THE DRIVE FOLDER ──────────────────────────────────────────
// Open the folder in Drive; the id is the last part of the address:
//     drive.google.com/drive/folders/THIS_PART
//
// Only used for audio storage. If you are not using that yet, leave the
// placeholder — everything else works without it.
var DRIVE_ROOT_ID = 'PUT_YOUR_FOLDER_ID_HERE';


// ─── 4 ─── WHO CAN LOG IN ────────────────────────────────────────────
// Used by setup() to build a tab for each person on day one. Somebody
// not listed still gets a tab automatically on first use, so this list
// only saves you looking at an empty sheet.
var KNOWN_USERS = ['user1', 'user2', 'user3'];


// ─── 5 ─── WHICH PROVIDERS GET A KEY TAB ─────────────────────────────
// One k_ tab is made for each. Add a name here to add a tab.
// THE KEYS THEMSELVES ARE NEVER IN THIS FILE — they go in the tabs, in
// the spreadsheet, and the app reads them through doGet.
var KEY_PROVIDERS = ['assemblyai', 'anthropic', 'speechify', 'groq'];


// ─── 6 ─── RARELY CHANGED ────────────────────────────────────────────
// Sensible as they are. Here only so that nothing is hidden further
// down the file.

// How long a signed download link stays valid, in seconds. Short on
// purpose: the app signs one the moment it needs it.
var LINK_SECONDS = 600;

// Biggest audio part accepted, as base64. The platform refuses a request
// body over 50 MiB — measured, not guessed — so the app sends one
// 10-minute part at a time, about 14 MB. Anything near the ceiling is a
// bug in the caller and is refused here rather than half-written.
var MAX_PART_BYTES = 40 * 1024 * 1024;


// ╔═══════════════════════════════════════════════════════════════════╗
// ║   END OF THE PART YOU EDIT.                                       ║
// ║   Everything below is the working code.                           ║
// ╚═══════════════════════════════════════════════════════════════════╝


// ---------------------------------------------------------------------

var EVENT_HEADERS = [
  'When', 'Date', 'Action', 'Amount', 'Unit', 'Engine', 'Seconds in app'
];

/** Run this ONCE from the Apps Script editor. Builds every tab, the
 *  headers, and the Summary. Safe to run again — it never deletes data. */
function setup() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  KNOWN_USERS.forEach(function (u) { getUserSheet(ss, u); });
  buildSummary(ss);
  buildDaily(ss);
  SpreadsheetApp.getUi().alert(
    'TTT-LLL logging is ready.\n\n' +
    'Next, IF THIS IS THE FIRST TIME:\n' +
    'Deploy > New deployment > Web app, set "Who has access" to ' +
    '"Anyone", and put the URL it gives you into Streamlit secrets as ' +
    'SHEETS_URL.\n\n' +
    'IF YOU ALREADY HAVE A DEPLOYMENT — which you do, if the app has ' +
    'ever worked:\n' +
    'Deploy > Manage deployments > pencil > Version: New version > ' +
    'Deploy.\n\n' +
    'DO NOT use "New deployment" the second time. It makes a SECOND web ' +
    'app with a DIFFERENT URL, and SHEETS_URL in Streamlit then points ' +
    'at the old one, which keeps answering with the old code.'
  );
}

/** The app calls this. Never throws at the caller — a logging failure must
 *  never be able to break the app that is being logged. */
function doPost(e) {
  try {
    var body = JSON.parse(e.postData.contents);
    if (body.token !== SHEETS_TOKEN) {
      return json({ ok: false, error: 'bad token' });
    }

    // --- Drive audio storage -----------------------------------------
    // This dispatch MUST stay above the appendRow below. These requests
    // are not usage events, and if they fall through, every 10-minute
    // audio part also writes a usage row and the counts become fiction.
    if (body.what === 'audio_put')  return json(putAudio_(body));
    if (body.what === 'audio_reg')  return json(registerRec_(body));
    if (body.what === 'audio_del')  return json(deleteRec_(body));
    if (body.what === 'text_put')   return json(putText_(body));
    if (body.what === 'text_get')   return json(getText_(body));
    if (body.what === 'audio_list') {
      return json({ ok: true, recordings: listRecs_(body.user) });
    }
    // ------------------------------------------------------------------

    var user = String(body.user || 'unknown').toLowerCase().trim();
    if (!user) user = 'unknown';

    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = getUserSheet(ss, user);
    var now = new Date();
    var tz = ss.getSpreadsheetTimeZone();

    sheet.appendRow([
      now,
      Utilities.formatDate(now, tz, 'yyyy-MM-dd'),
      String(body.action || 'unknown'),
      Number(body.amount || 0),
      String(body.unit || ''),
      String(body.engine || ''),
      Number(body.session_seconds || 0)
    ]);
    return json({ ok: true });
  } catch (err) {
    return json({ ok: false, error: String(err) });
  }
}

/** So you can check it is alive by opening the URL in a browser. */
// doGet needs the token, because it
// returns settings and API keys. The old one took no token and reported
// the user count to anyone holding the URL.

function json(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function getUserSheet(ss, user) {
  var name = 'u_' + user;
  var sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
    sheet.appendRow(EVENT_HEADERS);
    sheet.getRange(1, 1, 1, EVENT_HEADERS.length).setFontWeight('bold');
    sheet.setFrozenRows(1);
    sheet.setColumnWidth(1, 160);
  }
  return sheet;
}

function userTabs() {
  return SpreadsheetApp.getActiveSpreadsheet().getSheets().filter(function (s) {
    return s.getName().indexOf('u_') === 0;
  });
}

/** Totals per user. Rebuilt from scratch each time so it always matches
 *  whichever user tabs currently exist. */
function buildSummary(ss) {
  var sheet = ss.getSheetByName('Summary') || ss.insertSheet('Summary', 0);
  sheet.clear();
  sheet.appendRow(['User', 'Uses', 'Audio minutes', 'Characters',
                   'Hours in app', 'First use', 'Last use']);
  sheet.getRange(1, 1, 1, 7).setFontWeight('bold');
  sheet.setFrozenRows(1);

  var tabs = userTabs();
  tabs.forEach(function (tab, i) {
    var n = tab.getName();
    var q = "'" + n + "'";
    var row = i + 2;
    sheet.getRange(row, 1).setValue(n.substring(2));
    // COUNTA on the Action column: one row per use.
    sheet.getRange(row, 2).setFormula('=COUNTA(' + q + '!C2:C)');
    // Audio seconds -> minutes, only rows whose unit says seconds.
    sheet.getRange(row, 3).setFormula(
      '=ROUND(SUMIF(' + q + '!E2:E,"seconds",' + q + '!D2:D)/60,1)');
    sheet.getRange(row, 4).setFormula(
      '=SUMIF(' + q + '!E2:E,"chars",' + q + '!D2:D)');
    sheet.getRange(row, 5).setFormula(
      '=ROUND(SUM(' + q + '!G2:G)/3600,2)');
    sheet.getRange(row, 6).setFormula('=IFERROR(MIN(' + q + '!B2:B),"")');
    sheet.getRange(row, 7).setFormula('=IFERROR(MAX(' + q + '!B2:B),"")');
  });
  sheet.autoResizeColumns(1, 7);
}

/** Per day, per user — the "how hard are they hammering it" view.
 *  One QUERY per user tab, laid out side by side. */
function buildDaily(ss) {
  var sheet = ss.getSheetByName('Daily') || ss.insertSheet('Daily');
  sheet.clear();
  var tabs = userTabs();
  var col = 1;
  tabs.forEach(function (tab) {
    var n = tab.getName();
    sheet.getRange(1, col).setValue(n.substring(2)).setFontWeight('bold');
    sheet.getRange(2, col).setFormula(
      '=IFERROR(QUERY(' + "'" + n + "'" + '!B2:D,' +
      '"select B, count(C), sum(D) where B is not null ' +
      'group by B order by B desc label count(C) \'Uses\', sum(D) \'Amount\'",0),' +
      '"no data yet")');
    col += 4;
  });
  sheet.setFrozenRows(1);
}

/** Rebuild Summary and Daily after new users appear. Also wired to a menu
 *  so you can press it yourself without opening the editor. */
function refresh() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  buildSummary(ss);
  buildDaily(ss);
}

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('TTT-LLL')
    .addItem('Refresh statistics', 'refresh')
    .addItem('First-time setup', 'setup')
    .addToUi();
}


/** Settings the app understands, with their built-in defaults. These are
 *  written into the sheet by setupConfig() so the list is discoverable —
 *  Baba can see what exists rather than having to remember it. */
var DEFAULT_SETTINGS = [
  ['global', 'prompt_grammar',
   'Fix spelling, punctuation and obvious slips. Do not change the wording or the style.'],
  ['global', 'prompt_reshape',
   'Tidy this into clear paragraphs. Remove filler and repetition. Keep every fact and the speaker\'s own voice.'],
  ['global', 'allow_user_keys', 'TRUE'],
  ['global', 'allow_patch_bay', 'FALSE'],
  ['global', 'store_audio', 'TRUE']
];

function setupConfig() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();

  var s = ss.getSheetByName('settings');
  if (!s) {
    s = ss.insertSheet('settings');
    s.appendRow(['scope', 'key', 'value']);
    s.getRange(1, 1, 1, 3).setFontWeight('bold');
    DEFAULT_SETTINGS.forEach(function (row) { s.appendRow(row); });
    s.setFrozenRows(1);
    s.setColumnWidth(1, 120);
    s.setColumnWidth(2, 170);
    s.setColumnWidth(3, 520);
  }

  KEY_PROVIDERS.forEach(function (p) {
    var name = 'k_' + p;
    if (!ss.getSheetByName(name)) {
      var k = ss.insertSheet(name);
      k.appendRow(['key', 'label (optional)']);
      k.getRange(1, 1, 1, 2).setFontWeight('bold');
      k.setFrozenRows(1);
      k.setColumnWidth(1, 480);
    }
  });

  SpreadsheetApp.getUi().alert(
    'Config tabs ready.\n\n' +
    'settings — one row per setting. scope is "global" or a username; ' +
    'a user row beats the global row.\n\n' +
    'k_assemblyai, k_anthropic, k_speechify, k_groq — put a key in ' +
    'column A, one per row. The app uses these when the key is not in ' +
    'Streamlit secrets.'
  );
}

/** The app reads configuration through this. Same token as doPost.
 *
 *  GET ?token=...&what=config
 *    -> { ok, settings: [[scope,key,value],...], keys: {provider:[...]}}
 *
 *  Returns keys, so it must never be reachable without the token. */
function doGet(e) {
  try {
    var p = (e && e.parameter) || {};

    // --- Audio download ------------------------------------------------
    // Deliberately ABOVE the SHEETS_TOKEN check. This branch carries its
    // own short-lived signature made with DRIVE_SECRET, so a download
    // link that leaks into a log cannot be replayed to read the settings
    // and API keys below. Moving this under the token check would undo
    // the entire reason there are two secrets.
    if (p.what === 'audio') {
      return json(getAudio_(p));
    }
    // --------------------------------------------------------------------

    if (p.token !== SHEETS_TOKEN) {
      return json({ ok: false, error: 'bad token' });
    }
    if (p.what !== 'config') {
      return json({ ok: false, error: 'unknown request' });
    }

    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var out = { ok: true, settings: [], keys: {} };

    var s = ss.getSheetByName('settings');
    if (s && s.getLastRow() > 1) {
      var rows = s.getRange(2, 1, s.getLastRow() - 1, 3).getValues();
      rows.forEach(function (r) {
        var scope = String(r[0] || '').toLowerCase().trim();
        var key = String(r[1] || '').trim();
        if (scope && key) out.settings.push([scope, key, String(r[2])]);
      });
    }

    KEY_PROVIDERS.forEach(function (prov) {
      var k = ss.getSheetByName('k_' + prov);
      if (!k || k.getLastRow() < 2) return;
      var vals = k.getRange(2, 1, k.getLastRow() - 1, 1).getValues();
      var list = [];
      vals.forEach(function (v) {
        var key = String(v[0] || '').trim();
        if (key) list.push(key);
      });
      if (list.length) out.keys[prov] = list;
    });

    return json(out);
  } catch (err) {
    return json({ ok: false, error: String(err) });
  }
}


// =====================================================================
//  DRIVE AUDIO STORAGE
//  Keeps each user's levelled 16 kHz audio in your Drive, so changing
//  the language and transcribing again costs no upload from the phone.
// =====================================================================


// has_text and chars exist so the archive list can offer "pull" versus
// "retranscribe" WITHOUT fetching anything. One request returns every
// row; scanning Drive instead would mean an API call per user folder,
// then per recording, then per file — dozens of round trips through the
// slowest part of the stack. The sheet is the index; Drive is the store.
var REC_HEADERS = ['user', 'rec_id', 'created', 'seconds', 'parts',
                   'folder_id', 'language', 'note', 'has_text', 'chars'];

/** The transcript, stored as a FILE beside the audio rather than in a
 *  sheet cell. Two reasons, both load-bearing:
 *
 *  1. A folder trash removes the audio AND the text in one action, so
 *     the pair cannot come apart. Baba: "they go in pairs always."
 *  2. A sheet cell tops out at 50,000 characters. A long transcript
 *     would be silently truncated, which is the worst way to lose text. */
var TEXT_NAME = 'text.txt';

/** Run ONCE from the editor. Creates the recordings tab. Safe to re-run. */
function setupDrive() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  recSheet_(ss);
  var ok = true, msg = '';
  try {
    var f = DriveApp.getFolderById(DRIVE_ROOT_ID);
    msg = 'Drive folder found: ' + f.getName();
  } catch (err) {
    ok = false;
    msg = 'CANNOT OPEN THE DRIVE FOLDER.\n\n' +
          'Check DRIVE_ROOT_ID is the id from the folder URL.\n\n' + err;
  }
  if (DRIVE_SECRET === SHEETS_TOKEN) {
    ok = false;
    msg += '\n\nDRIVE_SECRET IS THE SAME AS SHEETS_TOKEN. ' +
           'Change it — the whole point is that they are different.';
  }
  if (String(DRIVE_SECRET).indexOf('CHANGE_ME') === 0) {
    ok = false;
    msg += '\n\nDRIVE_SECRET is still the placeholder.';
  }
  SpreadsheetApp.getUi().alert(
    (ok ? 'Drive storage ready.\n\n' : 'NOT READY.\n\n') + msg);
}

function recSheet_(ss) {
  var s = ss.getSheetByName('recordings');
  if (!s) {
    s = ss.insertSheet('recordings');
    s.appendRow(REC_HEADERS);
    s.getRange(1, 1, 1, REC_HEADERS.length).setFontWeight('bold');
    s.setFrozenRows(1);
    s.setColumnWidth(2, 200);
    s.setColumnWidth(6, 260);
    return s;
  }

  // MIGRATION. Baba's sheet already exists with eight columns, made
  // before text was stored. Widening it here rather than asking him to
  // re-run setupDrive() means the upgrade costs him nothing and cannot
  // be half-done. Only ever ADDS the missing headers on the right: the
  // existing columns keep their positions, so every row already written
  // still reads correctly.
  var have = s.getLastColumn();
  if (have < REC_HEADERS.length) {
    var missing = REC_HEADERS.slice(have);
    s.getRange(1, have + 1, 1, missing.length).setValues([missing])
     .setFontWeight('bold');
  }
  return s;
}

// ---------------------------------------------------------------------
//  SIGNING
// ---------------------------------------------------------------------

/** HMAC-SHA256 of "recId|part|expiry", lowercase hex. The app computes
 *  the same thing with the same secret; nothing else can.
 *
 *  CONTRACT, and a trap found in testing: recId here is ALREADY through
 *  safeName_, which lowercases and strips punctuation. A client that
 *  signs the RAW rec_id gets "bad signature" for a recording that exists,
 *  which reads like a broken secret and is not. The Python side must
 *  apply the identical safe_name() before signing — there is a test that
 *  proves the two agree character for character. The app also mints
 *  rec_ids that are already lowercase hex, so the two can never diverge
 *  in practice. */
function signPart_(recId, part, exp) {
  var msg = String(recId) + '|' + String(part) + '|' + String(exp);
  var raw = Utilities.computeHmacSha256Signature(msg, DRIVE_SECRET);
  return raw.map(function (b) {
    return ('0' + (b & 0xFF).toString(16)).slice(-2);
  }).join('');
}

/** Compare without leaking WHERE two strings differ through timing. */
function sameSig_(a, b) {
  a = String(a || ''); b = String(b || '');
  if (a.length !== b.length) return false;
  var diff = 0;
  for (var i = 0; i < a.length; i++) {
    diff |= (a.charCodeAt(i) ^ b.charCodeAt(i));
  }
  return diff === 0;
}

function nowSecs_() { return Math.floor(Date.now() / 1000); }

// ---------------------------------------------------------------------
//  FOLDERS
// ---------------------------------------------------------------------

function childFolder_(parent, name) {
  var it = parent.getFoldersByName(name);
  return it.hasNext() ? it.next() : parent.createFolder(name);
}

/** <root>/<user>/<recId>/ — created on first write, as §17 says. */
function recFolder_(user, recId) {
  var root = DriveApp.getFolderById(DRIVE_ROOT_ID);
  return childFolder_(childFolder_(root, user), recId);
}

/** A user id that cannot climb out of its own folder or collide. */
function safeName_(s) {
  return String(s || '').toLowerCase().replace(/[^a-z0-9_\-]/g, '').slice(0, 60);
}

// ---------------------------------------------------------------------
//  WRITE — called from doPost with what:"audio_put"
//
//  *** This is why doPost needs its one edit: the dispatch must happen
//  BEFORE appendRow, or every audio part also writes a usage row.
// ---------------------------------------------------------------------

function putAudio_(body) {
  var user = safeName_(body.user);
  var recId = safeName_(body.rec_id);
  if (!user || !recId) return { ok: false, error: 'user and rec_id required' };

  var part = Number(body.part || 0);
  if (!(part >= 0 && part < 10000)) return { ok: false, error: 'bad part' };

  var b64 = String(body.data || '');
  if (!b64) return { ok: false, error: 'no data' };
  if (b64.length > MAX_PART_BYTES) return { ok: false, error: 'part too large' };

  var bytes;
  try {
    bytes = Utilities.base64Decode(b64);
  } catch (err) {
    return { ok: false, error: 'bad base64' };
  }

  var name = 'part_' + ('000' + part).slice(-4) + '.flac';
  var folder = recFolder_(user, recId);

  // Writing the same part twice must leave exactly one file, so a retry
  // after a timeout cannot double the storage. Replace, never add.
  var old = folder.getFilesByName(name);
  while (old.hasNext()) old.next().setTrashed(true);

  var blob = Utilities.newBlob(bytes, 'audio/flac', name);
  var file = folder.createFile(blob);

  return { ok: true, file_id: file.getId(), name: name,
           bytes: bytes.length, folder_id: folder.getId() };
}

/** The transcript, written beside the audio in the SAME folder.
 *
 *  Replace, never add — the same trap as putAudio_. A retranscribe
 *  writes text.txt a second time and must leave exactly one file, or
 *  the folder ends up holding two transcripts with no way to tell which
 *  is current.
 *
 *  The sheet row is updated in the same call, so has_text and chars can
 *  never disagree with what is actually in Drive. Doing it in two calls
 *  would leave a window where the list says "pull" for a recording that
 *  has no text. */
function putText_(body) {
  var user = safeName_(body.user);
  var recId = safeName_(body.rec_id);
  if (!user || !recId) return { ok: false, error: 'user and rec_id required' };

  var text = String(body.text == null ? '' : body.text);

  // THE PAIR IS ENFORCED HERE, and this was a real bug caught by test F1.
  //
  // recFolder_ CREATES the folder when it is missing — correct for
  // putAudio_, where the first part is what brings a recording into
  // existence. For text it is wrong: writing text for an unknown rec_id
  // would mint a folder holding a transcript and no audio, with no row
  // in the index, which is precisely the half of a pair that must never
  // exist. The sheet is the index, so the row is what says a recording
  // is real.
  if (findRecRow_(user, recId) < 0) {
    return { ok: false, error: 'no such recording' };
  }

  var folder;
  try {
    folder = recFolder_(user, recId);
  } catch (err) {
    return { ok: false, error: 'no such recording' };
  }

  var old = folder.getFilesByName(TEXT_NAME);
  while (old.hasNext()) old.next().setTrashed(true);

  // UTF-8 explicitly. Croatian is the first language of this app and
  // č/ć/š/ž/đ must survive the round trip; the default charset would
  // depend on the script's locale, which is not something to leave to
  // chance for the only content the user actually wrote.
  var blob = Utilities.newBlob('', 'text/plain', TEXT_NAME)
                      .setDataFromString(text, 'UTF-8');
  var file = folder.createFile(blob);

  var chars = text.length;
  setTextFlags_(user, recId, chars > 0, chars);

  return { ok: true, file_id: file.getId(), name: TEXT_NAME, chars: chars };
}

/** Read the transcript back. Instant and free next to a retranscribe,
 *  which is the whole point of storing it. */
function getText_(body) {
  var user = safeName_(body.user);
  var recId = safeName_(body.rec_id);
  if (!user || !recId) return { ok: false, error: 'user and rec_id required' };

  var folder;
  try {
    folder = recFolder_(user, recId);
  } catch (err) {
    return { ok: false, error: 'no such recording' };
  }
  var it = folder.getFilesByName(TEXT_NAME);
  if (!it.hasNext()) return { ok: false, error: 'no text stored' };

  var text = it.next().getBlob().getDataAsString('UTF-8');
  return { ok: true, text: text, chars: text.length };
}

/** Keep the index honest about what the store holds. Silent when the row
 *  is missing: an orphan recording is a real state (registration happens
 *  after upload, on purpose) and it must not turn a good text write into
 *  a reported failure. */
/** Sheet row number for a recording, or -1. One place that knows how a
 *  row is matched, so the index cannot be searched two different ways. */
function findRecRow_(user, recId) {
  var s = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('recordings');
  if (!s || s.getLastRow() < 2) return -1;
  var vals = s.getRange(2, 1, s.getLastRow() - 1, 2).getValues();
  for (var i = 0; i < vals.length; i++) {
    if (safeName_(vals[i][0]) === safeName_(user) &&
        safeName_(vals[i][1]) === safeName_(recId)) {
      return i + 2;
    }
  }
  return -1;
}

function setTextFlags_(user, recId, hasText, chars) {
  var row = findRecRow_(user, recId);
  if (row < 0) return false;
  var s = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('recordings');
  s.getRange(row, REC_HEADERS.indexOf('has_text') + 1)
   .setValue(hasText ? 'TRUE' : 'FALSE');
  s.getRange(row, REC_HEADERS.indexOf('chars') + 1).setValue(Number(chars || 0));
  return true;
}

/** One row per recording, so the archive survives a cleared browser.
 *  Re-registering the same rec_id updates its row instead of adding a
 *  second one — doing it twice must change nothing. */
function registerRec_(body) {
  var user = safeName_(body.user);
  var recId = safeName_(body.rec_id);
  if (!user || !recId) return { ok: false, error: 'user and rec_id required' };

  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var s = recSheet_(ss);
  var hasText = body.has_text ? 'TRUE' : 'FALSE';
  var chars = Number(body.chars || 0);

  var last = s.getLastRow();
  if (last > 1) {
    var vals = s.getRange(2, 1, last - 1, REC_HEADERS.length).getValues();
    var iHas = REC_HEADERS.indexOf('has_text');
    var iChars = REC_HEADERS.indexOf('chars');
    for (var i = 0; i < vals.length; i++) {
      if (safeName_(vals[i][0]) === user && safeName_(vals[i][1]) === recId) {
        // PRESERVE THE TEXT FLAGS unless this call actually carries them.
        // Registration runs BEFORE the transcript is written, and a
        // retranscribe re-registers; blindly writing FALSE here would
        // tell the list there is no text for a recording whose text.txt
        // is sitting in Drive, and the row would offer "retranscribe"
        // for something that could simply be pulled.
        if (body.has_text === undefined) {
          hasText = String(vals[i][iHas] || 'FALSE');
          chars = Number(vals[i][iChars] || 0);
        }
        s.getRange(i + 2, 1, 1, REC_HEADERS.length).setValues([[
          user, recId, new Date(), Number(body.seconds || 0),
          Number(body.parts || 0), String(body.folder_id || ''),
          String(body.language || ''), String(body.note || ''),
          hasText, chars]]);
        return { ok: true, updated: true };
      }
    }
  }
  s.appendRow([user, recId, new Date(), Number(body.seconds || 0),
               Number(body.parts || 0), String(body.folder_id || ''),
               String(body.language || ''), String(body.note || ''),
               hasText, chars]);
  return { ok: true, updated: false };
}

/** Everything this user has, newest first. No content, only ids. */
function listRecs_(user) {
  user = safeName_(user);
  var s = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('recordings');
  var out = [];
  if (!s || s.getLastRow() < 2) return out;
  var vals = s.getRange(2, 1, s.getLastRow() - 1, REC_HEADERS.length).getValues();
  vals.forEach(function (r) {
    if (safeName_(r[0]) !== user) return;
    out.push({ rec_id: String(r[1]), created: String(r[2]),
               seconds: Number(r[3] || 0), parts: Number(r[4] || 0),
               folder_id: String(r[5] || ''), language: String(r[6] || ''),
               note: String(r[7] || ''),
               // String(true) is 'true' and the sheet stores 'TRUE', so
               // compare case-insensitively — a checkbox column and a
               // text column must both read as the same boolean.
               has_text: String(r[8] || '').toUpperCase() === 'TRUE',
               chars: Number(r[9] || 0) });
  });
  return out.reverse();
}

/** Trash the audio and forget the row. Baba's "until he chooses to
 *  delete it" — nothing here expires on its own. */
function deleteRec_(body) {
  var user = safeName_(body.user);
  var recId = safeName_(body.rec_id);
  if (!user || !recId) return { ok: false, error: 'user and rec_id required' };
  try {
    var folder = recFolder_(user, recId);
    var files = folder.getFiles();
    while (files.hasNext()) files.next().setTrashed(true);
    folder.setTrashed(true);
  } catch (err) { /* already gone is success */ }

  var s = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('recordings');
  if (s && s.getLastRow() > 1) {
    var vals = s.getRange(2, 1, s.getLastRow() - 1, 2).getValues();
    for (var i = vals.length - 1; i >= 0; i--) {
      if (safeName_(vals[i][0]) === user && safeName_(vals[i][1]) === recId) {
        s.deleteRow(i + 2);
      }
    }
  }
  return { ok: true };
}

// ---------------------------------------------------------------------
//  READ — called from doGet with what=audio
//
//  Returns base64, because ContentService can only serve text. This is a
//  platform limit, not a choice: there is no way to hand raw audio back
//  from a web app, so the app decodes it and passes the bytes to Whisper
//  itself. Confirmed against the ContentService docs before building.
// ---------------------------------------------------------------------

function getAudio_(p) {
  var recId = safeName_(p.rec_id);
  var user = safeName_(p.user);
  var part = String(p.part || '0');
  var exp = Number(p.exp || 0);

  if (!recId || !user) return { ok: false, error: 'user and rec_id required' };
  if (!exp || exp < nowSecs_()) return { ok: false, error: 'link expired' };
  if (exp > nowSecs_() + 86400) return { ok: false, error: 'expiry too far' };
  if (!sameSig_(p.sig, signPart_(recId, part, exp))) {
    return { ok: false, error: 'bad signature' };
  }

  var name = 'part_' + ('000' + Number(part)).slice(-4) + '.flac';
  var folder;
  try {
    folder = recFolder_(user, recId);
  } catch (err) {
    return { ok: false, error: 'no such recording' };
  }
  var it = folder.getFilesByName(name);
  if (!it.hasNext()) return { ok: false, error: 'no such part' };

  var blob = it.next().getBlob();
  return { ok: true, part: Number(part), name: name,
           data: Utilities.base64Encode(blob.getBytes()) };
}
