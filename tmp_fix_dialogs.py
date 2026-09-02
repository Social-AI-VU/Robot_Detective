import pathlib, json, copy


p = pathlib.Path(r'C:\Users\viq021\repositories\Robot_Detective\RobotDetective_Narrative_Jsons\Episode_1_all_dialogs.json')
dialogs = json.loads(p.read_text(encoding='utf-8'))

# ── Per-scene character annotations ──────────────────────────────────────────
# Each entry maps (scene_id, text_substring) -> character key.
# "narrator" = Robin/S.Tegel narrating action; actual speech uses the real key.

ANNOTATIONS = {
  "Ep1_Scene_1_Intro": [
    # S.Tegel narrates the whole intro monologue, then Robin takes over
    ("Goedemiddag luistervinkjes",         "s_tegel"),
    ("Wat is het te gek dat je luistert",  "s_tegel"),
    ("Waarin ik detective S. Tegel",       "s_tegel"),
    ("Ik ontmasker leugens",               "s_tegel"),
    ("En ik gebruik mijn uitmuntende",     "s_tegel"),
    ("Ik sta hier op de zevende",          "s_tegel"),
    ("en ik kijk uit op de grijze golven", "s_tegel"),
    ("Onder mijn plateauzolen",            "s_tegel"),
    ("Want dat deze flat",                 "s_tegel"),
    ("Er gebeuren hier vaak",              "s_tegel"),
    ("Ten eerste zwerven",                 "s_tegel"),
    ("Daarnaast wonen er twee jongens",    "s_tegel"),
    ("Dit pand kent een stortgat",         "s_tegel"),
    ("Er is een leen-auto",                "s_tegel"),
    ("In deze flat verschijnen",           "s_tegel"),
    ("Dus stel ik die vragen",             "s_tegel"),
    ("Ik traceer de sporen",               "s_tegel"),
    ("Oh hallo daar!",                     "robin"),
    ("Mijn naam is Robin",                 "robin"),
    ("Hoi %name%!",                        "robin"),
    ("Wat gezellig dat je er bij bent",    "robin"),
    ("Ohjee dat verstond ik niet",         "robin"),
    ("Kijk, ik kan het heel goed",         "robin"),
    ("Eehh jij daar helemaal links",       "robin"),
    ("Dat was een hartstikke",             "robin"),
    ("Ik vind het eigenlijk heel spannend","robin"),
    ("Vooral bij volwassenen",             "robin"),
    ("Bij kinderen gaat het nog wel",      "robin"),
    ("Maar volwassenen zijn zo groot",     "robin"),
    ("Ze kunnen mij zo optillen",          "robin"),
    ("Maar nu is de achtbaan van Toon",    "robin"),
    ("Zeg... Ik krijg ineens een idee",    "robin"),
    ("Joepie!!!!",                         "robin"),
    ("Dat is super lief van jullie",       "robin"),
    ("Laten we naar de flat gaan",         "robin"),
    ("Daar zullen we vast veel sporen",    "robin"),
    ("Oh, jullie mogen er over nadenken",  "robin"),
    ("Ik ga vast naar de flat toe",        "robin"),
  ],
  "Ep1_Scene_2_Toon_Rami": [
    ("Oh hey!",                             "robin"),
    ("Wat fijn dat jullie toch",            "robin"),
    ("Toon en Rami, dit zijn",              "robin"),
    ("Aha, dus dit zijn je nieuwe hulpjes", "toon"),
    ("Hoihoi!",                             "rami"),
    ("Beste junior detectives",             "robin"),
    ("Goed, wat jullie moeten weten",       "toon"),
    ("En ik had een mega grote achtbaan",   "toon"),
    ("Een geweldig ding!",                  "toon"),
    ("Deze prachtige achtbaan",             "toon"),
    ("Maar nu...",                          "toon"),
    ("Twee dagen geleden...",               "toon"),
    ("Is hij ineens verdwenen!",            "toon"),
    ("Mega gek toch!",                      "toon"),
    ("We gaan nu kiezen wie we als eerste", "robin"),
  ],
  "Ep1_Scene_3_Trudy": [
    ("Lalalalaaa!",                         "trudy"),
    ("Oh hallo daar!",                      "trudy"),
    ("Trudy is haar was",                   "narrator"),
    ("Al haar werkbloezen",                 "narrator"),
    ("Ze knipt in haar vingers",            "narrator"),
    ("Alle was past nu perfect",            "narrator"),
    ("Zo, dat was handig zeg!",             "trudy"),
    ("Zeker! Ik heb ooit Origami",          "trudy"),
    ("Maar he! wat hebben jullie",          "trudy"),
    ("Beste Trudy, mijn naam is Robin",     "robin"),
    ("Wij wilden u graag wat vragen",       "robin"),
    ("Wat bijzonder! Deze stofzuiger",      "trudy"),
    ("Ik wil best wat vragen beantwoorden", "trudy"),
    ("Ik heb vanavond een karaoke avond",   "trudy"),
    ("Dat betekent dat ik een liedje",      "trudy"),
    ("Wat een leuke muzieksmaak",           "trudy"),
    ("Maar ohja, jullie kwamen mij iets",   "trudy"),
    ("Stel je detectivevraag maar",         "trudy"),
  ],
  "Ep1_Scene_4_Eddy": [
    ("Mhmmm interessant.",                          "eddy"),
    ("En ik wist zeker dat dit stukje",             "eddy"),
    ("Oh hallo! Wie zijn jullie?",                  "eddy"),
    ("Beste Professor Eddy, mijn naam is Robin",    "robin"),
    ("Wij wilden u graag wat vragen stellen",       "robin"),
    ("Krijg nou! Een robot?",                       "eddy"),
    ("Ik wist niet dat er een robot",               "eddy"),
    ("Ik ben vorige week door Detective Stoep",     "robin"),
    ("Oude dingen opnieuw gebruiken",               "robin"),
    ("Ik ben gemaakt om mysteries op te lossen",    "robin"),
    ("Aha! Op die fiets!",                          "eddy"),
    ("Kijk eens in de groene bak",                  "eddy"),
    ("Ik wil de blokjes in de vorm",                "eddy"),
    ("Denken jullie dat jullie dit kunnen",         "eddy"),
    ("Oei, dat is best een uitdaging!",             "robin"),
    ("Maar ohja, jullie kwamen mij iets vragen",    "eddy"),
    ("Uitstekende vraag!",                          "eddy"),
    ("Oei die kon ik even niet verstaan",           "eddy"),
    ("Het was leuk jullie te ontmoeten!",           "eddy"),
  ],
  "Ep1_Scene_5_Yoyo": [
    ("Yoyo ik ben Yoyo.",                           "yoyo"),
    ("Wie zijn jullie?",                            "yoyo"),
    ("Beste meneer Yoyo, mijn naam is Robin.",      "robin"),
    ("Wij zijn detectives en we onderzoeken",       "robin"),
    ("Ik heb niks gezien!",                         "yoyo"),
    ("Oh? Dat is interessant meneer Yoyo.",         "robin"),
    ("We stellen toch graag een paar vragen",       "robin"),
    ("Ok wacht ik wil eerst",                       "yoyo"),
    ("Goed gedaan, detectives.",                    "robin"),
  ],
  "Ep1_Scene_6_Jennifer": [
    ("Nouja zeg",                                   "robin"),
    ("Meneer Yoyo verdenkt Jennifer",               "robin"),
    ("Maar ik vind het een beetje vreemd",          "robin"),
    ("Bijzonder...",                                "robin"),
    ("Ik heb inderdaad nog nooit",                  "robin"),
    ("Maar wie weet",                               "robin"),
    ("Soms kan iemand er een beetje vreemd",        "robin"),
    ("En toch heel aardig zijn!",                   "robin"),
    ("Aha",                                         "robin"),
    ("Misschien is Yoyo wel aan het overdrijven",   "robin"),
    ("Misschien heeft hij zelf wel iets",           "robin"),
    ("We komen er vanzelf achter!",                 "robin"),
    ("Maar goed, laten we Jennifer",                "robin"),
    ("Waar zou ze toch zijn",                       "robin"),
    ("Wacht eens even",                             "robin"),
    ("Ik hoor voetstappen!",                        "robin"),
    ("voetstappen.mp3 hier",                        "narrator"),
    ("Dat lange haar...",                           "robin"),
    ("En die lange tanden!!!",                      "robin"),
    ("Dat moet Jennifer wel zijn!!",                "robin"),
    ("Ohjee ze loopt weg",                          "robin"),
    ("Kom , we gaan snel achter haar aan",          "robin"),
    ("Een achtervolgindsscene later",               "narrator"),
    ("Oh hallo daar!",                              "jennifer"),
    ("Wat een schattige robot!",                    "jennifer"),
    ("Zeg, gaan jullie ook naar het feestje",       "jennifer"),
  ],
  "Ep1_Scene_7_Dj_Kata": [
    ("boem boem gaat de technomuziek",              "narrator"),
    ("Kijk dat is Dj Kata.",                        "robin"),
    ("Dat is onze laatste verdachte",               "robin"),
    ("Kata is een super coole DJ",                  "robin"),
    ("Laten we eens kijken wat de DJ",              "robin"),
  ],
  "Ep1_Scene_8_Ontknoping": [
    ("Ding dong bing bong",                         "narrator"),
    ("Hallo Stoep Tegel hier",                      "s_tegel"),
    ("Ik wilde even bellen",                        "s_tegel"),
    ("Dank jullie wel! Deze tip",                   "s_tegel"),
    ("Geen probleem, dan ronden we",                "s_tegel"),
    ("Wauw. Dat is een interessante theorie.",      "s_tegel"),
    ("Aha, dat is misschien nog een open vraag",    "s_tegel"),
    # Confrontation branches — narrator sets the scene, character speaks
    ("Trudy slaat een hoge noot",                   "narrator"),
    ("Ik was het echt niet!",                       "trudy"),
    ("Op dat moment voelen jullie een trilling",    "narrator"),
    ("Is dat... de achtbaan?",                      "robin"),
    ("Dan laten we Trudy nog even",                 "robin"),
    ("Eddy fronst en zegt",                         "narrator"),
    ("Ik was het alleen echt niet!",                "eddy"),
    ("Dan laten we Eddy verder",                    "robin"),
    ("Yoyo kijkt nerveus opzij",                    "narrator"),
    ("Jullie gaan toch niet de politie",            "yoyo"),
    ("Dan observeren we Yoyo",                      "robin"),
    ("Jennifer glimlacht en zegt",                  "narrator"),
    ("Jullie zijn goede speurneuzen",               "jennifer"),
    ("Dan wachten we met Jennifer",                 "robin"),
    ("DJ Kata zet de beat zachter",                 "narrator"),
    ("Luister detectives, als jullie een beetje",   "dj_kata"),
    ("Dan laten we DJ Kata nog even draaien",       "robin"),
    ("Ik kan nog geen duidelijke verdachte",        "robin"),
    ("Geen probleem: dan verzamelen we",            "robin"),
  ],
  "Ep1_Scene_9_Kelder_Disco": [
    ("Wacht eens even... DE KELDER!",              "robin"),
    ("Dat stortgat! Misschien is de achtbaan",     "robin"),
    ("Kom snel, detectives!",                      "robin"),
    ("We rennen zo snel",                          "narrator"),
    ("De trap af, de trap af",                     "narrator"),
    ("Steeds dieper in het duister",               "narrator"),
    ("Tot we eindelijk... bij de kelder",          "narrator"),
    ("En wat zien we daar?",                       "robin"),
    ("BOEM BOEM BOEM! De technobeat!",             "narrator"),
    ("De Kelder disco!",                           "narrator"),
    ("Dj Kata staat daar te draaien",              "narrator"),
    ("WAUW!",                                      "robin"),
    ("Daar staat-ie!",                             "robin"),
    ("De ACHTBAAN!",                               "robin"),
    ("Glimmend, mooi en helemaal intact!",         "narrator"),
    ("De achtbaan was nooit echt verdwenen",       "narrator"),
    ("Je moest eens weten hoe moeilijk",           "jennifer"),
    ("Gelukkig is Trudy heel goed in Origami",     "jennifer"),
    ("Wij zijn met de leenauto",                   "jennifer"),
    ("Trudy heeft de achtbaan opgevouwen",         "jennifer"),
    ("We een verdieping naar beneden",             "jennifer"),
    ("Yoyo had hem beneden in de kelder",          "jennifer"),
    ("De achtbaan was een paar dagen",             "jennifer"),
    ("Ik hou van herrie",                          "dj_kata"),
    ("Maar goed, het belangrijkste",               "robin"),
    ("Toen kwamen Toon en Rami binnen",            "narrator"),
    ("En dat is het einde van het mysterie",       "s_tegel"),
    ("Tot ziens, luistervinkjes",                  "s_tegel"),
    ("Dit was de Robot Detective",                 "s_tegel"),
  ],
}

