# Sandbox, new shaders and game weather notes (30 Sep 2026, late)

## New shaders (on the PC in reshade-shaders\Shaders, sources in handover/src/*.fx.txt)
- **CnCTiberiumLife.fx** "4_ Living Tiberium" v2. Crystals found by hue (green ~130 deg, blue ~227 deg) + saturation + local sparkle. Breathing = slow value-noise-phased sine on the crystals themselves; fairy lights = one possible light per 8x8 px cell, own period 3-10 s, cubed-sine fade, random peak; palettes Crystal / Refraction / Warm / Cold. Ground glow kept tiny. v1 was "disco ball" (all glints at once, glow hid the artwork): Shell ran Glow 0.014, Richness 0.1, Glint 0.07, Pulse 1.0, PulseSpeed 0.064. Tiberian Midnight now has it after LightGuard_After with calm v2 values. Loaded without error in game (v1, log 21:38).
- **CnCWeather.fx** "5_ Weather": camera tracker (200x150 luma, 25x25 SAD search, accumulates scroll into a 1x1 RG32F) so clouds/mist stay on the ground; fbm cloud shadows + sun patches; mist; rain / heavy storm / snow / blizzard / tiberium rain / sandstorm; lightning flashes. Self-lit protection = very bright OR clearly brighter than its 4x4 surroundings (bright sand is not protected). Not yet seen in game.
- **CnCBlast.fx** "6_ Blast light and heat": half-res frame diff; a pixel that is hot (white or r>=g>=b) and jumped above last frame's 5x5 max triggers energy that decays over Fade seconds; wide blur lights surrounding ground (multiply + small add), flickering light from sustained fire, heat shimmer, optional screen kick. Not yet seen in game.
- All three pass fxcheck (HLSL + GLSL). ReShade 4.5 FX: no fmod, tex2Dfetch needs int4.

## Sandbox presets: reshade-shaders\Custom\Sandbox\S1..S8 (+README_Sandbox.txt)
Chain: UI_Before, LightGuard_Before, LiftGammaGain, Curves, Vibrance, LightGuard_After, CnCBlast, TiberiumLife, CnCWeather, UI_After. Light grades only: the engine lighting option does the time of day. Generator: handover/src/gen_sandbox.py.txt.
S1 Dawn, S2 Midday, S3 GoldenDusk, S4 NightWatch, S5 Thunderstorm, S6 TiberiumStorm, S7 Winter, S8 Sandstorm. Pairing with launcher options is in the README. Unverified: whether ReShade 4.5's preset list lets Shell browse into the Sandbox subfolder (if not, move them into Custom with an S_ prefix).

## Game-side weather and lighting (read from INI\Game Options)
- The launcher's Lighting option overwrites the map's [Lighting]: Dawn amb 0.35 (R1.2 G1.1 B1.08), Mid day 0.81 neutral, Dusk 0.45 (R1.3 G1.3 B0.9), Night 0.25 (R0.9 G0.9 B1.3), Artic Day/Night/Storm, plus "Day and Night" = trigger loop that ramps ambient.
- Weather options are hacks: hundreds of invisible neutral structures with animations (RINDR/RINDR2 rain x178, LBOLTSTB thunderbolts, WHSNOSTR2 snow, DSTS sand, TBRINDR tiberium rain which also emits green light) plus their own [Lighting]. TibRainStorm also turns on ion storms.
- Tiberium crystal structures (TIBCRIS1-3, TIBCRISBL1 blue) are real light sources: LightIntensity=0.001 (almost nothing), green 0.8. Raising it would make fields light the terrain in-engine (real, world-locked). Big lever for "alive tiberium" without shaders, but it is a rules.ini change: may break online sync / client file checks. Skirmish only, ask Shell first.
- ion.ini: ion storm lighting R1.62 G1.25 B0.34 amb 0.5; lightning damage 200.

## Next
Shell tries the Sandbox presets with the paired launcher options; pull OPENGL32.log for compile errors; screenshot bursts (windowed works, ~2 s bursts) for tuning.
