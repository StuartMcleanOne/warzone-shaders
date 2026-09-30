"""Batch 2: Weather slim-down, 8 new presets (AI_11..AI_18) with custom LUTs.
- Section keys are validated against real uniform names.
- Every active shader gets a COMPLETE section: shader defaults parsed from source, then overrides.
- LUTs generated in the exact layout LUT.fx samples (1024x32: x=tile(blue)*32+red, y=green)."""
import re, os, sys
import numpy as np
from PIL import Image

ROOT = "/mnt/user-data/uploads/reshade-shaders"
SHD = ROOT + "/Shaders"
OUT = "/mnt/user-data/outputs/batch2"
os.makedirs(OUT + "/Textures", exist_ok=True)
PF_CENTER = (0.395, 0.518333)  # playfield centre (sidebar right 168px, top strip 22px)

# ------------------------------------------------------------------ shader introspection
TECH2FILE, UNIFORMS = {}, {}
for root, _, fs in os.walk(SHD):
    for f in fs:
        if not f.endswith(".fx"): continue
        p = os.path.join(root, f); txt = open(p, encoding="latin-1").read()
        for t in re.findall(r"technique\s+(\w+)", txt): TECH2FILE.setdefault(t, p)
        UNIFORMS[f] = txt

def parse_defaults(fname):
    """uniform name -> default string (ini format), skipping source-bound uniforms."""
    txt = UNIFORMS[fname]; out = {}
    for m in re.finditer(r"uniform\s+(bool|u?int[234]?|float[234]?)\s+(\w+)\s*(<(?:[^>]|>(?!\s*[=;]))*>)?\s*(=\s*([^;]+))?;", txt):
        typ, name, ann, _, val = m.groups()
        if ann and "source" in ann: continue
        if val is None: continue
        v = val.strip()
        v = re.sub(r"^(float|int|uint)[234]?\s*\((.*)\)$", r"\2", v)
        parts = [x.strip() for x in v.split(",")]
        conv = []
        for x in parts:
            x = x.rstrip("fF")
            if x in ("true", "false"): conv.append("1" if x == "true" else "0"); continue
            try:
                if re.fullmatch(r"-?\d+", x) and not typ.startswith("float"): conv.append(str(int(x)))
                else: conv.append("%.6f" % eval(x, {"__builtins__": {}}, {}))
            except Exception: conv = None; break
        if conv: out[name] = ",".join(conv)
    return out

def uniform_names(fname):
    return set(re.findall(r"uniform\s+(?:bool|u?int[234]?|float[234]?)\s+(\w+)", UNIFORMS[fname]))

def fmt(v):
    if isinstance(v, bool): return "1" if v else "0"
    if isinstance(v, int): return str(v)
    if isinstance(v, float): return "%.6f" % v
    if isinstance(v, (tuple, list)): return ",".join(fmt(x) for x in v)
    return str(v)

MASTER_SORT = [t for t in re.search(r"TechniqueSorting=(.*)", open(ROOT + "/C&CWarzoneWeather.ini", encoding="latin-1").read()).group(1).strip().split(",") if t]
errors, report = [], []

def emit(path, chain, settings, defines="", base_sections=None):
    """settings: {shaderfile.fx: {key: value}}; every active shader gets full defaults + overrides."""
    for t in chain:
        if t not in TECH2FILE: errors.append(f"{os.path.basename(path)}: unknown technique {t}")
    sections = dict(base_sections or {})
    active_files = {os.path.basename(TECH2FILE[t]) for t in chain if t in TECH2FILE}
    for f in active_files | set(settings):
        valid = uniform_names(f)
        sec = dict(parse_defaults(f)); sec.update(sections.get(f, {}))
        for k, v in settings.get(f, {}).items():
            if k not in valid: errors.append(f"{os.path.basename(path)}: [{f}] {k} not a uniform")
            sec[k] = fmt(v)
        sections[f] = sec
    sort = chain + [t for t in MASTER_SORT if t not in chain]
    lines = [f"PreprocessorDefinitions={defines}", "Techniques=" + ",".join(chain), "TechniqueSorting=" + ",".join(sort), ""]
    for name in sorted(sections, key=str.lower):
        lines.append(f"[{name}]"); lines += [f"{k}={v}" for k, v in sections[name].items()]; lines.append("")
    open(path, "wb").write(("\r\n".join(lines) + "\r\n").encode("latin-1"))
    report.append((os.path.basename(path), len(chain) - 2))

