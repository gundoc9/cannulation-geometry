# -*- coding: utf-8 -*-
"""Collision census, in Chrome with the embedded faces.

For every card, every control option and the in-between positions of every drag, at sixteen
screen sizes from a 320 px phone to a 16-inch laptop: record each piece of canvas text with its
measured box, repaint with text switched off, and look at what lies under each box.

Fails on: text across a drawn line, text over other text, text outside the window or in a
clipped corner, and any script error. Labels drawn with a rim (htxt) are meant to be able to
cross a faint line; they are listed and not failed.

    python3 qa-census.py index.html            # the full run, about two minutes
    python3 qa-census.py index.html quick      # options only, no in-between drag positions
    python3 qa-census.py index.html only=ip14,se

Needs Playwright for Python and Chrome (set CHROME to the binary if Playwright has none of its own).
Viewport heights are the ones phones report for vh, which is the height with the toolbars away.
"""
import sys, json, os, asyncio, itertools, collections
from playwright.async_api import async_playwright

INIT = r"""
(() => {
  const P = CanvasRenderingContext2D.prototype, ft = P.fillText, stx = P.strokeText;
  window.__T = []; window.__noText = false; window.__rec = false;
  P.fillText = function (s, x, y) {
    if (window.__rec) {
      const m = this.measureText(s), t = this.getTransform();
      let l = x - m.actualBoundingBoxLeft, r = x + m.actualBoundingBoxRight, tp = y - m.actualBoundingBoxAscent, b = y + m.actualBoundingBoxDescent;
      const pts = [[l, tp], [r, tp], [l, b], [r, b]].map(([px, py]) => [t.a * px + t.c * py + t.e, t.b * px + t.d * py + t.f]);
      const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
      window.__T.push({ s: String(s), x0: Math.min(...xs), x1: Math.max(...xs), y0: Math.min(...ys), y1: Math.max(...ys),
        font: this.font, fill: String(this.fillStyle), halo: !!this.__halo, cv: this.canvas.__id || 0 });
    }
    this.__halo = false;
    if (!window.__noText) return ft.apply(this, arguments);
  };
  P.strokeText = function (s) { this.__halo = true; if (!window.__noText) return stx.apply(this, arguments); };
})();
"""

MEASURE = r"""
async ([id, st]) => {
  const i = CARDS.findIndex(c => c.id === id), c = CARDS[i];
  if (!window.__cur || window.__cur !== id) { entry(i); window.__cur = id; }
  Object.assign(state[id], st || {});
  const cv = document.querySelector('.win canvas');
  if (refresh) refresh();
  window.__T = []; window.__rec = true; window.__noText = false;
  const aria = paint(cv, c, state[id], false);
  window.__rec = false;
  const items = window.__T.slice();
  window.__noText = true; paint(cv, c, state[id], false); window.__noText = false;
  const W = cv.width, H = cv.height, ctx = cv.getContext('2d');
  const img = ctx.getImageData(0, 0, W, H).data;
  paint(cv, c, state[id], false);
  const dpr = W / cv.getBoundingClientRect().width;
  // merge letterspaced runs: same baseline box, same font and colour, next char starts within 3.2 css px
  const merged = [];
  for (const t of items) {
    const m = merged[merged.length - 1];
    if (m && m.font === t.font && m.fill === t.fill && Math.abs(m.y1 - t.y1) < 2.5 * dpr && t.x0 >= m.x1 - 1 && t.x0 - m.x1 < 3.4 * dpr && t.s.length === 1 && m.run) {
      m.s += t.s; m.x1 = t.x1; m.y0 = Math.min(m.y0, t.y0); m.y1 = Math.max(m.y1, t.y1); continue;
    }
    merged.push({ ...t, run: t.s.length === 1 });
  }
  const lum = (x, y) => { const o = (y * W + x) * 4; return 0.2126 * img[o] + 0.7152 * img[o + 1] + 0.0722 * img[o + 2]; };
  const out = [];
  const R = 18 * dpr;   // the window's rounded corners
  for (const t of merged) {
    if (!t.s.trim()) continue;
    const x0 = Math.max(0, Math.floor(t.x0 - 1)), x1 = Math.min(W - 1, Math.ceil(t.x1 + 1)), y0 = Math.max(0, Math.floor(t.y0 - 1)), y1 = Math.min(H - 1, Math.ceil(t.y1 + 1));
    const f = { s: t.s, box: [t.x0 / dpr, t.y0 / dpr, t.x1 / dpr, t.y1 / dpr].map(v => Math.round(v * 10) / 10), halo: t.halo, font: t.font };
    if (t.x0 < 2 * dpr || t.x1 > W - 2 * dpr || t.y0 < 2 * dpr || t.y1 > H - 2 * dpr) f.out = true;
    for (const [cx, cy] of [[R, R], [W - R, R], [R, H - R], [W - R, H - R]]) {
      const px = cx < W / 2 ? t.x0 : t.x1, py = cy < H / 2 ? t.y0 : t.y1;
      const inCornerBox = (cx < W / 2 ? px < cx : px > cx) && (cy < H / 2 ? py < cy : py > cy);
      if (inCornerBox && Math.hypot(px - cx, py - cy) > R - 3 * dpr) f.corner = true;
    }
    if (x1 > x0 && y1 > y0) {
      const v = [];
      for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) v.push(lum(x, y));
      const srt = v.slice().sort((a, b) => a - b), med = srt[srt.length >> 1];
      let n = 0, mx = 0; for (const q of v) { const d = Math.abs(q - med); if (d > 26) n++; if (d > mx) mx = d; }
      f.ink = n; f.inkFrac = n / v.length; f.inkMax = Math.round(mx);
    }
    out.push(f);
  }
  const ov = [];
  for (let a = 0; a < merged.length; a++) for (let b = a + 1; b < merged.length; b++) {
    const p = merged[a], q = merged[b];
    if (!p.s.trim() || !q.s.trim()) continue;
    const w = Math.min(p.x1, q.x1) - Math.max(p.x0, q.x0), h = Math.min(p.y1, q.y1) - Math.max(p.y0, q.y0);
    if (w > 0.6 * dpr && h > 0.6 * dpr) ov.push([p.s, q.s, Math.round(w / dpr * 10) / 10, Math.round(h / dpr * 10) / 10]);
  }
  return { W: W / dpr, H: H / dpr, texts: out, overlaps: ov, aria, errs: ERRS.slice() };
}
"""

