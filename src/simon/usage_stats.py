"""Anonymous usage counts for the public app: how many visits it gets, how
many of them actually played (bots and link previews open the page but
never start a game), how many different browsers visited -- new or
returning -- and how often each game is started. Daily totals only, with
nothing about who visited (no names, addresses or IDs).

Different visitors are counted without any ID: the browser keeps just the
date it was last counted (record_visitor), and counts itself once a day --
as returning if it has visited before.

The counts are `usage:<day>` hashes in the family's Upstash database, but
the public service never gets the family keys: it gets
USAGE_REDIS_REST_URL / USAGE_REDIS_REST_TOKEN, a token for a restricted
Redis user that may only add to `usage:*` counters (HINCRBY) -- it can't
read or change anything else (see README). The family app reads the counts
with its own keys for its usage page (screens/usage_view.py).

Counting is best-effort and runs in the background -- a slow or broken
counter must never delay or break a game.
"""

import json
import os
import sys
import threading
import urllib.request
from datetime import date, datetime, timedelta, timezone

from simon.app_mode import is_public_mode
from simon.kv_store import REQUEST_TIMEOUT_S, _clean_env

VISIT = "visit"
PLAYED = "played"
NEW_VISITOR = "visitor:new"
RETURNING_VISITOR = "visitor:returning"
# the browser's local storage: the last day this browser was counted
LAST_COUNTED_KEY = "usage_last_counted"
_GAME_PREFIX = "game:"
_KEY_PREFIX = "usage:"


def game_event(game_key: str) -> str:
    return f"{_GAME_PREFIX}{game_key}"


def game_counts(counts: dict[str, int]) -> dict[str, int]:
    """{game key: times started} out of a day's counts."""
    return {k.removeprefix(_GAME_PREFIX): v for k, v in counts.items() if k.startswith(_GAME_PREFIX)}


def today() -> date:
    """The day in Israel, where the players are (the server runs on UTC)."""
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("Asia/Jerusalem")).date()
    except Exception:  # no time zone data on this machine
        return datetime.now(timezone.utc).date()


def _log(message: str) -> None:
    print(f"[usage_stats] {message}", file=sys.stderr, flush=True)


def _in_background(job) -> None:
    threading.Thread(target=job, daemon=True).start()


class UsageStats:
    def __init__(self, url: str, token: str) -> None:
        self._url = url.rstrip("/")
        self._token = token

    def _post(self, path: str, body) -> object:
        req = urllib.request.Request(
            f"{self._url}{path}",
            data=json.dumps(body).encode(),
            method="POST",
            headers={"Authorization": f"Bearer {self._token}"},
        )
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S) as resp:
            return json.loads(resp.read())

    def record(self, event: str, day: date | None = None) -> None:
        """Adds one to `event`'s count for the day, in the background."""
        key = f"{_KEY_PREFIX}{(day or today()).isoformat()}"

        def job() -> None:
            try:
                self._post("", ["HINCRBY", key, event, 1])
            except Exception as e:  # best-effort: never let counting break play
                _log(f"record({event!r}) failed: {type(e).__name__}: {e}")

        _in_background(job)

    def daily_counts(self, days: int = 30, until: date | None = None) -> list[tuple[date, dict[str, int]]]:
        """[(day, {event: count})], newest first; [] if the counts can't be read."""
        last = until or today()
        day_list = [last - timedelta(days=i) for i in range(days)]
        try:
            results = self._post("/pipeline", [["HGETALL", f"{_KEY_PREFIX}{d.isoformat()}"] for d in day_list])
        except Exception as e:
            _log(f"daily_counts failed: {type(e).__name__}: {e}")
            return []
        counts = []
        for day, result in zip(day_list, results):
            flat = result.get("result") or []
            counts.append((day, {flat[i]: int(flat[i + 1]) for i in range(0, len(flat), 2)}))
        return counts


def visitor_event(last_counted: str | None, day: date) -> str | None:
    """How to count a browser that was last counted on `last_counted`
    (None: never) -- or None if it was already counted `day`."""
    if last_counted == day.isoformat():
        return None
    return RETURNING_VISITOR if last_counted else NEW_VISITOR


async def record_visitor(stats: UsageStats, prefs, day: date | None = None) -> None:
    """Counts this browser once a day, new or returning, using only the
    date it keeps in its local storage (`prefs`, Flet's shared_preferences)."""
    day = day or today()
    try:
        last = await prefs.get(LAST_COUNTED_KEY)
        event = visitor_event(last if isinstance(last, str) else None, day)
        if event is None:
            return
        await prefs.set(LAST_COUNTED_KEY, day.isoformat())
    except Exception as e:  # no local storage (e.g. blocked): just skip it
        _log(f"record_visitor failed: {type(e).__name__}: {e}")
        return
    stats.record(event, day)


def get_usage_stats() -> UsageStats | None:
    """The counter, or None when it isn't configured (e.g. local
    development) -- then nothing is counted.

    The public app uses USAGE_REDIS_REST_URL / _TOKEN: a token limited to
    adding to `usage:*` counters (see README). The family app, which only
    reads the counts, may fall back to its own database keys -- the public
    app never does, so it can't reach the family's data."""
    url = _clean_env(os.environ.get("USAGE_REDIS_REST_URL"))
    token = _clean_env(os.environ.get("USAGE_REDIS_REST_TOKEN"))
    if not (url and token) and not is_public_mode():
        url = _clean_env(os.environ.get("UPSTASH_REDIS_REST_URL"))
        token = _clean_env(os.environ.get("UPSTASH_REDIS_REST_TOKEN"))
    return UsageStats(url, token) if url and token else None
