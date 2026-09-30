import re,os,sys
def find_techniques(src):
    """yield (name, name_start, name_end, ann_start, ann_end) ; ann_* None if no <...>"""
    out=[]
    for m in re.finditer(r'(?m)^[ \t]*technique[ \t]+(\w+)',src):
        i=m.end()
        # skip ws & comments
        j=i
        while True:
            k=j
            while k<len(src) and src[k] in ' \t\r\n': k+=1
            if src.startswith('//',k):
                k=src.find('\n',k); k=len(src) if k<0 else k
                j=k; continue
            if src.startswith('/*',k):
                e=src.find('*/',k); j=e+2; continue
            j=k; break
        if j<len(src) and src[j]=='<':
            # scan to matching '>' outside strings
            k=j+1; instr=False
            while k<len(src):
                c=src[k]
                if instr:
                    if c=='\\': k+=1
                    elif c=='"': instr=False
                else:
                    if c=='"': instr=True
                    elif c=='>': break
                k+=1
            out.append((m.group(1),m.start(1),m.end(1),j,k+1))
        else:
            out.append((m.group(1),m.start(1),m.end(1),None,None))
    return out
if __name__=='__main__':
    root='/mnt/user-data/outputs/shaders_orig'
    n=0
    for dp,_,fs in os.walk(root):
        for f in sorted(fs):
            p=os.path.join(dp,f); s=open(p,encoding='latin-1').read()
            for name,a,b,c,d in find_techniques(s):
                n+=1
                ann=s[c:d].replace('\n',' ')[:150] if c else '-'
                print(f"{os.path.relpath(p,root)} | {name} | {ann}")
    print(n)
