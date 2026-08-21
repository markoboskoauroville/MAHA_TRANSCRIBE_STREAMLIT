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

    // Reachable with the LOGIN token, all three. None of them can be
    // used without something the caller must already know: a valid
    // remember token, or the current password.
    if (body.what === 'remember_login')  return json_(rememberLogin_(body));
    if (body.what === 'remember_forget') return json_(rememberForget_(body));
    if (body.what === 'password_change') return json_(passwordChange_(body));

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
    if (body.what === 'user_engine')   { return isAdmin ? json_(userEngine_(body))
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
var N_COLS = 9;

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
    var out = { ok: true,
                user:   name,
                engine: cell_(rows[i], C_ENGINE).trim().toLowerCase(),
                note:   cell_(rows[i], C_NOTE) };

    // A remember token, ONLY when the tick-box asked for one. Wrapped
    // because a login must never fail over a convenience: if minting
    // throws, they are still logged in, just not remembered.
    if (body.remember) {
      try {
        out.remember = rememberMint_(sheet_().getSheetByName('users'),
                                     i + 2, cell_(rows[i], C_REMEMBER));
      } catch (err) { /* logged in anyway */ }
    }
    return out;
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
var HEADERS_ADDED = { 5: 'salt', 6: 'hash', 7: 'rounds', 8: 'folder',
                      9: 'remember' };

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
    // THE SAME SECOND FACTOR AS DELETE AND RENAME. A reset is not the
    // gentle one of the three: it locks the person out of their own
    // account and signs every remembered device out below. The token
    // alone is a string that can leak; this needs the person.
    if (!adminProved_(body)) return { ok: false, error: 'administrator password required' };
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
    // A reset exists to get somebody OUT as much as to let them back in.
    // Leaving their old phone logged in would defeat half of that.
    rememberClear_(s, row);
    return { ok: true, user: u, password: pw };
  });
}

/**
 * Give one person their own engine, or take it away.
 *
 * THIS SCRIPT OWNS THE USERS TAB NOW. The main script's `set_user_engine`
 * writes the same column, and two writers with a lock between them in
 * only one of the scripts is a race waiting for a Sunday. It also has a
 * plainer benefit: the owner's panel needs ONE token and ONE reachable
 * script to do all five things, so a half-deployed main script can no
 * longer make the list of people look empty.
 *
 * AN EMPTY STRING IS A REAL ANSWER, not a missing one: it means "use the
 * global engine", and it is the way back from a choice.
 */
