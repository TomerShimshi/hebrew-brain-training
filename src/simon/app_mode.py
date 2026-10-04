"""Which flavour of the app this server runs.

The same code is deployed twice (see render.yaml):

- the family app (default): per-profile progress saved to the Upstash
  database, streaks, records and the progress screen;
- the public app (APP_MODE=public): the games only, for anyone. Nothing is
  saved anywhere -- each visit gets its own throwaway in-memory storage --
  and no profile names or history are ever shown.

The public service is also never given the Upstash credentials, and
kv_store.get_default_store() refuses to run in public mode, so the public
app has no path to the family's data even if it were misconfigured.
"""

import os

PUBLIC = "public"


def is_public_mode() -> bool:
    return os.environ.get("APP_MODE", "").strip().strip("\"'").lower() == PUBLIC
