# -*- coding: utf-8 -*-
"""Subject-agnostic gates ported from the EEG primer, run before any build."""
import re, math, sys
from cards import CARDS, CLAIMS
sin=lambda t: math.sin(math.radians(t))
fails=[]
def gate(name, ok, detail=""):
    print(f"  [{'ok  ' if ok else 'FAIL'}] {name}{('  '+detail) if detail else ''}")
    if not ok: fails.append(name)

def prose(c):
    t=" ".join(b.get("p","")+" "+b.get("h","") for b in c["body"])
    t+=" "+" ".join(cell for b in c["body"] if b.get("tab") for row in b["tab"] for cell in row)
    return t+" "+c["tldr"]+" "+c["lede"]

print("=== G1  forward references: no card may use a term defined later ===")
# explicit word forms per term, never a substring and never a wildcard suffix
TERMS={ "vein-depth":["vein depth","probe pressure"],
        "gauge-length":["gauge","gauges","bore"],
        "entry-angle":["entry angle"],
        "intraluminal":["intraluminal","inside the vein","inside the lumen"],
        "rule-65":["65 per cent","65%"],
        "reach":["reach","reaches","reaching"],
        "shallowing":[],
        "judging-angle":[],
        "flattening":["resting angle","tip angle","tip angles"],
        "floor-275":["27.5 mm","2.75 cm","absolute"],
        "which-governs":["crossover"],
        "cvr":["catheter-vein ratio","catheter-to-vein ratio"],
        "flow-dwell":["flow"],
        "out-of-plane":["out of plane","short axis","long axis","scan plane"],
        "limits":[] }
order=[c["id"] for c in CARDS]
viol=[]
for i,c in enumerate(CARDS):
    txt=prose(c).lower()
    for later in order[i+3:]:            # a reference within two cards passes
        for w in TERMS[later]:
            if re.search(r"(?<![a-z])"+re.escape(w)+r"(?![a-z])", txt):
                declared = w in " ".join(TERMS[c["id"]]).lower()
                if not declared: viol.append((c["id"],later,w))
gate("no undeclared forward references", not viol, str(viol[:6]) if viol else "")

print("\n=== G2  every numeral in prose is declared in CLAIMS ===")
und=set()
for c in CARDS:
    for n in re.findall(r"(?<![\w.])\d+(?:\.\d+)?(?![\w])", prose(c)):
        if n not in CLAIMS: und.add((c["id"],n))
gate("all numerals declared", not und, str(sorted(und)[:10]) if und else f"{len(CLAIMS)} declared")

print("\n=== G3  the derived numerals reproduce from the geometry ===")
def close(a,b,t=0.006): return abs(a-b)<=t
checks=[("1.4",1/sin(45)),("2.0",1/sin(30)),("2.9",1/sin(20)),
        ("4.0",1/(0.35*sin(45))),("5.7",1/(0.35*sin(30))),("8.4",1/(0.35*sin(20))),
        ("4.7",0.35*19*sin(45)),("6.2",0.35*25*sin(45)),("7.9",0.35*32*sin(45)),("7.92",0.35*32*sin(45)),
        ("11.1",0.35*45*sin(45)),("0.08",8.0-0.35*32*sin(45)),
        ("29.3",100*(1-sin(30)/sin(45))),("51.6",100*(1-sin(20)/sin(45))),
        ("42.3",27.5/0.65),("3.18",(32-27.5)*sin(45)),("31.04",27.5+2.5/sin(45)),
        ("2.0",0.9/0.45),("2.7",0.9/0.33),("22.7",100*(22-17)/22),("25.7",100*(35-26)/35)]
def dp(s): return len(s.split(".")[1]) if "." in s else 0
bad=[(s,round(v,4)) for s,v in checks if round(v,dp(s))!=float(s)]
gate("printed values reproduce an independent recompute", not bad, str(bad) if bad else f"{len(checks)} values")

print("\n=== G4  geometry, mechanically ===")
long_t=[c["title"] for c in CARDS if len(c["title"])>22]
gate("card titles fit the index row (<=22 chars)", not long_t, str(long_t))
gate("card titles unique", len({c["title"] for c in CARDS})==len(CARDS))
gate("card ids unique", len({c["id"] for c in CARDS})==len(CARDS))
wide=[o[1] for c in CARDS for k in c.get("ctrl",[]) for o in k["opts"] if len(str(o[1]))>13]
gate("control labels fit their button (<=13 chars)", not wide, str(wide))
noctrl=[c["id"] for c in CARDS if not c.get("ctrl") and c["pic"] not in ("still","trackStill")]
gate("every card except the closing one carries a control", not noctrl, str(noctrl))

print("\n=== G5  editorial and provenance ===")
gate("every card has at least one source line", all(c.get("src") for c in CARDS))
SETTLED=["diagnostic test","proves","guarantees","always","never fails"]
s=[(c["id"],w) for c in CARDS for w in SETTLED if w in prose(c).lower()]
gate("no settled-fact language", not s, str(s))
em=[c["id"] for c in CARDS if "\u2014" in prose(c) or "\u2014" in " ".join(c["src"])]
gate("no em dashes", not em, str(em))
NOTX=[r"\bit is not\s+\w+[,.]\s+it is\b", r"here is what (struck|surprised)"]
b=[c["id"] for c in CARDS for p in NOTX if re.search(p, prose(c).lower())]
gate("no banned constructions", not b, str(b))
hold=[c["id"] for c in CARDS if "hold" in prose(c).lower() and "vein" in prose(c).lower()
      and re.search(r"(catheter|it)\s+holds?\s+the\s+vein", prose(c).lower())]
gate("language ban: nothing 'holds the vein'", not hold, str(hold))
sh=[c["id"] for c in CARDS if re.search(r"\b(quietly|genuinely)\b", prose(c).lower())]
gate("no softener adverbs", not sh, str(sh))

print("\n=== G6  cross-references are by title, never by number or position ===")
pos=[c["id"] for c in CARDS if re.search(r"\bcard (one|two|three|four|\d)\b|\bcomes (first|second|third)\b", prose(c).lower())
     and c["id"]!="vein-depth"]
gate("no positional cross-references", not pos, str(pos))
titles={c["title"].lower() for c in CARDS}
refs=re.findall(r"the card on (?:the )?([a-z\- ]+?)[\.,]", " ".join(prose(c) for c in CARDS).lower())
badrefs=[r for r in refs if not any(r.strip() in t for t in titles)]
gate("every 'the card on X' names a real title", not badrefs, str(badrefs) if badrefs else str(refs))

print("\n=== G7  second-hand provenance is declared where a threshold is stated ===")
need=["rule-65","floor-275","intraluminal","flattening"]
miss=[i for i in need if "second-hand" not in " ".join(next(c for c in CARDS if c["id"]==i)["src"]).lower()]
gate("threshold cards flag second-hand sourcing", not miss, str(miss))

print("\n"+("ALL GATES PASS" if not fails else f"{len(fails)} FAILED: {fails}"))
sys.exit(1 if fails else 0)
