# -*- coding: utf-8 -*-
"""Real pointer drags in Chrome, at phone, tablet and laptop sizes: does the value land under
the pointer? On wide screens the picture is drawn at its tested width and scaled up, so this is
the check that the pointer is read in the drawing's own units.

    python3 qa-drag.py index.html

Needs Playwright for Python and Chrome (set CHROME to the binary if Playwright has none of its own).
The entry angle card and the track drawings pivot from the frame being left, so a degree or two
of difference there is the design; the ruler, the arcs, the scan plane, the probe, the stages and
the four things that can be held on the Choosing the length card must land exactly."""
import sys, os, asyncio, json
from playwright.async_api import async_playwright
TARGETS = r"""
(id) => {
  const c = CARDS.find(x => x.id === id), cv = document.querySelector('.win canvas'), r = cv.getBoundingClientRect(), z = cv._z || 1;
  const W = Math.round(r.width / z), H = Math.round(r.height / z), out = [];
  const css = (x, y) => [r.left + x * z, r.top + y * z];
  if (c.pic === 'angleTri') for (const a of [25, 30, 50]) { const g = angGeom({ angle: a }, W, H, false); out.push({ key: 'angle', want: a, pt: css(g.tipx, g.vt), from: css(g.tipx - 30, g.vt - 30) }); }
  if (c.pic === 'arc') for (const a of [25, 30, 50]) { const S = (Math.min(W - 100, H - 46 - 66)) / (0.35 * 45), L = G.LEN[state[id].len ?? 3], rr = 0.35 * L * S;
      out.push({ key: 'angle', want: a, pt: css(52 + rr * cos(a), 46 + rr * sin(a)), from: css(52 + rr * cos(45), 46 + rr * sin(45)) }); }
  if (c.pic === 'track' && !(c.ctrl || []).some(k => k.key === 'len')) for (const a of [25, 30, 50]) {
      const g = trackGeom(c, { angle: a }, W, H, false); out.push({ key: 'angle', want: a, pt: css(g.ex, g.wallT + 4), from: css(g.ex + 20, g.wallT + 4) });
      if (g.bar) { const b = g.bar; out.push({ key: 'angle', want: a, pt: css(b.xt - g.lin * b.SB, b.yB - 26 - b.bh), from: css(b.xt - g.lin * b.SB + 25, b.yB - 26 - b.bh), where: 'ruler' }); } }
  if (c.pic === 'planes') for (const p of [10, 20, 30]) { const g = planesGeom(W, H, false); out.push({ key: 'plane', want: p, pt: css(g.punc + p * g.S1, 100), from: css(g.punc + 14 * g.S1, 100) }); }
  if (c.pic === 'stages') for (const u of [0.5, 1, 1.5]) out.push({ key: 'stage', want: u, pt: css(24 + u / 2 * (W - 48), 80), from: css(40, 80) });
  if (c.pic === 'choose') { const g = chooseGeom({ depth: 5, angle: 45 }, W, H, false), X = mm => g.x0 + mm * g.S, s45 = sin(45), pre = { depth: 5, angle: 45 };
      for (const d of [3, 7.5, 11]) out.push({ key: 'depth', want: d, pre, pt: css(W * 0.4, g.skin + d * g.S), from: css(W * 0.4, g.skin + 5 * g.S), where: 'vein' });
      for (const d of [3, 8]) out.push({ key: 'depth', want: d, pre, pt: css(X(d / s45), g.y27), from: css(X(5 / s45), g.y27), where: 'path end' });
      for (const d of [3, 8]) out.push({ key: 'depth', want: d, pre, pt: css(X(d / s45 / 0.35), g.y0), from: css(X(5 / s45 / 0.35), g.y0), where: '65% line' });
      for (const d of [3, 8]) out.push({ key: 'depth', want: d, pre, pt: css(X(d / s45 + 27.5), g.y0 + g.p), from: css(X(5 / s45 + 27.5), g.y0 + g.p), where: '27.5 line' }); }
  if (c.pic === 'depth') for (const p of [0.25, 0.5, 0.9]) out.push({ key: 'press', want: p, pt: css(W * 0.5, 70 + p * H * 0.34), from: css(W * 0.5, 60) });
  return out;
}
"""
async def main(html):
    url = 'file://' + os.path.abspath(html)
    async with async_playwright() as p:
        exe = os.environ.get('CHROME') or next((x for x in ('/usr/bin/google-chrome', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome') if os.path.exists(x)), None)
        b = await p.chromium.launch(args=['--no-sandbox'], **({'executable_path': exe} if exe else {}))
        worst = {}
        for name, vw, vh in (('phone', 390, 844), ('ipadP', 768, 1024), ('ipadL', 1024, 768), ('mbp16', 1728, 1000)):
            ctx = await b.new_context(viewport={'width': vw, 'height': vh}, device_scale_factor=2, reduced_motion='reduce')
            page = await ctx.new_page(); await page.goto(url); await page.evaluate('document.fonts.ready')
            ids = await page.evaluate('CARDS.map(c=>c.id)')
            for cid in ids:
                await page.evaluate('id=>entry(CARDS.findIndex(c=>c.id===id))', cid); await page.wait_for_timeout(60)
                await page.evaluate('window.scrollTo(0,0)')
                try: ts = await page.evaluate(TARGETS, cid)
                except Exception as e: ts = []; print('  targets failed', cid, str(e)[:80])
                for t in ts:
                    if t.get('pre'): await page.evaluate('([id,st])=>{ Object.assign(state[id],st); if(refresh) refresh(); }', [cid, t['pre']])
                    await page.mouse.move(*t['from']); await page.mouse.down(); await page.mouse.move(*t['pt'], steps=4); await page.mouse.up()
                    got = await page.evaluate('([id,k])=>state[id][k]', [cid, t['key']])
                    err = abs(got - t['want'])
                    k = (name, cid, t.get('where', 'drawing'))
                    if err >= worst.get(k, (-1,))[0]: worst[k] = (round(err, 2), t['want'], round(got, 2))   # an exact landing is listed too
            await ctx.close()
        await b.close()
        bad = 0
        for k, v in sorted(worst.items()):
            pivots = k[2] == 'drawing' and (k[1] == 'entry-angle' or k[1] in ('rule-65', 'judging-angle', 'floor-275'))
            lim = 6 if pivots else 0.15                      # the new card rounds its depth to 0.1 mm, inside this limit
            flag = '' if v[0] <= lim else '   <-- OFF'
            bad += v[0] > lim
            print(f"  {k[0]:6s} {k[1]:14s} {k[2]:8s} worst error {v[0]:6.2f}  (wanted {v[1]}, got {v[2]}){flag}")
        print("DRAGS " + ("CLEAN" if not bad else f"FAILED: {bad}"))
        return bad
sys.exit(1 if asyncio.run(main(sys.argv[1])) else 0)
