# -*- coding: utf-8 -*-
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from ..auth.service import authenticate, user_from_session, logout

router = APIRouter()
COOKIE = "satyagrah_session"

@router.get("/login", response_class=HTMLResponse)
def login_form():
    # Simple HTML that sends JSON to /auth/login_json (no python-multipart needed)
    return """<!doctype html><meta charset="utf-8">
<style>body{font-family:sans-serif;margin:2rem} .card{max-width:420px;padding:1rem;border:1px solid #eee;border-radius:12px;box-shadow:0 3px 12px #0001}</style>
<div class="card"><h3>Login</h3>
  <label>Username <input id="u"></label><br><br>
  <label>Password <input id="p" type="password"></label><br><br>
  <button onclick="login()">Sign in</button>
  <div id="msg" style="color:#c00;margin-top:.5rem"></div>
</div>
<script>
async function login(){
  const r = await fetch('/auth/login_json',{method:'POST',headers:{'Content-Type':'application/json'},
    body: JSON.stringify({username:document.getElementById('u').value, password:document.getElementById('p').value})});
  if(r.ok){ location.href='/' } else { document.getElementById('msg').textContent='Invalid credentials' }
}
</script>"""

@router.post("/login_json")
async def login_json(request: Request):
    data = await request.json()
    token = authenticate(str(data.get("username","")), str(data.get("password","")))
    if not token:
        return JSONResponse({"ok": False, "error": "invalid"}, status_code=401)
    resp = JSONResponse({"ok": True})
    resp.set_cookie(COOKIE, token, httponly=True, samesite="lax", secure=False)
    return resp

def current_user(request: Request):
    token = request.cookies.get(COOKIE)
    return user_from_session(token) if token else None

@router.get("/me")
def me(request: Request):
    u = current_user(request)
    return JSONResponse(u or {"anonymous": True})

@router.post("/logout")
def do_logout(request: Request):
    token = request.cookies.get(COOKIE)
    logout(token)
    resp = RedirectResponse(url="/", status_code=302)
    resp.delete_cookie(COOKIE)
    return resp
