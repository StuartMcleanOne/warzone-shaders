src=open('build2.py').read()
head=src[:src.index("# ------------------------------------------------------------------ grades")]
head=head.replace('OUT = "/mnt/user-data/outputs/batch2"','OUT = "/mnt/user-data/outputs/batch10"')
exec(head)
def sstep(a,b,x): t=np.clip((x-a)/(b-a),0,1); return t*t*(3-2*t)
def grid(path):
    I=np.asarray(Image.open(path).convert("RGB")).astype(float)/255; n=32; g=np.zeros((n,n,n,3))
    for bi in range(n): g[:,:,bi,:]=I[:,bi*n:(bi+1)*n,:].transpose(1,0,2)
    return g
def fire(lit,c,amt):
    hsv=rgb2hsv(c); wm=hue_mask(hsv,30,50)*np.clip((hsv[...,2:3]-0.35)/0.3,0,1)*amt
    return lit*(1-wm)+c*wm
def lamp(lit,c,gain=1.06,amt=0.95):
    # narrow gate: only really bright, nearly colourless pixels (lamp cores). Mid/light greys and sky are untouched.
    hsv=rgb2hsv(c); l=luma(c); s=hsv[...,1:2]
    w=sstep(0.80,0.93,l)*(1-np.clip((s-0.22)*2.0,0,1))
    return lit*(1-amt*w)+np.clip(c*gain,0,1)*amt*w
# Midnight = v4 look + narrow lamp gate
OLD=grid("/mnt/user-data/outputs/batch6/Textures/AI_12_TiberiumNight_lut.png")
def g_mid(c):
    old=OLD; hsv=rgb2hsv(c); l_in=luma(c); s_in=hsv[...,1:2]
    lit=old*(1-0.07*(1-sstep(0.45,0.9,l_in)))
    l=luma(lit); lit=lit+(1-l)**1.5*np.array([-0.01,0.006,0.05])
    white=sstep(0.58,0.82,l_in)*(1-np.clip((s_in-0.15)*1.6,0,1))
    lit=lit*(1-0.95*white)+np.clip(c*1.04,0,1)*0.95*white
    lit=lamp(lit,c,1.10,0.95)
    lit=fire(lit,c,0.75)
    emis=np.clip(hue_mask(hsv,125,55)+hue_mask(hsv,195,45),0,1)
    lit=lit*(1-0.85*emis)+old*0.85*emis
    return np.clip(lit,0,1)
make_lut("AI_19_TiberiumMidnight_lut.png",g_mid)
U="/mnt/user-data/uploads/reshade-shaders/Textures/"
for n,amt in [("AI_11_IonStorm",0.75),("AI_13_ScorchedEarth",0.75),("AI_14_ChromeAndRain",0.75),("AI_15_Kodachrome99",0.75),("AI_16_Firestorm",0.75),("AI_17_NodPropaganda",0.5),("AI_18_GDITacticalFeed",0.75)]:
    base=grid(U+n+"_lut.png")
    make_lut(n+"_lut.png",lambda c,b=base,a=amt: lamp(fire(b,c,a),c,1.06,0.9))
print(errors)
