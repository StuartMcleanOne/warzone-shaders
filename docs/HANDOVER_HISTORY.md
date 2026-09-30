# Warzone Shader Project: Handover

Written 2026-09-30 for a fresh session. Owner: Shell (Stuart), Berlin, designer/developer. He likes concept approval before big builds, the "why" explained, and direct practical replies.

## The project
Custom ReShade 4 presets and documentation for the Tiberian War: WarZone mod (5.7.7). Game folder on his PC: `C:\Users\Lenovo\Documents\TW_Warzone_Fin`. The engine renders through DirectDraw via ts-ddraw OpenGL at 800x600, with no usable depth buffer, so depth effects do nothing. The plan is to release a community pack later, in a NEW thread once everything is polished. He will not infringe the original authors and wants them credited.

## What exists (all done unless stated)
- 18 presets (`AI_*` and `C_*`) in `...\reshade-shaders` Custom folder, 7 LUT PNGs in Textures. Authoritative copies in the old container at `/mnt/user-data/outputs/final/Custom` and `/final/Textures` (may be gone; the device copies are the truth).
- Backups on his PC: `Tiberian_Shaders_OV\` (Custom, Textures, `Shaders_original.zip` of 101 untouched .fx). An older folder `Tiberian_Shaders_ OV` (typo with a trailing space) still exists; he should delete it.
- All 101 shaders relabelled (display names only) with stage prefixes and tooltips, committed to `...\reshade-shaders\Shaders\`. Technique internal names are unchanged, so presets still load. NOT yet confirmed in game by Shell. Rollback: `Shaders_original.zip`.
- Prefix scheme: 0_ UI wrappers, 1_ Clean-up, 2_ Colour, 3_ Light, 4_ Detail, 5_ Finish, 6_ Novelty, X_ needs depth (dead).
- Cheat sheet Doc: https://claude.ai/artifact/6hRUjEfmgCfjB7MFmaGeR3
- Landscape poster artifact: https://claude.ai/artifact/3cE8wpqs9eQTpru3pGvdL7 (+ PNG/PDF)
- Portrait A3 posters (Basic and Full), PDF/PNG, delivered. Shell said "both awesome".
- Multi-page guide, first pass: https://claude.ai/artifact/L1RvM6bXeuBJgtwJjCGd9R and `Warzone_Shader_Guide.pdf` (A4, 17 pages). Shell's verdict: "not a bad first pass" but needs polish.

## Open work, in priority order
1. **Redo/polish the guide (Shell's request for the new session).** His feedback: formatting errors, font use and contrast ratios not adequate. He gave no more detail. Ask him to point at specific pages if he can, otherwise audit it yourself. My own suspicions (not verified at full resolution; I only viewed thumbnails):
   - Body text is very small on A4 (about 9-11px equivalent) and the muted grey `#8ea699` on dark panels is low contrast. Mono footers and label text (`.kick`, `.pf`) are tiny.
   - Type sizes differ page to page, because I fitted each page with a per-page CSS `zoom` (1.02 to 1.4). It is a hack. Better: fixed type scale, and split or reflow content to fill pages.
   - Several pages are half empty (Detail, Finish, Skip list, presets, Glossary) while others are dense.
   - Skip list "Depth of field / Distance effects" rows, chips and prefix rows may wrap awkwardly. Cover and "The order" page layouts were only lightly checked.
   - Artifact version uses Google Fonts (Chakra Petch, IBM Plex Sans/Mono); the PDF used embedded fontsource woff2. Confirm both look the same.
   - Suggested approach: pick a proper scale (body at least 11pt equivalent in print, muted text at least 4.5:1, ideally 7:1 on the dark panels), consider a light print variant, render each page at full resolution and actually look at every one.
