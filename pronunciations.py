"""
Words that ElevenLabs stresses wrongly, with a spelling that makes it say them right.

Only what is sent to ElevenLabs changes; the scripts and the console keep the normal spelling.
Each entry: a regular expression for the start of the word (case is ignored), and what to send
instead. An accent (é, á) marks the stressed syllable, as in Dutch ("omvérlopen"). Word endings
are kept, so "verrassing" also covers "verrassingen" and "verrassingsfeest".

After changing a respelling, the line is generated again the next time it is said (the voice
cache is keyed on the text that is sent).
"""
import re

PRONUNCIATIONS = [
    (r"omver", "omvér"),               # omvérlopen, omvérgelopen, omvérgooien
    (r"ver+assing", "verrássing"),     # verrássing (also the misspelling "verassing")
    (r"sinaasappel", "sináásappel"),   # sináásappelsap
]

_COMPILED = [(re.compile(r"\b" + pattern, re.IGNORECASE), respelling) for pattern, respelling in PRONUNCIATIONS]


def respell(text: str) -> str:
    def keep_case(respelling):
        def sub(match):
            return respelling[0].upper() + respelling[1:] if match.group(0)[0].isupper() else respelling
        return sub

    for pattern, respelling in _COMPILED:
        text = pattern.sub(keep_case(respelling), text)
    return text
