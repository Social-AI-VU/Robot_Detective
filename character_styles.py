"""
Eye colour and gestures per character, so children can see who is talking on the NAO.

- "eyes" is (red, green, blue), each 0.0 to 1.0. Green is kept free: green eyes mean
  "it is your turn to talk".
- "gestures" are NAO animations; one is picked at random each time the character speaks.
  Only use animation names that exist on the NAO (the ones below are standard NAOqi animations).
- "thinking" are short sounds the character makes while the answer to a child is being generated,
  so the wait does not feel empty. Keep them short (1 to 3 words); they are cached after first use.

Characters that never share a scene may reuse a colour; the NAO eyes can only show a handful
of clearly different colours.
"""

CHARACTER_STYLES = {
    # Robin: curious detective, explains and thinks out loud.
    "robin": {
        "eyes": (0.0, 0.3, 1.0),  # blue
        "gestures": [
            "animations/Stand/Gestures/Explain_1",
            "animations/Stand/Gestures/Explain_10",
            "animations/Stand/Gestures/Thinking_1",
            "animations/Stand/Gestures/Thinking_3",
            "animations/Stand/Gestures/YouKnowWhat_2",
            "animations/Stand/Gestures/Me_1",
        ],
        "thinking": [
            "Hmm, even nadenken...",
            "Hmmm...",
            "Even kijken...",
        ],
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
        "thinking": [
            "Hmm, interessant...",
            "Even denken...",
            "Aha, hmm...",
        ],
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
        "thinking": [
            "Ooh, even denken hoor...",
            "Hmmm, kinders...",
            "Tjonge, even nadenken...",
        ],
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
        "thinking": [
            "Hmm, fascinerend...",
            "Even nadenken...",
            "Hmm, hmm...",
        ],
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
        "thinking": [
            "Uhh, even denken...",
            "Hmm...",
            "Ehm, wacht even...",
        ],
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
        "thinking": [
            "Hmmm... tja...",
            "Ach schat, even denken...",
            "Mmm...",
        ],
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
        "thinking": [
            "Hmm, wacht effe...",
            "Uhh, yo, even denken...",
            "Hmm...",
        ],
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
        "thinking": [
            "Hmm, ja man...",
            "Uhh...",
            "Even denken...",
        ],
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
        "thinking": [
            "Uhh...",
            "Hmm, even denken...",
            "Ehm...",
        ],
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
        "thinking": [
            "Well, hmm...",
            "Even denken, honey...",
            "Hmm...",
        ],
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
        "thinking": [
            "Uhh, even denken...",
            "Hmm...",
            "Ehm, wacht...",
        ],
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
        "thinking": [
            "Hmm... even denken...",
            "Oh, eh...",
            "Mmm...",
        ],
    },
    "leen": {
        "eyes": (1.0, 0.85, 0.0),  # yellow
        "gestures": [
            "animations/Stand/Gestures/Explain_2",
            "animations/Stand/Gestures/Give_3",
            "animations/Stand/Gestures/Me_1",
        ],
        "thinking": [
            "Hmm...",
            "Even denken...",
            "Ehm...",
        ],
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
