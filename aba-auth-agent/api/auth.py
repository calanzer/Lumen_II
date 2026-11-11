"""Login for the API: username and password from auth_config.yaml, kept in a signed
session cookie. Every other route depends on `require_user`."""

import os
import time
from typing import Optional
from urllib.parse import urlsplit

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from auth_config import load_auth_config

router = APIRouter(prefix="/api/auth", tags=["auth"])

MAX_FAILURES = 5
LOCKOUT_SECONDS = 300
_failures: dict[str, list[float]] = {}

# A real bcrypt hash to check against when the username doesn't exist, so a wrong username
# takes as long to reject as a wrong password.
_DUMMY_HASH = bcrypt.hashpw(b"not-a-real-password", bcrypt.gensalt()).decode()


class LoginBody(BaseModel):
    username: str
    password: str


def _recent_failures(username: str) -> list[float]:
    cutoff = time.time() - LOCKOUT_SECONDS
    recent = [t for t in _failures.get(username, []) if t > cutoff]
    _failures[username] = recent
    return recent


def authenticate(username: str, password: str) -> Optional[dict]:
    """The user's record if the password is right, else None."""
    users = load_auth_config()["credentials"]["usernames"]
    user = users.get(username)
    stored = (user or {}).get("password") or _DUMMY_HASH
    try:
        valid = bcrypt.checkpw(password.encode(), stored.encode())
    except ValueError:  # stored value isn't a bcrypt hash
        valid = False
    if user and valid:
        return {"username": username, "name": user.get("name", username)}
    return None


@router.post("/login")
def login(body: LoginBody, request: Request) -> dict:
    if len(_recent_failures(body.username)) >= MAX_FAILURES:
        raise HTTPException(429, "Too many failed attempts. Try again in a few minutes.")
    user = authenticate(body.username, body.password)
    if user is None:
        _failures.setdefault(body.username, []).append(time.time())
        raise HTTPException(401, "Username or password is incorrect.")
    _failures.pop(body.username, None)
    request.session["user"] = user
    return user


@router.post("/logout")
def logout(request: Request) -> dict:
    request.session.clear()
    return {"ok": True}


# --- Skipping sign-in on your own machine ---------------------------------------------
# Opt-in with ABA_LOCAL_NO_LOGIN=1 (the local run configuration sets it). Even then it only
# applies to a request that is plainly from a browser on this computer talking to
# localhost, because other websites you visit can also send requests to localhost.

LOCAL_USER = {"username": "local", "name": "Local tester", "local": True}
_LOOPBACK = {"127.0.0.1", "::1", "localhost"}
_PROXY_HEADERS = ("x-forwarded-for", "x-forwarded-host", "x-real-ip", "forwarded")


def local_login_skip_enabled() -> bool:
    return os.environ.get("ABA_LOCAL_NO_LOGIN", "").lower() in ("1", "true", "yes")


def _hostname(host_header: str) -> str:
    """The host part of a Host header: 'localhost:5173' -> 'localhost', '[::1]:8000' -> '::1'."""
    host = host_header.strip()
    if host.startswith("["):
        return host[1:].split("]")[0]
    return host.rsplit(":", 1)[0] if host.count(":") == 1 else host


def is_local_request(request: Request) -> bool:
    """True only for a same-machine, same-site request addressed to localhost."""
    if not local_login_skip_enabled():
        return False
    if (request.client.host if request.client else None) not in _LOOPBACK:
        return False  # the connection isn't from this machine
    if _hostname(request.headers.get("host", "")) not in _LOOPBACK:
        return False  # addressed to some other name (DNS rebinding)
    if any(header in request.headers for header in _PROXY_HEADERS):
        return False  # came through a proxy, so the loopback address says nothing
    if request.headers.get("sec-fetch-site") == "cross-site":
        return False  # the browser says another website caused this request
    origin = request.headers.get("origin")
    if origin and (urlsplit(origin).hostname or "") not in _LOOPBACK:
        return False  # a form or script on another site
    return True


def require_user(request: Request) -> dict:
    user = request.session.get("user")
    if user:
        return user
    if is_local_request(request):
        return LOCAL_USER
    raise HTTPException(401, "Not signed in.")


@router.get("/me")
def me(user: dict = Depends(require_user)) -> dict:
    return user
