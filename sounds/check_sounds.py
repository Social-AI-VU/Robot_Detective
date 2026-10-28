"""
Check every sound effect for things that make it fail or go unheard on the NAO.

    python sounds/check_sounds.py

- format: nardial only plays 16-bit WAV (make_sounds.py writes mono 16-bit 24 kHz);
- loudness: very quiet sounds disappear next to the robot's speech;
- low tones: the NAO's small speakers barely play anything below ~200 Hz, so a sound whose
  energy is mostly that low (a deep rumble, a strongly muffled beat) is silent on the robot.
"""
import sys
import wave
from pathlib import Path

import numpy as np

SOUNDS_DIR = Path(__file__).resolve().parent
LOW_HZ = 200
MAX_LOW_SHARE = 60   # % of the energy below LOW_HZ before we warn
MIN_LOUDNESS_DB = -30


def main() -> int:
    problems = 0
    print(f"{'sound':24} {'sec':>5} {'loudness':>9} {'< 200 Hz':>9}  verdict")
    for path in sorted(SOUNDS_DIR.glob("*.wav")):
        try:
            with wave.open(str(path)) as w:
                width, rate, frames = w.getsampwidth(), w.getframerate(), w.getnframes()
                raw = w.readframes(frames)
                channels = w.getnchannels()
        except Exception as exc:
            print(f"{path.stem:24} cannot read: {exc}")
            problems += 1
            continue
        if width != 2:
            print(f"{path.stem:24} not 16-bit ({8 * width}-bit): nardial cannot play it")
            problems += 1
            continue
        x = np.frombuffer(raw, dtype=np.int16).astype(float)
        if channels > 1:
            x = x.reshape(-1, channels).mean(axis=1)
        loud = 20 * np.log10(np.sqrt(np.mean(x ** 2)) / 32768 + 1e-12)
        energy = np.abs(np.fft.rfft(x)) ** 2
        freqs = np.fft.rfftfreq(len(x), 1 / rate)
        low = energy[freqs < LOW_HZ].sum() / max(energy.sum(), 1e-12) * 100
        notes = []
        if low > MAX_LOW_SHARE:
            notes.append("mostly too low for the NAO speaker")
        if loud < MIN_LOUDNESS_DB:
            notes.append("very quiet")
        problems += bool(notes)
        print(f"{path.stem:24} {len(x) / rate:5.1f} {loud:7.1f}dB {low:8.0f}%  {', '.join(notes) or 'ok'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
