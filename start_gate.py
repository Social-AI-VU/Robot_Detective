"""
Start gate: hold the episode until the operator gives the go-ahead.

After the robot and all services are set up, the episode runners call wait_for_start(). The NAO's
eyes turn blue and the robot waits until one of these happens:

- Enter is pressed in the episode's terminal window;
- the NAO's head (front, middle or back) or chest button is touched;
- someone says one of the start words (default "start" or "starten") into the microphone.

Then the eyes go off and the episode begins.

Settings in conf/.env (optional):
    START_GATE=0                 skip the gate and start immediately
    START_WORDS=start,starten    comma-separated words that start the episode
"""
import os
import re
import sys
import threading
import time

WAITING_EYES = {"r": 0, "g": 0, "b": 1}  # blue; green is already used for "robot is listening"
LISTEN_SECONDS = 5.0
STARTUP_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "startup_times.log")


def _process_start_time():
    """When this Python process started (so imports are included), or now if unknown."""
    try:
        import psutil

        return psutil.Process().create_time()
    except Exception:
        return time.time()


_PROCESS_START = _process_start_time()


def log_startup(step):
    """Write a timestamped startup step to logs/startup_times.log (and the console)."""
    now = time.time()
    line = "{}  {:<28} {:>6.1f} s after the episode script started  ({})".format(
        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)), step, now - _PROCESS_START,
        os.path.basename(sys.argv[0]) if sys.argv and sys.argv[0] else "?")
    print("[TIMING] " + line, flush=True)
    try:
        os.makedirs(os.path.dirname(STARTUP_LOG), exist_ok=True)
        with open(STARTUP_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def connect_nao(ip):
    """Connect to the NAO, and print how long it took.

    By default this skips SIC's install check on the robot: on every connect that check runs
    `pip install --upgrade social-interaction-cloud` on the NAO itself, which is slow on the robot
    and can hang for minutes when the robot's network has poor internet access. If SIC does not
    start on the robot without the check (e.g. a fresh NAO), it connects again with the check.
    Set NAO_CHECK_SIC_INSTALL=1 in conf/.env to always run it, for example after updating SIC
    on the laptop, so the robot gets the same version.
    """
    from sic_framework.devices import Nao

    check = os.getenv("NAO_CHECK_SIC_INSTALL", "0").strip().lower() in {"1", "true", "yes", "y"}
    log_startup("connecting to the NAO")
    print(f"[START] Connecting to the NAO at {ip}{' (with SIC install check)' if check else ''}...", flush=True)
    started = time.monotonic()
    try:
        nao = Nao(ip=ip, bypass_install=not check)
    except RuntimeError as exc:
        if check:
            raise
        print(f"[START] SIC did not start on the NAO ({exc}); trying again with the install check...", flush=True)
        nao = Nao(ip=ip, bypass_install=False)
    print(f"[START] NAO connected in {time.monotonic() - started:.0f} s", flush=True)
    log_startup("NAO connected")
    return nao


def _start_words():
    raw = os.getenv("START_WORDS", "start,starten")
    return [w.strip().lower() for w in raw.split(",") if w.strip()]


def wait_for_start(nao=None, device=None, nlu=None):
    """Block until the operator starts the episode. Returns how it was started."""
    log_startup("READY (waiting for start)")
    if os.getenv("START_GATE", "1").strip().lower() in {"0", "false", "no", "n"}:
        return "start gate disabled"

    started = threading.Event()
    how = {}

    def fire(source):
        if not started.is_set():
            how["source"] = source
            started.set()

    # 1. Enter in the terminal
    def keyboard():
        try:
            import msvcrt  # Windows console: poll keys, so this stops reading once the episode starts
        except ImportError:
            msvcrt = None
        if msvcrt is None:
            try:
                line = sys.stdin.readline()
            except Exception:
                return
            if line:  # "" means there is no keyboard (end of input), not an Enter press
                fire("Enter")
            return
        while not started.is_set():
            if msvcrt.kbhit() and msvcrt.getwch() in ("\r", "\n"):
                fire("Enter")
                return
            time.sleep(0.05)

    threading.Thread(target=keyboard, daemon=True).start()

    # 2. the NAO's head or chest button
    buttons_ok = False
    if nao is not None:
        def on_touch(message):
            for name, value in (getattr(message, "value", None) or []):
                if value and ("Head/Touch" in str(name) or "ChestBoard" in str(name)):
                    fire(f"button ({name})")
                    return
        try:
            nao.buttons.register_callback(on_touch)
            buttons_ok = True
        except Exception as exc:
            print(f"[START] NAO buttons not available: {exc}")

    # 3. a spoken start word
    words = _start_words()
    voice_thread = None
    if nlu is not None and words:
        pattern = re.compile(r"\b(" + "|".join(map(re.escape, words)) + r")\b", re.IGNORECASE)

        def voice():
            while not started.is_set():
                try:
                    result = nlu.listen(timeout=LISTEN_SECONDS)
                except Exception as exc:
                    print(f"[START] Listening failed: {exc}")
                    time.sleep(1)
                    continue
                if pattern.search(result.transcript or ""):
                    fire(f"voice ('{result.transcript}')")

        voice_thread = threading.Thread(target=voice, daemon=True)
        voice_thread.start()

    if device is not None:
        try:
            device.set_leds(**WAITING_EYES)
        except Exception as exc:
            print(f"[START] Could not set the eye colour: {exc}")

    ways = ["press Enter here"]
    if buttons_ok:
        ways.append("touch the NAO's head or chest")
    if voice_thread:
        ways.append("say " + " or ".join(f"'{w}'" for w in words))
    print("\n" + "=" * 70)
    print("  READY. The robot's eyes are blue.")
    print("  To start the episode: " + ", or ".join(ways) + ".")
    print("=" * 70 + "\n", flush=True)

    started.wait()
    print(f"[START] Starting the episode ({how['source']}).", flush=True)

    if device is not None:
        try:
            device.set_leds()
        except Exception:
            pass
    if voice_thread is not None:
        # Let the last start-word listen finish, so it cannot overlap with the episode's first question.
        voice_thread.join(timeout=LISTEN_SECONDS + 2)
    return how["source"]
