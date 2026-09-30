import html,re,sys,configparser
sys.path.insert(0,'/tmp/w'); sys.path.insert(0,'.')
import labels; from content import *
esc=html.escape
COL={'1':'#7fd8ff','2':'#5cf28a','3':'#ffc35c','4':'#b7a6ff','5':'#ff9ec4'}
NAME={'1':'Clean-up','2':'Colour','3':'Light','4':'Detail','5':'Finish'}
pages=[]; 
def foot(n,t=''): return f'<div class="pf"><span>Warzone Shader Guide</span><span>{esc(t)}</span><span class="pn">{n}</span></div>'
def add(cls,body,style=''): pages.append(f'<section class="page {cls}" style="{style}">{body}</section>')
def entry(e,st):
    tid,name,does,tr,wa=e
    return f'<article class="e"><div class="eh"><h3><b class="pre">{st}_</b>{esc(name)}</h3><code class="tid">{esc(tid)}</code></div><dl><dt>Does</dt><dd>{esc(does)}</dd><dt>Try</dt><dd>{esc(tr)}</dd><dt>Watch</dt><dd>{esc(wa)}</dd></dl></article>'
import subprocess,json
def measure(htmls):
    r=subprocess.run(['node','measure.js'],input=json.dumps(htmls),capture_output=True,text=True)
    return json.loads(r.stdout)
CONTENT=1123-53-68-10
def pack(heights,first_used,cont_used,gap=10,lim=None):
    lim=lim or CONTENT
    pages=[[]];used=first_used
    for i,h in enumerate(heights):
        add_=h+(gap if pages[-1] else 0)
        if used+add_>lim and pages[-1]:
            pages.append([]);used=cont_used;add_=h
        pages[-1].append(i);used+=add_
    return pages
def hdr(st,cont,title=None):
    return f'<header class="sh"><div class="big">{st}</div><div><div class="kick">Stage {st} of 5{" (continued)" if cont else ""}</div><h2>{title or NAME[st]}</h2></div></header>'
def stagepage(st,intro,entries,cont=False,title=None,extra=''):
    htmls=[entry(e,st) for e in entries]
    hs=measure([hdr(st,False),f'<p class="intro">{esc(intro)}</p>',hdr(st,True)]+htmls)
    hh,ih,ch=hs[0],(hs[1] if intro else 0),hs[2];hs=hs[3:]
    first=hh+14+(ih+14 if intro else 0);cont_used=ch+14
    groups=pack(hs,first,cont_used)
    if len(groups)>1:
        n_=len(groups);tot=sum(hs)+10*len(hs)
        best=None
        # try shrinking the limit until the greedy pack would need more pages, keep the tightest that still gives n_ pages
        lim=CONTENT
        while lim>500:
            gr=pack(hs,first,cont_used,lim=lim)
            if len(gr)>n_:break
            best=gr;lim-=8
        groups=best or groups
    # balance: avoid a nearly empty last page by pulling one entry over
    if len(groups)>1 and len(groups[-1])==1 and len(groups[-2])>2:
        groups[-1].insert(0,groups[-2].pop())
    for gi,idx in enumerate(groups):
        n=len(pages)+1
        body=hdr(st,cont or gi>0,title)+(f'<p class="intro">{esc(intro)}</p>' if (intro and gi==0) else '')+'<div class="grid">'+''.join(htmls[i] for i in idx)+'</div>'+(extra if gi==len(groups)-1 else '')+foot(n,f'{st}_ {NAME[st]}')
        add('stage',body,f'--sc:{COL[st]}')
