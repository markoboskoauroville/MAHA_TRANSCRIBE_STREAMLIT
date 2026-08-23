/* A fake Apps Script runtime.
 *
 * The REAL Code.gs is executed against this, untouched — only Google's
 * services are faked. A harness that re-implemented the logic would pass
 * forever while the deployed script drifted, which is the one thing a
 * test like this must not do.
 *
 * Rebuilt 19.8.2026: the original gastest/ described in HANDOVER §19 is
 * not in the repo and was never committed.
 */

'use strict';

// ---------------------------------------------------------------- Drive

let _idSeq = 1;
const nextId = (p) => p + '_' + (_idSeq++);

class FakeFile {
  constructor(name, bytes, mime) {
    this.name = name;
    this.bytes = bytes;          // array of ints, or a string
    this.mime = mime || 'application/octet-stream';
    this.id = nextId('file');
    this.trashed = false;
  }
  getId() { return this.id; }
  getName() { return this.name; }
  // setContent replaces a text file whole, as the real one does. Without
  // it notesPut_ silently did nothing on the second save and the
  // notebook would have frozen at whatever it held first.
  setContent(text) { this.bytes = String(text); return this; }
  setTrashed(v) { this.trashed = !!v; return this; }
  isTrashed() { return this.trashed; }
  getBlob() {
    const self = this;
    return {
      getBytes() { return self.bytes; },
      getDataAsString(cs) {
        if (typeof self.bytes === 'string') return self.bytes;
        return Buffer.from(self.bytes.map((b) => b & 0xFF)).toString(
          (cs || 'UTF-8').toLowerCase() === 'utf-8' ? 'utf8' : 'binary');
      },
    };
  }
}

class FakeFolder {
  constructor(name) {
    this.name = name;
    this.id = nextId('folder');
    this.files = [];
    this.folders = [];
    this.trashed = false;
  }
  getId() { return this.id; }
  getName() { return this.name; }
  setTrashed(v) {
    // Deliberately does NOT cascade to the files inside.
    //
    // The first version of this fake did cascade, and that made the
    // explicit file-trashing loop in deleteRec_ impossible to test: the
    // mutation that removed it still left zero files, so the test went
    // green on code that no longer worked. A fake that is more forgiving
    // than the thing it stands in for hides exactly the bug it was
    // written to catch.
    this.trashed = !!v;
    return this;
  }
  createFile(a, b, c) {
    // BOTH SHAPES, because the real DriveApp has both:
    // createFile(blob) and createFile(name, content, mimeType). The fake
    // knew only the first, so notesPut_ would have thrown here while
    // working perfectly in Drive — the wrong kind of red, and the kind
    // that teaches you to distrust the harness.
    const f = (typeof a === 'string')
      ? new FakeFile(a, b, c || 'text/plain')
      : new FakeFile(a._name, a._data, a._mime);
    this.files.push(f);
    return f;
  }
  createFolder(name) {
    const f = new FakeFolder(name);
    this.folders.push(f);
    return f;
  }
  _iter(arr) {
    let i = 0;
    return { hasNext: () => i < arr.length, next: () => arr[i++] };
  }
  getFiles() { return this._iter(this.files.filter((f) => !f.trashed)); }
  getFilesByName(n) {
    return this._iter(this.files.filter((f) => !f.trashed && f.name === n));
  }
  getFoldersByName(n) {
    return this._iter(this.folders.filter((f) => !f.trashed && f.name === n));
  }
}

const DRIVE = { roots: {} };

const DriveApp = {
  getFolderById(id) {
    if (!DRIVE.roots[id]) throw new Error('No item with the given ID: ' + id);
    return DRIVE.roots[id];
  },
};

// ----------------------------------------------------------- Spreadsheet

class FakeRange {
  constructor(sheet, row, col, nRows, nCols) {
    Object.assign(this, { sheet, row, col, nRows, nCols });
  }
  getValues() {
    const out = [];
    for (let r = 0; r < this.nRows; r++) {
      const line = [];
      for (let c = 0; c < this.nCols; c++) {
        line.push(this.sheet._cell(this.row + r, this.col + c));
      }
      out.push(line);
    }
    return out;
  }
  setValues(vals) {
    for (let r = 0; r < vals.length; r++) {
      for (let c = 0; c < vals[r].length; c++) {
        this.sheet._set(this.row + r, this.col + c, vals[r][c]);
      }
    }
    return this;
  }
  setValue(v) { this.sheet._set(this.row, this.col, v); return this; }
  // The single-cell read. The main script only ever reads in blocks, so
  // this was never needed until the auth script's ensureUsersSheet_
  // checked one header cell at a time.
  getValue() { return this.sheet._cell(this.row, this.col); }
  setFontWeight() { return this; }
  setNumberFormat() { return this; }
}

