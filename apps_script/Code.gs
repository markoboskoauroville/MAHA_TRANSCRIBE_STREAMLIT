/**
 * TTT-LLL usage logging.
 *
 * Receives one small signal from the app after each use and writes it to
 * this spreadsheet: one tab per user, plus a Summary tab that adds itself
 * up automatically.
 *
 * PRIVACY, BY DESIGN. No text ever leaves the app. Not what was
 * transcribed, not what was translated, not what was read. This script
 * only ever sees: which user, what kind of action, how big it was
 * (seconds of audio or number of characters), which engine did it, and
 * when. There is deliberately no field for content, so none can be sent
 * even by accident.
 *
 * SETUP: see SETUP.md next to this file. Short version — paste this into
 * Extensions > Apps Script, run setup() once, then Deploy > New
 * deployment > Web app, and give the app the URL it prints.
 */

// ---------------------------------------------------------------------
// CONFIGURATION — change these two lines, nothing else.
// ---------------------------------------------------------------------

/** A password shared with the app so strangers cannot write to the sheet.
 *  Make up any long random string and put the SAME one in the Streamlit
 *  secrets as SHEETS_TOKEN. */
var SHARED_TOKEN = 'CHANGE_ME_to_a_long_random_string';

/** Everyone who can log in. Used by setup() to pre-build a tab for each.
 *  A user who is not listed still gets a tab automatically on first use,
 *  so this list only saves you seeing an empty sheet on day one. */
var KNOWN_USERS = ['user1', 'user2', 'user3'];

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
    'Next: Deploy > New deployment > Web app, ' +
    'set "Who has access" to "Anyone", then copy the URL it gives you ' +
    'and send it to Claude to put in the app.'
  );
}

/** The app calls this. Never throws at the caller — a logging failure must
 *  never be able to break the app that is being logged. */
function doPost(e) {
  try {
    var body = JSON.parse(e.postData.contents);
    if (body.token !== SHARED_TOKEN) {
      return json({ ok: false, error: 'bad token' });
    }
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
function doGet() {
  return json({ ok: true, service: 'TTT-LLL logging', users: userTabs().length });
}

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