# ------------------------------------------------------------------ LUT tooling
def rgb2hsv(c):
    r, g, b = c[..., 0], c[..., 1], c[..., 2]
    mx, mn = c.max(-1), c.min(-1); d = mx - mn
    h = np.zeros_like(mx)
    m = d > 1e-6
    rc = np.where(m, (mx - r) / np.where(m, d, 1), 0); gc = np.where(m, (mx - g) / np.where(m, d, 1), 0); bc = np.where(m, (mx - b) / np.where(m, d, 1), 0)
    h = np.where(r == mx, bc - gc, np.where(g == mx, 2.0 + rc - bc, 4.0 + gc - rc))
    h = np.where(m, (h / 6.0) % 1.0, 0.0)
    s = np.where(mx > 1e-6, d / np.where(mx > 1e-6, mx, 1), 0)
    return np.stack([h, s, mx], -1)

def hsv2rgb(hsv):
    h, s, v = hsv[..., 0] % 1.0, np.clip(hsv[..., 1], 0, 1), hsv[..., 2]
    i = np.floor(h * 6); f = h * 6 - i; i = i.astype(int) % 6
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    conds = [i == k for k in range(6)]
    r = np.select(conds, [v, q, p, p, t, v]); g = np.select(conds, [t, v, v, q, p, p]); b = np.select(conds, [p, p, t, v, v, q])
    return np.stack([r, g, b], -1)

LW = np.array([0.2126, 0.7152, 0.0722])
def luma(c): return (c * LW).sum(-1, keepdims=True)
def sat(c, s): l = luma(c); return l + (c - l) * s
def scurve(c, k): sm = c * c * (3 - 2 * c); return c + k * (sm - c)
def hue_mask(hsv, center_deg, width_deg):
    d = np.abs(((hsv[..., 0] * 360 - center_deg + 180) % 360) - 180)
    return (np.clip(1 - d / width_deg, 0, 1) * np.clip(hsv[..., 1] * 3, 0, 1))[..., None]
def hue_shift(c, center, width, shift_deg, sat_mul=1.0, val_mul=1.0, protect_vivid=False):
    hsv = rgb2hsv(np.clip(c, 0, 1)); w = hue_mask(hsv, center, width)[..., 0]
    if protect_vivid: w = w * np.clip((0.6 - hsv[..., 1]) / 0.2, 0, 1)   # leave saturated tiberium greens alone
    hsv[..., 0] = hsv[..., 0] + w * shift_deg / 360.0
    hsv[..., 1] = hsv[..., 1] * (1 + w * (sat_mul - 1)); hsv[..., 2] = hsv[..., 2] * (1 + w * (val_mul - 1))
    return hsv2rgb(hsv)
def keep_tiberium(fn, amount=0.75):
    def g(c):
        out = fn(c); hsv = rgb2hsv(c)
        m = hue_mask(hsv, 125, 45) * np.clip((hsv[..., 2:3] - 0.35) / 0.3, 0, 1) * amount
        return out * (1 - m) + c * m
    return g
def split(c, shadow, high):
    l = luma(c); return c + (1 - l) ** 2 * np.array(shadow) + l ** 2 * np.array(high)

def make_lut(name, fn):
    n = 32; r, g, b = np.meshgrid(np.arange(n), np.arange(n), np.arange(n), indexing="ij")
    c = np.stack([r, g, b], -1).astype(np.float64) / (n - 1)
    o = np.clip(fn(c), 0, 1)
    img = np.zeros((n, n * n, 3), np.uint8)
    for bi in range(n):  # tile = blue, x in tile = red, y = green
        img[:, bi * n:(bi + 1) * n, :] = np.round(o[:, :, bi, :].transpose(1, 0, 2) * 255)
    Image.fromarray(img, "RGB").save(f"{OUT}/Textures/{name}")
    return name

