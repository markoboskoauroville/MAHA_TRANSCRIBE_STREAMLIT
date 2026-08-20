/**
 * ═══════════════════════════════════════════════════════════════════
 *  TTT-LLL AUTH — the accounts script.
 * ═══════════════════════════════════════════════════════════════════
 *
 *  This is a SECOND, SEPARATE Apps Script project. It is standalone —
 *  not attached to the spreadsheet — because a Google Sheet can only
 *  ever have one script bound to it, and the main TTT-LLL script is
 *  already that one. So this one opens the sheet BY ID instead.
 *
 *  Two consequences of being standalone, both deliberate:
 *    * there is no TTT-LLL menu here. Setup runs from the editor.
 *    * SpreadsheetApp.getActiveSpreadsheet() does not work. Use sheet_().
 *
 *  NOTHING SECRET IS WRITTEN IN THIS FILE. The pepper and the two
 *  tokens live in Project Settings -> Script Properties, which is not
 *  part of the source and never reaches git.
 *
 * ───────────────────────────────────────────────────────────────────
 *  WHAT YOU FILL IN — one line, below. Everything else is machinery.
 * ───────────────────────────────────────────────────────────────────
 */

// The spreadsheet this script reads and writes. Not a secret: it is an
// address, not a key. Who may open it is Google's business, not ours.
var SHEET_ID = '18UPcHrawQ17l17fcLDi1YRTkjbS1LoQ5NXDDp-wtBEM';


// ─── SCRIPT PROPERTIES ───────────────────────────────────────────────
// Set by hand in Project Settings. Named here, never valued here.
//
//   AUTH_PEPPER       a secret that is NOT in the sheet and NOT in
//                     Streamlit. It is what makes a leaked spreadsheet
//                     useless on its own: the hashes in it cannot be
//                     attacked offline without this.
//   AUTH_LOGIN_TOKEN  may only ask "is this pair right".
//   AUTH_ADMIN_TOKEN  may change users. Sent only when the app already
//                     believes the caller is the administrator.
var P_PEPPER = 'AUTH_PEPPER';
var P_LOGIN  = 'AUTH_LOGIN_TOKEN';
var P_ADMIN  = 'AUTH_ADMIN_TOKEN';


// ─── HOW SLOW A PASSWORD IS ──────────────────────────────────────────
// Deliberate cost. A person waits this once; someone guessing waits it
// for every guess, which is the entire point.
//
// Measured on Google's own servers, not guessed — see benchmark() at
// the bottom of this file. Stored PER USER in the sheet as well, so
// this number can be raised later without invalidating anybody: an old
// row keeps verifying at its own rounds until their next reset.
var ROUNDS = 1000;   // measured 20.8.2026: 497 ms on Google's servers
//
// Apps Script is SLOW at this — one HMAC round costs 0.5 ms, so half a
// second buys a thousand rounds and no more. That is a low number by
// the standards of a public login. It is enough HERE because the
// pepper is not in the sheet: the realistic attack is somebody reading
// the spreadsheet, and without the pepper the rounds barely matter.
// Re-run benchmark() if Google ever gets faster.


function prop_(name) {
  var v = PropertiesService.getScriptProperties().getProperty(name);
  if (!v) throw new Error('script property not set: ' + name);
  return v;
}

function sheet_() {
  return SpreadsheetApp.openById(SHEET_ID);
}


// ═══════════════════════════════════════════════════════════════════
//  THE HASHING
// ═══════════════════════════════════════════════════════════════════

/**
 * A fresh salt, one per person.
 *
 * Math.random() is NOT used, deliberately: it is not made for this and
 * two accounts created in the same second could collide. Utilities
 * .getUuid() is a version-4 UUID from a real random source. Two of them
 * stripped of dashes give 64 hex characters.
 */
function makeSalt_() {
  return (Utilities.getUuid() + Utilities.getUuid()).replace(/-/g, '');
}

/**
 * Turn a password into something that cannot be turned back.
 *
 * HMAC-SHA256, keyed with the pepper, applied `rounds` times. The salt
 * goes into the first round so that two people who happen to choose the
 * same password still get different results — without it, equal hashes
 * would advertise equal passwords to anyone reading the sheet.
 *
 * The repetition is the cost. One round is instant and therefore
 * useless; the number in ROUNDS is chosen so this takes about half a
 * second on Google's servers.
 */
