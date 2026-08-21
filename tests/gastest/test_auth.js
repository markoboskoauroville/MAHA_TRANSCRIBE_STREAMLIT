/* TEST — THE ACCOUNTS SCRIPT, executed for the first time.
 *
 * Runs the REAL auth_script/Code.gs inside the fake runtime. Until now
 * NOTHING had ever executed this file: the hashing, the second factor,
 * the delete and rename guards and the login itself were all reasoned
 * about and never run. It is the script that guards every login, so it
 * was the worst possible file to have no test.
 *
 * WHAT THIS CANNOT TELL YOU: whether Google's HMAC agrees with node's.
 * The fake is faithful about SHAPE — signed bytes, byte-array messages,
 * web-safe base64 — and every hash here is checked against another hash
 * made the same way. If Google ever disagreed, this suite would still
 * pass and every password would still work, because the sheet only ever
 * compares Google's output with Google's output. What it does prove is
 * that the LOGIC is right: who may do what, what is refused, and what is
 * left behind afterwards.
 *
 *   node tests/gastest/test_auth.js
 */

'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');
const gas = require('./fakegas');

const SRC = path.join(__dirname, '..', '..', 'auth_script', 'Code.gs');

const LOGIN_TOK = 'login-token-aaa';
const ADMIN_TOK = 'admin-token-bbb';
const PEPPER    = 'pepper-ccc';
const ADMIN_PW  = 'admin-password-ddd';

let pass = 0, fail = 0;
const results = [];
function check(name, cond, detail) {
  if (cond) { pass++; results.push('  ok   ' + name); }
  else { fail++; results.push('  FAIL ' + name + (detail !== undefined ? '  — ' + JSON.stringify(detail) : '')); }
}

function loadScript(mutate) {
  let src = fs.readFileSync(SRC, 'utf8');
  // BY PATTERN, never by swapping a CHANGE_ME placeholder — §46: a
  // harness that only matches the placeholder passes on a template and
  // silently runs against the wrong secret on a real filled-in file.
  src = src.replace(/^var SHEET_ID = '[^']*';/m, "var SHEET_ID = 'SHEET';");
  // ROUNDS is 1000 because Google's servers take half a second over it.
  // The COST is not what is being tested here and a thousand rounds per
  // hash makes the suite crawl; the logic is identical at eight.
  src = src.replace(/^var ROUNDS = \d+;/m, 'var ROUNDS = 8;');
  if (mutate) src = mutate(src);

  const ctx = vm.createContext({
    SpreadsheetApp: gas.SpreadsheetApp, Utilities: gas.Utilities,
    ContentService: gas.ContentService, PropertiesService: gas.PropertiesService,
    LockService: gas.LockService, Logger: gas.Logger,
    Date, Math, String, Number, JSON, Object, Array, RegExp, console, require,
  });
  vm.runInContext(src, ctx, { filename: 'auth/Code.gs' });
  return ctx;
}

function post(ctx, body) {
  if (body.token === undefined) body.token = ADMIN_TOK;
  const out = ctx.doPost({ postData: { contents: JSON.stringify(body) } });
  return JSON.parse(out.getContent());
}

/** A world with a users tab and one administrator who can prove himself. */
function fresh(mutate) {
  gas.resetWorld('ROOT');
  gas.resetProps({
    AUTH_PEPPER: PEPPER,
    AUTH_LOGIN_TOKEN: LOGIN_TOK,
    AUTH_ADMIN_TOKEN: ADMIN_TOK,
    AUTH_ADMIN_USER: 'admin',
  });
  const ctx = loadScript(mutate);
  ctx.ensureUsersSheet_();
  // The administrator is made THROUGH the script, so the row is hashed
  // exactly the way a real one is rather than by a hand-built fixture
  // that could drift from what the code writes.
  const made = post(ctx, { what: 'user_create', username: 'admin' });
  // Then given a password we know, the same way a reset does it.
  const s = gas.SS.getSheetByName('users');
  const row = ctx.rowOf_(ctx.userRows_(), 'admin');
  const salt = ctx.makeSalt_();
  s.getRange(row, 5).setValue(salt);
  s.getRange(row, 6).setValue(ctx.hashPw_(ADMIN_PW, salt, 8));
  s.getRange(row, 7).setValue(8);
  return { ctx, made };
}

