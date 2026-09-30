import re,os,glob
SRC="/mnt/user-data/uploads/reshade-shaders/Custom/"
OUT="/mnt/user-data/outputs/batch11/Custom/"
targets=[f for f in sorted(os.listdir(SRC)) if f.endswith(".ini") and (f.startswith("AI_") or (f.startswith("C_C&CWarzone")))]
PRE_GEO=["HeatHaze","AspectRatioPS"]          # move pixels: must run before the guard takes its snapshot
POST_GEO=["MotionBlur","PerfectPerspective","TiltShift"]   # geometry/blur: stay after UI_After
FIRST=["CRT_NES_MINI"]                          # whole-screen look, stays first
GUARD="[CnCLightGuard.fx]\nFire_Strength=0.900000\nFire_Boost=0.080000\nLamp_Strength=1.000000\nLamp_Boost=0.300000\nLamp_Radius=3.000000\n"
FXAA="[FXAA.fx]\nEdgeThreshold=0.250000\nEdgeThresholdMin=0.062500\nSubpix=0.000000\n"
rep=[]
for f in targets:
    raw=open(SRC+f,"rb").read().decode("utf-8","ignore"); crlf="\r\n" in raw
    t=raw.replace("\r\n","\n")
    T=[x for x in re.search(r"^Techniques=(.*)$",t,re.M).group(1).split(",") if x]
    m=re.search(r"^TechniqueSorting=(.*)$",t,re.M); S=[x for x in (m.group(1).split(",") if m else []) if x]
    eff=[x for x in S if x in T]+[x for x in T if x not in S]
    if "LightGuard_Before" in eff: continue
    first=[x for x in FIRST if x in eff]
    pre=[x for x in PRE_GEO if x in eff]
    ui_b="UI_Before" in eff; ui_a="UI_After" in eff
    # everything after UI_After stays there only if it is geometry/blur; colour effects move inside the guarded chain
    if ui_a:
        i=eff.index("UI_After"); after=eff[i+1:]; before=eff[:i]
    else: after=[]; before=eff
    post=[x for x in after if x in POST_GEO]; moved=[x for x in after if x not in POST_GEO]
    body=[x for x in before if x not in first+pre+["UI_Before","UI_After"]]+moved
    new=first+(["UI_Before"] if ui_b else [])+pre+["LightGuard_Before"]+body+["LightGuard_After"]+(["UI_After"] if ui_a else [])+post
    rest=[x for x in S if x not in new]
    sorting=new+rest
    t=re.sub(r"^Techniques=.*$","Techniques="+",".join(new),t,flags=re.M)
    if m: t=re.sub(r"^TechniqueSorting=.*$","TechniqueSorting="+",".join(sorting),t,flags=re.M)
    else: t=t.replace("Techniques="+",".join(new),"Techniques="+",".join(new)+"\nTechniqueSorting="+",".join(sorting),1)
    t=t.rstrip("\n")+"\n\n"+GUARD
    if "FXAA" in new:
        if "[FXAA.fx]" in t:
            t=re.sub(r"(\[FXAA\.fx\][^\[]*?)Subpix=[0-9.]+",r"\1Subpix=0.000000",t,flags=re.S)
        else: t=t.rstrip("\n")+"\n\n"+FXAA
    t=t.rstrip("\n")+"\n"
    if crlf: t=t.replace("\n","\r\n")
    open(OUT+f,"wb").write(t.encode("utf-8"))
    rep.append((f,[x for x in eff if x not in new],moved,pre))
    print(f"{f}: {','.join(new)}")