# sanity: identity LUT must match the shipped neutral lut.png
ident = make_lut("_identity_check.png", lambda c: c)
a = np.asarray(Image.open(f"{OUT}/Textures/_identity_check.png")).astype(int)
bref = np.asarray(Image.open(ROOT + "/Textures/lut.png").convert("RGB")).astype(int)
diff = np.abs(a - bref).max(); os.remove(f"{OUT}/Textures/_identity_check.png")
if diff > 2: errors.append(f"LUT layout mismatch vs shipped lut.png (max diff {diff})")
print("identity LUT vs shipped lut.png max diff:", diff)

# ------------------------------------------------------------------ grades
def g_ion(c):
    c = hue_shift(c, 40, 40, 0, sat_mul=0.45)               # kill warm oranges/yellows
    c = hue_shift(c, 205, 50, 0, sat_mul=1.35, val_mul=1.05) # electrify cyans/blues
    c = sat(c, 0.9); c = split(c, (-0.02, 0.05, 0.13), (-0.02, 0.02, 0.05))
    return scurve(np.clip(c, 0, 1), 0.3)
def g_night(c):
    hsv = rgb2hsv(c); gm = hue_mask(hsv, 125, 55)             # tiberium greens
    lit = c * (0.64 + 0.36 * gm)                               # world drops ~40%, greens keep their light
    lit = sat(lit, 0.45 + 1.05 * gm[..., 0:1] * 1.0)            # everything grey-blue except tiberium
    lit = lit + (1 - luma(lit)) ** 2 * np.array([-0.005, 0.01, 0.06])
    lit = np.clip(lit, 0, 1) ** 1.1
    return scurve(lit, 0.2)
def g_scorch(c):
    c = hue_shift(c, 115, 60, -38, sat_mul=0.55, protect_vivid=True)  # vegetation -> dry khaki, tiberium stays green
    c = sat(c, 0.85); c = split(c, (0.03, 0.005, -0.03), (0.07, 0.02, -0.08))
    c = 0.025 + 0.975 * np.clip(c, 0, 1)                    # dusty lifted blacks
    return scurve(c, 0.3)
def g_rain(c):
    l = luma(c); hsv = rgb2hsv(c)
    s_mul = 0.45 + 0.85 * np.clip((hsv[..., 1:2] - 0.5) * 2, 0, 1) * np.clip(l * 2, 0, 1)  # only vivid lights keep colour
    c = sat(c, s_mul); c = split(c, (-0.02, 0.02, 0.06), (-0.01, 0.01, 0.03))
    c = np.clip((np.clip(c, 0, 1) - 0.03) / 0.97, 0, 1)      # wet, deep blacks
    return scurve(c, 0.35)
def g_koda(c):
    c = hue_shift(c, 5, 25, 0, sat_mul=1.3, val_mul=0.95)   # deep saturated reds
    c = hue_shift(c, 50, 25, -4, sat_mul=1.15)              # golden yellows
    c = hue_shift(c, 115, 50, -10, sat_mul=0.85)            # greens toward olive
    c = hue_shift(c, 225, 40, -10, sat_mul=1.1)             # blues toward cyan
    c = scurve(np.clip(c, 0, 1), 0.38)
    c = c * np.array([0.985, 0.965, 0.9]) + 0.025 * np.array([1.0, 0.9, 0.8])  # cream whites, warm film base
    return c
def g_fire(c):
    c = hue_shift(c, 20, 35, -4, sat_mul=1.4, val_mul=1.05)  # fire, embers, blood
    c = hue_shift(c, 120, 60, -20, sat_mul=0.5, protect_vivid=True)
    c = hue_shift(c, 215, 60, 0, sat_mul=0.5, val_mul=0.9)
    c = split(c, (0.035, -0.005, -0.02), (0.08, 0.0, -0.09))
    return scurve(np.clip(c, 0, 1), 0.35)
def g_nod(c):
    l = scurve(np.clip(luma(c), 0, 1), 0.6)
    stops = np.array([0.0, 0.4, 0.75, 1.0]); cols = np.array([[0.01, 0.0, 0.0], [0.34, 0.05, 0.04], [0.68, 0.6, 0.53], [0.98, 0.94, 0.85]])
    duo = np.stack([np.interp(l[..., 0], stops, cols[:, i]) for i in range(3)], -1)
    hsv = rgb2hsv(c); red = hue_mask(hsv, 0, 25)             # real reds stay red and hot
    return duo * (1 - 0.5 * red) + np.clip(c * 1.15, 0, 1) * 0.5 * red
