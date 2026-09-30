import numpy as np
def ss(a,b,x): t=np.clip((x-a)/(b-a),0,1); return t*t*(3-2*t)
def luma(c): return c@np.array([.2126,.7152,.0722])
def guard(orig,cur,FS=.9,FB=.08,LS=1.,LB=.3,R=3.):
    H,W,_=orig.shape; mx=orig.max(-1); mn=orig.min(-1); sat=(mx-mn)/np.maximum(mx,1e-4); lo=luma(orig)
    L=luma(orig); d=int(round(R)); e=int(round(R*.7071)); ring=0
    for dx,dy in [(d,0),(-d,0),(0,d),(0,-d),(e,e),(-e,e),(e,-e),(-e,-e)]:
        ring=ring+np.roll(np.roll(L,dy,0),dx,1)
    ring/=8; peak=np.clip((lo-ring-.12)/.25,0,1)
    lamp=peak*ss(.5,.8,lo)*(1-ss(.3,.55,sat))
    r,g,b=orig[...,0],orig[...,1],orig[...,2]
    warm=(g<=r+.01)*(b<=g+.01)*np.clip((r-b)*6,0,1)
    fb=ss(.86,.97,mx)*ss(.28,.5,sat); fe=peak*ss(.45,.7,mx)*ss(.4,.6,sat)
    fire=warm*np.maximum(fb,fe)
    lc=luma(cur)
    fT=np.clip(orig*(1+FB),0,1); fT=np.clip(fT*np.clip(lc/np.maximum(luma(fT),.05),1,1.6)[...,None],0,1)
    res=cur+(fT-cur)*(fire*FS)[...,None]
    lT=np.clip(orig+(1-orig)*LB,0,1); lT=np.clip(lT*np.clip(lc/np.maximum(luma(lT),.05),1,1.4)[...,None],0,1)
    res=res+(lT-res)*(lamp*LS)[...,None]
    return res,lamp,fire
H,W=60,80
o=np.full((H,W,3),.12); o[:,:,2]=.16               # dark ground
sand=np.array([.8,.66,.42]); o[:,:20]=sand           # sand patch
o[:,20:30]=np.array([.9,.9,.92])                     # big white wall
o[10:12,40:42]=[1,1,.95]                             # 2px headlight
o[30,50]=[.95,.95,1]                                 # 1px light
yy,xx=np.mgrid[:H,:W]; fb=((yy-40)**2+(xx-62)**2)<64 # fireball r8
o[fb]=[1,.55,.1]; o[((yy-40)**2+(xx-62)**2)<16]=[1,.9,.5]
# dulled grade: multiply .6 and cool
cur=np.clip(o*np.array([.55,.6,.7]),0,1)
res,lamp,fire=guard(o,cur)
def show(n,y,x): print(f"{n:10s} orig {np.round(o[y,x],2)} graded {np.round(cur[y,x],2)} -> {np.round(res[y,x],2)}  lamp={lamp[y,x]:.2f} fire={fire[y,x]:.2f}")
show("sand",30,10); show("wall",30,25); show("headlight",10,40); show("1px light",30,50); show("fire edge",40,68); show("fire core",40,62); show("ground",30,35)
