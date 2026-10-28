"""
Build the sound effects the episode JSONs play, from the source files in this folder.

nardial's "play" move only reads 16-bit WAV, so every effect is written as <name>.wav in the
same format as the robot's speech (mono, 16-bit, 24 kHz). The source MP3s stay untouched.
Needs ffmpeg on the PATH.

    python sounds/make_sounds.py            # build effects that have no WAV yet
    python sounds/make_sounds.py --force    # rebuild everything (after changing SOUNDS)

SOUNDS maps each effect name to the pieces it is made of: (source file, start second, length in
seconds or None for "until the end"), optionally followed by an ffmpeg audio filter for that piece
(e.g. "lowpass=f=450" to make it sound muffled). Pieces are joined in order; a short fade smooths each cut.
"""
import shutil
import subprocess
import sys
from pathlib import Path

SOUNDS_DIR = Path(__file__).resolve().parent
FADE_SEC = 0.15
NAO_MASTERING = ("highpass=f=200:poles=2,highpass=f=200:poles=2,"
                 "loudnorm=I=-18:TP=-1.5:LRA=11,aresample=24000")  # loudnorm works at 192 kHz internally

SOUNDS = {
    "aankloppen": [  # ep3: knocking on the glass front door; two knocks without the silence between them
        ("freesound_community-knocking-on-window-99754.mp3", 0.2, 1.45),
        ("freesound_community-knocking-on-window-99754.mp3", 4.2, 1.9),
    ],
    "bel_madeliefje": [("dragon-studio-cute-doorbell-chime-472376.mp3", 0, None)],
    "birdie_soundsystem": [("A_techno_house_remix_#2-1790175685680.mp3", 0, None)],
    "deurbel": [("dragon-studio-doorbell-ding-dong-482879.mp3", 0, None)],
    "gigagiebels": [("Hazel ligt in een deuk.mp3", 0, None)],
    "hazel_laugh_2": [("Hazel laugh 2.mp3", 0, None)],  # ep2: Hazel's second laugh
    "giebels_heike": [("Heike Gigagiebels.mp3", 0, None)],  # ep2: Heike gets the Gigagiebels
    "giebels_shukri": [("Choukri giebels.mp3", 0, None)],  # ep2: Shukri giggles and says to go to Eddy
    "hoesten": [("Stoep moet hoesten.mp3", 0, None)],
    "intercom_kraak": [("freesound_community-malfunctioning-intercom-31955.mp3", 0.6, 2.5)],
    "klokbel": [("klokbel.mp3", 0, None)],
    "kloppen_deur_kraakt": [  # ep2: knocking on Choukri's door, then the door creaking open
        ("freesound_community-knocking-on-door-6022.mp3", 0, 1.9),
        ("freesound_community-knocking-on-door-6022.mp3", 3.45, 1.65),
        ("universfield-creaking-door-03-487855.mp3", 0, None),
    ],
    "knal_voetstappen": [  # ep2: a bang from Eddy's lab, then footsteps
        ("universfield-animated-cartoon-explosion-impact-352744.mp3", 0, None),
        ("freesound_community-footsteps-in-a-hallway-47842.mp3", 0, 2.5),
    ],
    "pakketje_open": [("freesound_community-tearing-paper-76041.mp3", 0.7, 6.0)],
    "telefoon": [("freesound_community-telephone-electronic-42654.mp3", 0, None)],
    "skateboard": [("freesound_community-skateboard-40912.mp3", 0, 4.2)],  # ep2 + ep3; the rest is silence
    "kloppen": [  # ep1: knocking on Eddy's door
        ("freesound_community-knocking-on-door-6022.mp3", 0, 1.9),
        ("freesound_community-knocking-on-door-6022.mp3", 3.45, 1.65),
    ],
    "deur_kraakt": [("universfield-creaking-door-03-487855.mp3", 0, None)],  # ep1: Eddy's door opens
    "voetstappen": [("freesound_community-footsteps-in-a-hallway-47842.mp3", 0, 2.5)],  # ep1: Jennifer, chasing her
    "intercom_ruis": [  # ep1: Kata's intercom crackling on (after the doorbell) and off (after "Doeiii!")
        ("dragon-studio-radio-static-323621.mp3", 0.3, 2.5, "afade=t=in:d=0.15"),
    ],
    "techno_intercom": [  # ep1: Kata's new record, heard through the intercom (thin, phone-like)
        ("kata mix celebration.mp3", 0, 5.0, "highpass=f=400,lowpass=f=2800"),
    ],
    # NB: the NAO's small speakers barely play anything below ~200 Hz. A "muffled" sound made with a
    # low lowpass filter, or a deep rumble, is silent on the robot; keep the sound between ~250 and
    # 2000 Hz instead (check: python sounds/check_sounds.py).
    "techno_kelder": [  # ep1: the beat still coming up from the basement: mid frequencies only, so muffled
        ("kata mix celebration.mp3", 8.0, 6.0, "afade=t=in:d=0.5,highpass=f=300,lowpass=f=1200,volume=4dB"),
    ],
    "radio_bleep": [("radio bleep.mp3", 0, None)],  # ep1: Robin's radio on and off
    "trudy_zingt": [  # ep1: Trudy singing; 10 s from where the music comes in
        ("Carmen - Habanera.mp3", 6.0, 10.0, "afade=t=in:d=0.3"),
    ],
    "leenauto_opstijgen": [("flying car takeoff.mp3", 0, 7.0)],  # ep1: Jennifer flies off in the car
    "trilling": [  # ep1: the whole flat shakes. The rumble is far too deep for the NAO, so it is pitched
        # up 4x (same length) and saturated (tanh), which adds overtones the robot can play, plus a
        # fast tremolo for the shaking.
        ("rumbling.mp3", 0, 6.0, "asetrate=96000,aresample=24000,atempo=0.5,atempo=0.5,"
                                 "volume=18dB,aeval=tanh(1.5*val(0)),tremolo=f=8:d=0.6,afade=t=in:d=0.4"),
    ],
    "glijbaan": [("universfield-whistle-slide-down-323778.mp3", 0, None)],  # ep1: down the slide to the basement
    "party_horn": [("party horn.mp3", 0, None)],  # ep1: VERRASSING!
    "kata_feest": [("kata mix celebration.mp3", 0, None)],  # ep1: the dance at the end
    "scene_overgang": [  # all episodes: at the start of every new scene (on to the next character)
        ("scene transition.mp3", 0, 5.5, "afade=t=out:st=4.3:d=1.2"),
    ],
}


