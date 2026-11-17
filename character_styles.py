"""
Eye colour and gestures per character, so children can see who is talking on the NAO.

- "eyes" is (red, green, blue), each 0.0 to 1.0. Green is kept free: green eyes mean
  "it is your turn to talk".
- "gestures" are NAO animations; one is picked at random each time the character speaks.
  Only use animation names that exist on the NAO (the ones below are standard NAOqi animations).
- "thinking" are short sounds the character makes while the answer to a child is being generated,
  so the wait does not feel empty. Each character has its own, in its own style; the same one is not
  used twice in a row (runtime_patches.py remembers the last few). Keep them short (1 to 4 words), and
  no "wacht even": that sounded odd. They are cached after first use.
- "volume" (optional, default 1.0) multiplies how loud the character speaks on the robot. Some
  ElevenLabs voices come out much quieter than others; 2.0 is twice as loud. Audio is never pushed
  into distortion: a piece that would get too loud is turned up only as far as it cleanly can.

Characters that never share a scene may reuse a colour; the NAO eyes can only show a handful
of clearly different colours.
"""

CHARACTER_STYLES = {
    # Robin: curious detective, explains and thinks out loud.
    "robin": {
        "eyes": (0.0, 0.3, 1.0),  # blue
        # No Thinking_* gestures while he talks: in those the NAO looks down at the floor.
        "gestures": [
            "animations/Stand/Gestures/Explain_1",
            "animations/Stand/Gestures/Explain_3",
            "animations/Stand/Gestures/Explain_8",
            "animations/Stand/Gestures/Explain_10",
            "animations/Stand/Gestures/YouKnowWhat_1",
            "animations/Stand/Gestures/YouKnowWhat_2",
            "animations/Stand/Gestures/Me_1",
        ],
        "thinking": ["Hmm...", "Bliep... even denken.", "Mijn schroefjes draaien...", "Hmm, interessant...", "Even rekenen...", "Bzzt... hmm..."],
    },
    # Narrator: calm storyteller.
    "narrator": {
        "eyes": (1.0, 1.0, 1.0),  # white
        "gestures": [
            "animations/Stand/Gestures/Explain_2",
            "animations/Stand/Gestures/Explain_4",
            "animations/Stand/Gestures/Explain_5",
        ],
    },
    # Stoep Tegel: dramatic radio presenter, big gestures.
    "s_tegel": {
        "eyes": (1.0, 0.45, 0.0),  # orange
        "gestures": [
            "animations/Stand/Gestures/Everything_3",
            "animations/Stand/Gestures/Everything_4",
            "animations/Stand/Gestures/Far_1",
            "animations/Stand/Gestures/Far_2",
            "animations/Stand/Gestures/Enthusiastic_4",
        ],
        "thinking": ["Aha...", "Interessant, interessant...", "Hmm, even noteren...", "Oei, goeie vraag...", "Laat me even denken...", "Mmm..."],
    },
    # Trudy: dramatic, cheerful singer, arms up to the sky.
    "trudy": {
        "eyes": (1.0, 0.1, 0.6),  # pink
        "gestures": [
            "animations/Stand/Gestures/Enthusiastic_4",
            "animations/Stand/Gestures/ShowSky_1",
            "animations/Stand/Gestures/ShowSky_5",
            "animations/Stand/Gestures/ShowSky_7",
            "animations/Stand/Emotions/Positive/Happy_4",
        ],
        "thinking": ["Ooh, tjonge...", "Hmm, even denken hoor...", "Ach, hoe was het ook alweer...", "Ojee...", "Nou, eens kijken...", "Lalala... hmm..."],
    },
    # Professor Eddy: calm, smart, a bit absent-minded, thinks a lot.
    "eddy": {
        "eyes": (1.0, 0.85, 0.0),  # yellow
        "gestures": [
            "animations/Stand/Gestures/Thinking_1",
            "animations/Stand/Gestures/Thinking_3",
            "animations/Stand/Gestures/Thinking_6",
            "animations/Stand/Gestures/Explain_11",
            "animations/Stand/Gestures/IDontKnow_1",
        ],
        "thinking": ["Fascinerend...", "Hmm, hoe zat dat ook alweer...", "Eens even kijken...", "Interessant...", "Ahum...", "Laat me even nadenken..."],
    },
    # Yoyo: cool and funny.
    "yoyo": {
        "eyes": (1.0, 0.0, 0.0),  # red
        "gestures": [
            "animations/Stand/Gestures/YouKnowWhat_2",
            "animations/Stand/Gestures/But_1",
            "animations/Stand/Gestures/Yes_2",
            "animations/Stand/Gestures/Give_3",
        ],
        "thinking": ["Yo... eh...", "Hmm, effe denken...", "Euhm...", "Pfoe...", "Yo, goeie vraag...", "Hmm-hmm..."],
    },
    # Jennifer: mysterious and theatrical, slow calm gestures.
    "jennifer": {
        "eyes": (0.6, 0.0, 1.0),  # purple
        "gestures": [
            "animations/Stand/Gestures/CalmDown_6",
            "animations/Stand/Gestures/Far_3",
            "animations/Stand/Gestures/ShowFloor_3",
            "animations/Stand/Gestures/ShowFloor_4",
            "animations/Stand/Emotions/Positive/Peaceful_1",
        ],
        "thinking": ["Mmm, schat...", "Ach lieverd...", "Tsja...", "Oeh, even denken...", "Mmmh...", "Hmm, wauw..."],
    },
    # DJ Kata: cool and hyper, energetic.
    "kata": {
        "eyes": (0.0, 0.9, 1.0),  # cyan
        "gestures": [
            "animations/Stand/Gestures/Enthusiastic_4",
            "animations/Stand/Gestures/ShowSky_8",
            "animations/Stand/Gestures/Everything_3",
            "animations/Stand/Gestures/Yes_1",
            "animations/Stand/Emotions/Positive/Happy_4",
        ],
        "thinking": ["Yo, effe denken...", "Uhh...", "Hmm, sick vraag...", "Yo yo...", "Hmm, let me think...", "Mmm..."],
    },
    # Toon: relaxed and tough ("ja man").
    "toon": {
        "eyes": (1.0, 0.45, 0.0),  # orange
        "gestures": [
            "animations/Stand/Gestures/But_1",
            "animations/Stand/Gestures/Give_5",
            "animations/Stand/Gestures/You_1",
            "animations/Stand/Gestures/Yes_1",
        ],
        "thinking": ["Ja man... eh...", "Hmm...", "Uhh...", "Effe denken...", "Pff...", "Tja..."],
    },
    # Rami: relaxed and funny, Toon's younger brother.
    "rami": {
        "eyes": (1.0, 0.0, 0.0),  # red
        "gestures": [
            "animations/Stand/Gestures/Me_4",
            "animations/Stand/Gestures/Give_3",
            "animations/Stand/Gestures/No_2",
            "animations/Stand/Gestures/YouKnowWhat_2",
        ],
        "thinking": ["Uhh...", "Ehm...", "Ja man... eh...", "Pff...", "Hmm...", "Eh, nou..."],
    },
    # Hazel: 110 years old, tough and hearty.
    "hazel": {
        "eyes": (1.0, 0.1, 0.6),  # pink
        "gestures": [
            "animations/Stand/Gestures/Me_4",
            "animations/Stand/Gestures/Far_1",
            "animations/Stand/Gestures/Give_5",
            "animations/Stand/Gestures/Everything_2",
        ],
        "thinking": ["Well, honey...", "Hmm, let me think...", "Oh boy...", "Even denken, honey...", "Hmm...", "Goodness..."],
    },
    # Heike: tough, fast and direct.
    "heike": {
        "eyes": (0.0, 0.9, 1.0),  # cyan
        "gestures": [
            "animations/Stand/Gestures/Enthusiastic_4",
            "animations/Stand/Gestures/You_1",
            "animations/Stand/Gestures/No_9",
            "animations/Stand/Gestures/Yes_2",
        ],
        "thinking": ["Ehh...", "Hmm, effe kijken...", "Pff...", "Uhm...", "Oké, eh...", "Even denken..."],
    },
    # Choukri: soft, shy and dreamy, small gestures.
    "choukri": {
        "eyes": (0.6, 0.0, 1.0),  # purple
        "gestures": [
            "animations/Stand/Emotions/Positive/Peaceful_1",
            "animations/Stand/Gestures/Thinking_6",
            "animations/Stand/Gestures/ShowFloor_3",
            "animations/Stand/Gestures/Me_1",
        ],
        "thinking": ["Oh, eh...", "Mmm...", "Hmm... even denken...", "Eh... tja...", "Ohh...", "Hmm, ja..."],
    },
    "leen": {
        "eyes": (1.0, 0.85, 0.0),  # yellow
        "gestures": [
            "animations/Stand/Gestures/Explain_2",
            "animations/Stand/Gestures/Give_3",
            "animations/Stand/Gestures/Me_1",
        ],
        "thinking": ["Hmm...", "Even denken...", "Ehm...", "Tja...", "Goeie vraag...", "Eens kijken..."],
    },
}

# Played together with a "thinking" sound.
THINKING_GESTURES = [
    "animations/Stand/Gestures/Thinking_1",
    "animations/Stand/Gestures/Thinking_3",
    "animations/Stand/Gestures/Thinking_6",
]

# Lines without their own voice are spoken in the default voice, which is Robin.
DEFAULT_CHARACTER = "robin"
