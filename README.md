# Warzone shaders

ReShade 4.5.4 presets and shaders for **Tiberian War: WarZone 5.7.7** (Tiberian Sun mod), 800x600, OpenGL (ts-ddraw).

- `game/` mirrors the game folder `C:\Users\Lenovo\Documents\TW_Warzone_Fin`. **The PC is the live copy; this repo is the history.**
  - `reshade-shaders/Custom` – presets (AI_*, C_*), `Custom/Sandbox` – experiments and v2 versions, never the originals
  - `reshade-shaders/Shaders` – all shaders; ours are `CnC*.fx`
  - `reshade-shaders/Textures` – our LUTs only (the stock textures live on the PC)
  - `INI-reference/` – the game's own lighting/weather option files (read-only reference)
- `tools/` – build scripts, `fxcheck` (ReShade 4.5.4's own compiler, compile check), renderer
- `docs/` – handovers, notes, changelog
- `plates/` – reference frames captured from the game

## Workflow
1. Stage the file from the PC, commit it (so the live state is recorded).
2. Change it here, test (fxcheck + renderer), commit.
3. Deploy to the PC. Every deploy is a commit, so anything can be rolled back.

Rules: Tiberian Night keeps its original LUT and grade. New work goes to `Custom/Sandbox` until Shell approves it.
