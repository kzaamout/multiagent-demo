"""Shared login from .env (spec 0.7 section 2.8, slice S7, research D5 and D6).

One username and password pair, read from .env into Settings and never serialized. When both are
set, a pure ASGI middleware guards every request that is not on the public list: page requests are
redirected to the login page, everything else answers 401. Sessions are random tokens held in
process memory, so a restart signs everyone out. There are no accounts, resets, or lockouts
(constitution non-goal on per-user accounts).
"""

from __future__ import annotations

import hmac
import secrets
import time
from typing import Any
from urllib.parse import parse_qs, quote

from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import Settings

COOKIE = "sterling_session"
LOGIN_PATH = "/login"
DEFAULT_AFTER_LOGIN = "/demo"
ERROR_LINE = "Wrong username or password."
REFUSAL = "sign in required"

# The routes S6 keeps public (specs/007-introduction-replay/contracts/introduction.md), plus the login
# page and the static assets every page needs.
PUBLIC_PATHS = frozenset({LOGIN_PATH, "/introduction", "/introduction.pdf"})
PUBLIC_PREFIXES = ("/static/", "/public/")


def login_enabled(settings: Settings) -> bool:
    return bool(settings.demo_username) and bool(settings.demo_password)


def credentials_match(settings: Settings, username: str, password: str) -> bool:
    """Constant-time comparison of both fields; always False when the login is off."""
    if not login_enabled(settings):
        return False
    same_user = hmac.compare_digest(username.encode("utf-8"), settings.demo_username.encode("utf-8"))
    same_password = hmac.compare_digest(password.encode("utf-8"), settings.demo_password.encode("utf-8"))
    return same_user and same_password


def is_public(path: str, query: str, settings: Settings) -> bool:
    """Whether a request needs no session. The public Demo (S6) is the pinned run only."""
    if path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES):
        return True
    if path == "/demo":
        params = parse_qs(query)
        pinned = getattr(settings, "public_run_id", None)
        return bool(pinned) and params.get("public") == ["1"] and params.get("run") == [pinned]
    return False


def is_page(path: str) -> bool:
    """A browser navigation, which gets a redirect; API paths get a JSON refusal."""
    return not path.startswith("/api/")


def safe_next(value: str | None) -> str:
    """Only a path on this site may be the landing page after a sign-in."""
    if value and value.startswith("/") and not value.startswith("//") and "\\" not in value:
        return value
    return DEFAULT_AFTER_LOGIN


class SessionStore:
    """Tokens created by a successful sign-in, in memory only."""

    def __init__(self) -> None:
        self._tokens: dict[str, float] = {}

    def create(self) -> str:
        token = secrets.token_urlsafe(32)
        self._tokens[token] = time.time()
        return token

    def has(self, token: str | None) -> bool:
        return bool(token) and token in self._tokens

    def __len__(self) -> int:
        return len(self._tokens)


class LoginGuard:
    """Pure ASGI middleware, so the event stream and file responses pass through untouched."""

    def __init__(self, app: ASGIApp, settings: Settings, store: SessionStore) -> None:
        self.app = app
        self.settings = settings
        self.store = store

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not login_enabled(self.settings):
            await self.app(scope, receive, send)
            return
        path = str(scope.get("path", ""))
        query = bytes(scope.get("query_string", b"")).decode("utf-8", "replace")
        if is_public(path, query, self.settings):
            await self.app(scope, receive, send)
            return
        request = Request(scope)
        if self.store.has(request.cookies.get(COOKIE)):
            await self.app(scope, receive, send)
            return
        response: Any
        if is_page(path):
            target = path + (f"?{query}" if query else "")
            response = RedirectResponse(f"{LOGIN_PATH}?next={quote(target, safe='')}", status_code=303)
        else:
            response = JSONResponse({"error": REFUSAL}, status_code=401)
        await response(scope, receive, send)


def parse_form(body: bytes) -> dict[str, str]:
    """The sign-in form is application/x-www-form-urlencoded; no multipart dependency is needed."""
    parsed = parse_qs(body.decode("utf-8", "replace"), keep_blank_values=True)
    return {key: values[0] for key, values in parsed.items() if values}
