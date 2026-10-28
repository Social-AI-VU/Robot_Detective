# Sound effects for episodes 1–4

Every place a sound effect is played, generated from the episode JSONs (`"type": "play"` moves).

## How to add the sounds

1. Put the source files (MP3 is fine) in this `sounds` folder, under any name.
2. In `make_sounds.py`, the `SOUNDS` table says which source file (and which part of it) becomes which effect.
   Add or change a line there when you add or swap a sound.
3. Run `python sounds/make_sounds.py --force`. It trims and joins the pieces and writes `<name>.wav` for each effect,
   in the format the NAO plays (mono, 16-bit, 24 kHz). nardial can only play 16-bit WAV, so the MP3s themselves are
   never played. It needs ffmpeg, which is installed on this machine.
4. Start the episodes from the repository root, so that `sounds/…` is found. A missing file is logged and skipped;
   the scene continues.

## The 13 files you need

| Effect | Sound | Used in |
|---|---|---|
| `aankloppen.wav` | hard knocking on a glass front door | episode 3 |
| `bel_madeliefje.wav` | a cheerful little doorbell melody | episode 3 |
| `birdie_soundsystem.wav` | an awful beat made of cats wailing and car horns | episode 4 |
| `deurbel.wav` | a doorbell | episode 1 (Kata's intercom), 2, 3 |
| `gigagiebels.wav` | an uncontrollable giggling fit (snorting, hiccuping, giggling) | episode 2 |
| `hazel_laugh_2.wav` | Hazel's second laugh (from `Hazel laugh 2.mp3`) | episode 2 |
| `giebels_heike.wav` | Heike's Gigagiebels (from `Heike Gigagiebels.mp3`) | episode 2 |
| `giebels_shukri.wav` | Shukri's Gigagiebels; he says to go to Eddy (from `Choukri giebels.mp3`) | episode 2 |
| `hoesten.wav` | someone coughing (hidden in a bush) | episode 4 |
| `intercom_kraak.wav` | a broken intercom crackling | episode 3 |
| `klokbel.wav` | a clapper striking a bell | episode 3 |
| `kloppen_deur_kraakt.wav` | knocking, then a door creaking open | episode 2 |
| `knal_voetstappen.wav` | a bang from the lab, then footsteps | episode 2 |
| `pakketje_open.wav` | a package being torn open | episode 2 |
| `skateboard.wav` | a skateboard rolling closer | episode 2, 3 |
| `kloppen.wav` | knocking on a door | episode 1 |
| `deur_kraakt.wav` | a door creaking open | episode 1 |
| `voetstappen.wav` | footsteps | episode 1 |
| `intercom_ruis.wav` | Kata's intercom crackling on and off (from `dragon-studio-radio-static-323621.mp3`) | episode 1 |
| `techno_intercom.wav` | Kata's mix, thin, as if through the intercom (from `kata mix celebration.mp3`) | episode 1 |
| `techno_kelder.wav` | muffled party music from the basement | episode 1 |
| `radio_bleep.wav` | Robin's radio switching on/off | episode 1 |
| `trudy_zingt.wav` | Trudy singing the Habanera from Carmen | episode 1 |
| `leenauto_opstijgen.wav` | the borrowed car taking off | episode 1 |
| `trilling.wav` | the whole flat rumbling | episode 1 |
| `glijbaan.wav` | a slide whistle going down (from `universfield-whistle-slide-down-323778.mp3`) | episode 1 |
| `party_horn.wav` | a party horn | episode 1 |
| `kata_feest.wav` | Kata's celebration mix, for the dance | episode 1 |
| `telefoon.wav` | a phone ringing | episode 1 |

## Episode 1: Het mysterie van de verdwenen achtbaan (19 cues)

| # | Scene | File | Where |
|---|---|---|---|
| 0a | `Ep1_Scene_1_Intro` | `radio_bleep` | after "Luister maar mee..." (the radio switches on) |
| 0b | `Ep1_Scene_1_Intro` | `radio_bleep` | after "Zo, de radio gaat even uit." |
| 0c | `Ep1_Scene_3_Trudy` | `trudy_zingt` | at the start, before Trudy: "La la la! Wat een mooie dag vandaag!" |
| 1 | `Ep1_Scene_4_Eddy` | `kloppen` | instead of Robin saying "KLOP KLOP KLOP" |
| 2 | `Ep1_Scene_4_Eddy` | `deur_kraakt` | right before Robin: "Oh! De deur gaat open" |
| 3 | `Ep1_Scene_6_Jennifer` | `voetstappen` | after "Jennifer! Jenniferr!!!", before "Dat lange haar..." |
| 4 | `Ep1_Scene_6_Jennifer` | `voetstappen` | after "Ze gaat naar de garage toe! Kom snel!" |
| 5 | `Ep1_Scene_7_Dj_Kata` | `deurbel` | after "Kata woont in de kelder. We moeten bij haar aanbellen via een intercom." |
| 5b | `Ep1_Scene_7_Dj_Kata` | `intercom_ruis` | right after the doorbell, before Kata: "Hoi, wie is daar?" (the intercom switches on) |
| 6 | `Ep1_Scene_7_Dj_Kata` | `techno_intercom` | after Kata: "...een nieuwe plaat aan het draaien. Bizar lekker. Hoor je?" |
| 6b | `Ep1_Scene_6_Jennifer_Interview_Afsluiten` | `leenauto_opstijgen` | right before Robin: "Ik zie hoe de leenauto opstijgt..." |
| 6b | `Ep1_Scene_7_Dj_Kata_Interview_Afsluiten` | `intercom_ruis` | after Kata: "Doeiii!" (the intercom switches off) |
| 7 | `Ep1_Scene_7_Dj_Kata_Interview_Afsluiten` | `techno_kelder` | right before Robin: "Hoor je dat? Die technobeat klinkt nog steeds uit de kelder..." |
| 8 | `Ep1_Scene_8_Ontknoping` | `telefoon` | instead of the narrator saying "Tring tring! Tring tring!" |
| 8b | `Ep1_Scene_9_Trilling` | `trilling` | after the narrator: "Opeens... begint de hele flat te trillen!" |
| 8b2 | `Ep1_Scene_9_Trilling` | `glijbaan` | after Robin: "Drie... twee... één...", before "WHIEEEEEEE!" (down the slide) |
| 8c | `Ep1_Scene_10_Kelder_Disco` | `party_horn` | after "VERRASSING!" |
| 9 | `Ep1_Scene_10_Kelder_Disco` | `kata_feest` | after "Detectives, dansen jullie mee?" (instead of a silent pause) |
| 10 | `Ep1_Scene_11_Outro` | `telefoon` | instead of the narrator saying "Tring tring!" |

## Episode 2: Het mysterie van de Gigagiebels (12 cues)

| # | Scene | File | Right after | Right before |
|---|---|---|---|---|
| 1 | `Ep2_Scene_2_Mysterie` | `gigagiebels` | Stoep Tegel: “Hazel, wat is er gebeurd?” | Stoep Tegel: “Hazel?” |
| 2 | `Ep2_Scene_2_Mysterie` | `hazel_laugh_2` | Stoep Tegel: “Hazel?” | Stoep Tegel: “Je begrijpt dat ik nogal in de war ben. Mevrouw Hellastrong is net heel hard gevallen, maa…” |
| 4 | `Ep2_Scene_5_Heike` | `deurbel` | Robin: “Heike woont samen met haar moeder Jennifer. Laten we aanbellen bij hun deur en zien of ze …” | Jennifer: “Hallo daar Robin, wat leuk je te zien.” |
| 5 | `Ep2_Scene_5_Heike` | `skateboard` | Robin: “Kunnen jullie me helpen Heike te roepen? Op drie roepen we allemaal heel hard: Heike! Een,…” | Heike: “Wow, pas op! Dat ging net goed hoor. Ik was bijna tegen jullie opgebotst. Er staan niet va…” |
| 6 | `Ep2_Scene_5_Heike_Interview_Afsluiten` | `pakketje_open` | Heike: “Van wie zou het zijn? En wat zit erin? Een nieuw skateboard, of een bal, of een nieuwe bro…” | Heike: “Oh kijk nou, er zit een soort parfumfles in. Is dit dezelfde als Hazel heeft gekregen? Eve…” |
| 7 | `Ep2_Scene_5_Heike_Interview_Afsluiten` | `giebels_heike` | Heike: “Oh kijk nou, er zit een soort parfumfles in. Is dit dezelfde als Hazel heeft gekregen? Eve…” | Robin: “Oh nee, wat gebeurt er nu? Heike is ook getroffen door de Gigagiebels!” |
| 8 | `Ep2_Scene_6_Choukri` | `kloppen_deur_kraakt` | Robin: “Choukri heeft ook geen bel. Het is alsof hij liever geen bezoek krijgt. Gelukkig weet ik d…” | Choukri: “Wie is daar? Ik dacht al dat ik iets hoorde. Hallo, wat kan ik voor jullie doen? Jullie wi…” |
| 9 | `Ep2_Scene_6_Choukri_Interview_Afsluiten` | `pakketje_open` | Choukri: “Dit pakketje heeft geen afzender, vreemd hè. Er zitten niet eens postzegels op. Even spiek…” | Choukri: “Oh kijk nou, iemand heeft aan me gedacht. Ze weten dat ik ontzettend van een goed parfum h…” |
| 10 | `Ep2_Scene_6_Choukri_Interview_Afsluiten` | `giebels_shukri` | Choukri: “Oh kijk nou, iemand heeft aan me gedacht. Ze weten dat ik ontzettend van een goed parfum h…” | Robin: “Oh nee, dat is nu al de derde die getroffen wordt door de Gigagiebels. Dit gaat niet de go…” |
| 11 | `Ep2_Scene_7_Eddy` | `knal_voetstappen` | Robin: “Laten we Eddy roepen. Helpen jullie mee? Op drie: Eddy! Een, twee, drie!” | Eddy: “Oh. Oh. Oh. Goedemiddag daar. Stonden jullie hier al lang? Mijn excuses, mijn excuses. Ik …” |

## Episode 3: Het mysterie van de kapotte intercom (13 cues)

| # | Scene | File | Right after | Right before |
|---|---|---|---|---|
| 1 | `Ep3_Scene_2_Mysterie` | `intercom_kraak` | (scene start/end) | Stoep Tegel: “Hallo? Robin, detectives, horen jullie mij?” |
| 2 | `Ep3_Scene_2_Mysterie` | `intercom_kraak` | Stoep Tegel: “Ik weet niet wát er precies aan de hand is, maar de intercom maakt enorm rare geluiden! Lu…” | Stoep Tegel: “Het is zó erg dat ik me amper kan concentreren op mijn speurwerk. En wanneer er iemand aan…” |
| 3 | `Ep3_Scene_4_DJ_Kata` | `aankloppen` | Narrator: “We kloppen hard op de deur. DJ Kata doet haar koptelefoon af en kijkt om. Eerst kijkt ze v…” | Kata: “Yo boss! Mini-baasjes! Ik had jullie bijna niet gehoord.” |
| 4 | `Ep3_Scene_4_DJ_Kata_Interview_Afsluiten` | `intercom_kraak` | Stoep Tegel: “Robin! Detectives! Ik ben iets op het spoor gekomen. Spits jullie oren, want dit is een er…” | Trudy: “Och gossie, wat een... Moet DJ Kata nou altijd die mixes van haar over de intercom laten h…” |
| 5 | `Ep3_Scene_4_DJ_Kata_Interview_Afsluiten` | `intercom_kraak` | Trudy: “Och gossie, wat een... Moet DJ Kata nou altijd die mixes van haar over de intercom laten h…” | Stoep Tegel: “Hmmm... dat klinkt verdacht! Misschien kunnen jullie eens kijken wat Trudy weet over de ka…” |
| 6 | `Ep3_Scene_5_Trudy` | `bel_madeliefje` | Narrator: “De voordeur van Trudy is paars geschilderd. Haar bel heeft de vorm van een madeliefje. Als…” | Trudy: “Oh hallo! Ik ben Trudy. Sinds een aantal jaar ben ik met pensioen, en dat vind ik geweldig…” |
| 7 | `Ep3_Scene_5_Trudy_Interview_Afsluiten` | `intercom_kraak` | Stoep Tegel: “Ik ben iets nieuws op het spoor gekomen. Luister maar eens goed naar dit!” | Heike: “Hahaha, mijn pa schrikt zich de hele tijd rot, echt grappig... we zouden vaker de intercom…” |
| 8 | `Ep3_Scene_5_Trudy_Interview_Afsluiten` | `intercom_kraak` | Heike: “Hahaha, mijn pa schrikt zich de hele tijd rot, echt grappig... we zouden vaker de intercom…” | Stoep Tegel: “Ik moet zeggen dat dat wel heel erg klinkt als een schuldbekentenis. Kunnen jullie dat voo…” |
| 9 | `Ep3_Scene_6_Heike` | `deurbel` | Narrator: “De deur van Heike, Jennifer en Leen zit vol kleuren: geel, paars, blauw, groen, rood, oran…” | Leen: “Hallo daar Robin, wat leuk je te zien.” |
| 10 | `Ep3_Scene_6_Heike` | `skateboard` | Robin: “Aha, bedankt meneer Leen. Detectives, helpen jullie mee roepen? Op drie: Heike! Een, twee,…” | Heike: “Wow, pas op! Dat ging net goed hoor. Ik was bijna tegen jullie opgebotst.” |
| 11 | `Ep3_Scene_6_Heike_Interview_Afsluiten` | `intercom_kraak` | Stoep Tegel: “Detectives! Ik ben toch weer iets vreemds op het spoor gekomen. Een nieuwe hint in dit ing…” | Choukri: “Technologie tegenwoordig... Ik sloop het nog eens een keer... Onding!” |
| 12 | `Ep3_Scene_6_Heike_Interview_Afsluiten` | `intercom_kraak` | Choukri: “Technologie tegenwoordig... Ik sloop het nog eens een keer... Onding!” | Stoep Tegel: “Jullie kunnen je voorstellen dat ik super druk ben met alle informatie die maar op me af b…” |
| 13 | `Ep3_Scene_7_Choukri` | `klokbel` | Robin: “AUW! Nou ja, ik voel eigenlijk niets, ik heb geen zenuwen in dit plastic. Maar gaat het me…” | Choukri: “Hallo?” |

## Episode 4: De verdwenen detective en de parkietenplaag (2 cues)

| # | Scene | File | Right after | Right before |
|---|---|---|---|---|
| 1 | `Ep4_Scene_8_DJ_Kata_Interview_Afsluiten` | `birdie_soundsystem` | Kata: “Oké, done. Dit is dé oplossing voor de parkietenplaag, I swear! De birdie soundsystem extr…” | Robin: “Een afschuwelijke beat klinkt, gemaakt van kattengejammer en autotoeters. Maar de parkiete…” |
| 2 | `Ep4_Scene_11_Onthulling` | `hoesten` | Yoyo: “Oké luisterparkieten, uh, ik bedoel vinkjes, we lopen nu richting de ritselende struik in …” | Yoyo: “Ik zie armen en benen, en een groen gezicht. Is dat het nou echt... Het is Stoep Tegel!” |
