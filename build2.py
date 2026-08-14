import json, re, sys, subprocess
from cards import CARDS
t=open("template2.html").read()
F=json.load(open("fonts.json"))
for k in ("BS","IS","ISB","GM"):
    assert t.count(f"__F_{k}__")==1; t=t.replace(f"__F_{k}__",F[k])
assert t.count("__CARDS__")==1
out=t.replace("__CARDS__", json.dumps(CARDS,ensure_ascii=False).replace("</","<\\/"))
import re as _re
_VER=_re.search(r'const VERSION="(v\d+)"',out).group(1)
OUT=f"cannulation-geometry-{_VER}.html"
open(OUT,"w").write(out)
open(".latest","w").write(OUT)
print(f"built {len(out):,} bytes")
fails=[]
def g(n,ok,d=""):
    print(f"  [{'ok  ' if ok else 'FAIL'}] {n}{('  '+d) if d else ''}")
    if not ok: fails.append(n)
print("=== B1 self-contained ===")
ext=[u for _,u in re.findall(r'src\s*=\s*["\']([^"\']+)',out) if u.startswith(("http","//"))]
ext+=[u for u in re.findall(r'<link[^>]+href=["\']([^"\']+)',out) if u.startswith(("http","//"))]
g("no external loads (src / link)", not ext, str(ext))
g("both paper links present", "doi.org/10.1111/pan.70076" in out and "doi.org/10.1016/j.bjae.2026.05.003" in out)
import re as _re
_r=out[out.index("function picDepth"):out.index("const PICS")]
_l=_re.findall(r"\[\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\]",_r)
g("no inline colour literals in renderers", not _l, str(_l[:4]))
g("no @import","@import" not in out)
g("four embedded faces", out.count("data:font/woff;base64,")==4)
print("=== B2 JS parses ===")
js=re.search(r'<script>(.*?)</script>',out,re.S).group(1)
open("built2.js","w").write(js)
r=subprocess.run(["node","--check","built2.js"],capture_output=True,text=True)
g("node --check", r.returncode==0, r.stderr.strip()[:300])
print("=== B3 a11y floor ===")
for n,p in (("aria-pressed",r"aria-pressed"),("live region",r'aria-live="polite"'),
            ("canvas label",r"setAttribute\('aria-label'"),("role img",r"setAttribute\('role','img'\)"),
            ("focus ring",r"focus-visible"),("retina",r"devicePixelRatio"),
            ("reduced motion",r"prefers-reduced-motion"),("pointer capture",r"setPointerCapture"),
            ("touch-action none on canvas",r"touch-action:none")):
    g(n,bool(re.search(p,out)))
m=re.search(r"\.krow button\{[^}]*min-height:(\d+)px",out); g("chip targets >=44",int(m.group(1))>=44,m.group(1))
print("=== B4 attribution ===")
dec=re.sub(r"\\u([0-9a-fA-F]{4})",lambda m:chr(int(m.group(1),16)),out)
g("author",'Dr Ganesh Sivasankara' in dec)
g("credentials exact",'MD \u00b7 FRCA \u00b7 FCARCSI \u00b7 Consultant Anaesthetist' in dec)
g("no institution", not re.search(r"KFSHRC|King Faisal|Riyadh",dec,re.I))
print("=== B4b deployable head ===")
for _tag in ("apple-mobile-web-app-capable","apple-touch-icon","og:image","twitter:card","og:url"):
    g(f"head carries {_tag}", _tag in out)
print("=== B4a error pill ===")
g("masked script errors stay silent","Script error" in out and "masked=" in out)
g("attributable paint errors still report","repErr((e.message||" in out)
print("=== B5a table block ===")
g("ledger-table renderer present","b.tab" in out and "dv2" in out and "dvp" in out)
from cards import CARDS as _C
_nt=sum(1 for c in _C for bl in c["body"] if bl.get("tab"))
g("tab blocks declared where expected", _nt>=3, f"{_nt} tab blocks")
print("=== B5 renderer per pic kind ===")
kinds=sorted({c["pic"] for c in CARDS})
pi=out.split("const PICS={",1)[1].split("};",1)[0]
miss=[k for k in kinds if k+":" not in pi]
g("all kinds mapped", not miss, ",".join(kinds))
print("BUILD "+("CLEAN -> "+OUT if not fails else f"{len(fails)} FAILED: {fails}"))
sys.exit(1 if fails else 0)