function userEngine_(body) {
  return withLock_(function () {
    var u = String(body.username || '').trim().toLowerCase();
    var e = String(body.engine || '').trim().toLowerCase();
    if (e && e !== 'free' && e !== 'studio') return { ok: false, error: 'not an engine: ' + e };

    var s = usersSheet_();
    var row = rowOf_(userRows_(), u);
    if (!row) return { ok: false, error: 'no such user' };

    s.getRange(row, C_ENGINE).setValue(e);
    // The reply NAMES THE USER BACK on purpose. §47: a deployment
    // without this branch falls through and still answers ok, so the
    // caller must have something to check other than the word ok.
    return { ok: true, user: u, engine: e };
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


// ═══════════════════════════════════════════════════════════════════
//  FIRST RUN — the tab, and the administrator
// ═══════════════════════════════════════════════════════════════════

var ALL_HEADERS = ['username', 'password', 'engine', 'note',
                   'salt', 'hash', 'rounds', 'folder', 'remember'];

// Where you put your chosen password for ONE run.
//
// Not a constant in this file: this file is committed to git, and a
// password typed into it would be committed with it and stay in the
// history afterwards even if deleted. A script property is not part of
// the source, and setupAdmin() removes it as soon as it has been used.
var SETUP_PW_PROP = 'AUTH_SETUP_PASSWORD';

/** The tab, with all eight headers. Made if missing, repaired if partial. */
function ensureUsersSheet_() {
  var ss = sheet_();
  var s = ss.getSheetByName('users');
  if (!s) {
    s = ss.insertSheet('users');
    s.appendRow(ALL_HEADERS);
    s.setFrozenRows(1);
    s.setColumnWidth(1, 140); s.setColumnWidth(2, 160);
    s.setColumnWidth(3, 110); s.setColumnWidth(4, 240);
    s.setColumnWidth(5, 260); s.setColumnWidth(6, 300);
    s.setColumnWidth(7, 80);  s.setColumnWidth(8, 140);
    s.setColumnWidth(9, 300);
  }
  for (var i = 0; i < ALL_HEADERS.length; i++) {
    if (!String(s.getRange(1, i + 1).getValue() || '').trim()) {
      s.getRange(1, i + 1).setValue(ALL_HEADERS[i]);
    }
  }
  s.getRange(1, 1, 1, ALL_HEADERS.length).setFontWeight('bold');
  return s;
}

/**
 * RUN THIS ONCE, FROM THE EDITOR. It makes the users tab and your own
 * account, and nothing else.
 *
 * BEFORE RUNNING, in Project Settings -> Script Properties:
 *   AUTH_SETUP_PASSWORD  = the password you want
 *
 * Leave it out and one is generated for you instead. Either way the
 * password is printed to the log ONCE, and the property is deleted as
 * soon as it has been used — so it does not sit in the project settings
 * afterwards waiting to be read by whoever opens them next.
 *
 * The account is named after AUTH_ADMIN_USER, not a name written here,
 * so the administrator and the person who may delete users are by
 * construction the same person.
 *
 * It will NOT overwrite an existing account. If you already have one and
 * have lost the password, reset it instead — that is what a reset is for.
 */
function setupAdmin() {
  var props = PropertiesService.getScriptProperties();

  var who = String(props.getProperty(P_ADMIN_USER) || '').trim().toLowerCase();
  if (!who) { Logger.log('AUTH_ADMIN_USER is not set. Set it first.'); return; }
  if (!okName_(who)) { Logger.log('AUTH_ADMIN_USER is not a usable name: ' + who); return; }

  // Fail before touching the sheet if the pepper is missing, rather than
  // making a tab and then dying halfway through the account.
  prop_(P_PEPPER);

  var chosen = String(props.getProperty(SETUP_PW_PROP) || '');
  var generated = !chosen;
  var pw = generated ? makePassword_() : chosen;

  var s = ensureUsersSheet_();
  if (rowOf_(userRows_(), who)) {
    Logger.log([
      'There is already an account called "' + who + '". Nothing was changed.',
      'If you have lost the password, reset it rather than making a second one.'
    ].join('\n'));
    props.deleteProperty(SETUP_PW_PROP);
    return;
  }

  var salt = makeSalt_();
  s.appendRow([who, '', '', 'administrator',
               salt, hashPw_(pw, salt, ROUNDS), ROUNDS, who]);

  // Used, and gone. It existed in the project settings for one run.
  props.deleteProperty(SETUP_PW_PROP);

  Logger.log([
    'Made the users tab and one account.',
    '',
    '    username:  ' + who,
    '    password:  ' + pw,
    '',
    (generated ? 'That password was generated for you — nothing was set in'
               + ' AUTH_SETUP_PASSWORD.'
               : 'That is the password you chose. AUTH_SETUP_PASSWORD has been'
               + ' deleted.'),
    '',
    'WRITE IT DOWN NOW. It is stored only as a hash and cannot be read',
    'back — not by you, not by this script. Losing it means a reset.',
    '',
    'This log keeps it. Clear the execution log if that bothers you.'
  ].join('\n'));
  return { ok: true, user: who };
}


// ═══════════════════════════════════════════════════════════════════
//  REMEMBER ME
// ═══════════════════════════════════════════════════════════════════

/**
 * A NINTH COLUMN, and why it has to exist.
 *
 * The old Remember me stored sha256(password) in the browser and
 * compared it against APP_PASSWORDS — which only ever worked because the
 * app knows those passwords by heart. It does not know the family's, so
 * for every one of them the tick-box silently did nothing.
 *
 * The two obvious shortcuts are both password-equivalents:
 *   * keep the password in the browser — plainly no.
 *   * keep the stored hash and let it stand in for the password — then
 *     anyone who reads the sheet can log in as anybody, and the pepper
 *     stops being worth anything.
 *
 * So the browser holds a long random token, and the sheet holds only its
 * hash. Reading the sheet gets you nothing you can use; losing the phone
 * costs one token, revoked by logging out or by changing the password.
 *
 * Up to REMEMBER_MAX of them, comma-separated: a phone AND a laptop is
 * ordinary, and one column per device would be a column per device.
 */
var C_REMEMBER = 9;
var REMEMBER_MAX = 5;

/**
 * Fast on purpose — ONE round, not ROUNDS.
 *
 * Slow hashing exists to make guessing a human-chosen password
 * expensive. This token is 256 bits of randomness that nobody typed and
 * nobody can guess, so the slow loop would buy nothing and cost half a
 * second on every page load.
 */
function hashTok_(token) {
  return Utilities.base64EncodeWebSafe(
    Utilities.computeHmacSha256Signature(
      Utilities.newBlob('rt|' + String(token)).getBytes(),
      Utilities.newBlob(prop_(P_PEPPER)).getBytes()));
}

function tokList_(cellValue) {
  return String(cellValue || '').split(',')
    .map(function (x) { return x.trim(); })
    .filter(function (x) { return !!x; });
}

/** Mint one, remember its hash, hand the token back exactly once. */
function rememberMint_(sheet, row, existing) {
  var token = makeSalt_() + makeSalt_();
  var list = tokList_(existing);
  list.push(hashTok_(token));
  // Newest kept. An old phone falls off the end rather than the list
  // growing without limit.
  if (list.length > REMEMBER_MAX) list = list.slice(list.length - REMEMBER_MAX);
  sheet.getRange(row, C_REMEMBER).setValue(list.join(','));
  return token;
}

/** Every device forgotten. Used when a password changes, either way. */
function rememberClear_(sheet, row) {
  sheet.getRange(row, C_REMEMBER).setValue('');
}

/**
 * Log in with a token instead of a password.
 *
 * Answers exactly like login_ does — same shape, same flat 'no' for
 * every kind of failure — so the caller cannot tell a stale token from
 * an unknown name from a sheet that would not open.
 */
function rememberLogin_(body) {
  var u = String(body.username || '').trim().toLowerCase();
  var tok = String(body.remember || '');
  if (!u || !tok) return { ok: false, error: 'no' };

  var rows;
  try { rows = userRows_(); } catch (err) { return { ok: false, error: 'no' }; }

  for (var i = 0; i < rows.length; i++) {
    if (cell_(rows[i], C_USER).trim().toLowerCase() !== u) continue;
    var want = hashTok_(tok);
    var have = tokList_(cell_(rows[i], C_REMEMBER));
    for (var j = 0; j < have.length; j++) {
      if (sameHash_(have[j], want)) {
        return { ok: true, user: u,
                 engine: cell_(rows[i], C_ENGINE).trim().toLowerCase(),
                 note: cell_(rows[i], C_NOTE) };
      }
    }
    return { ok: false, error: 'no' };
  }
  return { ok: false, error: 'no' };
}

/** Log out on THIS device. The others keep working. */
function rememberForget_(body) {
  return withLock_(function () {
    var u = String(body.username || '').trim().toLowerCase();
    var tok = String(body.remember || '');
    var s, row;
    try {
      s = usersSheet_();
      row = rowOf_(userRows_(), u);
    } catch (err) { return { ok: true };  }   // nothing to forget is fine
    if (!row) return { ok: true };
    if (tok) {
      var gone = hashTok_(tok);
      var keep = tokList_(s.getRange(row, C_REMEMBER).getValue())
                   .filter(function (h) { return !sameHash_(h, gone); });
      s.getRange(row, C_REMEMBER).setValue(keep.join(','));
    }
    return { ok: true };
  });
}


// ═══════════════════════════════════════════════════════════════════
//  CHANGING YOUR OWN PASSWORD
// ═══════════════════════════════════════════════════════════════════

var MIN_PASSWORD = 8;

/**
 * THE OLD PASSWORD IS THE ONLY THING PROVING IT IS REALLY THEM.
 *
 * This is reachable with the LOGIN token, which every phone in the house
 * carries — so the token cannot be the authorisation. Knowing the
 * current password is. That is the same proof the login screen asks for
 * and no weaker, and a leaked login token on its own still changes
 * nothing.
 *
 * EVERY REMEMBERED DEVICE IS FORGOTTEN. ADMIN.md §3.2 complains that a
 * changed password does not evict a browser that ticked Remember me;
 * after this it does, for the person's own change and for the
 * administrator's reset alike.
 */
function passwordChange_(body) {
  return withLock_(function () {
    var u = String(body.username || '').trim().toLowerCase();
    var oldPw = String(body.old_password == null ? '' : body.old_password);
    var newPw = String(body.new_password == null ? '' : body.new_password);

    if (newPw.length < MIN_PASSWORD) {
      return { ok: false, error: 'too short: at least ' + MIN_PASSWORD + ' characters' };
    }
    if (newPw === oldPw) return { ok: false, error: 'that is the same password' };

    // The same check the login screen makes, and the same flat 'no'.
    var proved = login_({ username: u, password: oldPw });
    if (!proved.ok) return { ok: false, error: 'no' };

    var s = usersSheet_();
    var row = rowOf_(userRows_(), u);
    if (!row) return { ok: false, error: 'no' };

    var salt = makeSalt_();
    s.getRange(row, C_SALT).setValue(salt);
    s.getRange(row, C_HASH).setValue(hashPw_(newPw, salt, ROUNDS));
    s.getRange(row, C_ROUNDS).setValue(ROUNDS);
    s.getRange(row, C_PASS).setValue('');
    rememberClear_(s, row);

    // NOTHING COMES BACK. Not the new password, not a hash, not a token.
    return { ok: true, user: u };
  });
}