def g_gdi(c):
    c = sat(c, 0.7); c = split(c, (-0.02, 0.012, 0.035), (-0.012, 0.01, 0.02))
    return scurve(np.clip(c, 0, 1), 0.25)

L = {k: make_lut(f"AI_{k}_lut.png", f) for k, f in [
    ("11_IonStorm", g_ion), ("12_TiberiumNight", g_night), ("13_ScorchedEarth", keep_tiberium(g_scorch)), ("14_ChromeAndRain", g_rain),
    ("15_Kodachrome99", g_koda), ("16_Firestorm", keep_tiberium(g_fire)), ("17_NodPropaganda", g_nod), ("18_GDITacticalFeed", g_gdi)]}
def lutdef(k): return f'fLUT_TextureName="{L[k]}"'

# ------------------------------------------------------------------ shared building blocks
UI = {"CnCUIskip.fx": {"Isolate_UI": True}}
DEBAND = {"Deband.fx": {"threshold_preset": 1, "range": 16.0, "iterations": 1}}
def LUT(chroma=1.0, luma_=1.0): return {"LUT.fx": {"fLUT_AmountChroma": chroma, "fLUT_AmountLuma": luma_}}
def VIG(a, r, s): return {"Vignette.fx": {"Type": 0, "Ratio": 1.0, "Radius": r, "Amount": a, "Slope": s, "Center": PF_CENTER}}
def LUMA(s, c): return {"LumaSharpen.fx": {"sharp_strength": s, "sharp_clamp": c, "pattern": 1, "offset_bias": 1.0}}
def GRAIN(i, snr=6, var=0.4): return {"FilmGrain.fx": {"Intensity": i, "Variance": var, "Mean": 0.5, "SignalToNoiseRatio": snr}}
def GRAIN2(a, col=0.3, size=1.6): return {"FilmGrain2.fx": {"grainamount": a, "coloramount": col, "lumamount": 1.0, "grainsize": size}}
def CURVE(k, mode=0): return {"Curves.fx": {"Mode": mode, "Formula": 4, "Contrast": k}}
def M(*ds):
    out = {}
    for d in ds:
        for f, kv in d.items(): out.setdefault(f, {}).update(kv)
    return out
C = f"{OUT}/Custom"; os.makedirs(C, exist_ok=True)

# ------------------------------------------------------------------ 11 Ion Storm
emit(f"{C}/AI_11_IonStorm.ini",
 ["UI_Before", "Deband", "AmbientLight", "BloomAndLensFlares", "PPFX_Godrays", "LUT", "Clarity", "LumaSharpen", "Vignette", "FilmGrain2", "UI_After"],
 M(UI, DEBAND,
   {"AmbientLight.fx": {"alInt": 6.0, "alThreshold": 12.0, "AL_Adaptive": 1, "AL_Adaptation": True, "AL_Dirt": True, "alDirtInt": 0.5, "alDirtOVInt": 0.6, "AL_Lens": False, "alDebug": False}},
   {"Bloom.fx": {"iBloomMixmode": 2, "fBloomThreshold": 0.72, "fBloomAmount": 1.4, "fBloomSaturation": 1.3, "fBloomTint": (0.55, 0.8, 1.0),
                 "bAnamFlareEnable": True, "fAnamFlareThreshold": 0.82, "fAnamFlareWideness": 2.2, "fAnamFlareAmount": 12.0, "fAnamFlareCurve": 1.2, "fAnamFlareColor": (0.1, 0.45, 1.0),
                 "bLensdirtEnable": False, "bLenzEnable": False, "bChapFlareEnable": False, "bGodrayEnable": False}},
   {"PPFX_Godrays.fx": {"pGodraysSampleAmount": 96, "pGodraysSource": (0.2, -0.25), "pGodraysExposure": 0.12, "pGodraysFreq": 1.4, "pGodraysThreshold": 0.7, "pGodraysFalloff": 1.08}},
   LUT(), {"Clarity.fx": {"ClarityRadius": 3, "ClarityOffset": 2.0, "ClarityBlendMode": 2, "ClarityStrength": 0.5, "ClarityDarkIntensity": 0.45, "ClarityLightIntensity": 0.1}},
   LUMA(0.45, 0.025), VIG(-0.8, 1.5, 4), GRAIN2(0.02, 0.2)),
 defines=lutdef("11_IonStorm"))

