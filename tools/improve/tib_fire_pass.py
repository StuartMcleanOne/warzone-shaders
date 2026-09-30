#!/usr/bin/env python3
"""Mature tiberium + fire pop, baked into Shell's own AI_ preset LUTs.

For each preset the existing LUT (or an identity LUT for presets without one) is
re-graded entry by entry:
  - tiberium green / blue (detected on the LUT *input* colour) is pulled to a
    per-preset "time of day" hue and its saturation capped relative to the input,
    so crystals stay tiberium but lose the lime / neon-blue fruit-loop look;
  - fire and explosion colours (hot orange-yellow) are pushed hotter and richer;
  - near-white lamps get a small lift.
Everything else in the LUT is left exactly as it was.

    python3 tib_fire_pass.py SRC_TEXTURES_DIR OUT_TEXTURES_DIR
"""
import os
import sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "campaign"))
from build_campaign import rgb2hsv, hsv2rgb, ss, hue_window  # noqa: E402

# g_dark/g_bright: target hue (deg) for dark / bright parts of green crystals
# g_cap: max saturation, g_rel: max saturation relative to the input colour
# b_hue / b_cap / b_rel: same for blue tiberium (kept gentle: civilian blues)
# g_val: brightness multiplier on crystals, fire: fire-pop amount
MOODS = {
    # day, neutral: natural emerald body, yellow-green tips
    "AI_01_Remaster":       dict(tib=0.85, g_dark=150, g_bright=98,  g_cap=0.60, g_rel=0.88, b_hue=212, b_cap=0.50, b_rel=0.85, g_val=1.00, fire=0.75),
    # the tiberium showcase: richest of the set, still not neon
    "AI_03_TiberiumBloom":  dict(tib=0.75, g_dark=145, g_bright=100, g_cap=0.68, g_rel=0.95, b_hue=215, b_cap=0.56, b_rel=0.90, g_val=1.00, fire=0.75),
    # hot red sun: baked olive-amber crystals
    "AI_05_CrimsonSun":     dict(tib=0.85, g_dark=112, g_bright=80,  g_cap=0.52, g_rel=0.85, b_hue=205, b_cap=0.45, b_rel=0.80, g_val=0.98, fire=0.80),
    # late sun: warm yellow-green
    "AI_08_GoldenHour":     dict(tib=0.85, g_dark=125, g_bright=86,  g_cap=0.56, g_rel=0.86, b_hue=208, b_cap=0.48, b_rel=0.82, g_val=1.00, fire=0.80),
    # ion storm: cold, muted, steel-teal
    "AI_11_IonStorm":       dict(tib=0.90, g_dark=160, g_bright=122, g_cap=0.46, g_rel=0.80, b_hue=214, b_cap=0.44, b_rel=0.80, g_val=0.97, fire=0.80),
    # heat wave: dusty olive and amber-green
    "AI_13_ScorchedEarth":  dict(tib=0.90, g_dark=106, g_bright=78,  g_cap=0.50, g_rel=0.84, b_hue=205, b_cap=0.42, b_rel=0.78, g_val=0.97, fire=0.85),
    # wet night-ish chrome: emerald-teal
    "AI_14_ChromeAndRain":  dict(tib=0.85, g_dark=162, g_bright=128, g_cap=0.58, g_rel=0.88, b_hue=210, b_cap=0.50, b_rel=0.85, g_val=0.99, fire=0.80),
    # film stock: natural and rich
    "AI_15_Kodachrome99":   dict(tib=0.80, g_dark=140, g_bright=95,  g_cap=0.62, g_rel=0.90, b_hue=212, b_cap=0.52, b_rel=0.86, g_val=1.00, fire=0.80),
    # burning world: dry olive-gold crystals so the fire owns the frame
    "AI_16_Firestorm":      dict(tib=0.85, g_dark=115, g_bright=82,  g_cap=0.54, g_rel=0.85, b_hue=205, b_cap=0.45, b_rel=0.80, g_val=0.98, fire=0.85),
    # stylised looks: lighter touch
    "AI_17_NodPropaganda":  dict(tib=0.55, g_dark=140, g_bright=95,  g_cap=0.62, g_rel=0.90, b_hue=212, b_cap=0.52, b_rel=0.86, g_val=1.00, fire=0.75),
    "AI_18_GDITacticalFeed": dict(tib=0.55, g_dark=145, g_bright=110, g_cap=0.58, g_rel=0.90, b_hue=212, b_cap=0.50, b_rel=0.86, g_val=1.00, fire=0.70),
    # night: deep emerald, darker bodies, cool pale tips (not lime)
    "AI_19_TiberiumMidnight": dict(tib=0.90, g_dark=158, g_bright=126, g_cap=0.56, g_rel=0.88, b_hue=218, b_cap=0.50, b_rel=0.85, g_val=0.94, fire=0.80),
}
NO_LUT = ["AI_01_Remaster", "AI_03_TiberiumBloom", "AI_05_CrimsonSun", "AI_08_GoldenHour"]


