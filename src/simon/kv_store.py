"""Storage backend abstraction for the app's small JSON progress records.

Render's free web service has no persistent disk -- its filesystem resets
on every restart/redeploy, which would otherwise wipe progress history each
time the app is updated. `get_default_store()` picks an Upstash Redis-backed
store (survives redeploys) when the UPSTASH_REDIS_REST_URL/TOKEN env vars
are set, and falls back to local JSON files otherwise -- so `python main.py`
still works offline with no external account needed for local development.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Protocol

from simon.app_mode import is_public_mode
from simon.storage_paths import storage_dir as _local_storage_dir

REQUEST_TIMEOUT_S = 5


def _log(message: str) -> None:
    """Plain stderr print rather than the logging module -- guaranteed to
    show up in Render's log stream with zero configuration, which matters
    since Upstash failures are otherwise swallowed silently by design (a
    caregiver losing one session's stats must never crash the app, but that
    same swallowing makes failures invisible without this)."""
    print(f"[kv_store] {message}", file=sys.stderr, flush=True)


class KeyValueStore(Protocol):
    def load(self, key: str, default: dict) -> dict: ...
    def save(self, key: str, data: dict) -> None: ...


class FileKeyValueStore:
    """One JSON file per key in a local directory. Not durable on Render's
    free tier (ephemeral filesystem) -- used for local desktop development
    and as the fallback when no remote store is configured."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def _path(self, key: str) -> Path:
        # NamespacedKeyValueStore joins namespace and key with ":" (the
        # idiomatic Redis separator), but ":" is an NTFS Alternate Data
        # Stream separator on Windows -- a raw "efraim:progress_v1.json"
        # filename silently creates a broken 0-byte file there instead of
        # erroring. Treating ":" as a path separator sidesteps this
        # entirely and reads naturally as "one subdirectory per namespace".
        *parts, filename = key.split(":")
        directory = self._directory.joinpath(*parts) if parts else self._directory
        return directory / f"{filename}.json"

    def load(self, key: str, default: dict) -> dict:
        path = self._path(key)
        if not path.is_file():
            return json.loads(json.dumps(default))
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return json.loads(json.dumps(default))

    def save(self, key: str, data: dict) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class NamespacedKeyValueStore:
    """Wraps another store, prefixing every key with a namespace -- used to
    give each user profile (e.g. "efraim", "tomer") completely separate
    progress records while sharing the same underlying backend/connection."""

    def __init__(self, inner: KeyValueStore, namespace: str) -> None:
        self._inner = inner
        self._namespace = namespace

    def _key(self, key: str) -> str:
        return f"{self._namespace}:{key}"

    def load(self, key: str, default: dict) -> dict:
        return self._inner.load(self._key(key), default)

    def save(self, key: str, data: dict) -> None:
        self._inner.save(self._key(key), data)


class InMemoryKeyValueStore:
    """Pure in-memory store, no filesystem I/O -- used by tests so store
    behavior is verified hermetically and fast."""

    def __init__(self) -> None:
        self._data: dict[str, dict] = {}

    def load(self, key: str, default: dict) -> dict:
        return json.loads(json.dumps(self._data.get(key, default)))

    def save(self, key: str, data: dict) -> None:
        self._data[key] = json.loads(json.dumps(data))


class UpstashKeyValueStore:
    """Stores each key as a value in an Upstash Redis database via its REST
    API -- the only one of these that survives a Render redeploy. Read/write
    failures (network hiccup, misconfigured credentials) degrade gracefully
    to an empty/unsaved record rather than crashing a game session; a
    caregiver losing one session's stats is far better than the app
    breaking mid-game for a stroke-recovery patient."""

    def __init__(self, url: str, token: str) -> None:
        self._url = url.rstrip("/")
        self._token = token

    def _request(self, method: str, path: str, body: bytes | None = None) -> dict:
        req = urllib.request.Request(
            f"{self._url}/{path}",
            data=body,
            method=method,
            headers={"Authorization": f"Bearer {self._token}"},
        )
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S) as resp:
            return json.loads(resp.read())

    def load(self, key: str, default: dict) -> dict:
        try:
            response = self._request("GET", f"get/{key}")
        except urllib.error.HTTPError as e:
            _log(f"load({key!r}) failed: HTTP {e.code} {e.reason} -- {e.read()[:200]!r}")
            return json.loads(json.dumps(default))
        except (urllib.error.URLError, OSError, TimeoutError, ValueError) as e:
            _log(f"load({key!r}) failed: {type(e).__name__}: {e}")
            return json.loads(json.dumps(default))

        result = response.get("result")
        if result is None:
            return json.loads(json.dumps(default))
        try:
            return json.loads(result)
        except json.JSONDecodeError as e:
            _log(f"load({key!r}) got unparsable result {result!r}: {e}")
            return json.loads(json.dumps(default))

    def save(self, key: str, data: dict) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        try:
            self._request("POST", f"set/{key}", body=payload)
        except urllib.error.HTTPError as e:
            _log(f"save({key!r}) failed: HTTP {e.code} {e.reason} -- {e.read()[:200]!r}")
        except (urllib.error.URLError, OSError, TimeoutError, ValueError) as e:
            _log(f"save({key!r}) failed: {type(e).__name__}: {e}")
            # best-effort -- the in-progress session still has the data in memory


def _clean_env(value: str | None) -> str | None:
    """Strips whitespace and, if present, a matching pair of surrounding
    quotes -- guards against the common copy-paste mistake of grabbing the
    quoted value straight out of Upstash's example curl snippet."""
    if value is None:
        return None
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value


class PublicModeStorageError(RuntimeError):
    """Raised if anything tries to reach persistent storage in public mode."""


def get_default_store() -> KeyValueStore:
    if is_public_mode():
        # The public app must never touch the family's database -- nor the
        # local-file fallback, which every visitor would share. Its storage
        # is a fresh InMemoryKeyValueStore per visit (AppState.activate_guest).
        raise PublicModeStorageError("persistent storage is disabled in public mode")
    url = _clean_env(os.environ.get("UPSTASH_REDIS_REST_URL"))
    token = _clean_env(os.environ.get("UPSTASH_REDIS_REST_TOKEN"))
    if url and token:
        _log(f"using Upstash Redis backend at {url}")
        return UpstashKeyValueStore(url, token)
    _log(
        "UPSTASH_REDIS_REST_URL/TOKEN not set -- using local file storage "
        "(will not survive a Render restart/redeploy)"
    )
    return FileKeyValueStore(_local_storage_dir())