# ------------------------------------------------------------------ 12 Tiberium Night
emit(f"{C}/AI_12_TiberiumNight.ini",
 ["UI_Before", "Deband", "LUT", "MagicBloom", "Bloom", "EyeAdaption", "LumaSharpen", "Vignette", "FilmGrain", "UI_After"],
 M(UI, DEBAND, LUT(),
   {"MagicBloom.fx": {"fBloom_Intensity": 5.0, "fBloom_Threshold": 3.0, "fDirt_Intensity": 0.2, "fExposure": 0.5, "fAdapt_Speed": 0.2, "fAdapt_Sensitivity": 0.6, "iDebug": 0}},
   {"qUINT_bloom.fx": {"BLOOM_INTENSITY": 1.4, "BLOOM_CURVE": 1.2, "BLOOM_SAT": 3.0, "BLOOM_DIRT": 0.0,
                       "BLOOM_LAYER_MULT_1": 0.05, "BLOOM_LAYER_MULT_2": 0.1, "BLOOM_LAYER_MULT_3": 0.3, "BLOOM_LAYER_MULT_4": 0.4,
                       "BLOOM_LAYER_MULT_5": 0.5, "BLOOM_LAYER_MULT_6": 0.25, "BLOOM_LAYER_MULT_7": 0.1,
                       "BLOOM_ADAPT_STRENGTH": 0.2, "BLOOM_ADAPT_EXPOSURE": 0.0, "BLOOM_ADAPT_SPEED": 2.0, "BLOOM_TONEMAP_COMPRESSION": 3.0}},
   {"EyeAdaption.fx": {"fAdp_Delay": 1.2, "fAdp_TriggerRadius": 6.0, "fAdp_YAxisFocalPoint": 0.5, "fAdp_Equilibrium": 0.35, "fAdp_Strength": 1.0,
                       "fAdp_BrightenHighlights": 0.05, "fAdp_BrightenMidtones": 0.25, "fAdp_BrightenShadows": 0.2,
                       "fAdp_DarkenHighlights": 0.25, "fAdp_DarkenMidtones": 0.1, "fAdp_DarkenShadows": 0.05}},
   LUMA(0.5, 0.03), VIG(-1.1, 1.3, 4), GRAIN(0.3, 4, 0.45)),
 defines=lutdef("12_TiberiumNight"))

# ------------------------------------------------------------------ 13 Scorched Earth
emit(f"{C}/AI_13_ScorchedEarth.ini",
 ["UI_Before", "Deband", "FilmicPass", "AmbientLight", "PPFX_Godrays", "LUT", "HeatHaze", "Curves", "LumaSharpen", "Vignette", "FilmGrain", "UI_After"],
 M(UI, DEBAND,
   {"FilmicPass.fx": {"Strength": 0.7, "Fade": 0.05, "Contrast": 1.05, "Bleach": 0.35, "Saturation": -0.05}},
   {"AmbientLight.fx": {"alInt": 8.0, "alThreshold": 6.0, "AL_Adaptive": 0, "AL_Adaptation": True, "AL_Dirt": True, "alDirtInt": 0.9, "alDirtOVInt": 0.9, "AL_Lens": False, "alDebug": False}},
   {"PPFX_Godrays.fx": {"pGodraysSampleAmount": 128, "pGodraysSource": (0.9, -0.3), "pGodraysExposure": 0.2, "pGodraysFreq": 1.2, "pGodraysThreshold": 0.55, "pGodraysFalloff": 1.04}},
   LUT(),
   {"HeatHaze.fx": {"fHeatHazeSpeed": 0.9, "fHeatHazeOffset": 0.8, "fHeatHazeTextureScale": 6.0, "fHeatHazeChromaAmount": 0.12, "bHeatHazeDebug": False}},
   CURVE(0.2), LUMA(0.5, 0.025), VIG(-0.7, 1.5, 4), GRAIN(0.18, 7)),
 defines=lutdef("13_ScorchedEarth"))