function proof(extra) {
  return Object.assign({ admin_user: 'admin', admin_password: ADMIN_PW }, extra);
}

function rowOf(ctx, name) {
  return ctx.userList_().filter((r) => r.user === name)[0];
}

// ---------------------------------------------------------------------
// A. the door, and who may open it
// ---------------------------------------------------------------------
console.log('\nTHE ACCOUNTS SCRIPT\n');
{
  const { ctx } = fresh();
  check('1 a wrong token reaches nothing',
        post(ctx, { what: 'ping', token: 'nonsense' }).error === 'bad token');
  check('2 the login token is not the admin token',
        post(ctx, { what: 'ping', token: LOGIN_TOK }).admin === false);
  check('3 the admin token says so', post(ctx, { what: 'ping' }).admin === true);

  const asks = ['users', 'user_create', 'user_delete', 'user_rename',
                'user_password', 'user_engine'];
  const refused = asks.filter((w) => post(ctx, { what: w, token: LOGIN_TOK })
                                       .error === 'admin token required');
  check('4 EVERY admin action refuses the login token — the token every '
        + 'phone in the house carries can change nothing',
        refused.length === asks.length, refused);
}

// ---------------------------------------------------------------------
// B. making a person
// ---------------------------------------------------------------------
{
  const { ctx } = fresh();
  const r = post(ctx, { what: 'user_create', username: 'Baba', note: 'grandfather' });
  check('5 create returns a password, once', !!r.password && r.ok === true, r);
  check('6 and lower-cases the name', r.user === 'baba', r.user);
  check('7 the password it gave WORKS',
        post(ctx, { what: 'login', token: LOGIN_TOK,
                    username: 'baba', password: r.password }).ok === true);
  check('8 and nothing else does',
        post(ctx, { what: 'login', token: LOGIN_TOK,
                    username: 'baba', password: 'guess' }).ok !== true);
  check('9 the sheet keeps NO plaintext', rowOf(ctx, 'baba').hashed === true
        && ctx.userRows_().every((row) => !ctx.cell_(row, 2)));
  check('10 the same name cannot be taken twice',
        post(ctx, { what: 'user_create', username: 'baba' }).error === 'that name is taken');
  check('11 a name with a space is refused',
        /bad name/.test(post(ctx, { what: 'user_create', username: 'two words' }).error || ''));
  // A VALID NAME, deliberately: okName_ runs first and would answer
  // "bad name" to a one-letter username, which would make this check
  // pass while proving nothing about engines at all.
  check('12 an engine that is not an engine is refused',
        /not an engine/.test(post(ctx, { what: 'user_create',
                                         username: 'mama', engine: 'turbo' }).error || ''));
  check('13 two people made in the same moment get DIFFERENT salts — the '
        + 'reason salts come from getUuid and not Math.random',
        (() => {
          post(ctx, { what: 'user_create', username: 'aa' });
          post(ctx, { what: 'user_create', username: 'bb' });
          const rows = ctx.userRows_();
          const salts = rows.map((r) => ctx.cell_(r, 5)).filter(Boolean);
          return new Set(salts).size === salts.length;
        })());
}

// ---------------------------------------------------------------------
// C. THE SECOND FACTOR — the change this session made
// ---------------------------------------------------------------------
{
  const { ctx } = fresh();
  post(ctx, { what: 'user_create', username: 'baba' });

  check('14 RESET NEEDS THE ADMINISTRATOR PASSWORD, not just the token',
        post(ctx, { what: 'user_password', username: 'baba' }).error
          === 'administrator password required');
  check('15 and a WRONG administrator password is refused',
        post(ctx, { what: 'user_password', username: 'baba',
                    admin_user: 'admin', admin_password: 'wrong' }).error
          === 'administrator password required');
  check('16 delete needs it too',
        post(ctx, { what: 'user_delete', username: 'baba' }).error
          === 'administrator password required');
  check('17 rename needs it too',
        post(ctx, { what: 'user_rename', username: 'baba', new_username: 'deda' }).error
          === 'administrator password required');
  check('18 NOBODY MAY NOMINATE THEMSELVES ADMINISTRATOR — proving your '
        + 'own password under another name is not proof',
        post(ctx, { what: 'user_delete', username: 'baba',
                    admin_user: 'baba', admin_password: 'whatever' }).error
          === 'administrator password required');
}

