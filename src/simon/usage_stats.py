"""Anonymous usage counts for the public app: how many visits it gets, how
many of them actually played (bots and link previews open the page but
never start a game), how many different browsers visited and how often
they come, and how often each game is started. Totals only, with nothing
about who visited (no names, addresses or IDs).

Visitors are counted without any ID: the browser keeps just the date it
was last counted and how many different days it has visited, and once a
day adds one to the count for that day of visiting -- "a browser came for
its 3rd day" -- both in the day's counts and in the all-time `usage:all`
(record_visitor). So all time, the "day 1" count is how many different
browsers ever came and the "day 5" count how many came at least 5 days.

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
_VISITOR_PREFIX = "visitor:day:"
_KEY_PREFIX = "usage:"
ALL_TIME_KEY = f"{_KEY_PREFIX}all"
# the browser's local storage: the last day this browser was counted, and
# on how many different days it has visited
LAST_COUNTED_KEY = "usage_last_counted"
DAYS_VISITED_KEY = "usage_days_visited"
_GAME_PREFIX = "game:"


def game_event(game_key: str) -> str:
    return f"{_GAME_PREFIX}{game_key}"


def game_counts(counts: dict[str, int]) -> dict[str, int]:
    """{game key: times started} out of a day's counts."""
    return {k.removeprefix(_GAME_PREFIX): v for k, v in counts.items() if k.startswith(_GAME_PREFIX)}


def visitor_day_event(n: int) -> str:
    """A browser came for its n-th day of visiting."""
    return f"{_VISITOR_PREFIX}{n}"


def visitor_days(counts: dict[str, int]) -> dict[int, int]:
    """{day of visiting: browsers} out of a day's (or all-time) counts."""
    return {int(k.removeprefix(_VISITOR_PREFIX)): v for k, v in counts.items() if k.startswith(_VISITOR_PREFIX)}


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
        self._increment(f"{_KEY_PREFIX}{(day or today()).isoformat()}", event)

    def record_all_time(self, event: str) -> None:
        self._increment(ALL_TIME_KEY, event)

    def _increment(self, key: str, event: str) -> None:
        def job() -> None:
            try:
                self._post("", ["HINCRBY", key, event, 1])
            except Exception as e:  # best-effort: never let counting break play
                _log(f"record({event!r}) failed: {type(e).__name__}: {e}")

        _in_background(job)

    def totals(self) -> dict[str, int] | None:
        """The all-time counts, or None if they can't be read."""
        try:
            flat = self._post("", ["HGETALL", ALL_TIME_KEY]).get("result") or []
        except Exception as e:
            _log(f"totals failed: {type(e).__name__}: {e}")
            return None
        return {flat[i]: int(flat[i + 1]) for i in range(0, len(flat), 2)}

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


def visitor_day(last_counted: str | None, days_visited: int | None, day: date) -> int | None:
    """Which day of visiting `day` is for a browser last counted on
    `last_counted` after `days_visited` days -- None if already counted."""
    if last_counted == day.isoformat():
        return None
    return (days_visited or 0) + 1


async def record_visitor(stats: UsageStats, prefs, day: date | None = None) -> None:
    """Counts this browser once a day by its day of visiting, using only
    what it keeps in its local storage (`prefs`, Flet's shared_preferences)."""
    day = day or today()
    try:
        last = await prefs.get(LAST_COUNTED_KEY)
        days = await prefs.get(DAYS_VISITED_KEY)
        n = visitor_day(last if isinstance(last, str) else None, days if isinstance(days, int) else None, day)
        if n is None:
            return
        await prefs.set(LAST_COUNTED_KEY, day.isoformat())
        await prefs.set(DAYS_VISITED_KEY, n)
    except Exception as e:  # no local storage (e.g. blocked): just skip it
        _log(f"record_visitor failed: {type(e).__name__}: {e}")
        return
    stats.record(visitor_day_event(n), day)
    stats.record_all_time(visitor_day_event(n))


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