function hashPw_(password, salt, rounds) {
  var key = Utilities.newBlob(prop_(P_PEPPER)).getBytes();
  var acc = Utilities.computeHmacSha256Signature(
              Utilities.newBlob(salt + '|' + String(password)).getBytes(), key);
  for (var i = 1; i < rounds; i++) {
    acc = Utilities.computeHmacSha256Signature(acc, key);
  }
  return Utilities.base64EncodeWebSafe(acc);
}

/**
 * Compare without leaking WHERE two strings first differ.
 *
 * A plain === returns the moment it finds a mismatched character, so
 * the time it takes is a hint about how much of a guess was correct.
 * This always walks the whole length.
 */
function sameHash_(a, b) {
  a = String(a); b = String(b);
  if (a.length !== b.length) return false;
  var diff = 0;
  for (var i = 0; i < a.length; i++) {
    diff |= (a.charCodeAt(i) ^ b.charCodeAt(i));
  }
  return diff === 0;
}


// ═══════════════════════════════════════════════════════════════════
//  TUNING — run benchmark() from the editor, read the log
// ═══════════════════════════════════════════════════════════════════

/**
 * How long does a login cost at various round counts?
 *
 * Times the real hashPw_ on this machine — which is a Google server,
 * not a laptop, and is the only measurement that means anything. Prints
 * a table and the round count nearest half a second.
 */
function benchmark() {
  var salt = makeSalt_();

  // One warm-up. The first crypto call in a run pays a setup cost that
  // is not part of what a real login costs, and counting it would make
  // the answer too slow on purpose.
  hashPw_('warm', salt, 200);

  // Time a small probe, then work out the target arithmetically rather
  // than climbing a ladder of ever-slower runs — a 50,000-round guess
  // on a slow day can take minutes and hit the execution limit.
  var probe = 2000;
  var t0 = Date.now();
  hashPw_('a-password-of-ordinary-length', salt, probe);
  var ms = Date.now() - t0;
  var per = ms / probe;

  var target = Math.round((500 / per) / 1000) * 1000;
  if (target < 1000) target = 1000;

  // Then prove the arithmetic by actually running it.
  var t1 = Date.now();
  hashPw_('a-password-of-ordinary-length', salt, target);
  var check = Date.now() - t1;

  var msg = [
    probe + ' rounds took ' + ms + ' ms',
    'one round is ' + per.toFixed(5) + ' ms',
    'SUGGESTED ROUNDS = ' + target,
    'verified: ' + target + ' rounds took ' + check + ' ms'
  ].join('\n');
  Logger.log(msg);
  return msg;
}


// ═══════════════════════════════════════════════════════════════════
//  THE DOOR
// ═══════════════════════════════════════════════════════════════════

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
                       .setMimeType(ContentService.MimeType.JSON);
}

/**
 * Every request carries a token, and WHICH token decides what it may
 * ask for. The login token can only ever ask "is this pair right"; it
 * cannot change a thing. Changing users needs the admin token, which
 * the app only ever sends when it already believes the caller is the
 * administrator.
 *
 * Two tokens rather than one so that the loud, everyday path — a login
 * from a phone — carries a credential that is useless for damage.
 */
