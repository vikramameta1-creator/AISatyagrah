# -*- coding: utf-8 -*-
"""
Mount into your FastAPI app:
    from satyagrah.web.auth_router import router as auth_router
    app.include_router(auth_router, prefix="/auth")
"""
try:
    from fastapi import APIRouter, Form, Response, Request, Depends
    from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
except Exception:
    # FastAPI not installed — harmless no-op shim
    APIRouter = lambda *a, **k: None

from ..auth.service import authenticate, user_from_session, logout

router = APIRouter() if callable(APIRouter) else None
if router:
    COOKIE = "satyagrah_session"
    @router.get("/login", response_class=HTMLResponse)
    def login_form():
        return """<html><body style="font-family:sans-serif">
        <h2>Login</h2>
        <form method="post">
          <label>Username <input name="username"></label><br>
          <label>Password <input type="password" name="password"></label><br>
          <button type="submit">Sign in</button>
        </form></body></html>"""

    @router.post("/login")
    def login_post(response: Response, username: str = Form(...), password: str = Form(...)):
        token = authenticate(username, password)
        if not token:
            return HTMLResponse("<h3>Invalid credentials</h3>", status_code=401)
        resp = RedirectResponse(url="/", status_code=302)
        # cookie: HttpOnly; Secure recommended if served over HTTPS
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