# ------------------------------------------------------------------ 14 Chrome & Rain  (ReflectiveBumpmapping is the experiment)
emit(f"{C}/AI_14_ChromeAndRain.ini",
 ["UI_Before", "Deband", "ReflectiveBumpmapping", "LUT", "BloomAndLensFlares", "Clarity", "Curves", "Vignette", "FilmGrain2", "UI_After"],
 M(UI, DEBAND,
   {"ReflectiveBumpMapping.fx": {"fRBM_BlurWidthPixels": 60.0, "iRBM_SampleCount": 48, "fRBM_ReliefHeight": 0.6, "fRBM_FresnelReflectance": 0.4,
                                 "fRBM_FresnelMult": 0.6, "fRBM_LowerThreshold": 0.1, "fRBM_UpperThreshold": 0.35}},
   LUT(),
   {"Bloom.fx": {"iBloomMixmode": 2, "fBloomThreshold": 0.75, "fBloomAmount": 1.1, "fBloomSaturation": 1.5, "fBloomTint": (0.7, 0.85, 1.0),
                 "bAnamFlareEnable": True, "fAnamFlareThreshold": 0.85, "fAnamFlareWideness": 2.4, "fAnamFlareAmount": 9.0, "fAnamFlareCurve": 1.3, "fAnamFlareColor": (0.3, 0.55, 1.0),
                 "bLensdirtEnable": False, "bLenzEnable": False, "bChapFlareEnable": False, "bGodrayEnable": False}},
   {"Clarity.fx": {"ClarityRadius": 3, "ClarityOffset": 2.0, "ClarityBlendMode": 2, "ClarityStrength": 0.6, "ClarityDarkIntensity": 0.5, "ClarityLightIntensity": 0.2}},
   CURVE(0.2), VIG(-0.9, 1.4, 4), GRAIN2(0.022, 0.15)),
 defines=lutdef("14_ChromeAndRain"))

# ------------------------------------------------------------------ 15 Kodachrome '99
emit(f"{C}/AI_15_Kodachrome99.ini",
 ["UI_Before", "Deband", "LUT", "prod80_02_Bloom", "Bloom", "LumaSharpen", "Vignette", "FilmGrain2", "UI_After"],
 M(UI, DEBAND, LUT(),
   {"PD80_02_Bloom.fx": {"BloomMix": 0.45, "BloomLimit": 0.5, "GreyValue": 0.35, "bExposure": 0.2, "BlurSigma": 12.0, "BloomSaturation": 1.3,
                         "enableBKelvin": True, "BKelvin": 3200, "dither_strength": 2.0, "debugBloom": False}},
   {"qUINT_bloom.fx": {"BLOOM_INTENSITY": 0.5, "BLOOM_CURVE": 2.5, "BLOOM_SAT": 1.2, "BLOOM_DIRT": 0.0,
                       "BLOOM_LAYER_MULT_1": 0.0, "BLOOM_LAYER_MULT_2": 0.0, "BLOOM_LAYER_MULT_3": 0.05, "BLOOM_LAYER_MULT_4": 0.1,
                       "BLOOM_LAYER_MULT_5": 0.35, "BLOOM_LAYER_MULT_6": 0.35, "BLOOM_LAYER_MULT_7": 0.25,
                       "BLOOM_ADAPT_STRENGTH": 0.3, "BLOOM_ADAPT_EXPOSURE": 0.0, "BLOOM_ADAPT_SPEED": 2.0, "BLOOM_TONEMAP_COMPRESSION": 4.0}},
   LUMA(0.4, 0.025), VIG(-0.6, 1.6, 4), GRAIN2(0.035, 0.45, 1.7)),
 defines=lutdef("15_Kodachrome99"))