# 1 cover
crystals='''<svg class="crys" viewBox="0 0 600 520" aria-hidden="true">
<g fill="none" stroke-linejoin="round">
<polygon points="70,520 120,250 170,520" fill="#5cf28a" fill-opacity=".16" stroke="#5cf28a" stroke-width="2"/>
<polygon points="120,250 170,520 120,520" fill="#5cf28a" fill-opacity=".28"/>
<polygon points="150,520 230,120 300,520" fill="#5cf28a" fill-opacity=".20" stroke="#5cf28a" stroke-width="2"/>
<polygon points="230,120 300,520 230,520" fill="#5cf28a" fill-opacity=".34"/>
<polygon points="270,520 340,300 400,520" fill="#54bfff" fill-opacity=".18" stroke="#54bfff" stroke-width="2"/>
<polygon points="340,300 400,520 340,520" fill="#54bfff" fill-opacity=".32"/>
<polygon points="380,520 470,60 560,520" fill="#54bfff" fill-opacity=".22" stroke="#54bfff" stroke-width="2"/>
<polygon points="470,60 560,520 470,520" fill="#54bfff" fill-opacity=".38"/>
<polygon points="20,520 60,400 100,520" fill="#54bfff" fill-opacity=".2" stroke="#54bfff" stroke-width="1.5"/>
</g></svg>'''
add('cover',f'''<div class="cv-top"><span>Tiberian War: WarZone 5.7.7</span><span>ReShade 4 &middot; 800&times;600</span></div>
{crystals}
<div class="cv-title"><div class="kick">The field guide to</div><h1>Warzone<br><span>Shader</span><br>Order</h1>
<p>What every effect does, where it goes in the chain, and the values our presets actually use.</p></div>
<div class="cv-stages">{''.join(f'<div style="--sc:{COL[k]}"><b>{k}_</b>{NAME[k]}</div>' for k in '12345')}</div>''')
# 2 how it works
n=len(pages)+1
sample='''<pre class="code"><span class="c">; the top of a preset file</span>
PreprocessorDefinitions=fLUT_TextureName="AI_12_TiberiumNight_lut.png"
Techniques=UI_Before,Deband,LUT,MagicBloom,prod80_02_Bloom,LumaSharpen,Vignette,FilmGrain,UI_After
TechniqueSorting=UI_Before,Deband,LUT,MagicBloom, ...every other effect...

<span class="c">; then one block of settings per effect</span>
[MagicBloom.fx]
fBloom_Intensity=4.000000
fBloom_Threshold=3.500000</pre>'''
add('how',f'''<header class="sh" style="--sc:#5cf28a"><div class="big">?</div><div><div class="kick">Start here</div><h2>How it works</h2></div></header>
<div class="two">
<div><h3>A chain, top to bottom</h3><p>ReShade takes the finished game picture and passes it through each effect in the list, in order. The output of one is the input of the next. That is why order changes the look: sharpening before bloom sharpens noise that bloom then smears.</p>
<h3>A preset is a text file</h3><p>A preset is an <code>.ini</code> file. <code>Techniques=</code> is the list of effects that are on, in the order they run. Each effect then has its own block of settings. Effects are called techniques, and presets refer to them by technique name, so the names in this guide never change.</p></div>
<div>{sample}</div></div>
<div class="cards">
<div class="card"><h3>What Warzone gives ReShade</h3><ul><li>The picture only. The game draws through DirectDraw on OpenGL at 800&times;600.</li><li>No usable depth buffer, so effects that need depth do nothing (the X_ list).</li><li>A sidebar 168 pixels wide on the right, with a 22 pixel offset at the top.</li></ul></div>
<div class="card"><h3>Keeping the sidebar clean</h3><p><code>UI_Before</code> hides the sidebar from the effects and <code>UI_After</code> puts it back. Wrap every chain in the pair and set <code>Isolate_UI=1</code>, or the sidebar gets graded with the map.</p></div>
<div class="card"><h3>Where things live</h3><ul><li><code>reshade-shaders\\Shaders</code> holds the effects.</li><li><code>reshade-shaders\\Textures</code> holds LUT images.</li><li>Presets sit in <code>reshade-shaders</code> and in the <code>Custom</code> subfolder.</li></ul></div>
</div>{foot(n,'How it works')}''')
# 3 order + prefix key
n=len(pages)+1
rail='<div class="rail"><div class="nd ui">0_ UI_Before</div><i></i>'+'<i></i>'.join(f'<div class="nd" style="--sc:{COL[k]}"><b>{k}_</b>{NAME[k]}</div>' for k in '12345')+'<i></i><div class="nd ui">0_ UI_After</div></div>'
rows=[('1','Clean-up','Fix the raw image so later effects work on clean pixels.','Deband, anti-aliasing'),('2','Colour','Set the mood. A LUT does the whole grade in one step.','LUT, curves, vibrance, tone'),('3','Light','Glow and atmosphere. After colour, so the glow takes the graded tint.','Ambient light, one bloom, heat haze'),('4','Detail','Sharpen after bloom so the glow stays crisp.','Clarity, one sharpener'),('5','Finish','The last visible touches. Grain goes last.','Vignette, grain, scanlines')]
tbl=''.join(f'<div class="orow" style="--sc:{COL[a]}"><b>{a}_</b><h4>{b}</h4><p>{c}</p><span>{d}</span></div>' for a,b,c,d in rows)
add('order',f'''<header class="sh" style="--sc:#5cf28a"><div class="big">&rarr;</div><div><div class="kick">The one rule</div><h2>The order</h2></div></header>
<p class="intro">Every preset in this pack follows the same six steps. The prefix on each effect name in the ReShade menu says which step it belongs to, so you can place it without remembering.</p>{rail}<div class="orows">{tbl}</div>
<div class="two"><div class="card"><h3>Prefix key</h3><div class="key"><b>0_</b><span>UI wrappers, first and last</span><b>1_ to 5_</b><span>The five stages, in chain order</span><b>6_</b><span>Novelty and special-purpose effects</span><b class="x">X_</b><span>Needs depth. Does nothing in this game</span></div></div>
<div class="card good"><h3>Don't stack</h3><ul><li><b>Two main blooms.</b> They fight.</li><li><b>Two sharpeners.</b> Raise one instead.</li><li><b>Three tone curves.</b> Two is plenty.</li><li><b>Two CRTs or two anti-aliasers.</b> Pick one.</li><li><b>Flares and godrays.</b> They look wrong here.</li></ul></div></div>{foot(n,'The order')}''')
# stage pages
def tip(title,items,cls='good'):
    return f'<div class="card {cls}"><h3>{title}</h3><ul>'+''.join(f'<li>{i}</li>' for i in items)+'</ul></div>'
