"""
Pick the laptop microphone for the *_laptop_mic episode scripts and utils/mic_check.py.

Set one of these in conf/.env:

    LAPTOP_MIC_NAME=Microphone (DJI MIC MINI)   # by (part of) the name; preferred, numbers change
    LAPTOP_MIC_INDEX=2                          # by number, see: python utils/mic_check.py list

Without either, the Windows default microphone is used. The name match ignores upper/lower case;
an exact name wins over a partial match. If the name matches no microphone, or several, the script
stops and lists the microphones, so a session never runs on the wrong microphone by accident.
"""

import os

import pyaudio


def list_input_devices() -> list[tuple[int, str]]:
    """(index, name) of every input device, as Windows lists them (MME, like the Sound settings)."""
    p = pyaudio.PyAudio()
    try:
        devices = []
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info["maxInputChannels"] > 0 and p.get_host_api_info_by_index(info["hostApi"])["name"] == "MME":
                devices.append((i, info["name"]))
        return devices
    finally:
        p.terminate()


def _device_list_text(devices: list[tuple[int, str]]) -> str:
    return "\n".join("  {:3}: {}".format(i, name) for i, name in devices)


def resolve_laptop_mic_index() -> int | None:
    """The microphone number to use, from LAPTOP_MIC_NAME or LAPTOP_MIC_INDEX; None = Windows default."""
    name = os.getenv("LAPTOP_MIC_NAME", "").strip()
    if name:
        devices = list_input_devices()
        # MME cuts names off at 31 characters, so also match on the start of a long name.
        wanted = name.lower()
        exact = [(i, n) for i, n in devices
                 if n.lower() == wanted or (len(n) >= 31 and wanted.startswith(n.lower()))]
        partial = [(i, n) for i, n in devices if wanted in n.lower()]
        matches = exact or partial
        if len(matches) == 1:
            return matches[0][0]
        problem = "matches no microphone" if not matches else "matches more than one microphone"
        raise RuntimeError(
            "LAPTOP_MIC_NAME={!r} {}. Use (more of) the exact name from this list:\n{}".format(
                name, problem, _device_list_text(matches or devices)))

    index = os.getenv("LAPTOP_MIC_INDEX", "").strip()
    return int(index) if index else None


def describe_laptop_mic(index: int | None) -> str:
    if index is None:
        p = pyaudio.PyAudio()
        try:
            return "Windows default ({})".format(p.get_default_input_device_info()["name"])
        finally:
            p.terminate()
    names = dict(list_input_devices())
    return "{}: {}".format(index, names.get(index, "unknown device"))