# ------------------------------------------------------------------ 16 Firestorm
emit(f"{C}/AI_16_Firestorm.ini",
 ["UI_Before", "Deband", "AmbientLight", "MagicBloom", "BloomAndLensFlares", "LUT", "EyeAdaption", "HeatHaze", "Curves", "LumaSharpen", "Vignette", "FilmGrain", "UI_After"],
 M(UI, DEBAND,
   {"AmbientLight.fx": {"alInt": 8.0, "alThreshold": 8.0, "AL_Adaptive": 0, "AL_Adaptation": True, "AL_Dirt": True, "alDirtInt": 1.0, "alDirtOVInt": 1.0, "AL_Lens": False, "alDebug": False}},
   {"MagicBloom.fx": {"fBloom_Intensity": 6.0, "fBloom_Threshold": 3.5, "fDirt_Intensity": 0.45, "fExposure": 0.5, "fAdapt_Speed": 0.25, "fAdapt_Sensitivity": 0.9, "iDebug": 0}},
   {"Bloom.fx": {"iBloomMixmode": 2, "fBloomThreshold": 0.85, "fBloomAmount": 0.6, "fBloomSaturation": 1.4, "fBloomTint": (1.0, 0.7, 0.45),
                 "bLenzEnable": True, "fLenzIntensity": 0.8, "fLenzThreshold": 0.85,
                 "bAnamFlareEnable": True, "fAnamFlareThreshold": 0.9, "fAnamFlareWideness": 2.0, "fAnamFlareAmount": 8.0, "fAnamFlareCurve": 1.2, "fAnamFlareColor": (1.0, 0.45, 0.1),
                 "bLensdirtEnable": False, "bChapFlareEnable": False, "bGodrayEnable": False}},
   LUT(),
   {"EyeAdaption.fx": {"fAdp_Delay": 0.6, "fAdp_TriggerRadius": 5.0, "fAdp_YAxisFocalPoint": 0.5, "fAdp_Equilibrium": 0.45, "fAdp_Strength": 1.3,
                       "fAdp_BrightenHighlights": 0.05, "fAdp_BrightenMidtones": 0.15, "fAdp_BrightenShadows": 0.15,
                       "fAdp_DarkenHighlights": 0.4, "fAdp_DarkenMidtones": 0.3, "fAdp_DarkenShadows": 0.1}},
   {"HeatHaze.fx": {"fHeatHazeSpeed": 1.3, "fHeatHazeOffset": 0.7, "fHeatHazeTextureScale": 5.0, "fHeatHazeChromaAmount": 0.2, "bHeatHazeDebug": False}},
   CURVE(0.25), LUMA(0.5, 0.03), VIG(-0.9, 1.4, 4), GRAIN(0.22, 6)),
 defines=lutdef("16_Firestorm"))

# ------------------------------------------------------------------ 17 Nod Propaganda
emit(f"{C}/AI_17_NodPropaganda.ini",
 ["UI_Before", "Deband", "LUT", "Curves", "Clarity", "prod80_02_Bloom", "Vignette", "FilmGrain2", "UI_After"],
 M(UI, DEBAND, LUT(chroma=0.7, luma_=1.0),   # 30% of original hue survives so team colours stay readable
   CURVE(0.35),
   {"Clarity.fx": {"ClarityRadius": 4, "ClarityOffset": 2.5, "ClarityBlendMode": 2, "ClarityStrength": 0.65, "ClarityDarkIntensity": 0.6, "ClarityLightIntensity": 0.25}},
   {"PD80_02_Bloom.fx": {"BloomMix": 0.55, "BloomLimit": 0.4, "GreyValue": 0.3, "bExposure": 0.35, "BlurSigma": 16.0, "BloomSaturation": 1.6,
                         "enableBKelvin": True, "BKelvin": 2200, "dither_strength": 2.0, "debugBloom": False}},
   VIG(-1.4, 1.2, 4), GRAIN2(0.04, 0.1, 2.0)),
 defines=lutdef("17_NodPropaganda"))

