"""The shared login rules (S7 research D5, D6): public list, constant-time match, sessions, form parsing."""

from __future__ import annotations

from dataclasses import dataclass

from app.auth import (
    SessionStore,
    credentials_match,
    is_page,
    is_public,
    login_enabled,
    parse_form,
    safe_next,
)
from app.config import Settings


def guarded() -> Settings:
    return Settings(demo_username="presenter", demo_password="open sesame")


@dataclass(frozen=True)
class Pinned(Settings):
    """What Settings looks like once S6 adds the pinned public run."""

    public_run_id: str = "f2dda488-0a2f-457a-9ef1-33fcac05fa70"


def test_login_is_off_until_both_values_are_set() -> None:
    assert not login_enabled(Settings())
    assert not login_enabled(Settings(demo_username="presenter"))
    assert not login_enabled(Settings(demo_password="x"))
    assert login_enabled(guarded())


def test_public_list_matches_the_s6_contract() -> None:
    settings = guarded()
    for path in (
        "/login",
        "/static/css/app.css",
        "/introduction",
        "/introduction.pdf",
        "/public/run/x/events",
    ):
        assert is_public(path, "", settings), path
    for path in ("/", "/demo", "/settings", "/preflight", "/api/meta", "/api/runs", "/api/preflight"):
        assert not is_public(path, "", settings), path


def test_public_demo_only_for_the_pinned_run() -> None:
    pinned = Pinned(demo_username="presenter", demo_password="open sesame")
    assert is_public("/demo", f"public=1&run={pinned.public_run_id}&speed=4", pinned)
    assert not is_public("/demo", "public=1&run=another", pinned)
    assert not is_public("/demo", f"run={pinned.public_run_id}", pinned)
    # Before S6 lands there is no pinned run, so the public Demo stays behind the login.
    assert not is_public("/demo", "public=1&run=anything", guarded())


def test_pages_redirect_and_api_refuses() -> None:
    assert is_page("/demo")
    assert is_page("/")
    assert not is_page("/api/runs")


def test_credentials_compare_both_fields() -> None:
    settings = guarded()
    assert credentials_match(settings, "presenter", "open sesame")
    assert not credentials_match(settings, "presenter", "open")
    assert not credentials_match(settings, "someone", "open sesame")
    assert not credentials_match(settings, "", "")
    assert not credentials_match(Settings(), "", "")


def test_safe_next_keeps_only_paths_on_this_site() -> None:
    assert safe_next("/settings") == "/settings"
    assert safe_next("/demo?dataset=clean-run") == "/demo?dataset=clean-run"
    assert safe_next("//evil.example/x") == "/demo"
    assert safe_next("https://evil.example") == "/demo"
    assert safe_next("\\evil") == "/demo"
    assert safe_next(None) == "/demo"
    assert safe_next("") == "/demo"


def test_sessions_live_in_one_process_only() -> None:
    store = SessionStore()
    token = store.create()
    assert store.has(token)
    assert not store.has("nope")
    assert not store.has(None)
    assert not store.has("")
    assert not SessionStore().has(token)
    assert len(store) == 1


def test_form_parsing_decodes_urlencoded_fields() -> None:
    form = parse_form(b"username=presenter&password=open%20sesame%26more&next=%2Fsettings")
    assert form == {"username": "presenter", "password": "open sesame&more", "next": "/settings"}
    assert parse_form(b"") == {}
