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

/**
 * THE CELLS AS THEY ARE ON THE SHEET, not as userList_ reports them.
 *
 * userList_ normalises: an engine cell reads back through engineOf_, so
 * a blank one answers 'normal' and a migration that did nothing would
 * look like it had worked. Anything asserting what was WRITTEN has to
 * read the row itself.
 */
function rawOf(ctx, name) {
  const rows = ctx.userRows_();
  const row = rows[ctx.rowOf_(rows, name) - 2];
  return { password: ctx.cell_(row, 2), engine: ctx.cell_(row, 3),
           must: ctx.cell_(row, 10) };
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

  // THE SECOND FACTOR IS GONE (v127), AND THIS RECORDS WHAT THAT MEANS.
  //
  // Baba: "if I am logging as admin, do not ask me to enter a password
  // before I change things for users. It is annoying." His app, his
  // family, his call — and the friction was real: the box rendered
  // BELOW the confirm buttons, so pressing yes sent an empty password
  // and the script refused, which reads as being asked for something
  // there is nowhere to type.
  //
  // What it costs: THE ADMIN TOKEN ALONE NOW DELETES PEOPLE. The second
  // factor existed because a token can leak into a screenshot, and his
  // has, once. For five family members on a sheet he owns that is a
  // fair trade. These checks assert the new truth rather than being
  // deleted, so the day it stops being fair, the change is visible.
  check('14 reset needs ONLY the admin token now',
        post(ctx, { what: 'user_password', username: 'baba' }).ok === true);
  check('15 delete needs only the token',
        post(ctx, { what: 'user_delete', username: 'baba' }).ok === true);

  const { ctx: ctx2 } = fresh();
  post(ctx2, { what: 'user_create', username: 'baba' });
  check('16 rename needs only the token',
        post(ctx2, { what: 'user_rename', username: 'baba',
                     new_username: 'deda' }).ok === true);

  // AND THE TOKEN IS STILL THE WHOLE DOOR. The login token must not
  // reach any of this — that separation is what is left, and it is now
  // the only thing standing between a leaked login token and the
  // family's accounts.
  const { ctx: ctx3 } = fresh();
  ctx3.token = 'LOGIN-TOK';
  check('17 THE LOGIN TOKEN STILL CANNOT DELETE ANYBODY',
        post(ctx3, { what: 'user_delete', username: 'baba' }).ok !== true);
  check('18 nor reset a password',
        post(ctx3, { what: 'user_password', username: 'baba' }).ok !== true);
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
  // WAS: an empty engine meant "follow the global row". That third
  // state is gone. Empty still has to be ACCEPTED — the panel deployed
  // today sends it for its "global" button, and this script reaches
  // Baba's phone before the app does — but it now lands on the engine
  // that blank always resolved to.
  check('39 an empty engine is accepted and becomes normal, so the older '
        + 'panel\'s "global" press is not an error',
        post(ctx, { what: 'user_engine', username: 'baba', engine: '' }).ok === true
        && rowOf(ctx, 'baba').engine === 'normal');
  check('39b the old word "free" also becomes normal',
        post(ctx, { what: 'user_engine', username: 'baba', engine: 'free' }).ok === true
        && rowOf(ctx, 'baba').engine === 'normal');
  check('39c and normal is accepted by its own name',
        post(ctx, { what: 'user_engine', username: 'baba', engine: 'normal' }).ok === true
        && rowOf(ctx, 'baba').engine === 'normal');
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
                 && keys === 'engine,folder,hashed,must_change,note,user';
        })());
}