function doPost(e) {
  try {
    var body = JSON.parse(e.postData.contents);
    var tok  = String(body.token || '');
    var isLogin = sameHash_(tok, prop_(P_LOGIN));
    var isAdmin = sameHash_(tok, prop_(P_ADMIN));
    if (!isLogin && !isAdmin) return json_({ ok: false, error: 'bad token' });

    if (body.what === 'login') return json_(login_(body));

    // EVERYTHING BELOW NEEDS THE ADMIN TOKEN. The login token can
    // reach exactly one thing, above, and it cannot change anything.
    if (body.what === 'users')         { return isAdmin ? json_({ ok: true, users: userList_() })
                                                       : json_({ ok: false, error: 'admin token required' }); }
    if (body.what === 'user_create')   { return isAdmin ? json_(userCreate_(body))
                                                       : json_({ ok: false, error: 'admin token required' }); }
    if (body.what === 'user_delete')   { return isAdmin ? json_(userDelete_(body))
                                                       : json_({ ok: false, error: 'admin token required' }); }
    if (body.what === 'user_rename')   { return isAdmin ? json_(userRename_(body))
                                                       : json_({ ok: false, error: 'admin token required' }); }
    if (body.what === 'user_password') { return isAdmin ? json_(userPassword_(body))
                                                       : json_({ ok: false, error: 'admin token required' }); }

    if (body.what === 'ping') {
      return json_({ ok: true, admin: isAdmin, rounds: ROUNDS });
    }

    // Timing run. Admin only: it is deliberately expensive, which is
    // exactly what you do not hand to anyone holding the login token.
    if (body.what === 'bench') {
      if (!isAdmin) return json_({ ok: false, error: 'admin token required' });
      var n = Math.max(1, Math.min(200000, Number(body.rounds) || 1000));
      var salt = makeSalt_();
      var t0 = Date.now();
      hashPw_('a-password-of-ordinary-length', salt, n);
      return json_({ ok: true, rounds: n, ms: Date.now() - t0 });
    }

    return json_({ ok: false, error: 'unknown request' });
  } catch (err) {
    return json_({ ok: false, error: String(err) });
  }
}


// ═══════════════════════════════════════════════════════════════════
//  THE USERS TAB
// ═══════════════════════════════════════════════════════════════════

/**
 * THE SAME TAB THE MAIN SCRIPT ALREADY USES, WITH COLUMNS ADDED ON THE
 * RIGHT. Not a new tab, on purpose.
 *
 *   1 username | 2 password | 3 engine | 4 note | 5 salt | 6 hash | 7 rounds
 *   \______ the main script reads exactly these four ______/
 *
 * The main TTT-LLL script's userRows_() asks for four columns and gets
 * four columns; anything to the right of them is invisible to it. So
 * this script can add hashing to the same rows WITHOUT touching the old
 * login, the engine panel, or the per-user tabs — nothing to keep in
 * sync, and nothing that can disagree about who is called what.
 *
 * Column 2 stays for now and is emptied at migration. Once it is empty
 * the old plaintext login simply stops matching and falls through to
 * APP_PASSWORDS, which is exactly what it is designed to do.
 */
var C_USER = 1, C_PASS = 2, C_ENGINE = 3, C_NOTE = 4;
var C_SALT = 5, C_HASH = 6, C_ROUNDS = 7;
var N_COLS = 7;

function userRows_() {
  var s = sheet_().getSheetByName('users');
  if (!s || s.getLastRow() < 2) return [];
  var wide = Math.max(s.getLastColumn(), N_COLS);
  return s.getRange(2, 1, s.getLastRow() - 1, wide).getValues();
}

function cell_(row, col) {
  var v = row[col - 1];
  return v == null ? '' : String(v);
}


// ═══════════════════════════════════════════════════════════════════
//  LOGIN
// ═══════════════════════════════════════════════════════════════════

/**
 * Is this pair right?
 *
 * EVERY WAY OF FAILING ANSWERS THE SAME WORD. A name nobody has, a
 * wrong password, a tab that does not exist, a sheet that cannot be
 * opened — all of them are 'no'. Telling the difference would tell a
 * guesser which half to keep working on.
 *
 * PLAINTEXT IS NEVER ACCEPTED HERE. A row that still has its old
 * password in column 2 but no hash in column 6 cannot log in through
 * this script at all. That is not an oversight: if this endpoint fell
 * back to comparing plaintext, migrating would be optional and the
 * whole point would quietly rot.
 */
function login_(body) {
  var u = String(body.username || '').trim().toLowerCase();
  var p = String(body.password == null ? '' : body.password);
  if (!u || !p) return { ok: false, error: 'no' };

  var rows;
  try {
    rows = userRows_();
  } catch (err) {
    return { ok: false, error: 'no' };   // never a reason, never a crash
  }

  for (var i = 0; i < rows.length; i++) {
    var name = cell_(rows[i], C_USER).trim().toLowerCase();
    if (!name || name !== u) continue;

    var salt = cell_(rows[i], C_SALT);
    var hash = cell_(rows[i], C_HASH);
    if (!salt || !hash) return { ok: false, error: 'no' };   // not migrated

    // Their OWN round count, not today's. Raising ROUNDS later must not
    // lock out everybody hashed before the change; an old row keeps
    // verifying at its own cost until their next password reset.
    var rounds = Number(cell_(rows[i], C_ROUNDS)) || ROUNDS;

    if (!sameHash_(hashPw_(p, salt, rounds), hash)) {
      return { ok: false, error: 'no' };
    }
    return { ok: true,
             user:   name,
             engine: cell_(rows[i], C_ENGINE).trim().toLowerCase(),
             note:   cell_(rows[i], C_NOTE) };
  }

  // NOBODY OF THAT NAME — and it must not come back faster than a real
  // one would. A quick 'no' for unknown names and a slow 'no' for known
  // ones is a way to read the family list off the login screen, one
  // guess at a time. So do the work anyway and throw it away.
  hashPw_(p, makeSalt_(), ROUNDS);
  return { ok: false, error: 'no' };
}