def annotate_moves(moves, scene_id):
    annotation_map = ANNOTATIONS.get(scene_id, [])
    result = []
    for m in moves:
        m = copy.deepcopy(m)
        if m.get("type") == "say" and "character" not in m:
            text = m.get("text", "")
            for substr, char in annotation_map:
                if substr in text:
                    m["character"] = char
                    break
        if m.get("type") == "branch":
            new_cases = {}
            for case_key, case_moves in m.get("cases", {}).items():
                new_cases[case_key] = annotate_moves(case_moves, scene_id)
            m["cases"] = new_cases
        result.append(m)
    return result

all_characters = {
    "narrator":       {"voice_settings": {"voice_id": "REPLACE_WITH_NARRATOR_VOICE_ID",        "language": "nl"}},
    "detective_robot":{"voice_settings": {"voice_id": "REPLACE_WITH_DETECTIVE_ROBOT_VOICE_ID", "language": "nl"}},
    "dj_kata":        {"voice_settings": {"voice_id": "REPLACE_WITH_DJ_KATA_VOICE_ID",          "language": "nl"}},
    "eddy":           {"voice_settings": {"voice_id": "AVIlLDn2TVmdaDycgbo3",                   "language": "nl"}},
    "jennifer":       {"voice_settings": {"voice_id": "G6fmUXq3ziFf6Uae1jFh",                   "language": "nl"}},
    "robin":          {"voice_settings": {"voice_id": "f2yUVfK5jdm78zlpcZ8C",                   "language": "nl"}},
    "yoyo":           {"voice_settings": {"voice_id": "2wqbkywMMH2LWAlR4EMt",                   "language": "nl"}},
    "toon":           {"voice_settings": {"voice_id": "tvFp0BgJPrEXGoDhDIA4",                   "language": "nl"}},
    "rami":           {"voice_settings": {"voice_id": "7OMIHDA6SHxNlNDgPRdB",                   "language": "nl"}},
    "choukri":        {"voice_settings": {"voice_id": "G9lzzm05bGAXnuymdcqF",                   "language": "nl"}},
    "heike":          {"voice_settings": {"voice_id": "REPLACE_WITH_HEIKE_VOICE_ID",             "language": "nl"}},
    "hazel":          {"voice_settings": {"voice_id": "tfweP7lGJyLeNV9dH1Rm",                   "language": "nl"}},
    "s_tegel":        {"voice_settings": {"voice_id": "D50w2srwVohKTPx9X6Th",                   "language": "nl"}},
    "kata":           {"voice_settings": {"voice_id": "7qdUFMklKPaaAVMsBTBt",                   "language": "nl"}},
    "trudy":          {"voice_settings": {"voice_id": "OlBRrVAItyi00MuGMbna",                   "language": "nl"}},
}

def collect_characters_from_moves(moves):
    chars = set()
    for m in moves:
        if isinstance(m, dict):
            c = m.get("character")
            if c:
                chars.add(c)
            for case_moves in (m.get("cases") or {}).values():
                if isinstance(case_moves, list):
                    chars |= collect_characters_from_moves(case_moves)
    return chars

updated = []
for d in dialogs:
    d = copy.deepcopy(d)
    scene_id = d.get("id", "")
    # Annotate moves with character tags
    d["moves"] = annotate_moves(d.get("moves", []), scene_id)
    # Build characters block from what's actually used
    used = collect_characters_from_moves(d["moves"])
    # Never include "narrator" in voice characters block (no real voice needed)
    used.discard("narrator")
    chars_for_dialog = {k: v for k, v in all_characters.items() if k in used}
    rebuilt = {}
    for k, v in d.items():
        if k == "moves" and chars_for_dialog:
            rebuilt["characters"] = chars_for_dialog
        if k != "characters":
            rebuilt[k] = v
    updated.append(rebuilt)

p.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding='utf-8')
print(f"Done. {len(updated)} dialogs written.")
for d in updated:
    print(f"  {d['id']} | characters: {list(d.get('characters', {}).keys())} | moves: {len(d.get('moves', []))}")



