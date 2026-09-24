# -*- coding: utf-8 -*-
"""Turn a built page into QtWebKit-runnable harness pages (wkhtmltoimage).
Harness-only down-levelling; the shipped file is never touched."""
import re, subprocess, sys, os
def downlevel(js):
    js = js.replace("(OD/2)**2", "Math.pow(OD/2,2)")
    assert "**" not in js, "unhandled ** operator"
    js = re.sub(r'([\w$.]+)\?\?([\w$.]+)', r'(((\1)!=null)?(\1):\2)', js)
    assert "??" not in js, "unhandled ?? operator"
    js = re.sub(r'\{\s*\.\.\.(\w+)\s*\}', r'Object.assign({},\1)', js)
    out, i = [], 0
    while True:
        j = js.find('[...', i)
        if j < 0: out.append(js[i:]); break
        out.append(js[i:j]); k, d = j + 4, 1
        while d:
            d += {'[': 1, ']': -1}.get(js[k], 0); k += 1
        out.append('__arr(' + js[j+4:k-1] + ')'); i = k
    js = ''.join(out)
    js = re.sub(r'([\w$]+(?:\.[\w$]+)*)\(\.\.\.', r'\1.apply(null,', js)      # f(...xs) -> f.apply(null,xs)
    assert '...' not in re.sub(r'"[^"\n]*"|\'[^\'\n]*\'|`[^`]*`', '', js), "unhandled spread"
    return js
def make(src_html, hook="", phone_height_fix=True):
    s = open(src_html).read()
    m = re.search(r'<script>([\s\S]*?)</script>', s)
    js = downlevel(m.group(1))
    if phone_height_fix:
        js = js.replace("'min(58vh,'+(KH[c.pic]||470)+'px)'", "(KH[c.pic]||470)+'px'")
        js = js.replace("'min(58vh,'+kh+'px)'", "kh+'px'")
    boot = re.search(r"if\(document\.fonts&&document\.fonts\.ready\) document\.fonts\.ready\.then\((\w+)\); else \w+\(\);\s*$", js)
    assert boot, "boot line not found"
    js = js[:boot.start()] + "setTimeout(function(){ %s(); %s },700);\n" % (boot.group(1), hook)
    helper = "function __arr(a){var r=[];for(var i=0;i<a.length;i++)r.push(a[i]);return r;}\n"
    js = "(function(){\n" + helper + js + "\n})();"
    js = js.replace("function entry(i){", "window.__entry=function(i){return entry(i);};\nfunction entry(i){", 1)
    return s[:m.start(1)] + js + s[m.end(1):]
def shoot(html_text, out_png, width, height=None, delay=1700, name='h'):
    p = f'/tmp/{name}.html'; open(p, 'w').write(html_text)
    cmd = ['wkhtmltoimage', '--width', str(width), '--javascript-delay', str(delay), '--quality', '88', '--debug-javascript']
    if height: cmd += ['--height', str(height)]
    r = subprocess.run(cmd + [p, out_png], capture_output=True, text=True)
    errs = [l for l in (r.stdout + r.stderr).splitlines() if ('Error' in l or 'error' in l) and 'viewport' not in l]
    return errs
if __name__ == '__main__':
    src = sys.argv[1]
    base = make(src, hook="")
    print("harness ok", len(base))