// ═══════════════════════════════════════════════════════════════════
//  THE ADMINISTRATOR
// ═══════════════════════════════════════════════════════════════════

// An eighth column, and the reason renaming is safe.
//
// Drive folders are USERS/<name>/. If a rename changed the folder name,
// every recording made under the old one would stop being listed —
// HANDOVER §67 already records that happening once. So the folder name
// is written ONCE, at creation, and never changed again. Renaming moves
// the DISPLAY name only; the folder keeps its birth name forever.
//
// Wiring the main script to READ this column is a separate change. Until
// then it is written and unused, which is harmless.
var C_FOLDER = 8;
var HEADERS_ADDED = { 5: 'salt', 6: 'hash', 7: 'rounds', 8: 'folder' };

// Which name may change users. NOT a secret and NOT hardcoded — the app
// should no more contain a specific person's name than a password, and
// an owner who renames himself should not need a code change.
var P_ADMIN_USER = 'AUTH_ADMIN_USER';

function usersSheet_() {
  var s = sheet_().getSheetByName('users');
  if (!s) throw new Error('no users tab');
  for (var c in HEADERS_ADDED) {
    if (!String(s.getRange(1, Number(c)).getValue() || '').trim()) {
      s.getRange(1, Number(c)).setValue(HEADERS_ADDED[c]).setFontWeight('bold');
    }
  }
  return s;
}

/** Row number in the sheet, or 0. Capitals never matter. */
function rowOf_(rows, name) {
  var want = String(name || '').trim().toLowerCase();
  if (!want) return 0;
  for (var i = 0; i < rows.length; i++) {
    if (cell_(rows[i], C_USER).trim().toLowerCase() === want) return i + 2;
  }
  return 0;
}

/**
 * A name that will not cause trouble later.
 *
 * It becomes a Drive folder and a sheet tab, so ADMIN.md's warning is
 * enforced here rather than left as advice: ana-marija is fine, and
 * 'Ana Marija!' is not.
 */
function okName_(name) {
  return /^[a-z0-9][a-z0-9_-]{1,31}$/.test(String(name || '').trim().toLowerCase());
}

/**
 * A password to read out loud once and then never again.
 *
 * Twelve characters in three groups, from an alphabet with no l, o, 0 or
 * 1 in it — those are the ones people mishear and mistype. 256 divides
 * by 32 exactly, so no character is likelier than another.
 */
function makePassword_() {
  var A = 'abcdefghijkmnpqrstuvwxyz23456789';
  var bytes = Utilities.computeHmacSha256Signature(
                Utilities.newBlob(Utilities.getUuid()).getBytes(),
                Utilities.newBlob(Utilities.getUuid()).getBytes());
  var out = [];
  for (var i = 0; i < 12; i++) {
    if (i && i % 4 === 0) out.push('-');
    out.push(A.charAt((bytes[i] & 0xFF) % 32));
  }
  return out.join('');
}

/**
 * THE SECOND FACTOR, for the two things that cannot be undone.
 *
 * The admin token alone is not enough to delete or rename somebody. A
 * token is a string that can leak — into a log, a screenshot, a chat
 * window. Proving the administrator's own password at the moment of the
 * act needs the person, not just the string.
 *
 * The name must match AUTH_ADMIN_USER, or anyone holding the token could
 * nominate themselves administrator and prove their own password.
 */
function adminProved_(body) {
  var who = String(prop_(P_ADMIN_USER) || '').trim().toLowerCase();
  if (!who) return false;
  var got = login_({ username: body.admin_user, password: body.admin_password });
  return got.ok === true && got.user === who;
}