# ------------------------------------------------------------------ 18 GDI Tactical Feed
emit(f"{C}/AI_18_GDITacticalFeed.ini",
 ["UI_Before", "Deband", "LUT", "Clarity", "HighPassSharp", "Bloom", "ScanlinesAbs", "Vignette", "FilmGrain", "UI_After"],
 M(UI, DEBAND, LUT(),
   {"Clarity.fx": {"ClarityRadius": 3, "ClarityOffset": 2.0, "ClarityBlendMode": 2, "ClarityStrength": 0.7, "ClarityDarkIntensity": 0.5, "ClarityLightIntensity": 0.3}},
   {"HighPassSharpen.fx": {"HighPassSharpRadius": 1, "HighPassSharpOffset": 1.0, "HighPassBlendMode": 0, "HighPassSharpStrength": 0.5,
                           "HighPassBlendIfDark": 0, "HighPassBlendIfLight": 255, "HighPassDarkIntensity": 1.0, "HighPassLightIntensity": 1.0}},
   {"qUINT_bloom.fx": {"BLOOM_INTENSITY": 0.6, "BLOOM_CURVE": 3.0, "BLOOM_SAT": 0.8, "BLOOM_DIRT": 0.0,
                       "BLOOM_LAYER_MULT_1": 0.2, "BLOOM_LAYER_MULT_2": 0.3, "BLOOM_LAYER_MULT_3": 0.2, "BLOOM_LAYER_MULT_4": 0.05,
                       "BLOOM_LAYER_MULT_5": 0.02, "BLOOM_LAYER_MULT_6": 0.0, "BLOOM_LAYER_MULT_7": 0.0,
                       "BLOOM_ADAPT_STRENGTH": 0.2, "BLOOM_ADAPT_EXPOSURE": 0.0, "BLOOM_ADAPT_SPEED": 2.0, "BLOOM_TONEMAP_COMPRESSION": 4.0}},
   {"scanlines-abs.fx": {"texture_sizeY": 300.0, "amp": 1.0, "phase": 0.0, "lines_black": 0.86, "lines_white": 1.04}},
   VIG(-0.7, 1.5, 4), GRAIN(0.12, 8, 0.3)),
 defines=lutdef("18_GDITacticalFeed"))

# ------------------------------------------------------------------ Weather slim (his preset; original file left untouched in root)
wsrc = open(ROOT + "/C&CWarzoneWeather.ini", encoding="latin-1").read().replace("\r", "")
base, cur = {}, None
for line in wsrc.split("\n"):
    m = re.match(r"^\[(.+)\]$", line.strip())
    if m: cur = m.group(1); base[cur] = {}; continue
    if cur and "=" in line: k, v = line.split("=", 1); base[cur][k] = v
REMOVED = ["MXAO", "PPFXSSDO", "LightDoF_Near", "UIDetect", "UIDetect_Before", "UIDetect_After", "AspectRatioPS", "GaussianBlur", "DELC_Sharpen"]
emit(f"{C}/C_C&CWarzoneWeather.ini",
 ["UI_Before", "FXAA", "Deband", "LumaSharpen", "Vibrance", "Tint", "ReflectiveBumpmapping", "Vignette", "AmbientLight", "BloomAndLensFlares",
  "DPX", "Curves", "Clarity", "Technicolor", "EyeAdaption", "HDR", "Technicolor2", "prod80_04_ContrastBrightnessSaturation",
  "Pirate_Bloom", "MagicBloom", "MultiLUT", "FilmGrain", "UI_After"],
 {"Vignette.fx": {"Center": PF_CENTER}},   # only change to values: vignette centred on the playfield
 base_sections=base)
orig_chain = re.search(r"Techniques=(.*)", wsrc).group(1).split(",")
assert set(orig_chain) - set(REMOVED) - {"UI_Before", "UI_After"} == set(["FXAA", "Deband", "LumaSharpen", "Vibrance", "Tint", "ReflectiveBumpmapping", "Vignette", "AmbientLight", "BloomAndLensFlares", "DPX", "Curves", "Clarity", "Technicolor", "EyeAdaption", "HDR", "Technicolor2", "prod80_04_ContrastBrightnessSaturation", "Pirate_Bloom", "MagicBloom", "MultiLUT", "FilmGrain"]), "weather chain mismatch"

if errors:
    print("ERRORS:"); print("\n".join(errors)); sys.exit(1)
for n, k in report: print(f"{n:34s} {k:2d} effects")
print("LUTs:", ", ".join(L.values()))
