import asyncio

import flet_audio as fa

from simon.models import COLORS

TONE_FILES = {
    "red": "sounds/tone_red.wav",
    "blue": "sounds/tone_blue.wav",
    "green": "sounds/tone_green.wav",
    "yellow": "sounds/tone_yellow.wav",
}
ERROR_SOUND = "sounds/error.wav"


class SoundBoard:
    """Wraps Flet Audio controls for the 4 color tones plus the error cue.

    Audio is a "service" control (no visible UI): it must be attached via a
    View's `services=` list, not added as a regular child control or mutated
    onto `page.services` after the fact (`page.services` only proxies to
    `page.views[0].services`, so it's unusable before a view exists and is
    the wrong place to add per-screen services anyway). `controls` below is
    handed straight to `ft.View(services=...)` by the caller.

    Two things keep the first note of a game from going silent:
    - the client loads each sound file only once the view appears, so
      `wait_until_loaded()` lets the game hold its first note until the
      tones are ready (on the web, right after a sleeping server wakes up,
      that can take longer than the game's short opening pause);
    - ReleaseMode.STOP keeps each sound loaded after it plays -- the default
      (RELEASE) throws it away and reloads it before every replay.
    """

    def __init__(self) -> None:
        self._loaded: set[str] = set()
        self._all_tones_loaded = asyncio.Event()
        self._tones = {color: self._audio(path, color) for color, path in TONE_FILES.items()}
        self._error = self._audio(ERROR_SOUND, "error")
        self.controls = [*self._tones.values(), self._error]

    def _audio(self, path: str, name: str) -> fa.Audio:
        def on_loaded(_) -> None:
            self._loaded.add(name)
            if self._loaded >= set(TONE_FILES):
                self._all_tones_loaded.set()

        return fa.Audio(src=path, release_mode=fa.ReleaseMode.STOP, on_loaded=on_loaded)

    async def wait_until_loaded(self, timeout_s: float) -> bool:
        """Waits until all four tones are ready to play, but never longer than
        `timeout_s` -- if audio is broken on a device, the game still starts
        (silently) rather than hanging. Returns whether the tones loaded."""
        try:
            await asyncio.wait_for(self._all_tones_loaded.wait(), timeout_s)
            return True
        except asyncio.TimeoutError:
            return False

    async def stop_all(self, timeout_s: float = 0.5) -> None:
        """Stops any sound that's still playing (e.g. when the player leaves
        the game mid-note). Best effort and bounded, so leaving the screen is
        never held up by the audio backend."""
        pauses = [audio.pause() for audio in self.controls]
        try:
            await asyncio.wait_for(asyncio.gather(*pauses, return_exceptions=True), timeout_s)
        except asyncio.TimeoutError:
            pass

    async def play_color(self, index: int) -> None:
        await self._tones[COLORS[index]].play()

    async def play_error(self) -> None:
        await self._error.play()
