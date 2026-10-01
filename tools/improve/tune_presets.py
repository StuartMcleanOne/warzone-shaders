#!/usr/bin/env python3
"""Fine-tune the Fire and Light Pop pair in the AI_ presets and give the
no-LUT presets a pass-only LUT (tiberium + fire). Keeps CRLF."""
import re, sys, os
D = sys.argv[1]
POP = dict(Fire_Anchor="0.450000", Fire_Gain="0.550000", Fire_Reach="0.500000", Fire_Saturation="0.450000",
           Fire_Strength="1.000000", Glow_Size="1.000000", Glow_Strength="0.250000",
           Lamp_Anchor="0.400000", Lamp_Boost="0.550000", Lamp_Strength="1.000000")
KEEP = {"AI_16_Firestorm": {"Fire_Gain", "Lamp_Boost"},        # his own hot values
        "AI_19_TiberiumMidnight": set(POP)}                     # his own tuning, untouched
NO_LUT = ["AI_01_Remaster", "AI_03_TiberiumBloom", "AI_05_CrimsonSun", "AI_08_GoldenHour"]

def set_key(txt, sec, key, val):
    m = re.search(r"\[%s\]\n(.*?)(?=\n\[|\Z)" % re.escape(sec), txt, re.S)
    body = m.group(1)
    if re.search(r"^%s=" % key, body, re.M):
        body = re.sub(r"^%s=.*$" % key, "%s=%s" % (key, val), body, flags=re.M)
    else:
        body = body.rstrip("\n") + "\n%s=%s" % (key, val)
    return txt[:m.start(1)] + body + txt[m.end(1):]

def insert_before(lst, item, before):
    lst = [t for t in lst if t != item]
    lst.insert(lst.index(before), item)
    return lst

for f in sorted(os.listdir(D)):
    if not f.startswith("AI_") or not f.endswith(".ini"): continue
    name = f[:-4]; p = os.path.join(D, f)
    txt = open(p, "rb").read().decode("latin-1").replace("\r\n", "\n")
    for k, v in POP.items():
        if k not in KEEP.get(name, ()): txt = set_key(txt, "CnCLightGuard.fx", k, v)
    lines = txt.split("\n")
    tech = [i for i, l in enumerate(lines) if l.startswith("Techniques=")][0]
    sort = [i for i, l in enumerate(lines) if l.startswith("TechniqueSorting=")][0]
    T = lines[tech].split("=", 1)[1].split(","); S = lines[sort].split("=", 1)[1].split(",")
    if name in NO_LUT:
        T = insert_before(T, "LUT", "LightGuard_After"); S = insert_before(S, "LUT", "LightGuard_After")
        lines[0] = 'PreprocessorDefinitions=fLUT_TextureName="%s_lut.png"' % name
    if name == "AI_19_TiberiumMidnight" and "TiberiumLife" in T:   # keep it off the sidebar
        T = insert_before(T, "TiberiumLife", "LightGuard_After"); S = insert_before(S, "TiberiumLife", "LightGuard_After")
    lines[tech] = "Techniques=" + ",".join(T); lines[sort] = "TechniqueSorting=" + ",".join(S)
    txt = "\n".join(lines)
    if name in NO_LUT and "[LUT.fx]" not in txt:
        txt = txt.rstrip("\n") + "\n\n[LUT.fx]\nfLUT_AmountChroma=1.000000\nfLUT_AmountLuma=1.000000\n\n"
    open(p, "wb").write(txt.replace("\n", "\r\n").encode("latin-1"))
    print(name, "ok")