// ---------------------------------------------------------------------
// I. A CHOSEN PASSWORD, AND THE FLAG THAT MAKES IT TEMPORARY
// ---------------------------------------------------------------------
{
  const { ctx } = fresh();

  const made = post(ctx, { what: 'user_create', username: 'emina',
                           password: 'kruh-i-more-9' });
  check('49 a chosen password comes back as the one that was chosen',
        made.ok === true && made.password === 'kruh-i-more-9', made);
  check('50 and it is the password that actually logs in',
        post(ctx, { what: 'login', token: LOGIN_TOK,
                    username: 'emina', password: 'kruh-i-more-9' }).ok === true);
  check('51 the plaintext column stays empty even so',
        rawOf(ctx, 'emina').password === '');
  check('52 a chosen password too short is refused, by the SAME floor '
        + 'the change-password endpoint uses',
        /too short/.test(post(ctx, { what: 'user_create', username: 'kratka',
                                     password: 'abc' }).error || ''));
  check('53 and nobody was made by that refusal',
        ctx.rowOf_(ctx.userRows_(), 'kratka') === 0
        || ctx.rowOf_(ctx.userRows_(), 'kratka') === null
        || ctx.rowOf_(ctx.userRows_(), 'kratka') === undefined);

  check('54 an empty password still means "make me one"',
        (() => {
          const r = post(ctx, { what: 'user_create', username: 'marinko',
                                password: '' });
          return r.ok === true && r.password && r.password.length >= 8;
        })());

  // ---- must_change ----------------------------------------------
  check('55 a new account MUST change its password',
        rawOf(ctx, 'emina').must === 'yes'
        && rowOf(ctx, 'emina').must_change === true);
  check('56 and login says so, so the app can stop them',
        post(ctx, { what: 'login', token: LOGIN_TOK, username: 'emina',
                    password: 'kruh-i-more-9' }).must_change === true);
  check('57 changing it clears the flag — the one place that does',
        (() => {
          const r = post(ctx, { what: 'password_change', token: LOGIN_TOK,
                                username: 'emina',
                                old_password: 'kruh-i-more-9',
                                new_password: 'moja-vlastita-8' });
          return r.ok === true && rawOf(ctx, 'emina').must === ''
                 && rowOf(ctx, 'emina').must_change === false;
        })());
  check('58 and the next login no longer asks',
        post(ctx, { what: 'login', token: LOGIN_TOK, username: 'emina',
                    password: 'moja-vlastita-8' }).must_change === false);
  check('59 A RESET SETS IT AGAIN — that password went through a chat app too',
        (() => {
          const r = post(ctx, { what: 'user_password', username: 'emina',
                                admin_user: 'admin', admin_password: ADMIN_PW });
          return r.ok === true && r.must_change === true
                 && rawOf(ctx, 'emina').must === 'yes';
        })());
  check('60 A REMEMBERED PHONE IS TOLD TOO — it skips the login form, so '
        + 'without this it would walk past the one screen it must not',
        (() => {
          const made2 = post(ctx, { what: 'user_create', username: 'sonia',
                                    password: 'lozinka-123' });
          const li = post(ctx, { what: 'login', token: LOGIN_TOK,
                                 username: 'sonia', password: made2.password,
                                 remember: true });
          const rl = post(ctx, { what: 'remember_login', token: LOGIN_TOK,
                                 username: 'sonia', remember: li.remember });
          return rl.ok === true && rl.must_change === true;
        })());
  check('61 a row written before this column existed reads as NO, not yes',
        (() => {
          const s2 = gas.SS.getSheetByName('users');
          s2.appendRow(['stara', '', 'normal', '', '', '', '', 'stara']);
          const rows = ctx.userRows_();
          return ctx.mustOf_(rows[ctx.rowOf_(rows, 'stara') - 2]) === false;
        })());
}

// ---------------------------------------------------------------------
// J. THE ENGINE MIGRATION
// ---------------------------------------------------------------------
{
  const { ctx } = fresh();
  const s2 = gas.SS.getSheetByName('users');
  s2.appendRow(['blanka', '', '', '', 'x', 'y', 8, 'blanka']);
  s2.appendRow(['stari', '', 'free', '', 'x', 'y', 8, 'stari']);
  s2.appendRow(['nova', '', 'studio', '', 'x', 'y', 8, 'nova']);

  const preview = ctx.migrateEnginesPreview();
  check('62 the preview writes NOTHING', rawOf(ctx, 'blanka').engine === ''
        && rawOf(ctx, 'stari').engine === 'free');
  check('63 and it names who is affected, blank apart from free',
        preview.blank.indexOf('blanka') !== -1
        && preview.from_free.indexOf('stari') !== -1
        && preview.already.indexOf('nova') !== -1, preview);

  ctx.migrateEnginesRun();
  check('64 the run rewrites blank to normal', rawOf(ctx, 'blanka').engine === 'normal');
  check('65 and free to normal', rawOf(ctx, 'stari').engine === 'normal');
  check('66 and leaves studio alone', rawOf(ctx, 'nova').engine === 'studio');
}

// ---------------------------------------------------------------------
console.log(results.join('\n'));
console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
