"""Builds the Campaign preset set: one LUT + one preset per look.

Each look is a colour grade baked into a 32x32x32 LUT (LUT.fx layout: x = blue tile*32 + red, y = green),
plus a subtle vignette and film grain. All looks share:
  - Natural tiberium: flat lime/neon green is spread into mineral greens (dark crystal parts go deep emerald,
    bright tips go pale yellow-green) and neon is calmed; blue tiberium goes to icy steel instead of neon.
  - Hot protection: fire, explosions, lamps and near-white keep the game's own colour and brightness.
Outputs: game/reshade-shaders/Textures/WZC_<Look>_lut.png and game/reshade-shaders/Custom/Campaign/<Look>.ini
"""
import os
import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TEX = os.path.join(ROOT, "game", "reshade-shaders", "Textures")
OUT = os.path.join(ROOT, "game", "reshade-shaders", "Custom", "Campaign")

LOOKS = {
    # name: dict(wb=gain rgb, lift=shadow tint rgb, gamma, contrast, sat, shoulder, tib=natural-tiberium strength,
    #            split=highlight tint rgb, vig=vignette amount, grain)
    "WZ_Baked_Day":    dict(wb=(1.14, 1.00, 0.76), lift=(0.040, 0.018, 0.000), gamma=0.92, contrast=1.22, sat=0.84,
                            shoulder=0.72, tib=1.0, split=(1.05, 1.00, 0.90), vig=-0.45, grain=0.10,
                            note="Scorching, sun-bleached day: hot amber light, bleached colour, soft glare rolloff."),
    "WZ_Day":          dict(wb=(1.06, 1.00, 0.91), lift=(0.012, 0.008, 0.004), gamma=0.97, contrast=1.18, sat=1.02,
                            shoulder=0.82, tib=1.0, split=(1.02, 1.0, 0.98), vig=-0.40, grain=0.10,
                            note="Clear day: more depth and warmth, natural tiberium."),
    "WZ_Overcast":     dict(wb=(0.93, 1.00, 1.07), lift=(0.000, 0.016, 0.034), gamma=1.05, contrast=1.14, sat=0.62,
                            shoulder=0.82, tib=1.0, split=(0.98, 1.0, 1.02), vig=-0.55, grain=0.14,
                            note="Grey, heavy sky: drained colour, cold shadows, the muted dystopia."),
    "WZ_Night":        dict(wb=(0.86, 0.98, 1.16), lift=(0.000, 0.022, 0.060), gamma=0.90, contrast=1.16, sat=0.72,
                            shoulder=0.88, tib=1.0, split=(1.05, 1.0, 0.93), vig=-0.65, grain=0.16,
                            note="For missions that are already dark: no extra darkening, moonlit blue shadows, lights stay warm."),
    "WZ_Burning_Dusk": dict(wb=(1.14, 0.97, 0.80), lift=(0.030, 0.000, 0.034), gamma=0.97, contrast=1.16, sat=1.02,
                            shoulder=0.78, tib=1.0, split=(1.06, 0.98, 0.88), vig=-0.55, grain=0.12,
                            note="Red-sky missions: amber light, violet shadows."),
    "WZ_Ion_Storm":    dict(wb=(0.90, 1.00, 1.12), lift=(0.022, 0.010, 0.060), gamma=1.08, contrast=1.30, sat=0.45,
                            shoulder=0.82, tib=0.9, split=(0.96, 1.0, 1.06), vig=-0.65, grain=0.18,
                            note="Ion storm missions: drained colour, cold electric shadows, hard contrast."),
    "WZ_Snow_Day":     dict(wb=(0.94, 1.00, 1.08), lift=(0.000, 0.008, 0.022), gamma=1.02, contrast=1.10, sat=0.82,
                            shoulder=0.70, tib=1.0, split=(0.98, 1.0, 1.04), vig=-0.40, grain=0.10,
                            note="Snow in daylight: cold white balance, snow keeps its detail instead of glaring."),
    "WZ_Snow_Night":   dict(wb=(0.86, 0.97, 1.14), lift=(0.000, 0.014, 0.060), gamma=0.94, contrast=1.10, sat=0.70,
                            shoulder=0.76, tib=1.0, split=(1.03, 1.0, 0.95), vig=-0.65, grain=0.14,
                            note="Snow at night: deep blue shadows, still readable."),
}