def states_for(c, quick):
    """sampled states: every option, plus in-between values for the draggable controls"""
    axes = []
    for k in c.get('ctrl', []):
        key = k['key']
        if key == 'len': vals = list(range(len(k['opts'])))
        elif key == 'depth': vals = [3, 5, 8, 11] if quick else [2, 2.4, 3, 3.2, 4, 5, 6, 7, 7.9, 8, 9, 10, 10.5, 11, 11.5, 12]
        elif key == 'angle' and c['pic'] == 'choose': vals = [20, 30, 45] if quick else [20, 25, 30, 37.5, 45]   # chips only: the in-between values are the chip animation
        elif key == 'angle': vals = [20, 30, 45] if quick else [20, 22.5, 25, 27.5, 30, 33, 36, 40, 45, 50, 55, 60]
        elif key == 'press': vals = [0, 1] if quick else [0, 0.2, 0.4, 0.6, 0.8, 1]
        elif key == 'stage': vals = [0, 1, 2] if quick else [0, 0.5, 1, 1.25, 1.5, 1.75, 2]
        elif key == 'plane': vals = [14, 30.2, 33] if quick else [4, 6, 8, 10, 14, 18, 22, 26, 28, 29, 29.5, 30.2, 31, 32, 33, 33.5]
        else: vals = [o[0] for o in k['opts']]
        axes.append((key, vals))
    if c['pic'] == 'arc' and not any(k == 'angle' for k, _ in axes):     # reach: the arc is dragged as well
        axes.append(('angle', [20, 45, 60] if quick else [20, 25, 30, 36, 45, 52, 60]))
    if not axes: return [{}]
    out = [dict(zip([k for k, _ in axes], combo)) for combo in itertools.product(*[v for _, v in axes])]
    if c.get('tilt'):                                                     # after a tilt check: what was held, drawn within the picture's range
        out += [{'angle': max(20, min(60, h)), 'held': h} for h in ((33, 45, 58) if quick else (8, 20, 26, 33, 45, 58, 60, 88))]
    return out

VIEWPORTS = [
    ('se', 375, 628), ('android360', 360, 720), ('mini', 375, 719), ('ip14', 390, 750), ('ip16', 393, 759),
    ('plus', 430, 839), ('his440', 440, 863), ('a2hs390', 390, 844), ('w320', 320, 600),
    ('land', 844, 390), ('ipadP', 768, 1024), ('ipadAirP', 820, 1180), ('ipadL', 1024, 768), ('ipadAirL', 1180, 820),
    ('mac1440', 1440, 900), ('mbp16', 1728, 1000),
]

