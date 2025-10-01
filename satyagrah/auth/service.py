# -*- coding: utf-8 -*-
import datetime
from .db import connect, init_db
from .crypto import hash_password, verify_password, new_token, sign_session, verify_session

def ensure_db():
    init_db()

def create_user(username: str, password: str, role=None):
    """
    Default role: 'admin' if username == 'admin', else 'editor'.
    (No default-arg magic; we decide at runtime to avoid NameError.)
    """
    ensure_db()
    if role is None:
        role = "admin" if str(username).lower() == "admin" else "editor"
    con = connect(); cur = con.cursor()
    cur.execute(
        "INSERT INTO users (username, passhash, role, created_at) VALUES (?,?,?,?)",
        (username, hash_password(password), role, datetime.datetime.utcnow().isoformat())
    )
    con.commit(); con.close()

def reset_password(username: str, new_password: str):
    ensure_db()
    con = connect(); cur = con.cursor()
    cur.execute("UPDATE users SET passhash=? WHERE username=?", (hash_password(new_password), username))
    con.commit(); con.close()

def set_active(username: str, active: bool):
    ensure_db()
    con = connect(); cur = con.cursor()
    cur.execute("UPDATE users SET is_active=? WHERE username=?", (1 if active else 0, username))
    con.commit(); con.close()

def list_users():
    ensure_db()
    con = connect()
    rows = con.execute(
        "SELECT id, username, role, is_active, created_at FROM users ORDER BY id"
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]

def authenticate(username: str, password: str):
    ensure_db()
    con = connect(); cur = con.cursor()
    row = cur.execute(
        "SELECT id, passhash, is_active FROM users WHERE username=?", (username,)
    ).fetchone()
    if not row or not row["is_active"] or not verify_password(password, row["passhash"]):
        con.close()
        return None
    # create a 24h session
    token = new_token()
    expires = (datetime.datetime.utcnow() + datetime.timedelta(hours=24)).isoformat()
    cur.execute(
        "INSERT INTO sessions (user_id, token, expires_at, created_at) VALUES (?,?,?,?)",
        (row["id"], token, expires, datetime.datetime.utcnow().isoformat())
    )
    con.commit(); con.close()
    return sign_session(token)

def user_from_session(signed_token: str):
    ensure_db()
    token = verify_session(signed_token or "")
    if not token:
        return None
    con = connect(); cur = con.cursor()
    row = cur.execute("""
        SELECT u.id, u.username, u.role
        FROM sessions s
        JOIN users u ON u.id = s.user_id
        WHERE s.token = ? AND s.expires_at > ?
    """, (token, datetime.datetime.utcnow().isoformat())).fetchone()
    con.close()
    return dict(row) if row else None

def logout(signed_token: str):
    token = verify_session(signed_token or "")
    if not token:
        return
    con = connect(); cur = con.cursor()
    cur.execute("DELETE FROM sessions WHERE token=?", (token,))
    con.commit(); con.close()