function withLock_(fn) {
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(10000)) return { ok: false, error: 'busy, try again' };
  try { return fn(); } finally { lock.releaseLock(); }
}


/** Make a person. The password is returned ONCE and is never stored. */
function userCreate_(body) {
  return withLock_(function () {
    var u = String(body.username || '').trim().toLowerCase();
    if (!okName_(u)) return { ok: false, error: 'bad name: letters, digits, - and _ only' };

    var s = usersSheet_();
    var rows = userRows_();
    if (rowOf_(rows, u)) return { ok: false, error: 'that name is taken' };

    var e = String(body.engine || '').trim().toLowerCase();
    if (e && e !== 'free' && e !== 'studio') return { ok: false, error: 'not an engine: ' + e };

    var pw = makePassword_();
    var salt = makeSalt_();
    s.appendRow([u, '', e, String(body.note || ''),
                 salt, hashPw_(pw, salt, ROUNDS), ROUNDS, u]);

    // The only time this password exists anywhere. Not stored, not
    // recoverable, not printed twice.
    return { ok: true, user: u, password: pw };
  });
}

/** Unmake a person. Their recordings are deliberately left alone. */
function userDelete_(body) {
  return withLock_(function () {
    if (!adminProved_(body)) return { ok: false, error: 'administrator password required' };
    var u = String(body.username || '').trim().toLowerCase();

    // YOU MAY NOT DELETE YOURSELF. There would be no way back in.
    if (u === String(prop_(P_ADMIN_USER) || '').trim().toLowerCase()) {
      return { ok: false, error: 'the administrator cannot be deleted' };
    }

    var s = usersSheet_();
    var row = rowOf_(userRows_(), u);
    if (!row) return { ok: false, error: 'no such user' };
    s.deleteRow(row);

    // ADMIN.md §3.3: losing a person's audio because you tidied a
    // spreadsheet would be the wrong direction to fail in.
    return { ok: true, user: u, recordings: 'kept' };
  });
}

/** Change the name shown. The Drive folder keeps its birth name. */
function userRename_(body) {
  return withLock_(function () {
    if (!adminProved_(body)) return { ok: false, error: 'administrator password required' };
    var from = String(body.username || '').trim().toLowerCase();
    var to   = String(body.new_username || '').trim().toLowerCase();
    if (!okName_(to)) return { ok: false, error: 'bad name: letters, digits, - and _ only' };

    // Renaming the administrator would leave AUTH_ADMIN_USER pointing at
    // a name that no longer exists, and no admin action would work again.
    if (from === String(prop_(P_ADMIN_USER) || '').trim().toLowerCase()) {
      return { ok: false, error: 'change AUTH_ADMIN_USER in Script Properties first' };
    }

    var s = usersSheet_();
    var rows = userRows_();
    var row = rowOf_(rows, from);
    if (!row) return { ok: false, error: 'no such user' };
    if (from !== to && rowOf_(rows, to)) return { ok: false, error: 'that name is taken' };

    s.getRange(row, C_USER).setValue(to);
    // C_FOLDER is NOT touched. That is the whole point.
    return { ok: true, user: to, was: from,
             folder: cell_(rows[row - 2], C_FOLDER) || from };
  });
}

/** A new password, shown once. The old one cannot be recovered. */
function userPassword_(body) {
  return withLock_(function () {
    var u = String(body.username || '').trim().toLowerCase();
    var s = usersSheet_();
    var row = rowOf_(userRows_(), u);
    if (!row) return { ok: false, error: 'no such user' };

    var pw = makePassword_();
    var salt = makeSalt_();
    // Re-hashed at TODAY'S cost, not the cost it was made at. A reset is
    // the moment an old, cheaper row quietly becomes a current one.
    s.getRange(row, C_SALT).setValue(salt);
    s.getRange(row, C_HASH).setValue(hashPw_(pw, salt, ROUNDS));
    s.getRange(row, C_ROUNDS).setValue(ROUNDS);
    s.getRange(row, C_PASS).setValue('');   // never plaintext, ever again
    return { ok: true, user: u, password: pw };
  });
}

