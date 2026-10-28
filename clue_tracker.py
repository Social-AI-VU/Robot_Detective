"""
Count exactly which clues the children discovered in the interviews (chitchat + interview with a character).

The clues come straight from the knowledge files ("Clue 1 (...): text" in
Detective_Data/Episode_<n>_Detective_Data/Ep<n>_<Name>/conversation_guidelines.txt), so changing a clue
there changes what is counted. After every chitchat or interview, a background check compares everything
that character said in the conversation with their clues. Only what came up in conversation counts as
discovered; scripted lines (intros, the scripted clues in the short versions) do not.

Results:
- logs/clues_found.jsonl: one line per check, and one summary line at Stoep Tegel's finale;
- the episode window: "[CLUES] Yoyo: 2/3 (1, 3)";
- Stoep Tegel's summary at the end gets the exact list and an estimate based on the count.
"""

import asyncio
import datetime
import json
import os
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent
DATA_DIR = REPO / "Detective_Data"
LOG_FILE = REPO / "logs" / "clues_found.jsonl"
CLUE_LINE = re.compile(r"^\s*\**\s*clue\s*(\d+)\s*(?:\([^)]*\))?\s*:\s*(.+)$", re.IGNORECASE)

# What the children discovered in this session: character -> set of clue numbers.
_found: dict[str, set[int]] = {}
_met: dict[str, tuple[int, str]] = {}  # character -> (episode, display name) of the characters interviewed
_pending: dict[str, asyncio.Task] = {}


def _character_key(folder_name: str) -> str:
    """'Ep1_Dj_Kata' -> 'kata', 'Ep3_S_Tegel' -> 's_tegel' (the character keys of the episode JSONs)."""
    key = re.sub(r"^Ep\d+_", "", folder_name).lower()
    return {"dj_kata": "kata"}.get(key, key)


def clues_for(episode: int, character: str) -> dict[int, str]:
    """{clue number: clue text} for this character in this episode, read from the knowledge files."""
    for episode_dir in DATA_DIR.glob(f"Episode_{episode}_Detective_[Dd]ata"):
        for folder in episode_dir.iterdir():
            if folder.is_dir() and _character_key(folder.name) == character:
                clues = {}
                for path in sorted(folder.glob("*.txt")):
                    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                        match = CLUE_LINE.match(line)
                        if match:
                            clues.setdefault(int(match.group(1)), match.group(2).strip())
                return clues
    return {}


def episode_of(dialog_id: str) -> int | None:
    match = re.match(r"Ep(\d+)_", dialog_id or "")
    return int(match.group(1)) if match else None


def _log(entry: dict) -> None:
    entry = {"time": datetime.datetime.now().isoformat(timespec="seconds"),
             "participant": os.getenv("PARTICIPANT_ID", ""), **entry}
    try:
        LOG_FILE.parent.mkdir(exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as exc:
        print("[CLUES] could not write {}: {}".format(LOG_FILE, exc))


def _parse_numbers(text: str, valid) -> set[int]:
    match = re.search(r"\{.*\}", text or "", re.DOTALL)
    try:
        numbers = json.loads(match.group(0)).get("gevonden", []) if match else []
    except Exception:
        numbers = re.findall(r"\d+", text or "")
    return {int(n) for n in numbers if str(n).isdigit() and int(n) in valid}


async def _check(agent, episode: int, character: str, name: str, lines: list[str]) -> None:
    clues = clues_for(episode, character)
    if not clues:
        return
    numbered = "\n".join(f"{i + 1}. {line}" for i, line in enumerate(lines)) or "(niets)"
    clue_list = "\n".join(f"Clue {n}: {text}" for n, text in sorted(clues.items()))
    prompt = (
        f"Je controleert een detectivespel voor kinderen. Hieronder staan de clues van {name}, en alles wat "
        f"{name} in een gesprek tegen de kinderen heeft gezegd. Welke clues heeft {name} in dat gesprek echt "
        f"verteld? Een clue telt als verteld als de kern ervan duidelijk gezegd is, ook in andere woorden. "
        f"Een vage hint of iets wat er alleen op lijkt telt niet.\n\nCLUES VAN {name.upper()}:\n{clue_list}\n\n"
        f"WAT {name.upper()} ZEI:\n{numbered}\n\n"
        f'Antwoord alleen met JSON, zo: {{"gevonden": [1, 3]}} (een lege lijst als er geen clue verteld is).'
    )
    try:
        reply = await agent.ask_llm(user_prompt="Welke clues zijn verteld?", context_messages=[], system_prompt=prompt)
    except Exception as exc:
        print("[CLUES] check for {} failed: {}".format(name, exc))
        return
    found = _parse_numbers(reply, clues)
    _found[character] = _found.get(character, set()) | found
    total = len(clues)
    print("[CLUES] {}: {}/{} ({})".format(name, len(_found[character]), total,
                                         ", ".join(map(str, sorted(_found[character]))) or "none"), flush=True)
    _log({"episode": episode, "character": character, "found": sorted(_found[character]), "total": total,
          "found_this_check": sorted(found), "clues": {str(n): t for n, t in sorted(clues.items())}})


def check_in_background(agent, dialog_id: str, character: str, name: str, lines: list[str]) -> None:
    """Start the check for this character after a chitchat/interview; the episode does not wait for it."""
    episode = episode_of(dialog_id)
    if episode is None or not character or not clues_for(episode, character):
        return
    _met[character] = (episode, name)
    previous = _pending.get(character)

    async def run():
        if previous is not None:
            await previous  # checks of one character run in order, so the latest one counts
        await _check(agent, episode, character, name, lines)

    _pending[character] = asyncio.ensure_future(run())


async def summary(wait_seconds: float = 20.0) -> dict:
    """Wait for running checks, then: found/total per character and overall, plus the clue texts found."""
    pending = [t for t in _pending.values() if not t.done()]
    if pending:
        await asyncio.wait(pending, timeout=wait_seconds)
    per_character, found_texts, found, total = {}, [], 0, 0
    for character, (episode, name) in _met.items():
        clues = clues_for(episode, character)
        hits = sorted(_found.get(character, set()))
        per_character[name] = {"found": hits, "total": len(clues)}
        found_texts += [f"{name}: {clues[n]}" for n in hits]
        found += len(hits)
        total += len(clues)
    result = {"found": found, "total": total, "per_character": per_character, "found_texts": found_texts}
    if total:
        _log({"summary": True, "found": found, "total": total, "per_character": per_character})
        print("[CLUES] total: {}/{} clues discovered".format(found, total), flush=True)
    return result


def estimate(found: int, total: int) -> str:
    """Stoep Tegel's estimate of how close the children are, from the exact count."""
    if not total:
        return ""
    share = found / total
    if share >= 0.75:
        return "Jullie zijn al heel dichtbij de oplossing!"
    if share >= 0.4:
        return "Jullie zijn op de goede weg, maar er missen nog een paar stukjes van de puzzel."
    return "Er zijn nog veel stukjes van de puzzel te vinden, detectives."