2. **Fix wrong Ambient Light advice** in three places. Correct wording: keep `AL_Lens` off; `AL_Dirt` produces the glow, so leave it on; keep `AL_DirtTex` off. Still wrong in: (a) in-game tooltip, in `labels.py` (then regenerate with apply.py and recommit `AmbientLight.fx`); (b) posters (landscape artifact and PDFs, both portrait PDFs); (c) the Docs cheat sheet "Light" table, which says "Turn the lens and dirt options off." The guide itself is already correct.
3. **TriDither stage**: labelled 1_ but is a colour effect. Change to stage '2' in labels.py, regenerate, recommit `TriDither.fx`.
4. Ask Shell to confirm the prefixed labels and tooltips show in game.
5. **Credits decision**: the credits list crosire (ReShade), prod80 (PD80), Marty McFly / Pascal Gilcher (qUINT, MXAO), CeeJay.dk (SweetFX), and the WarZone team. The line about presets, LUTs and guide being shared has no author attribution. Ask how Shell wants to be credited.
6. Later, new thread: community pack (presets, textures, docs, credits, optional label patch script). Do not bundle modified shader files. Ship a patch script or instructions instead.

## How things were built (files uploaded alongside this doc, suffix .txt added to non-.py files)
- `labels.py.txt`: dict `D[technique]=(stage,label,tooltip)` for 115 techniques. Edit here for tooltip and stage changes.
- `parse.py.txt`: finds `technique NAME < annotations >` in .fx source, string-aware.
- `apply.py.txt`: rewrites only the annotation block to `ui_label`/`ui_tooltip` (keeps the original notes appended). Reads pristine `.fx` from `shaders_orig/`, writes to `shaders_new/`. Verify with a whitespace-normalised diff (0 code changes expected).
- Guide: `guide_content.py` (all text and real preset value ranges), `guide_gen.py` (builds page sections; expects /tmp/w for labels and the final Custom presets to look up chains), `guide.css.txt`, `guide_asm.py` (assembles index.html for the artifact and local.html with embedded fonts, injects per-page zoom from zooms), `guide_fit.js.txt` (binary-searches per-page zoom), `guide_zooms.json.txt`.
- Rendering: Playwright (`playwright-core` from npm) with chromium at `/opt/pw-browsers/chromium`, print media, `preferCSSPageSize`. Use pypdf for page count, `pdftoppm` for PNGs. Check every `.page` for `scrollHeight <= clientHeight`. Gotcha: my responsive rule `@media (max-width:820px)` also fired in print (A4 is 794px wide), which broke layout until I changed it to `@media screen and (max-width:820px)`.

## Device workflow gotchas
- Reach his PC only via the remote-devices tools: `device_stage_files` (PC to container uploads), `device_commit_files` (container `/mnt/user-data/outputs/...` to PC). No shell, no delete on the device. Commit lists must include full file lists.
- If the device tools are missing, the session is not linked to his computer; he opens the chat in the desktop app and picks "Link to this computer".
- ReShade cannot be run in the container, so anything shader-related must be confirmed by Shell in game.
- Preset .ini rules: `Techniques=` is the active chain in order; `TechniqueSorting=` is the full menu order; unknown or misspelled keys are silently ignored. Always wrap chains in `UI_Before ... UI_After` with `Isolate_UI=1` to protect the 168px right sidebar (22px top offset).

## Preset list
AI_01_Remaster, AI_03_TiberiumBloom, AI_05_CrimsonSun, AI_08_GoldenHour, AI_11_IonStorm, AI_12_TiberiumNight, AI_13_ScorchedEarth, AI_14_ChromeAndRain, AI_15_Kodachrome99, AI_16_Firestorm, AI_18_GDITacticalFeed. C_C&CWarzone, C_C&CWarzoneBladeRunner, ...Fog, ...Heat, ...OG, ...Retro, ...Weather. Tiberium Night: Shell once altered his copy by accident; the logged version is the good one.

## Update: guide v2 (same day)
Shell asked for another pass in the same session, so v2 is published at the same URL (version 2) and the PDF was re-sent. Changes: removed the per-page zoom hack; one fixed type scale (body 13-14.5px, labels at least 11px); muted text lifted from `#8ea699` to `#b3c8bb`/`#c4d6cb` for stronger contrast; entries are now full-width rows (name and technique id left, Does/Try/Watch right) with no stretched empty cards; pages are auto-paginated by measured height (`measure.js`, run from gen.py) and balanced; short pages gained small recipe cards (Clean-up, Detail, Finish, "Picking a look"). Still open: Shell has not yet reviewed v2, so his comments on it come first. Preset file names really are `C_C&CWarzone*` (the `&` is real). The uploaded src files in `handover/src/` are the v1 versions, so ask for or regenerate v2 files if needed (v2 gen.py/guide.css/measure.js live in the old session scratchpad only).

