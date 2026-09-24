# -*- coding: utf-8 -*-
"""Replay recorded canvas calls into PIL with the real faces. Glow, rotated round rects,
round caps and dashes supported. Also measures every text box for overlap/edge checks."""
import json, math, re, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
FD="/mnt/skills/examples/canvas-design/canvas-fonts/"
FACE={"BS":FD+"BigShoulders-Bold.ttf","GM":FD+"GeistMono-Regular.ttf","IS":FD+"InstrumentSans-Regular.ttf"}
def hsh(n):
    x=math.sin(n*127.1+311.7)*43758.5453; return x-math.floor(x)
_f={}
def field(W,H,K):
    key=(W,H,K)
    if key in _f: return _f[key].copy()
    F0,F1=(13,24,27),(26,44,49); w,h=int(W*K),int(H*K)
    im=Image.new("RGB",(w,h)); px=im.load()
    for y in range(h):
        g=y/h; v=1-0.10*g*g
        r,gg,b=[(a*(1-g)+bb*g)*v for a,bb in zip(F0,F1)]
        for x in range(w):
            n=(hsh((y//K)*W+(x//K))-0.5)*7
            px[x,y]=(int(r+n),int(gg+n),int(b+n))
    _f[key]=im; return im.copy()
def col(s,ga=1.0):
    m=re.match(r'rgba?\((\d+),(\d+),(\d+)(?:,([\d.]+))?\)',(s or "").replace(" ",""))
    if not m: return (200,200,200,int(255*ga))
    a=float(m.group(4) or 1); return (int(m.group(1)),int(m.group(2)),int(m.group(3)),max(0,min(255,int(255*a*ga))))
def font(f,K):
    m=re.search(r"(\d+(?:\.\d+)?)px\s+'?(\w+)'?",f or "")
    size=float(m.group(1)) if m else 10; fam=m.group(2) if m else "GM"
    return ImageFont.truetype(FACE.get(fam,FACE["GM"]),max(6,int(round(size*K)))),size
def dashed(dr,pts,c,w,dash,K):
    if not dash: dr.line(pts,fill=c,width=w,joint="curve"); return
    pat=[d*K for d in dash]; idx=0; left=pat[0]; on=True
    for (x0,y0),(x1,y1) in zip(pts,pts[1:]):
        L=math.hypot(x1-x0,y1-y0); pos=0
        while pos<L:
            step=min(left,L-pos); t0,t1=pos/L,(pos+step)/L
            if on: dr.line([(x0+(x1-x0)*t0,y0+(y1-y0)*t0),(x0+(x1-x0)*t1,y0+(y1-y0)*t1)],fill=c,width=w)
            pos+=step; left-=step
            if left<=1e-6: idx=(idx+1)%len(pat); left=pat[idx]; on=not on
def rr(base,seg,c,fillit,lw,K):
    w,h,rad,rot=seg["w"]*K,seg["h"]*K,(seg.get("rad") or 0)*K,seg.get("rot",0)
    if w<0: seg=dict(seg,x=seg["x"]+seg["w"]); w=-w
    if h<0: seg=dict(seg,y=seg["y"]+seg["h"]); h=-h
    L=int(math.hypot(w,h))+int(lw)+12
    lay=Image.new("RGBA",(2*L,2*L),(0,0,0,0)); ld=ImageDraw.Draw(lay)
    ld.rounded_rectangle([L,L,L+w,L+h],radius=min(rad,w/2,h/2),fill=c if fillit else None,outline=None if fillit else c,width=max(1,int(lw)))
    if abs(rot)>1e-4: lay=lay.rotate(-math.degrees(rot),center=(L,L),resample=Image.BICUBIC)
    base.alpha_composite(lay,(int(seg["x"]*K-L),int(seg["y"]*K-L)))
def draw(base,c,K,boxes=None):
    dr=ImageDraw.Draw(base,"RGBA"); op=c["op"]
    if op in("st","fi"):
        cc=col(c.get("ss") or c.get("fs"),c["ga"]); lw=max(1,int(round(c.get("lw",1)*K))); pts=[]
        for s in c["p"]:
            k=s["k"]
            if k in("m","l"): pts.append((s["x"]*K,s["y"]*K))
            elif k=="a":
                bb=[(s["x"]-s["r"])*K,(s["y"]-s["r"])*K,(s["x"]+s["r"])*K,(s["y"]+s["r"])*K]
                a0,a1=s["a0"]+s.get("rot",0),s["a1"]+s.get("rot",0)
                if abs(s["a1"]-s["a0"])>=6.28:
                    dr.ellipse(bb,fill=cc) if op=="fi" else dr.ellipse(bb,outline=cc,width=lw)
                else:
                    if s.get("ccw"): a0,a1=a1,a0
                    if op=="fi": dr.pieslice(bb,math.degrees(a0),math.degrees(a1),fill=cc)
                    else: dr.arc(bb,math.degrees(a0),math.degrees(a1),fill=cc,width=lw)
            elif k=="e":
                bb=[(s["x"]-s["rx"])*K,(s["y"]-s["ry"])*K,(s["x"]+s["rx"])*K,(s["y"]+s["ry"])*K]
                dr.ellipse(bb,fill=cc) if op=="fi" else dr.ellipse(bb,outline=cc,width=lw)
            elif k=="rr": rr(base,s,cc,op=="fi",lw,K)
        if len(pts)>=2:
            if op=="fi" and len(pts)>=3: dr.polygon(pts,fill=cc)
            else:
                dashed(dr,pts,cc,lw,c.get("dash"),K)
                if not c.get("dash") and (c.get("cap")=="round" or lw>=5*K*0.9):
                    r=lw/2
                    for p in (pts[0],pts[-1]): dr.ellipse([p[0]-r,p[1]-r,p[0]+r,p[1]+r],fill=cc)
    elif op=="fr": dr.rectangle([c["x"]*K,c["y"]*K,(c["x"]+c["w"])*K,(c["y"]+c["h"])*K],fill=col(c["fs"],c["ga"]))
    elif op=="sr": dr.rectangle([c["x"]*K,c["y"]*K,(c["x"]+c["w"])*K,(c["y"]+c["h"])*K],outline=col(c["ss"],c["ga"]),width=max(1,int(c["lw"]*K)))
    elif op=="tx":
        f,size=font(c["f"],K); w=dr.textlength(c["t"],font=f); x,y=c["x"]*K,c["y"]*K
        if c["al"] in("center",): x-=w/2
        elif c["al"] in("right","end"): x-=w
        asc=size*K*0.80
        if c.get("bl")=="middle": y+=size*K*0.35
        if c.get("stroke"):
            cc=col(c["fs"],c["ga"]); dr.text((x,y-asc),c["t"],font=f,fill=cc,stroke_width=max(1,int(c.get("sw",4)*K/2)),stroke_fill=cc); return
        dr.text((x,y-asc),c["t"],font=f,fill=col(c["fs"],c["ga"]))
        if boxes is not None: boxes.append((x/K,(y-asc)/K,(x+w)/K,(y-asc+size*K)/K,c["t"]))
PILLS=[]
def render(job,K=2):
    im=field(job["W"],job["H"],K).convert("RGBA"); boxes=[]
    PILLS.clear()
    for c in job["log"]:                     # the drag hint pill: a 22-high round rect
        for sg in c.get("p",[]) or []:
            if sg.get("k")=="rr" and abs(sg.get("h",0)-22)<0.01 and abs((sg.get("rad") or 0)-11)<0.01:
                PILLS.append((sg["x"],sg["y"],sg["x"]+sg["w"],sg["y"]+sg["h"]))
    for c in job["log"]:
        if c["op"]=="field": continue
        s=c.get("sh")
        if s and s.get("b",0)>0:
            lay=Image.new("RGBA",im.size,(0,0,0,0)); draw(lay,c,K)
            im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(radius=max(2,s["b"]*K*0.55))))
        draw(im,c,K,boxes)
    return im.convert("RGB"),boxes
def join_letters(boxes):
    """letterspaced strings arrive one glyph per call - merge touching glyph boxes on one baseline"""
    out=[]
    for b in boxes:
        if out and abs(out[-1][1]-b[1])<0.5 and 0<=b[0]-out[-1][2]<4 and len(b[4])==1:
            p=out[-1]; out[-1]=(p[0],p[1],b[2],max(p[3],b[3]),p[4]+b[4])
        else: out.append(b)
    return out
if __name__=="__main__":
    jobs=json.load(open(sys.argv[1])); pre=sys.argv[2]
    for j in jobs:
        im,boxes=render(j); im.save(f"{pre}-{j['name']}.png")
        bx=join_letters(boxes); bad=[]
        for i in range(len(bx)):
            a=bx[i]
            if a[0]<2 or a[2]>j["W"]-2: bad.append(("EDGE",a[4][:18],round(a[0]),round(a[2])))
            for (px0,py0,px1,py1) in set(PILLS):
                inside=a[0]>=px0-1 and a[2]<=px1+1 and a[1]>=py0-1 and a[3]<=py1+1
                ix=min(a[2],px1)-max(a[0],px0); iy=min(a[3],py1)-max(a[1],py0)
                if not inside and ix>0 and iy>0: bad.append(("PILL",a[4][:16],round(ix)))
            for k in range(i+1,len(bx)):
                b=bx[k]; ix=min(a[2],b[2])-max(a[0],b[0]); iy=min(a[3],b[3])-max(a[1],b[1])
                if ix>2 and iy>2: bad.append(("OVERLAP",a[4][:14],b[4][:14]))
        print(j["name"],"| label:",j["label"][:70],"|",bad if bad else "text clean")