stagepage('1','Fix the raw image first. Clean pixels take colour and sharpening better than noisy ones.',S1,extra=tip('Clean-up in practice',['<b>Deband goes first.</b> Everything after it then works on smooth gradients.','<b>One anti-aliaser at most.</b> FXAA, SMAA or nothing. Compare by eye, because they soften fine detail.','<b>Skip Surface Blur and Denoise</b> unless a preset asks for them. They cost detail on a low-resolution game.'],'good'))
stagepage('2','Set the mood. A LUT does the whole grade in one step, so the rest is fine-tuning. Tiberium comes in green and blue, so grade both. Two tone curves is the limit.',S2a+S2b)
stagepage('3','Glow and atmosphere. Put it after colour so the glow takes the graded tint. Use one main bloom.',S3a+S3b)
stagepage('4','Sharpen after bloom so the glow stays crisp. Use one sharpener and raise it before adding another.',S4,extra=tip('A sharpening recipe that works',['<b>Luma Sharpen:</b> strength 0.35 to 0.65, clamp 0.02 to 0.035. This is what most of our presets use.','<b>Sharpen once.</b> Raise the value instead of adding a second sharpener.'],'good'))
stagepage('5','The last visible touches. Vignette, then grain, then UI After.',S5,extra=tip('The finishing touch',['<b>Vignette:</b> radius 1.1 to 1.6, centre 0.395 and 0.518, so it sits on the playfield and not the sidebar.','<b>Film Grain:</b> intensity 0.12 to 0.28. Keep it low, it goes last before UI After.','<b>UI After is always last.</b> It puts the sidebar back.'],'good'))
# skip page
n=len(pages)+1
add('skip',f'''<header class="sh" style="--sc:#ff7a6b"><div class="big">X</div><div><div class="kick">Leave these off</div><h2>Skip list</h2></div></header>
<div class="card bad"><h3><b class="pre x">X_</b>Dead in this engine</h3><p>The game gives ReShade no usable depth buffer. These effects need one, so expect little or nothing, and some cost frames.</p><dl class="lst">{''.join(f'<dt>{a}</dt><dd>{b}</dd>' for a,b in DEAD)}</dl></div>
<div class="card"><h3><b class="pre">6_</b>Novelty and special purpose</h3><p>They work, but they are not part of a normal grade. Try them for a joke or a special look.</p><div class="chips">{''.join(f'<span>{esc(x)}</span>' for x in NOVELTY)}</div></div>
<div class="card"><h3>Why some effects are marked, not removed</h3><p>The labels are display names only. The effect names that presets use are unchanged, so every preset still loads. Nothing was deleted.</p></div>{foot(n,'Skip list')}''')
# presets
def chainof(name):
    p=f'/mnt/user-data/outputs/final/Custom/{name}.ini'
    for l in open(p,encoding='utf-8',errors='ignore'):
        if l.startswith('Techniques='):
            t=[x for x in l.strip()[11:].split(',') if x not in('UI_Before','UI_After')]
            return ', '.join(labels.D[x][1] if x in labels.D else x for x in t)
