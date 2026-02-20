from __future__ import annotations

from math import sin, tau

import sounddevice as sd


class Buzzer:
    def __init__(self) -> None:
        self.active = False
        self.phase = 0
        self.wave = tuple(int(6_000 * sin(tau * index / 100)) for index in range(100))
        self.stream: sd.RawOutputStream | None = None
        try:
            self.stream = sd.RawOutputStream(
                samplerate=44_100,
                channels=1,
                dtype="int16",
                callback=self._write,
            )
            self.stream.start()
        except (sd.PortAudioError, OSError):
            self.stream = None

    @property
    def available(self) -> bool:
        return self.stream is not None

    def set_active(self, active: bool) -> None:
        self.active = active and self.available

    def close(self) -> None:
        if self.stream:
            try:
                self.stream.close()
            except sd.PortAudioError:
                pass
            self.stream = None

    def _write(self, outdata: memoryview, frames: int, _time: object, _status: object) -> None:
        samples = memoryview(outdata).cast("h")
        if not self.active:
            for index in range(frames):
                samples[index] = 0
            return
        for index in range(frames):
            samples[index] = self.wave[self.phase]
            self.phase = (self.phase + 1) % len(self.wave)