## Update 2: Tiberian Night / Midnight session (2026-09-30, midday)

### Decisions made with Shell
- **Tiberian Night (`AI_12`) is ALWAYS my original file and original LUT.** Restored to `Custom` and `Textures` (and the `Tiberian_Shaders_OV` backup). Never modify it again without being asked. Its LUT is 33153 bytes; the original was recovered from the old typo backup folder `Tiberian_Shaders_ OV\Textures`.
- **Tiberian Midnight (`AI_19_TiberiumMidnight`) is a separate preset built around Shell's discoveries.** Shell's instruction, repeated three times: use the extra shaders he had switched on in his own messy Night (the ones between UI_Before and Deband, plus High Pass Sharpen) and "make it your own". Do NOT copy his file literally, and do NOT make it black with glowing tiberium. My first Midnight was far too dark (white lights went grey); the second literal copy of his file was rejected too.
- Shell's messy edit of Night is saved at `Tiberian_Shaders_OV\trash_review\AI_12_TiberiumNight_ShellEdit_0930.ini` (his values for LevelsPlus, Curves 0.65, FakeHDR 1.3, Technicolor 0.4, Vibrance 0.15, AmbientLight, FXAA, SMAA, HighPass etc.). Also in trash_review: my rejected too-dark Midnight and its LUT. `trash_review` is his convention for files he will delete. I cannot delete on his PC, so leftovers must be listed for him.
- Shell wants: white lights (headlights, refinery lamps) bright, explosions and weapon fire hot and visceral, tiberium alive.