def presetpage(title,kick,items,note,cont=False,extra=''):
    n=len(pages)+1
    rows=''.join(f'<div class="pr"><h4>{esc(a)}</h4><p>{esc(b)}</p><div class="ch">{esc(chainof(a))}</div></div>' for a,b in items)
    add('presets'+(' tight' if len(items)>=7 else ''),f'<header class="sh" style="--sc:#54bfff"><div class="big">P</div><div><div class="kick">{kick}</div><h2>{title}</h2></div></header><p class="intro">{note}</p><div class="prs">{rows}</div>{extra}'+foot(n,title))
presetpage('The AI presets','Presets, part one',PRESETS_AI[:6],'Eleven presets made for this pack. Chains are shown in run order between UI Before and UI After. Presets with a LUT load their own image from the Textures folder.')
presetpage('The AI presets, continued','Presets, part one',PRESETS_AI[6:],'The rest of the AI set. Same rules: UI Before first, UI After last.',extra=tip('Picking a look',['<b>Cold and night:</b> AI_11_IonStorm, AI_12_TiberiumNight, AI_14_ChromeAndRain.','<b>Warm and dusty:</b> AI_05_CrimsonSun, AI_08_GoldenHour, AI_13_ScorchedEarth, AI_15_Kodachrome99.','<b>Hot:</b> AI_16_Firestorm.','<b>Clean and light:</b> AI_01_Remaster and AI_03_TiberiumBloom.','<b>Readability first:</b> AI_18_GDITacticalFeed.'],"good"))
presetpage('The C_ presets','Presets, part two',PRESETS_C,'Improved versions of the mod default presets, kept in the Custom folder. The originals in the main folder are untouched.')
# fixes + edit
n=len(pages)+1
add('fix',f'''<header class="sh" style="--sc:#ffc35c"><div class="big">!</div><div><div class="kick">When it goes wrong</div><h2>Fixes and editing</h2></div></header>
<div class="card amber"><h3>Something looks wrong</h3><dl class="lst wide">{''.join(f'<dt>{esc(a)}</dt><dd>{esc(b)}</dd>' for a,b in FIXES)}</dl></div>
<div class="card"><h3>Editing a preset file</h3><ul><li><code>Techniques=</code> lists the effects that are on, in the order they run.</li><li><code>TechniqueSorting=</code> lists every effect in menu order. An effect that is off but sits above Deband will run there if you switch it on.</li><li>Edit the <code>.ini</code> in a text editor and reload the preset. The in-game menu freezes the game and covers most of the screen.</li><li>Copy the preset before you change it, and change one thing at a time.</li></ul></div>{foot(n,'Fixes and editing')}''')
# glossary + credits
n=len(pages)+1
add('gloss',f'''<header class="sh" style="--sc:#b7a6ff"><div class="big">A</div><div><div class="kick">Reference</div><h2>Glossary and credits</h2></div></header>
<dl class="lst wide gl">{''.join(f'<dt>{a}</dt><dd>{b}</dd>' for a,b in GLOSS)}</dl>
<div class="card"><h3>Credits</h3><p>Every effect belongs to its original author, credited in the header of its own .fx file. ReShade is by crosire. The PD80 effects are by prod80. The qUINT effects and MXAO are by Marty McFly (Pascal Gilcher). LumaSharpen, Vibrance, Curves, DPX, Technicolor and other SweetFX effects are by CeeJay.dk and contributors. Tiberian War: WarZone and its UI isolation shader come from the WarZone mod team.</p><p>The presets, LUT images and this guide are shared for the community. This pack does not include any effect files.</p></div>{foot(n,'Glossary and credits')}''')
CSS=open('guide.css').read()
body=''.join(pages)
open('guide_body.html','w').write(body)
print(len(pages),'pages')
