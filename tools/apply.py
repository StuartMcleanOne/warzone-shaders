import os,re,shutil,sys
sys.path.insert(0,'/tmp/w')
import labels,parse
SRC='/mnt/user-data/outputs/shaders_orig'; DST='/mnt/user-data/outputs/shaders_new'
def split_stmts(body):
    out=[];cur='';instr=False;i=0
    while i<len(body):
        c=body[i]; cur+=c
        if instr:
            if c=='\\': i+=1; cur+=body[i]
            elif c=='"': instr=False
        else:
            if c=='"': instr=True
            elif c==';': out.append(cur); cur=''
        i+=1
    if cur.strip(): out.append(cur)
    return out
def q(s): return '"'+s.replace('\\','\\\\').replace('"',"'").replace('\n','\\n')+'"'
def esc_tip(s): # keep intended \n escapes
    return '"'+s.replace('"',"'").replace('\n','\\n')+'"'
report=[]
shutil.rmtree(DST,ignore_errors=True)
for dp,_,fs in os.walk(SRC):
    for f in fs:
        p=os.path.join(dp,f); rel=os.path.relpath(p,SRC)
        raw=open(p,'rb').read(); s=raw.decode('latin-1')
        techs=parse.find_techniques(s)
        edits=[]
        for name,ns,ne,c,d in techs:
            st,label,tip=labels.D[name]
            full=f"{st}_ {label}"
            orig_tip=None; others=[]
            if c is not None:
                body=s[c+1:d-1]
                for stmt in split_stmts(body):
                    m=re.match(r'\s*(\w+)\s*=\s*(.*?);\s*$',stmt,re.S)
                    if m and m.group(1)=='ui_label': continue
                    if m and m.group(1)=='ui_tooltip': orig_tip=m.group(2).strip(); continue
                    if stmt.strip(): others.append(stmt.strip())
            tiplit=esc_tip(tip)
            if orig_tip:
                assert orig_tip.startswith('"'), (rel,name,orig_tip[:30])
                tiplit=esc_tip(tip+"\n\n--- Original notes ---\n")+' '+orig_tip
            ann=f"< ui_label = {q(full)}; ui_tooltip = {tiplit}; "+' '.join(others)+(' ' if others else '')+">"
            if c is None:
                edits.append((ne,ne,' '+ann))
            else:
                edits.append((c,d,ann))
        for a,b,t in sorted(edits,reverse=True): s=s[:a]+t+s[b:]
        # CinematicDOF fix: original has a second annotation list inside #if after the name, which is a syntax error once ours is added
        if f=='CinematicDOF.fx':
            pat=re.compile(r'(technique\s+CinematicDOF\s*<[^\n]*?)(";\s*>)(\s*\n#if __RESHADE__ >= 40000\s*\n\s*<.*?>\s*\n#endif)',re.S)
            assert pat.search(s),'CinematicDOF pattern'
            s=pat.sub(lambda m:m.group(1)+"\\n\\nCinematic DOF by Frans 'Otis_Inf' Bouma, part of OtisFX. https://fransbouma.com"+m.group(2),s)
        out=os.path.join(DST,rel); os.makedirs(os.path.dirname(out),exist_ok=True)
        open(out,'wb').write(s.encode('latin-1'))
        report.append((rel,len(techs)))
print(len(report),sum(n for _,n in report))