// ---------------------------------------------------------------------
// D. resetting a password
// ---------------------------------------------------------------------
{
  const { ctx } = fresh();
  const made = post(ctx, { what: 'user_create', username: 'baba' });
  // Two remembered devices, so the reset has something to clear.
  const s = gas.SS.getSheetByName('users');
  const row = ctx.rowOf_(ctx.userRows_(), 'baba');
  const tok = ctx.rememberMint_(s, row, '');
  check('19 a remembered device can log in without a password',
        post(ctx, { what: 'remember_login', token: LOGIN_TOK,
                    username: 'baba', remember: tok }).ok === true);

  const r = post(ctx, proof({ what: 'user_password', username: 'baba' }));
  check('20 reset returns a new password', !!r.password && r.password !== made.password, r);
  check('21 the OLD password stops working',
        post(ctx, { what: 'login', token: LOGIN_TOK,
                    username: 'baba', password: made.password }).ok !== true);
  check('22 the new one works',
        post(ctx, { what: 'login', token: LOGIN_TOK,
                    username: 'baba', password: r.password }).ok === true);
  check('23 AND EVERY REMEMBERED DEVICE IS SIGNED OUT — a reset exists to '
        + 'get somebody OUT as much as to let them back in',
        post(ctx, { what: 'remember_login', token: LOGIN_TOK,
                    username: 'baba', remember: tok }).ok !== true);
  check('24 a reset for nobody says so',
        post(ctx, proof({ what: 'user_password', username: 'ghost' })).error === 'no such user');
}

// ---------------------------------------------------------------------
// E. deleting
// ---------------------------------------------------------------------
{
  const { ctx } = fresh();
  post(ctx, { what: 'user_create', username: 'baba' });
  check('25 THE ADMINISTRATOR CANNOT DELETE HIMSELF — there would be no '
        + 'way back in',
        post(ctx, proof({ what: 'user_delete', username: 'admin' })).error
          === 'the administrator cannot be deleted');
  const r = post(ctx, proof({ what: 'user_delete', username: 'baba' }));
  check('26 deleting names the person back, so a deployment that fell '
        + 'through could not answer ok (§47)', r.ok === true && r.user === 'baba', r);
  check('27 and says the recordings were kept', r.recordings === 'kept', r);
  check('28 the row is gone', !rowOf(ctx, 'baba'));
  check('29 and they can no longer log in',
        post(ctx, { what: 'login', token: LOGIN_TOK,
                    username: 'baba', password: 'anything' }).ok !== true);
}

// ---------------------------------------------------------------------
// F. renaming — the folder column is the whole point
// ---------------------------------------------------------------------
{
  const { ctx } = fresh();
  const made = post(ctx, { what: 'user_create', username: 'baba' });
  const r = post(ctx, proof({ what: 'user_rename', username: 'baba',
                              new_username: 'deda' }));
  check('30 rename answers with the NEW name', r.ok === true && r.user === 'deda', r);
  check('31 THE DRIVE FOLDER KEEPS ITS BIRTH NAME — this is why rename is '
        + 'disabled in the app until the main script reads this column',
        r.folder === 'baba', r);
  check('32 the frozen column really is untouched in the sheet',
        ctx.cell_(ctx.userRows_()[ctx.rowOf_(ctx.userRows_(), 'deda') - 2], 8) === 'baba');
  check('33 the password survives a rename',
        post(ctx, { what: 'login', token: LOGIN_TOK,
                    username: 'deda', password: made.password }).ok === true);
  check('34 the old name is nobody now',
        post(ctx, { what: 'login', token: LOGIN_TOK,
                    username: 'baba', password: made.password }).ok !== true);
  post(ctx, { what: 'user_create', username: 'mama' });
  check('35 a name already taken is refused',
        post(ctx, proof({ what: 'user_rename', username: 'mama',
                          new_username: 'deda' })).error === 'that name is taken');
  check('36 RENAMING THE ADMINISTRATOR IS REFUSED — AUTH_ADMIN_USER would '
        + 'point at nobody and no admin action would ever work again',
        /Script Properties/.test(post(ctx, proof({ what: 'user_rename',
              username: 'admin', new_username: 'chief' })).error || ''));
}