def build(name, pieces):
    inputs, filters = [], []
    for i, (source, start, length, *extra) in enumerate(pieces):
        path = SOUNDS_DIR / source
        if not path.exists():
            return f"missing source file: {source}"
        inputs += ["-i", str(path)]
        trim = f"atrim=start={start}" + (f":duration={length}" if length else "")
        chain = f"[{i}:a]{trim},asetpts=PTS-STARTPTS"
        if extra:
            chain += "," + extra[0]
        chain += ",aformat=sample_fmts=s16:sample_rates=24000:channel_layouts=mono"
        if length:  # only fade where we actually cut the sound off
            chain += f",afade=t=out:st={max(0.0, length - FADE_SEC)}:d={FADE_SEC}"
        filters.append(chain + f"[p{i}]")
    joined = "".join(f"[p{i}]" for i in range(len(pieces)))
    # Made for the NAO's small speakers: drop the deep bass they cannot play (it only takes up
    # loudness), then bring every effect to the same loudness, so none is drowned out or too loud.
    filters.append(f"{joined}concat=n={len(pieces)}:v=0:a=1,{NAO_MASTERING}[out]")
    result = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filters),
         "-map", "[out]", "-ac", "1", "-ar", "24000", "-sample_fmt", "s16", str(SOUNDS_DIR / f"{name}.wav")],
        capture_output=True, text=True,
    )
    return None if result.returncode == 0 else result.stderr.strip()


def main() -> int:
    if shutil.which("ffmpeg") is None:
        print("ffmpeg not found; install it or add it to PATH.")
        return 1
    force = "--force" in sys.argv[1:]
    failures = 0
    for name, pieces in SOUNDS.items():
        if (SOUNDS_DIR / f"{name}.wav").exists() and not force:
            print(f"skip  {name}.wav (exists; use --force to rebuild)")
            continue
        error = build(name, pieces)
        if error:
            failures += 1
            print(f"FAIL  {name}.wav: {error}")
        else:
            print(f"ok    {name}.wav")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
