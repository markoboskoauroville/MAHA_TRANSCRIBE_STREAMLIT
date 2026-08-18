// =====================================================================
//  TTT-LLL — ADD THIS TO THE BOTTOM OF Code.gs
//
//  HOW TO PASTE THIS — read this bit, it matters.
//
//  Your Code.gs ALREADY HAS a doGet, near the bottom:
//
//      function doGet() {
//        return json({ ok: true, service: 'TTT-LLL logging',
//                      users: userTabs().length });
//      }
//
//  DELETE those three lines first, then paste everything below at the
//  end. Two functions with the same name is legal JavaScript — the
//  second silently replaces the first — so leaving it there would appear
//  to work and would confuse whoever reads the file next.
//
//  Deleting it also closes a small hole: that doGet takes NO token, so
//  anyone with the URL could read how many users you have. The version
//  below refuses without the token, which it must, because it returns
//  API keys.
//
//  Then redeploy: Deploy > Manage deployments > pencil > New version.
//
//  It adds two things the app can READ:
//
//    settings   one row per setting:  scope | key | value
//               scope is "global" or a username. A user's own row wins;
//               if they have none, the global row applies.
//
//    k_<name>   one tab per provider, holding API keys the app should
//               use when they are NOT in Streamlit secrets. One key per
//               row, column A. A key here needs no redeploy of the app.
//
//  Run setupConfig() ONCE from the editor after pasting, to create the
//  tabs with their headers and a few sensible starting rows.
// =====================================================================

/** Providers that may have a key tab. Add to this list to add a tab. */
var KEY_PROVIDERS = ['assemblyai', 'anthropic', 'speechify', 'groq'];

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
    if (p.token !== SHARED_TOKEN) {
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
