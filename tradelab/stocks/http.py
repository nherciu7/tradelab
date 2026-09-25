"""Polite HTTP downloads.

SEC fair-access rules (https://www.sec.gov/os/accessing-edgar-data):
  - every request carries a User-Agent with a name and a contact email;
  - no more than 10 requests a second (we stay at or below 5);
  - prefer the bulk files to per-filing requests.

`download()` never re-fetches a file that already exists, writes to a temporary
name first (so an interrupted download never looks complete), and retries on
429/5xx with exponential backoff.
"""
from __future__ import annotations

import re
import time
from pathlib import Path

import requests

_SEC_HOSTS = ("sec.gov",)
_MIN_INTERVAL = 0.2          # seconds between requests: <= 5 per second
_last_request = 0.0


def _is_sec(url: str) -> bool:
    return any(h in url for h in _SEC_HOSTS)


def check_user_agent(ua: str | None) -> str:
    """The SEC blocks anonymous clients. Require 'Name email@domain'."""
    if not ua or not re.search(r"\S+@\S+\.\S+", ua):
        raise ValueError(
            "SEC downloads need a User-Agent with a name and an email, e.g. "
            "--user-agent 'Jane Doe jane@example.com' (or env SEC_USER_AGENT).")
    return ua


def _throttle() -> None:
    global _last_request
    wait = _MIN_INTERVAL - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.monotonic()


def get(url: str, user_agent: str | None = None, tries: int = 5, **kw) -> requests.Response:
    """GET with throttling and retry. SEC URLs require `user_agent`."""
    headers = kw.pop("headers", {}) or {}
    if _is_sec(url):
        headers["User-Agent"] = check_user_agent(user_agent)
        headers.setdefault("Accept-Encoding", "gzip, deflate")
    elif user_agent:
        headers["User-Agent"] = user_agent
    else:
        headers.setdefault("User-Agent", "tradelab-research/0.1")
    for attempt in range(tries):
        _throttle()
        r = requests.get(url, headers=headers, timeout=120, **kw)
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(2 ** attempt * 2)
            continue
        return r
    return r


def download(url: str, dest: Path, user_agent: str | None = None) -> str:
    """Stream `url` to `dest`. Returns 'exists', 'ok' or 'missing (HTTP nnn)'."""
    dest = Path(dest)
    if dest.exists() and dest.stat().st_size > 0:
        return "exists"
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = get(url, user_agent=user_agent, stream=True)
    if r.status_code != 200:
        return f"missing (HTTP {r.status_code})"
    tmp = dest.with_suffix(dest.suffix + ".part")
    with open(tmp, "wb") as f:
        for chunk in r.iter_content(chunk_size=1 << 20):
            f.write(chunk)
    tmp.replace(dest)
    return "ok"