# ---------------------------------------------------------------- colour helpers
def rgb2hsv(c):
    r, g, b = c[..., 0], c[..., 1], c[..., 2]
    mx, mn = c.max(-1), c.min(-1)
    d = mx - mn + 1e-9
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) / 6.0
    s = np.where(mx > 0, (mx - mn) / (mx + 1e-9), 0)
    return np.stack([h % 1.0, s, mx], -1)


def hsv2rgb(hsv):
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    k = lambda n: (n + h * 6) % 6
    f = lambda n: v - v * s * np.clip(np.minimum(k(n), 4 - k(n)), 0, 1)
    return np.stack([f(5), f(3), f(1)], -1)


def ss(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def luma(c):
    return c @ np.array([0.2126, 0.7152, 0.0722])


def hue_window(h, centre, half, soft):
    d = np.abs(((h - centre + 0.5) % 1.0) - 0.5)
    return 1 - ss(half, half + soft, d)


# ---------------------------------------------------------------- the grade
def natural_tiberium(c, strength):
    hsv = rgb2hsv(c)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    green = hue_window(h, 118 / 360, 38 / 360, 15 / 360) * ss(0.12, 0.35, s) * ss(0.12, 0.3, v)
    blue = hue_window(h, 235 / 360, 35 / 360, 12 / 360) * ss(0.15, 0.40, s) * ss(0.15, 0.3, v)
    # green: dark parts -> deep emerald (150 deg), bright tips -> pale yellow-green (95 deg); calm the neon
    g_h = (150 - 55 * ss(0.25, 0.95, v)) / 360
    neon = ss(0.65, 1.0, s) * ss(0.5, 1.0, v)
    g_s = s * (1 - 0.15 * neon)
    g_v = v * (1 - 0.06 * neon)
    # blue: towards icy steel (212 deg), less saturated, bright parts go pale
    b_h = np.full_like(h, 212 / 360)
    b_s = s * 0.78
    b_v = v * 0.97
    hg = np.stack([h + (g_h - h) * 0.85, g_s, g_v], -1)
    hb = np.stack([h + (((b_h - h + 0.5) % 1.0) - 0.5) * 0.8, b_s, b_v], -1)
    out = c.copy()
    # keep the glowing lime / neon at the bright tips; reshape the body of the crystal
    wg = (green * strength * (1 - 0.65 * ss(0.65, 1.0, v)))[..., None]
    wb = (blue * strength * (1 - 0.70 * ss(0.55, 1.0, v)))[..., None]
    out = out * (1 - wg) + hsv2rgb(hg) * wg
    out = out * (1 - wb) + hsv2rgb(hb) * wb
    return out


def hot_mask(c):
    hsv = rgb2hsv(c)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    warm = hue_window(h, 30 / 360, 32 / 360, 12 / 360)
    return np.maximum(ss(0.82, 0.97, v) * warm, ss(0.88, 0.98, c.min(-1)))


def grade(c, p):
    x = natural_tiberium(c, p["tib"])
    # white balance
    x = x * np.array(p["wb"])
    # split tone: shadow lift tint, highlight tint
    l = luma(np.clip(x, 0, 1))[..., None]
    x = x + np.array(p["lift"]) * (1 - l) ** 2
    hl = ss(0.5, 1.0, l)
    x = x * (1 + (np.array(p["split"]) - 1) * hl)
    # gamma, contrast around 0.45
    x = np.clip(x, 0, None) ** p["gamma"]
    x = 0.45 + (x - 0.45) * p["contrast"]
    # saturation (tiberium keeps most of its glow colour)
    hsv0 = rgb2hsv(c)
    tibm = np.maximum(hue_window(hsv0[..., 0], 118 / 360, 40 / 360, 15 / 360), hue_window(hsv0[..., 0], 235 / 360, 35 / 360, 12 / 360))
    tibm = tibm * ss(0.2, 0.45, hsv0[..., 1]) * ss(0.2, 0.45, hsv0[..., 2])
    sat = p["sat"] + (max(p["sat"], 1.0) - p["sat"]) * 0.8 * tibm
    l = luma(x)[..., None]
    x = l + (x - l) * sat[..., None]
    # soft highlight shoulder
    k = p["shoulder"]
    over = np.maximum(x - k, 0)
    x = np.minimum(x, k) + over / (1 + over / (1 - k))
    x = np.clip(x, 0, 1)
    # fire, explosions, weapon fire: hotter and richer than the game drew them, the same in every preset;
    # lamps and near-white: pushed towards clean bright white
    hsv = rgb2hsv(c)
    h, sa, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    warm = hue_window(h, 30 / 360, 32 / 360, 12 / 360)
    fire = ss(0.72, 0.92, v) * warm * ss(0.45, 0.65, sa)
    hot_h = h + (np.where(h > 0.5, h - 1, h) * 0 + 0.075 - np.where(h > 0.5, h - 1, h)) * 0.35
    pop = hsv2rgb(np.stack([hot_h % 1.0, np.clip(sa * 1.25 + 0.05, 0, 1), np.clip(v * 1.15, 0, 1)], -1))
    white = ss(0.82, 0.97, c.min(-1))
    lamp = np.clip(c * 1.08 + 0.02, 0, 1)
    m1 = (fire * 0.9)[..., None]
    x = x * (1 - m1) + pop * m1
    m2 = (white * 0.85)[..., None]
    return x * (1 - m2) + lamp * m2


def make_lut(p):
    i = np.arange(32) / 31.0
    b, g, r = np.meshgrid(i, i, i, indexing="ij")          # [b, g, r]
    c = np.stack([r, g, b], -1)
    out = grade(c, p)                                         # [b, g, r, 3]
    img = np.zeros((32, 1024, 3))
    for bi in range(32):
        img[:, bi * 32:(bi + 1) * 32] = out[bi]               # rows = g, cols = r
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)