/** Names, engines and notes. No passwords, no hashes, no salts. */
function userList_() {
  return userRows_().map(function (r) {
    return { user:   cell_(r, C_USER).trim().toLowerCase(),
             engine: cell_(r, C_ENGINE).trim().toLowerCase(),
             note:   cell_(r, C_NOTE),
             folder: cell_(r, C_FOLDER),
             hashed: !!(cell_(r, C_SALT) && cell_(r, C_HASH)) };
  }).filter(function (r) { return r.user; });
}


// ═══════════════════════════════════════════════════════════════════
//  THE MIGRATION — run ONCE, from the editor
// ═══════════════════════════════════════════════════════════════════

/**
 * NOT AN ENDPOINT, ON PURPOSE. There is no `what` that reaches this.
 * A one-way, whole-table rewrite should need somebody sitting in the
 * Apps Script editor deciding to do it, not a JSON body arriving from
 * the internet with the right token in it.
 *
 * WHAT IT DOES, per row:
 *   reads the plaintext password in column 2
 *   makes a salt, hashes THAT SAME PASSWORD with it
 *   writes salt, hash, rounds, and the folder name (= today's username)
 *   empties column 2
 *
 * NOBODY'S PASSWORD CHANGES. What they type tomorrow is what they typed
 * yesterday; only the way the sheet remembers it changes. That is why
 * this is a migration and not a mass reset.
 *
 * IT IS ONE-WAY. After it runs, no one — you included — can read a
 * password out of the sheet again. Write them down first if you want
 * them; afterwards the only repair is a reset.
 *
 * IT IS SAFE TO RUN TWICE. A row that already has a salt and a hash is
 * left alone, so a half-finished run can simply be run again.
 */

function migrateReport_(commit) {
  var s = usersSheet_();
  var rows = userRows_();
  var done = [], already = [], stuck = [], blank = 0;

  for (var i = 0; i < rows.length; i++) {
    var row = i + 2;
    var name = cell_(rows[i], C_USER).trim().toLowerCase();
    if (!name) { blank++; continue; }

    if (cell_(rows[i], C_SALT) && cell_(rows[i], C_HASH)) { already.push(name); continue; }

    var plain = cell_(rows[i], C_PASS);
    if (!plain) {
      // No password to carry over and no hash yet. This person cannot be
      // migrated and cannot log in — they need a reset, which is a
      // decision, not something a migration should make silently.
      stuck.push(name);
      continue;
    }

    if (commit) {
      var salt = makeSalt_();
      s.getRange(row, C_SALT).setValue(salt);
      s.getRange(row, C_HASH).setValue(hashPw_(plain, salt, ROUNDS));
      s.getRange(row, C_ROUNDS).setValue(ROUNDS);
      if (!cell_(rows[i], C_FOLDER)) s.getRange(row, C_FOLDER).setValue(name);
      // LAST. If anything above threw, the plaintext is still there and
      // the row is simply not migrated yet — rather than a person with
      // no password at all.
      s.getRange(row, C_PASS).setValue('');
    }
    done.push(name);
  }

  return { ok: true, committed: !!commit,
           migrated: done, already_hashed: already,
           no_password: stuck, blank_rows: blank, rounds: ROUNDS };
}

/** Changes NOTHING. Says what a real run would do. Run this first. */
function migratePreview() {
  var r = migrateReport_(false);
  Logger.log([
    'DRY RUN — nothing was changed.',
    'would migrate (' + r.migrated.length + '): ' + (r.migrated.join(', ') || '-'),
    'already hashed (' + r.already_hashed.length + '): ' + (r.already_hashed.join(', ') || '-'),
    'CANNOT migrate, no password (' + r.no_password.length + '): ' + (r.no_password.join(', ') || '-'),
    'blank rows skipped: ' + r.blank_rows,
    'rounds to be used: ' + r.rounds
  ].join('\n'));
  return r;
}

/** The real thing. One way. Run migratePreview() first. */
function migrateRun() {
  var r = withLock_(function () { return migrateReport_(true); });
  Logger.log([
    'DONE — the plaintext column is now empty for these people.',
    'migrated (' + r.migrated.length + '): ' + (r.migrated.join(', ') || '-'),
    'already hashed (' + r.already_hashed.length + '): ' + (r.already_hashed.join(', ') || '-'),
    'CANNOT log in until reset (' + r.no_password.length + '): ' + (r.no_password.join(', ') || '-')
  ].join('\n'));
  return r;
}