### What Midnight is now (v3, awaiting his in-game feedback)
- Chain: UI_Before, Deband, FXAA, LevelsPlus, LUT, Curves, Vibrance, HDR (FakeHDR), ReflectiveBumpmapping, AmbientLight, MagicBloom, prod80_02_Bloom (warm 5200K), LumaSharpen, Vignette, FilmGrain, UI_After.
- Left out on purpose (would clash): Bloom+LensFlares (third bloom), SMAA (second AA), Levels (duplicates LevelsPlus), FineSharp and HighPass (second sharpener), Technicolor (three tone curves).
- New LUT `AI_19_TiberiumMidnight_lut.png` derived from the original Night LUT: about 16% darker in shadows and mids, colder, tiberium greens and blues kept at their Night values, near-white protected (white maps to about 0.93, headlight about 0.89), bright warm colours protected (orange fire about 0.83, 0.53, 0.14 instead of Night's dull 0.54, 0.41, 0.25). Verified numerically only; NOT seen in game.
- LevelsPlus insight: his black point (0.063, 0.071, 0.078) crushes blue hardest, so it deepens and warms shadows. His low blue white point (0.83) boosts blue highlights, which pales explosions. Midnight uses a near-neutral white point 0.93, 0.92, 0.90.
- Build tooling: `build2.py` (helpers: parse_defaults, emit, make_lut, hue_mask etc.; its head is exec'd by later scripts), `build7_midnight.py`. They expect the shader sources and preset templates under `/mnt/user-data/uploads/reshade-shaders/` (stage them from the PC first) and write to `/mnt/user-data/outputs/batchN/`.

### Shader load error found and fixed
- ReShade log (`OPENGL32.log`, ReShade 4.5.4) showed exactly one real failure, six times: `CinematicDOF.fx` line 1124, "syntax error: unexpected '<'". Cause: my label patch added an annotation list but the original had a second `< ui_tooltip ... >` list inside an `#if __RESHADE__ >= 40000` block. Fixed in `apply.py` (special-case), scanned all 101 files for the same pattern (none), and recommitted `CinematicDOF.fx`. Everything else in the log is normal "loaded with warnings" output. Always check `OPENGL32.log` in the game folder after committing shaders.
- Also fixed and recommitted: `AmbientLight.fx` tooltip (now says keep AL_Lens off, AL_Dirt is the glow, keep AL_DirtTex off) and `TriDither.fx` (now stage 2_).
- STILL WRONG with the old Ambient Light wording: the landscape poster artifact and PDFs, both portrait poster PDFs, and the Docs cheat sheet (Light table). Guide already correct.

### Discovery: engine time-of-day and ion storm files
- `TW_Warzone_Fin\INI\` contains `morning.ini`, `day.ini`, `dusk.ini`, `night.ini` (map trigger scripts: nightfall and daybreak transitions over 1800 frames, ambient actions) and `ion.ini` (ion storm lighting Red 1.62, Green 1.25, Blue 0.34, Ambient 0.5; lightning frequency 10, randomness 90, damage 200). So in-game lighting and storm colour can be changed in game files, not with ReShade. Not yet checked whether the mod's maps use them. Editing rules such as lightning damage could desync multiplayer. Read before touching. Future mod idea.

### Shell's creative direction (for the time-of-day family and the community pack)
- Make a preset per time of day (early morning, mid-morning, midday, afternoon, golden hour or evening, twilight, night, midnight). One shared chain, varying LUT, bloom warmth and a few values.
- Tiberium should feel alive, visceral and alien, and behave differently at each phase (midday: heat shimmer and sickly yellow-green; golden hour: amber; twilight: teal glow; night and midnight: crystals as light source). Explosions and weapon fire must stay hot and true to their palette. Full palette fidelity needs a real mod (game art and palettes), which is a later separate project.
- Principle that makes it work: darken the world, keep bright saturated pixels bright (bloom threshold picks them). Protect warm hues and near-white in LUTs. Colour effects cannot tell tiberium from anything else except by hue.

### Corrections and small facts
- The real preset file names are `C_C&CWarzone*.ini` (with an ampersand).
- Guide v2 published (17 pages, A4). Posters delivered. Files also in the project.
- Old typo folder `Tiberian_Shaders_ OV` still exists on his PC; he will delete it.
- Custom folder also holds `AI_17_NodPropaganda.ini`, `C_1.ini` and an `Old` folder, not part of this session's work.

### Next steps
1. Shell tests Midnight (v3) in game. Likely tweaks: brightness, headlight glare, explosion warmth, how strongly the extras show.
2. Check `OPENGL32.log` after his next run for any new shader errors.
3. Fix the Ambient Light wording in the posters and the Docs cheat sheet.
4. Time-of-day preset family.
5. Guide: add Midnight and the time-of-day family, and the lesson about protecting fire and white lights in LUTs.
6. Credits decision (how Shell wants to be credited) and, much later, the community pack in a new thread.

## Update 3: Midnight v4 (2026-09-30, afternoon)
Shell tested v3: explosions and fire "much better", building lights good, world "dark enough, too much even". Missing lights (all small, likely 1 to 3 pixels): the small white light on the front of Nod bikes, the two buggy headlights, the scout infantry helmet light, possibly a refinery light that comes on with them. He couldn't screenshot (game minimises). Colour of those lights is unknown.
v4 changes (build8_midnight_v4.py.txt, output batch8): lamp mask widened in the LUT (bright pale colours, including warm white and bluish white, are near-identity, white about 0.98, warm white 0.95, dim lamp 0.6); FXAA softened so it stops smearing tiny lights (Subpix 0, EdgeThreshold 0.25, EdgeThresholdMin 0.0625); world lighter (shadow and mid darkening 7% instead of 16%; LevelsPlus black point 0.04, 0.045, 0.05; Curves 0.35; Vignette -0.7). v3 archived in trash_review (ini and LUT). Untested in game.
If lights are still missing: ask what colour they look like when working (white, yellow, blue, cyan). Pale cyan is still only about 0.65 because the tiberium-blue mask protects it. Other suspects for tiny lights: LumaSharpen, Deband, Reflective Bump Mapping, the second bloom. They may also be flashing sprites, or drawn in a palette range that the engine dims itself.
