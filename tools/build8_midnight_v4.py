src=open('build2.py').read()
head=src[:src.index("# ------------------------------------------------------------------ grades")]
head=head.replace('OUT = "/mnt/user-data/outputs/batch2"','OUT = "/mnt/user-data/outputs/batch8"')
exec(head)
# Midnight LUT = the original Tiberian Night grade, taken one step colder and a little darker, with white lights and fire protected.
OLD=np.asarray(Image.open("/mnt/user-data/outputs/batch6/Textures/AI_12_TiberiumNight_lut.png").convert("RGB")).astype(float)/255
def sstep(a,b,x): t=np.clip((x-a)/(b-a),0,1); return t*t*(3-2*t)
def g_mid(c):
    n=32; old=np.zeros_like(c)
    for bi in range(n): old[:,:,bi,:]=OLD[:,bi*n:(bi+1)*n,:].transpose(1,0,2)
    hsv=rgb2hsv(c); l_in=luma(c); s_in=hsv[...,1:2]
    lit=old*(1-0.07*(1-sstep(0.45,0.9,l_in)))                     # a touch darker in the shadows and mids, not in the highlights
    l=luma(lit)
    lit=lit+(1-l)**1.5*np.array([-0.01,0.006,0.05])              # colder shadows and mids
    lit=sat(lit,1.0)
    white=sstep(0.58,0.82,l_in)*(1-np.clip((s_in-0.15)*1.6,0,1))          # near-white, low colour: headlights, lamps, muzzle flash core
    lit=lit*(1-0.95*white)+np.clip(c*1.04,0,1)*0.95*white
    wm=hue_mask(hsv,30,50)*np.clip((hsv[...,2:3]-0.35)/0.3,0,1)*0.75  # bright warm colours: fire and explosions
    lit=lit*(1-wm)+np.clip(c,0,1)*wm
    emis=np.clip(hue_mask(hsv,125,55)+hue_mask(hsv,195,45),0,1)   # tiberium keeps exactly its Night look
    lit=lit*(1-0.85*emis)+old*0.85*emis
    return np.clip(lit,0,1)
make_lut("AI_19_TiberiumMidnight_lut.png",g_mid)
UIS={"CnCUIskip.fx":{"Isolate_UI":True}}
DB={"Deband.fx":{"threshold_preset":1,"range":16.0,"iterations":1}}
FX={"FXAA.fx":{"EdgeThreshold":0.25,"EdgeThresholdMin":0.0625,"Subpix":0.0}}
LV={"LevelsPlus.fx":{"EnableLevels":1,"InputBlackPoint":(0.04,0.045,0.05),"InputWhitePoint":(0.93,0.92,0.90),"InputGamma":(1.0,1.0,1.0)}}
CU={"Curves.fx":{"Mode":0,"Formula":4,"Contrast":0.35}}
VB={"Vibrance.fx":{"Vibrance":0.15,"VibranceRGBBalance":(1.0,1.0,1.0)}}
HD={"FakeHDR.fx":{"HDRPower":1.15,"radius1":0.793,"radius2":0.87}}
RB={"ReflectiveBumpMapping.fx":{"fRBM_ReliefHeight":0.2,"fRBM_FresnelMult":0.5,"fRBM_FresnelReflectance":0.3,"fRBM_LowerThreshold":0.1,"fRBM_UpperThreshold":0.2,"fRBM_BlurWidthPixels":100.0,"iRBM_SampleCount":32}}
AL={"AmbientLight.fx":{"alInt":7.0,"alThreshold":12.0,"alAdapt":0.7,"AL_Dirt":1,"AL_DirtTex":0,"AL_Lens":0,"AL_Adaptation":1,"AL_Adaptive":0,"AL_Vibrance":0,"alDebug":0}}
LT={"LUT.fx":{"fLUT_AmountChroma":1.0,"fLUT_AmountLuma":1.0}}
MB={"MagicBloom.fx":{"fBloom_Intensity":3.6,"fBloom_Threshold":3.5,"fDirt_Intensity":0.15,"fExposure":0.45,"fAdapt_Speed":0.2,"fAdapt_Sensitivity":0.6}}
PB={"PD80_02_Bloom.fx":{"BloomMix":0.55,"BloomLimit":0.4,"GreyValue":0.3,"bExposure":0.3,"BlurSigma":12.0,"BloomSaturation":1.5,"enableBKelvin":1,"BKelvin":5200,"dither_strength":2.0}}
LS={"LumaSharpen.fx":{"sharp_strength":0.6,"sharp_clamp":0.035,"pattern":1,"offset_bias":1.0}}
VG={"Vignette.fx":{"Type":0,"Ratio":1.0,"Radius":1.35,"Amount":-0.7,"Slope":4,"Center":PF_CENTER}}
FG={"FilmGrain.fx":{"Intensity":0.22,"Variance":0.45,"Mean":0.5,"SignalToNoiseRatio":4}}
def merge(*ds):
    o={}
    for d in ds:
        for k,v in d.items(): o.setdefault(k,{}).update(v)
    return o
chain=["UI_Before","Deband","FXAA","LevelsPlus","LUT","Curves","Vibrance","HDR","ReflectiveBumpmapping","AmbientLight","MagicBloom","prod80_02_Bloom","LumaSharpen","Vignette","FilmGrain","UI_After"]
emit("/mnt/user-data/outputs/batch8/Custom/AI_19_TiberiumMidnight.ini",chain,merge(UIS,DB,FX,LV,LT,CU,VB,HD,RB,AL,MB,PB,LS,VG,FG),'fLUT_TextureName="AI_19_TiberiumMidnight_lut.png"')
print("errors",errors)