class FakeSheet {
  constructor(name) { this.name = name; this.rows = []; }
  getName() { return this.name; }
  _cell(r, c) {
    const row = this.rows[r - 1];
    return row === undefined || row[c - 1] === undefined ? '' : row[c - 1];
  }
  _set(r, c, v) {
    while (this.rows.length < r) this.rows.push([]);
    const row = this.rows[r - 1];
    while (row.length < c) row.push('');
    row[c - 1] = v;
  }
  appendRow(vals) { this.rows.push(vals.slice()); return this; }
  getLastRow() { return this.rows.length; }
  getLastColumn() {
    return this.rows.reduce((m, r) => Math.max(m, r.length), 0);
  }
  getRange(row, col, nRows, nCols) {
    return new FakeRange(this, row, col, nRows || 1, nCols || 1);
  }
  deleteRow(r) { this.rows.splice(r - 1, 1); return this; }
  setFrozenRows() { return this; }
  setColumnWidth() { return this; }
}

class FakeSpreadsheet {
  constructor() { this.sheets = {}; }
  getSheetByName(n) { return this.sheets[n] || null; }
  insertSheet(n) { this.sheets[n] = new FakeSheet(n); return this.sheets[n]; }
  getSpreadsheetTimeZone() { return 'Europe/Zagreb'; }
  getSheets() { return Object.values(this.sheets); }
}

let SS = new FakeSpreadsheet();

const SpreadsheetApp = {
  getActiveSpreadsheet: () => SS,
  // The auth script opens its sheet BY ID rather than being bound to
  // it. There is one fake spreadsheet, so any id reaches it.
  openById: () => SS,
  getUi: () => ({ alert: () => {}, createMenu: () => ({
    addItem() { return this; }, addToUi() {} }) }),
};

// ------------------------------------------------------------- Utilities

const Utilities = {
  base64Decode(s) {
    return Array.from(Buffer.from(String(s), 'base64'));
  },
  base64Encode(bytes) {
    if (typeof bytes === 'string') return Buffer.from(bytes).toString('base64');
    return Buffer.from(bytes.map((b) => b & 0xFF)).toString('base64');
  },
  newBlob(data, mime, name) {
    const blob = { _data: data, _mime: mime, _name: name };
    blob.setDataFromString = function (s, cs) {
      this._data = Buffer.from(String(s), 'utf8').toString('utf8');
      this._charset = cs;
      return this;
    };
    blob.getBytes = function () { return this._data; };
    return blob;
  },
  computeHmacSha256Signature(msg, key) {
    const crypto = require('crypto');
    // BYTE ARRAYS, NOT JUST STRINGS. hashPw_ feeds its own signed-byte
    // output back in as the next message a thousand times over; passing
    // that through String() would hash the text "12,-34,..." instead of
    // the bytes, and the harness would agree with itself while agreeing
    // with Google about nothing.
    const bin = (v) => (Array.isArray(v)
      ? Buffer.from(v.map((b) => b & 0xFF))
      : Buffer.from(String(v), 'utf8'));
    const buf = crypto.createHmac('sha256', bin(key))
                      .update(bin(msg)).digest();
    // GAS hands back SIGNED bytes, -128..127. Reproducing that is the
    // whole point: without & 0xFF on the other side the hex conversion
    // emits literal '-' characters and every signature is wrong.
    return Array.from(buf).map((b) => (b > 127 ? b - 256 : b));
  },
  // A version-4 UUID. The auth script builds salts out of two of these
  // BECAUSE Math.random() is not made for the job — so the fake must be
  // a real random source too, or every salt in a test run collides and
  // the suite would prove the opposite of what it claims.
  getUuid() {
    return require('crypto').randomUUID();
  },
  base64EncodeWebSafe(bytes) {
    return Utilities.base64Encode(bytes).replace(/\+/g, '-').replace(/\//g, '_');
  },
  formatDate(d, tz, fmt) {
    const p = (n) => String(n).padStart(2, '0');
    return fmt.replace('yyyy', d.getFullYear())
              .replace('MM', p(d.getMonth() + 1))
              .replace('dd', p(d.getDate()));
  },
};

const ContentService = {
  MimeType: { JSON: 'application/json' },
  createTextOutput(t) {
    return { _t: t, setMimeType() { return this; }, getContent() { return this._t; } };
  },
};

// ------------------------------------------------- Properties and locks

let PROPS = {};

const PropertiesService = {
  getScriptProperties: () => ({
    getProperty: (k) => (k in PROPS ? PROPS[k] : null),
    setProperty(k, v) { PROPS[k] = String(v); return this; },
    deleteProperty(k) { delete PROPS[k]; return this; },
    getProperties: () => Object.assign({}, PROPS),
  }),
};

// The lock always grants. A fake that could refuse would only be
// testing the fake — Apps Script runs one execution at a time here, and
// what the suite checks is that the code ASKS for it, which it does by
// going through withLock_ at all.
const LockService = {
  getScriptLock: () => ({
    tryLock: () => true,
    releaseLock: () => {},
  }),
};

const Logger = { log: () => {} };

function resetProps(props) {
  PROPS = Object.assign({}, props || {});
  return PROPS;
}

function resetWorld(rootId) {
  SS = new FakeSpreadsheet();
  DRIVE.roots = {};
  DRIVE.roots[rootId] = new FakeFolder('USERS');
  _idSeq = 1;
  return { ss: SS, root: DRIVE.roots[rootId] };
}

module.exports = {
  DriveApp, SpreadsheetApp, Utilities, ContentService,
  PropertiesService, LockService, Logger,
  resetWorld, resetProps, get SS() { return SS; }, DRIVE,
};