async def main(html, quick, only):
    sys.path.insert(0, os.path.dirname(os.path.abspath(html)))
    from cards import CARDS
    url = 'file://' + os.path.abspath(html)
    res = []
    async with async_playwright() as p:
        exe = os.environ.get('CHROME') or next((x for x in ('/usr/bin/google-chrome', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome') if os.path.exists(x)), None)
        b = await p.chromium.launch(args=['--no-sandbox', '--force-color-profile=srgb'], **({'executable_path': exe} if exe else {}))
        for name, vw, vh in VIEWPORTS:
            if only and name not in only: continue
            ctx = await b.new_context(viewport={'width': vw, 'height': vh}, device_scale_factor=2, has_touch=vw < 1100, reduced_motion='reduce')
            await ctx.add_init_script(INIT)
            page = await ctx.new_page()
            perr = []
            page.on('pageerror', lambda e: perr.append(str(e)))
            await page.goto(url); await page.evaluate('document.fonts.ready'); await page.wait_for_timeout(200)
            n = 0
            for c in CARDS:
                for st in states_for(c, quick):
                    r = await page.evaluate(MEASURE, [c['id'], st])
                    res.append({'vp': name, 'vw': vw, 'vh': vh, 'id': c['id'], 'st': st, **r}); n += 1
            if perr: res.append({'vp': name, 'pageerrors': perr})
            print(f"  {name:10s} {vw:4d} x {vh:4d}  {n} states", flush=True)
            await ctx.close()
        await b.close()
    return res

def report(res, MIN=8):
    errs = collections.Counter(); ink = {}; ov = {}; out = {}
    states = 0
    for r in res:
        if 'pageerrors' in r:
            for e in r['pageerrors']: errs[(r['vp'], e[:140])] += 1
            continue
        states += 1
        for e in r.get('errs', []): errs[(r['vp'], r['id'], e[:140])] += 1
        for t in r['texts']:
            key = (r['id'], t['s'])
            if t.get('out') or t.get('corner'): out.setdefault(key, []).append((r['vp'], r['st'], t['box']))
            if t.get('ink', 0) >= MIN and t.get('inkFrac', 0) > 0.012:
                d = ink.setdefault(key + (bool(t['halo']),), {'n': 0, 'worst': 0, 'eg': None, 'vps': set()})
                d['n'] += 1; d['vps'].add(r['vp'])
                if t['ink'] > d['worst']: d['worst'] = t['ink']; d['eg'] = (r['vp'], r['st'], t['box'])
        for a, b, w, h in r['overlaps']:
            d = ov.setdefault((r['id'], a, b), {'n': 0, 'worst': 0, 'eg': None})
            d['n'] += 1
            if w * h > d['worst']: d['worst'] = w * h; d['eg'] = (r['vp'], r['st'], w, h)
    hard = {k: d for k, d in ink.items() if not k[2]}; rim = {k: d for k, d in ink.items() if k[2]}
    print(f"states measured: {states}")
    print(f"script errors: {sum(errs.values())}")
    for k, v in errs.most_common(10): print('   ', v, k)
    print(f"text over text: {len(ov)}")
    for k, d in sorted(ov.items(), key=lambda kv: -kv[1]['worst'])[:40]: print(f"    {k[0]:14s} {k[1]!r} x {k[2]!r}  n={d['n']} eg={d['eg']}")
    print(f"text across a drawn line: {len(hard)}")
    for k, d in sorted(hard.items(), key=lambda kv: -kv[1]['worst'])[:60]: print(f"    {k[0]:14s} {k[1]!r}  n={d['n']} sizes={len(d['vps'])} worst={d['worst']}px eg={d['eg']}")
    print(f"text outside the window or in a clipped corner: {len(out)}")
    for k, v in list(out.items())[:30]: print('   ', k, len(v), v[0])
    print(f"rimmed labels over a line (allowed, listed): {len(rim)}")
    for k, d in sorted(rim.items(), key=lambda kv: -kv[1]['worst']): print(f"    {k[0]:14s} {k[1]!r}  n={d['n']} worst={d['worst']}px eg={d['eg']}")
    bad = sum(errs.values()) + len(ov) + len(hard) + len(out)
    print("CENSUS " + ("CLEAN" if not bad else f"FAILED: {bad} kinds of fault"))
    return bad

if __name__ == '__main__':
    quick = 'quick' in sys.argv[2:]
    only = [a[5:] for a in sys.argv[2:] if a.startswith('only=')]
    res = asyncio.run(main(sys.argv[1], quick, only[0].split(',') if only else None))
    sys.exit(1 if report(res) else 0)
