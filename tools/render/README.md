# Offline renderer (test environment)

Runs a preset's real ReShade chain on a captured game frame, so changes can be checked before they touch the game.

- `fxdump` — ReShade 4.5.4's own compiler (vendored in `tools/reshadefx`) emitting the GLSL + metadata the OpenGL runtime uses.
- `fxcheck` — compile check, HLSL + GLSL.
- `render.py` — mini ReShade OpenGL runtime (headless Mesa GL 4.5): same pass order, back-buffer copy per pass, shared textures,
  sRGB views, mipmaps, blend states, uniforms from the preset, timer/frametime/framecount sources. Runs 120 frames (2 s) so adaptation settles.

Setup (container): `pip install --break-system-packages moderngl PyOpenGL` and `make -C tools/render`.

    python3 tools/render/render.py game/reshade-shaders/Custom/AI_19_TiberiumMidnight.ini plates/<raw>.png out.png

Input must be a raw frame (ReShade off, Ctrl+Q). Stock textures (Dirt, Lens...) are read from the staged PC folder.
Not validated yet against in-game captures: see plates/ once captured.