def preset_ini(name, p):
    lines = [f'PreprocessorDefinitions=fLUT_TextureName="WZC_{name[3:]}_lut.png"',
             "Techniques=UI_Before,LightGuard_Before,Deband,LUT,Vignette,FilmGrain,LightGuard_After,UI_After",
             "TechniqueSorting=UI_Before,LightGuard_Before,Deband,LUT,Vignette,FilmGrain,LightGuard_After,UI_After",
             "",
             "[CnCLightGuard.fx]", "Debug_View=0", "Fire_Anchor=0.350000", "Fire_Gain=0.350000", "Fire_Reach=0.000000",
             "Fire_Saturation=0.350000", "Fire_Strength=1.000000", "Glow_Size=1.200000", "Glow_Strength=0.200000",
             "Lamp_Anchor=0.500000", "Lamp_Boost=0.450000", "Lamp_Radius=3.000000", "Lamp_Strength=1.000000", "",
             "[CnCUIskip.fx]", "Isolate_UI=1", "",
             "[Deband.fx]", "custom_avgdiff=1.800000", "custom_maxdiff=4.000000", "custom_middiff=2.000000",
             "debug_output=0", "iterations=1", "range=16.000000", "threshold_preset=1", "",
             "[FilmGrain.fx]", f"Intensity={p['grain']:.6f}", "Mean=0.500000", "SignalToNoiseRatio=6", "Variance=0.400000", "",
             "[LUT.fx]", "fLUT_AmountChroma=1.000000", "fLUT_AmountLuma=1.000000", "",
             "[Vignette.fx]", "Amount=%.6f" % p["vig"], "Center=0.395000,0.518333", "Radius=1.500000", "Ratio=1.000000",
             "Slope=3", "Type=0", ""]
    return "\r\n".join(lines) + "\r\n"


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, p in LOOKS.items():
        Image.fromarray(make_lut(p)).save(os.path.join(TEX, f"WZC_{name[3:]}_lut.png"))
        open(os.path.join(OUT, name + ".ini"), "wb").write(preset_ini(name, p).encode())
        print("built", name)


if __name__ == "__main__":
    main()
