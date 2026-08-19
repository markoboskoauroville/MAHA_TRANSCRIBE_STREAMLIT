// =====================================================================
//  TTT-LLL — DRIVE AUDIO STORAGE
//  ADD THIS TO THE BOTTOM OF Code.gs, AFTER config_addition.gs
//
//  WHAT IT DOES
//  Keeps each user's levelled 16 kHz audio in your Drive, so changing
//  the language and transcribing again costs no upload from the phone.
//
//  WHAT YOU MUST CHANGE — three lines, marked CHANGE ME below:
//    DRIVE_ROOT_ID    the folder you already made
//    DRIVE_SECRET  a NEW long random string, NOT the same as
//                     SHEETS_TOKEN
//  Put DRIVE_SECRET in Streamlit secrets too, as DRIVE_SECRET.
//
//  WHY A SECOND SECRET. SHEETS_TOKEN unlocks doGet, which returns your
//  settings AND your API keys. The download link is the part most likely
//  to end up in a log somewhere, so it gets its own credential and its
//  own expiry. Losing the download secret must never cost you the keys.
//
//  ONE EDIT TO EXISTING CODE IS ALSO REQUIRED — see STEP 2 in the
//  handover, or the comment marked *** in this file's putAudio note.
//  Without it, doPost writes a usage row for every audio chunk.
//
//  Run setupDrive() ONCE from the editor after pasting, then redeploy:
//  Deploy > Manage deployments > pencil > New version.
// =====================================================================

/** CHANGE ME — the Drive folder that holds everything. Take the id from
 *  its URL: drive.google.com/drive/folders/THIS_PART */
var DRIVE_ROOT_ID = 'PUT_YOUR_FOLDER_ID_HERE';

/** CHANGE ME — a NEW long random string. NOT SHEETS_TOKEN. */
var DRIVE_SECRET = 'CHANGE_ME_to_a_different_long_random_string';

/** How long a download link stays valid. Short on purpose: the app signs
 *  one the moment it needs it, so it never needs to last. */
var LINK_SECONDS = 600;

/** Guard rails. The platform refuses a request body over 50 MiB — this
 *  is measured, not guessed — so the app sends one 10-minute part at a
 *  time (~14 MB as base64). Anything near the ceiling is a bug in the
 *  caller, and is refused here rather than half-written to Drive. */
var MAX_PART_BYTES = 40 * 1024 * 1024;

var REC_HEADERS = ['user', 'rec_id', 'created', 'seconds', 'parts',
                   'folder_id', 'language', 'note'];

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

/** One row per recording, so the archive survives a cleared browser.
 *  Re-registering the same rec_id updates its row instead of adding a
 *  second one — doing it twice must change nothing. */
function registerRec_(body) {
  var user = safeName_(body.user);
  var recId = safeName_(body.rec_id);
  if (!user || !recId) return { ok: false, error: 'user and rec_id required' };

  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var s = recSheet_(ss);
  var row = [user, recId, new Date(), Number(body.seconds || 0),
             Number(body.parts || 0), String(body.folder_id || ''),
             String(body.language || ''), String(body.note || '')];

  var last = s.getLastRow();
  if (last > 1) {
    var vals = s.getRange(2, 1, last - 1, 2).getValues();
    for (var i = 0; i < vals.length; i++) {
      if (safeName_(vals[i][0]) === user && safeName_(vals[i][1]) === recId) {
        s.getRange(i + 2, 1, 1, REC_HEADERS.length).setValues([row]);
        return { ok: true, updated: true };
      }
    }
  }
  s.appendRow(row);
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
               note: String(r[7] || '') });
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