def grid():
    i = np.arange(32) / 31.0
    b, g, r = np.meshgrid(i, i, i, indexing="ij")  # [b, g, r]
    return np.stack([r, g, b], -1)


def lut_to_cube(img):
    a = np.asarray(img.convert("RGB")).astype(np.float64) / 255.0  # 32 x 1024
    return np.stack([a[:, bi * 32:(bi + 1) * 32] for bi in range(32)], 0)  # [b, g, r, 3]


def cube_to_lut(cube):
    img = np.zeros((32, 1024, 3))
    for bi in range(32):
        img[:, bi * 32:(bi + 1) * 32] = cube[bi]
    return Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8))


def hue_toward(h, target, amt):
    return (h + (((target - h + 0.5) % 1.0) - 0.5) * amt) % 1.0


def apply(cube, m):
    c = grid()
    hc = rgb2hsv(c)
    h0, s0, v0 = hc[..., 0], hc[..., 1], hc[..., 2]
    ho = rgb2hsv(cube)
    h, s, v = ho[..., 0], ho[..., 1], ho[..., 2]

    # --- tiberium masks on the input colour
    green = hue_window(h0, 118 / 360, 38 / 360, 15 / 360) * ss(0.14, 0.38, s0) * ss(0.12, 0.30, v0)
    blue = hue_window(h0, 232 / 360, 30 / 360, 12 / 360) * ss(0.30, 0.55, s0) * ss(0.15, 0.30, v0)
    blue *= 0.6  # civilian buildings and lights are blue too: static, gentle only

    g_h = (m["g_dark"] + (m["g_bright"] - m["g_dark"]) * ss(0.25, 0.95, v0)) / 360
    g_s = np.minimum(s, np.minimum(s0 * m["g_rel"], m["g_cap"] - 0.10 * ss(0.75, 1.0, v0)))
    tg = hsv2rgb(np.stack([hue_toward(h, g_h, 0.8), g_s, v * m["g_val"]], -1))

    b_h = (m["b_hue"] + 12 * (1 - ss(0.3, 0.9, v0))) / 360
    b_s = np.minimum(s, np.minimum(s0 * m["b_rel"], m["b_cap"] - 0.10 * ss(0.75, 1.0, v0)))
    tb = hsv2rgb(np.stack([hue_toward(h, b_h, 0.7), b_s, v * 0.98], -1))

    # keep a little of the glow at the very brightest tips
    wg = (green * m["tib"] * (1 - 0.25 * ss(0.8, 1.0, v0)))[..., None]
    wb = (blue * m["tib"] * (1 - 0.25 * ss(0.8, 1.0, v0)))[..., None]
    x = cube * (1 - wg) + tg * wg
    x = x * (1 - wb) + tb * wb

    # --- fire and explosions: hotter, richer, brighter (mask on the input colour)
    warm = hue_window(h0, 30 / 360, 32 / 360, 12 / 360)
    fire = ss(0.62, 0.90, v0) * warm * ss(0.40, 0.62, s0)
    hx = rgb2hsv(np.clip(x, 0, 1))
    wrapped = ((hx[..., 0] + 0.5) % 1.0) - 0.5
    hot_h = (hx[..., 0] + (0.075 - wrapped) * 0.35) % 1.0
    sat_src = np.maximum(hx[..., 1], s0)
    pop = hsv2rgb(np.stack([hot_h, np.clip(sat_src * 1.22 + 0.04, 0, 1), np.clip(np.maximum(hx[..., 2], v0) * 1.15, 0, 1)], -1))
    wf = (fire * m["fire"])[..., None]
    x = x * (1 - wf) + pop * wf

    # --- lamps: near-white stays bright
    white = ss(0.84, 0.97, c.min(-1))[..., None]
    x = x * (1 - white * 0.6) + np.clip(np.maximum(x, c) * 1.05 + 0.02, 0, 1) * white * 0.6
    return np.clip(x, 0, 1)


def main(src, out):
    os.makedirs(out, exist_ok=True)
    for name, m in MOODS.items():
        if name in NO_LUT:
            cube = grid()
        else:
            cube = lut_to_cube(Image.open(os.path.join(src, name + "_lut.png")))
        cube_to_lut(apply(cube, m)).save(os.path.join(out, name + "_lut.png"))
        print("wrote", name)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