// ---------------------------------------------------------------------
// G. user_engine — added this session
// ---------------------------------------------------------------------
{
  const { ctx } = fresh();
  post(ctx, { what: 'user_create', username: 'baba' });
  const r = post(ctx, { what: 'user_engine', username: 'baba', engine: 'studio' });
  check('37 an engine can be assigned, and is named back', r.ok === true
        && r.user === 'baba' && r.engine === 'studio', r);
  check('38 and the sheet holds it', rowOf(ctx, 'baba').engine === 'studio');
  check('39 AN EMPTY ENGINE IS A REAL ANSWER — it means "use the global "'
        + 'one" and is the way back from a choice',
        post(ctx, { what: 'user_engine', username: 'baba', engine: '' }).ok === true
        && rowOf(ctx, 'baba').engine === '');
  check('40 a made-up engine is refused',
        /not an engine/.test(post(ctx, { what: 'user_engine', username: 'baba',
                                         engine: 'turbo' }).error || ''));
  check('41 an engine for nobody says so',
        post(ctx, { what: 'user_engine', username: 'ghost', engine: 'free' })
          .error === 'no such user');
  check('42 it needs NO administrator password — it is reversible and '
        + 'changes nothing about who can get in',
        post(ctx, { what: 'user_engine', username: 'baba', engine: 'free' }).ok === true);
}

// ---------------------------------------------------------------------
// H. what the login refuses, and what it gives away
// ---------------------------------------------------------------------
{
  const { ctx } = fresh();
  const made = post(ctx, { what: 'user_create', username: 'baba' });
  const wrongPw = post(ctx, { what: 'login', token: LOGIN_TOK,
                              username: 'baba', password: 'no' });
  const noSuch  = post(ctx, { what: 'login', token: LOGIN_TOK,
                              username: 'nobody-at-all', password: 'no' });
  check('43 A NAME NOBODY HAS AND A WRONG PASSWORD ANSWER THE SAME WORD — '
        + 'telling them apart would say which half to keep guessing at',
        JSON.stringify(wrongPw) === JSON.stringify(noSuch), [wrongPw, noSuch]);
  check('44 a successful login carries no password, hash or salt back',
        (() => {
          const ok = post(ctx, { what: 'login', token: LOGIN_TOK,
                                 username: 'baba', password: made.password });
          const s = JSON.stringify(ok);
          return ok.ok === true && !/password|hash|salt/i.test(s)
                 && s.indexOf(made.password) === -1;
        })());
  check('45 PLAINTEXT IN COLUMN 2 IS NEVER ACCEPTED — a row with an old '
        + 'password and no hash cannot log in through this script at all',
        (() => {
          const s = gas.SS.getSheetByName('users');
          s.appendRow(['stari', 'plainpassword', '', '', '', '', '', 'stari']);
          return post(ctx, { what: 'login', token: LOGIN_TOK,
                             username: 'stari', password: 'plainpassword' }).ok !== true;
        })());
  check('46 the users list carries no secrets either — the VALUES are '
        + 'what matter, not the word "hashed" in a key name',
        (() => {
          const rows = ctx.userRows_();
          const baba = rows[ctx.rowOf_(rows, 'baba') - 2];
          const salt = ctx.cell_(baba, 5), hash = ctx.cell_(baba, 6);
          const json = JSON.stringify(post(ctx, { what: 'users' }).users);
          const keys = Object.keys(ctx.userList_()[0]).sort().join(',');
          return salt && hash
                 && json.indexOf(salt) === -1
                 && json.indexOf(hash) === -1
                 && json.indexOf(made.password) === -1
                 && keys === 'engine,folder,hashed,note,user';
        })());
}

// ---------------------------------------------------------------------
console.log(results.join('\n'));
console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
