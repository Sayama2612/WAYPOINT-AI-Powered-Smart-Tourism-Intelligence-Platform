import sqlite3
from pathlib import Path
import json
from datetime import datetime, timezone
import uuid

BASE = Path(__file__).parent.parent
DB_PATH = BASE / 'data' / 'waypoint.db'


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        destination_name TEXT NOT NULL,
        score REAL,
        meta TEXT,
        user TEXT,
        created_at TEXT
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT,
        destination_name TEXT,
        details TEXT,
        user TEXT,
        created_at TEXT
    )
    ''')
    # indices to speed common audit queries
    try:
        cur.execute('CREATE INDEX IF NOT EXISTS idx_history_created_at ON history(created_at)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_history_action ON history(action)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_history_user ON history(user)')
    except Exception:
        pass
    cur.execute('''
    CREATE TABLE IF NOT EXISTS admins (
        username TEXT PRIMARY KEY,
        created_at TEXT
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS preferences (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS magic_tokens (
        token TEXT PRIMARY KEY,
        email TEXT,
        expires_at TEXT,
        created_at TEXT
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        user TEXT,
        expires_at TEXT,
        created_at TEXT
    )
    ''')
    # seed admins table from config file if present
    try:
        cfgp = BASE / 'config' / 'admins.txt'
        if cfgp.exists():
            with cfgp.open('r', encoding='utf-8') as f:
                for line in f:
                    uname = line.strip()
                    if uname:
                        cur.execute('INSERT OR IGNORE INTO admins (username, created_at) VALUES (?,?)', (uname, datetime.now(timezone.utc).isoformat()))
    except Exception:
        pass
    cur.execute('''
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        destination_name TEXT,
        feedback TEXT,
        details TEXT,
        user TEXT,
        created_at TEXT
    )
    ''')
    # attempt to add user columns to existing tables (no-op if already present)
    try:
        cur.execute('ALTER TABLE favorites ADD COLUMN user TEXT')
    except Exception:
        pass
    try:
        cur.execute('ALTER TABLE history ADD COLUMN user TEXT')
    except Exception:
        pass
    try:
        cur.execute('ALTER TABLE feedback ADD COLUMN user TEXT')
    except Exception:
        pass
    conn.commit()
    conn.close()


def add_admin_db(username: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute('INSERT OR IGNORE INTO admins (username, created_at) VALUES (?,?)', (username, datetime.now(timezone.utc).isoformat()))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def remove_admin_db(username: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute('DELETE FROM admins WHERE username = ?', (username,))
        conn.commit()
        return cur.rowcount > 0
    except Exception:
        return False
    finally:
        conn.close()


def list_admins_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute('SELECT username FROM admins ORDER BY username')
        rows = cur.fetchall()
        return [r[0] for r in rows]
    except Exception:
        return []
    finally:
        conn.close()


def set_pref(key: str, value: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute('INSERT OR REPLACE INTO preferences (key, value) VALUES (?,?)', (key, value))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def get_pref(key: str) -> str:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute('SELECT value FROM preferences WHERE key = ?', (key,))
        row = cur.fetchone()
        return row[0] if row and row[0] is not None else ''
    except Exception:
        return ''
    finally:
        conn.close()


def save_export_file(filename: str, content_bytes: bytes, user: str = None) -> str:
    """Save an exported file into data/exports and log it in history. Returns the saved path."""
    exports_dir = BASE / 'data' / 'exports'
    exports_dir.mkdir(parents=True, exist_ok=True)
    # sanitize filename
    safe = ''.join([c if c.isalnum() or c in (' ','.','_','-') else '_' for c in filename])
    path = exports_dir / safe
    try:
        with open(path, 'wb') as f:
            f.write(content_bytes)
        # record in history
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute('INSERT INTO history (action, destination_name, details, user, created_at) VALUES (?,?,?,?,?)',
                        ('export_explanation', str(filename), json.dumps({'path': str(path)}), user, datetime.now(timezone.utc).isoformat()))
            conn.commit()
            conn.close()
        except Exception:
            pass
        return str(path)
    except Exception:
        return ''


def create_magic_token(email: str, token: str = None, expires_seconds: int = 900) -> str:
    try:
        init_db()
    except Exception:
        pass
    t = token or uuid.uuid4().hex
    expires = (datetime.now(timezone.utc).timestamp() + int(expires_seconds))
    expires_iso = datetime.fromtimestamp(expires, tz=timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute('INSERT OR REPLACE INTO magic_tokens (token, email, expires_at, created_at) VALUES (?,?,?,?)',
                    (t, email, expires_iso, datetime.now(timezone.utc).isoformat()))
        conn.commit()
        return t
    except Exception:
        return ''
    finally:
        conn.close()


def consume_magic_token(token: str) -> str:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute('SELECT email, expires_at FROM magic_tokens WHERE token = ?', (token,))
        row = cur.fetchone()
        if not row:
            return ''
        email, expires_at = row[0], row[1]
        # check expiry
        try:
            if datetime.fromisoformat(expires_at) < datetime.now(timezone.utc):
                # expired
                cur.execute('DELETE FROM magic_tokens WHERE token = ?', (token,))
                conn.commit()
                return ''
        except Exception:
            pass
        # delete token and return email
        cur.execute('DELETE FROM magic_tokens WHERE token = ?', (token,))
        conn.commit()
        return email
    except Exception:
        return ''
    finally:
        conn.close()


def create_session(user: str, ttl_seconds: int = 86400) -> str:
    try:
        init_db()
    except Exception:
        pass
    sid = uuid.uuid4().hex
    expires = (datetime.now(timezone.utc).timestamp() + int(ttl_seconds))
    expires_iso = datetime.fromtimestamp(expires, tz=timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute('INSERT OR REPLACE INTO sessions (session_id, user, expires_at, created_at) VALUES (?,?,?,?)',
                    (sid, user, expires_iso, datetime.now(timezone.utc).isoformat()))
        conn.commit()
        return sid
    except Exception:
        return ''
    finally:
        conn.close()


def get_session_user(session_id: str) -> str:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute('SELECT user, expires_at FROM sessions WHERE session_id = ?', (session_id,))
        row = cur.fetchone()
        if not row:
            return ''
        user, expires_at = row[0], row[1]
        try:
            if datetime.fromisoformat(expires_at) < datetime.now(timezone.utc):
                # expired
                cur.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
                conn.commit()
                return ''
        except Exception:
            pass
        return user
    except Exception:
        return ''
    finally:
        conn.close()


def delete_session(session_id: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
        conn.commit()
        return cur.rowcount > 0
    except Exception:
        return False
    finally:
        conn.close()


def list_sessions(user: str = None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        if user:
            cur.execute('SELECT session_id, user, expires_at, created_at FROM sessions WHERE user = ? ORDER BY created_at DESC', (user,))
        else:
            cur.execute('SELECT session_id, user, expires_at, created_at FROM sessions ORDER BY created_at DESC')
        rows = cur.fetchall()
        conn.close()
        out = []
        for r in rows:
            out.append({'session_id': r[0], 'user': r[1], 'expires_at': r[2], 'created_at': r[3]})
        return out
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        return []


def delete_sessions_for_user(user: str) -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute('DELETE FROM sessions WHERE user = ?', (user,))
        deleted = cur.rowcount
        conn.commit()
        conn.close()
        return deleted
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        return 0


def save_favorite(destination_name: str, score: float = None, meta: dict = None, user: str = None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('INSERT INTO favorites (destination_name, score, meta, user, created_at) VALUES (?,?,?,?,?)',
                (destination_name, score, json.dumps(meta or {}), user, datetime.now(timezone.utc).isoformat()))
    conn.commit()
    conn.close()


def list_favorites(user: str = None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    if user:
        cur.execute('SELECT id, destination_name, score, meta, user, created_at FROM favorites WHERE user = ? ORDER BY created_at DESC', (user,))
    else:
        cur.execute('SELECT id, destination_name, score, meta, user, created_at FROM favorites ORDER BY created_at DESC')
    rows = cur.fetchall()
    conn.close()
    out = []
    for r in rows:
        meta = {}
        try:
            meta = json.loads(r[3])
        except Exception:
            meta = {}
        out.append({'id': r[0], 'destination_name': r[1], 'score': r[2], 'meta': meta, 'user': r[4], 'created_at': r[5]})
    return out


def delete_favorite(fid: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('DELETE FROM favorites WHERE id = ?', (fid,))
    conn.commit()
    conn.close()


def save_history(action: str, destination_name: str, details: dict = None, user: str = None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('INSERT INTO history (action, destination_name, details, user, created_at) VALUES (?,?,?,?,?)',
                (action, destination_name, json.dumps(details or {}), user, datetime.now(timezone.utc).isoformat()))
    conn.commit()
    conn.close()


def list_history(limit: int = 100, user: str = None, start_iso: str = None, end_iso: str = None, offset: int = 0, action: str = None):
    """List history with optional filters: user, start_iso, end_iso, action; supports offset/limit for pagination."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    q = 'SELECT id, action, destination_name, details, user, created_at FROM history'
    clauses = []
    params = []
    if user:
        clauses.append('user = ?')
        params.append(user)
    if action:
        clauses.append('action = ?')
        params.append(action)
    if start_iso and end_iso:
        clauses.append('created_at >= ? AND created_at <= ?')
        params.extend([start_iso, end_iso])
    elif start_iso:
        clauses.append('created_at >= ?')
        params.append(start_iso)
    elif end_iso:
        clauses.append('created_at <= ?')
        params.append(end_iso)

    if clauses:
        q += ' WHERE ' + ' AND '.join(clauses)
    q += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
    params.extend([limit, offset])
    try:
        cur.execute(q, params)
        rows = cur.fetchall()
    except Exception:
        rows = []
    conn.close()
    out = []
    for r in rows:
        details = {}
        try:
            details = json.loads(r[3])
        except Exception:
            details = {}
        out.append({'id': r[0], 'action': r[1], 'destination_name': r[2], 'details': details, 'user': r[4], 'created_at': r[5]})
    return out


def count_history(user: str = None, start_iso: str = None, end_iso: str = None, action: str = None) -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    q = 'SELECT COUNT(1) FROM history'
    clauses = []
    params = []
    if user:
        clauses.append('user = ?')
        params.append(user)
    if action:
        clauses.append('action = ?')
        params.append(action)
    if start_iso and end_iso:
        clauses.append('created_at >= ? AND created_at <= ?')
        params.extend([start_iso, end_iso])
    elif start_iso:
        clauses.append('created_at >= ?')
        params.append(start_iso)
    elif end_iso:
        clauses.append('created_at <= ?')
        params.append(end_iso)
    if clauses:
        q += ' WHERE ' + ' AND '.join(clauses)
    try:
        cur.execute(q, params)
        row = cur.fetchone()
        return int(row[0]) if row else 0
    except Exception:
        return 0
    finally:
        conn.close()


def export_history_csv(path: str, start_iso: str = None, end_iso: str = None, action: str = None, user: str = None):
    """Export matching history rows to CSV at `path`. Returns the path on success."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    q = 'SELECT id, action, destination_name, details, user, created_at FROM history'
    clauses = []
    params = []
    if user:
        clauses.append('user = ?')
        params.append(user)
    if action:
        clauses.append('action = ?')
        params.append(action)
    if start_iso and end_iso:
        clauses.append('created_at >= ? AND created_at <= ?')
        params.extend([start_iso, end_iso])
    elif start_iso:
        clauses.append('created_at >= ?')
        params.append(start_iso)
    elif end_iso:
        clauses.append('created_at <= ?')
        params.append(end_iso)
    if clauses:
        q += ' WHERE ' + ' AND '.join(clauses)
    q += ' ORDER BY created_at DESC'
    try:
        cur.execute(q, params)
        rows = cur.fetchall()
    except Exception:
        rows = []
    conn.close()
    import csv
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        with p.open('w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'action', 'destination_name', 'details', 'user', 'created_at'])
            for r in rows:
                writer.writerow([r[0], r[1], r[2], r[3], r[4], r[5]])
        return str(p)
    except Exception:
        return ''


def save_feedback(destination_name: str, feedback: str, details: dict = None, user: str = None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('INSERT INTO feedback (destination_name, feedback, details, user, created_at) VALUES (?,?,?,?,?)',
                (destination_name, feedback, json.dumps(details or {}), user, datetime.now(timezone.utc).isoformat()))
    conn.commit()
    conn.close()


def list_feedback(limit: int = 500, user: str = None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    if user:
        cur.execute('SELECT id, destination_name, feedback, details, user, created_at FROM feedback WHERE user = ? ORDER BY created_at DESC LIMIT ?', (user, limit))
    else:
        cur.execute('SELECT id, destination_name, feedback, details, user, created_at FROM feedback ORDER BY created_at DESC LIMIT ?', (limit,))
    rows = cur.fetchall()
    conn.close()
    out = []
    for r in rows:
        details = {}
        try:
            details = json.loads(r[3])
        except Exception:
            details = {}
        out.append({'id': r[0], 'destination_name': r[1], 'feedback': r[2], 'details': details, 'user': r[4], 'created_at': r[5]})
    return out


def delete_feedback(feedback_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('DELETE FROM feedback WHERE id = ?', (feedback_id,))
    conn.commit()
    conn.close()


def export_feedback_csv(path: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT id, destination_name, feedback, details, created_at FROM feedback ORDER BY created_at DESC')
    rows = cur.fetchall()
    conn.close()
    import csv
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'destination_name', 'feedback', 'details', 'created_at'])
        for r in rows:
            writer.writerow([r[0], r[1], r[2], r[3], r[4]])
    return path


def export_feedback_csv_filtered(path: str, start_iso: str = None, end_iso: str = None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    q = 'SELECT id, destination_name, feedback, details, created_at FROM feedback'
    params = []
    if start_iso and end_iso:
        q += ' WHERE created_at >= ? AND created_at <= ?'
        params = [start_iso, end_iso]
    elif start_iso:
        q += ' WHERE created_at >= ?'
        params = [start_iso]
    elif end_iso:
        q += ' WHERE created_at <= ?'
        params = [end_iso]
    q += ' ORDER BY created_at DESC'
    cur.execute(q, params)
    rows = cur.fetchall()
    conn.close()
    import csv
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'destination_name', 'feedback', 'details', 'created_at'])
        for r in rows:
            writer.writerow([r[0], r[1], r[2], r[3], r[4]])
    return path


def delete_feedback_older_than(days: int):
    # delete feedback older than `days` days from now
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('DELETE FROM feedback WHERE created_at < ?', (cutoff,))
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return deleted


def delete_history(hid: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute('DELETE FROM history WHERE id = ?', (hid,))
        conn.commit()
        return cur.rowcount > 0
    except Exception:
        return False
    finally:
        conn.close()


def delete_export(hid: int) -> bool:
    """Delete an exported file and remove its history record if present."""
    try:
        # fetch history record
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('SELECT details FROM history WHERE id = ?', (hid,))
        row = cur.fetchone()
        details = {}
        if row and row[0]:
            try:
                details = json.loads(row[0])
            except Exception:
                details = {}
        path = details.get('path')
        if path:
            try:
                p = Path(path)
                if p.exists():
                    p.unlink()
            except Exception:
                pass
        # delete history record
        cur.execute('DELETE FROM history WHERE id = ?', (hid,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        return False
