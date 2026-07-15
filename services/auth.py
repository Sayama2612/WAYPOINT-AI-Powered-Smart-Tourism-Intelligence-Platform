from pathlib import Path


def _admins_file():
    return Path(__file__).parent.parent / 'config' / 'admins.txt'


def load_admins():
    # prefer DB-backed admins when available
    try:
        from services.db import list_admins_db
        init_admins = list_admins_db()
        if init_admins:
            return init_admins
    except Exception:
        pass
    p = _admins_file()
    if not p.exists():
        return ['admin']
    try:
        with p.open('r', encoding='utf-8') as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
            return lines or ['admin']
    except Exception:
        return ['admin']


def is_admin_user(username: str) -> bool:
    if not username:
        return False
    return username in load_admins()


def _ensure_config_dir():
    p = _admins_file().parent
    p.mkdir(parents=True, exist_ok=True)
    return p


def add_admin(username: str) -> bool:
    if not username:
        return False
    try:
        from services.db import add_admin_db
        if add_admin_db(username):
            return True
    except Exception:
        pass
    p = _admins_file()
    _ensure_config_dir()
    admins = load_admins()
    if username in admins:
        return False
    admins.append(username)
    try:
        with p.open('w', encoding='utf-8') as f:
            f.write('\n'.join(admins) + '\n')
        return True
    except Exception:
        return False


def remove_admin(username: str) -> bool:
    if not username:
        return False
    try:
        from services.db import remove_admin_db
        if remove_admin_db(username):
            return True
    except Exception:
        pass
    p = _admins_file()
    admins = load_admins()
    if username not in admins:
        return False
    admins = [a for a in admins if a != username]
    try:
        _ensure_config_dir()
        with p.open('w', encoding='utf-8') as f:
            f.write('\n'.join(admins) + ('\n' if admins else ''))
        return True
    except Exception:
        return False


def _last_user_file():
    return Path(__file__).parent.parent / 'config' / 'last_user.txt'


def initiate_magic_link(email: str, host: str = 'http://localhost:8501') -> dict:
    """Create a magic token for `email` and return a dict with token and a preview link.
    This function does NOT send email; it returns a link you can paste into a browser or share."""
    try:
        from services.db import create_magic_token
        token = create_magic_token(email)
        if not token:
            return {'ok': False, 'error': 'failed_create_token'}
        link = f"{host}/?magic={token}"
        # attempt to send email if SMTP configured
        emailed = False
        try:
            from services.email import send_magic_link_email
            emailed = send_magic_link_email(email, link)
        except Exception:
            emailed = False
        # record in history for audit (do not store token)
        try:
            from services.db import save_history
            save_history('magic_link_created', email, {'emailed': bool(emailed) or False}, user=email)
        except Exception:
            pass
        return {'ok': True, 'token': token, 'link': link, 'emailed': emailed}
    except Exception:
        return {'ok': False, 'error': 'exception'}


def verify_magic_link(token: str) -> dict:
    """Consume a magic token and create a session. Returns {'ok': True, 'session_id':..., 'user':...} on success."""
    try:
        from services.db import consume_magic_token, create_session
        email = consume_magic_token(token)
        if not email:
            return {'ok': False, 'error': 'invalid_or_expired'}
        sid = create_session(email)
        if not sid:
            return {'ok': False, 'error': 'session_failed'}
        return {'ok': True, 'session_id': sid, 'user': email}
    except Exception:
        return {'ok': False, 'error': 'exception'}


def get_user_from_session(session_id: str) -> str:
    try:
        from services.db import get_session_user
        return get_session_user(session_id)
    except Exception:
        return ''


def set_last_user(username: str) -> bool:
    # prefer DB-backed preference store
    try:
        from services.db import set_pref
        init_ok = set_pref('last_user', username or '')
        if init_ok:
            return True
    except Exception:
        pass
    try:
        _ensure_config_dir()
        p = _last_user_file()
        with p.open('w', encoding='utf-8') as f:
            f.write(username or '')
        return True
    except Exception:
        return False


def get_last_user() -> str:
    try:
        from services.db import get_pref
        v = get_pref('last_user')
        if v:
            return v
    except Exception:
        pass
    try:
        p = _last_user_file()
        if not p.exists():
            return ''
        return p.read_text(encoding='utf-8').strip()
    except Exception:
        return ''
