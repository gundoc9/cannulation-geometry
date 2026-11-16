# -*- coding: utf-8 -*-
"""The tilt check on Judging the angle, driven in Chrome with made-up tilt readings: a steady
hold, a hold with the needle end down and a jolt at the tap, holds beyond the drawing's range,
cancel, leaving the card part way, no readings at all, the iPhone permission step granted,
refused and failing, and no button on a screen without touch.

    python3 qa-tilt.py index.html

Needs Playwright for Python and Chrome (set CHROME to the binary if Playwright has none of its own)."""
import sys, os, asyncio
from playwright.async_api import async_playwright

FEED = """(async ([beta, ms, tail]) => {
  // steady readings at 60 Hz, then (optionally) a jolt in the last moments, as a tap gives
  const t0 = performance.now();
  while (performance.now() - t0 < ms) {
    const left = ms - (performance.now() - t0);
    const b = (tail && left < 90) ? beta + tail : beta + (Math.random() - 0.5) * 0.3;
    window.dispatchEvent(new DeviceOrientationEvent('deviceorientation', { alpha: 10, beta: b, gamma: 3 }));
    await new Promise(r => setTimeout(r, 16));
  }
})"""

async def main(html, shots):
    url = 'file://' + os.path.abspath(html); bad = []; note = lambda s: (print('  ' + s))
    async with async_playwright() as p:
        exe = os.environ.get('CHROME') or next((x for x in ('/usr/bin/google-chrome', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome') if os.path.exists(x)), None)
        b = await p.chromium.launch(args=['--no-sandbox'], **({'executable_path': exe} if exe else {}))
        async def fresh(vw=440, vh=800, touch=True, init=None):
            ctx = await b.new_context(viewport={'width': vw, 'height': vh}, device_scale_factor=2, has_touch=touch, is_mobile=touch)
            if init: await ctx.add_init_script(init)
            page = await ctx.new_page(); errs = []
            page.on('pageerror', lambda e: errs.append('pageerror ' + str(e)))
            page.on('console', lambda m: errs.append('console ' + m.text) if m.type == 'error' else None)
            await page.goto(url + '#judging-the-angle'); await page.evaluate('document.fonts.ready'); await page.wait_for_timeout(250)
            return ctx, page, errs
        st = lambda page: page.evaluate("JSON.stringify(state['judging-angle'])")
        pill = lambda page: page.evaluate("(document.getElementById('errpill')||{}).textContent||''")

        # 1. the ordinary run: hold 33, tap
        ctx, page, errs = await fresh()
        if await page.locator('.tiltbtn').count() != 1: bad.append('no tilt button on a touch device')
        await page.locator('.tiltbtn').click(); await page.wait_for_timeout(120)
        if await page.locator('.tiltov').count() != 1: bad.append('overlay did not open')
        if shots: await page.screenshot(path=os.path.join(shots, 'tilt-1-armed.png'))
        feed = asyncio.create_task(page.evaluate(FEED, [33, 900, 0]))
        await page.wait_for_timeout(700)
        await page.locator('.tiltov .go').click(); await feed; await page.wait_for_timeout(120)
        s = await st(page); txt = await page.locator('.tiltnote').inner_text(); aria = await page.locator('.win canvas').get_attribute('aria-label')
        note(f"held 33: state {s} | note {txt!r}")
        if '"held":3' not in s or 'You held 33' not in txt or '12° flatter' not in txt: bad.append('ordinary run: ' + s + ' ' + txt)
        if 'You held 33 degrees' not in aria: bad.append('aria does not say what was held')
        if await page.locator('.tiltov').count(): bad.append('overlay still up after the tap')
        if (await page.locator('.tiltbtn').inner_text()).strip() != 'Try again': bad.append('button did not become Try again')
        if shots: await page.screenshot(path=os.path.join(shots, 'tilt-2-result.png'))
        # a chip tap goes back to the card
        await page.locator('.krow button').nth(1).click(); await page.wait_for_timeout(600)
        s = await st(page); txt = await page.locator('.tiltnote').inner_text()
        if 'held' in s or txt.strip(): bad.append('chip tap did not clear the result: ' + s + ' ' + txt)
        if (await page.locator('.tiltbtn').inner_text()).strip() != 'Check your own 45°': bad.append('button label not restored')
        # 2. held like a needle, tip down (beta negative), with a jolt at the tap
        await page.locator('.tiltbtn').click(); await page.wait_for_timeout(100)
        feed = asyncio.create_task(page.evaluate(FEED, [-38, 900, 7]))
        await page.wait_for_timeout(860)
        await page.locator('.tiltov .go').click(); await feed; await page.wait_for_timeout(100)
        s = await st(page); txt = await page.locator('.tiltnote').inner_text(); note(f"held -38 with a jolt: {s} | {txt!r}")
        if 'You held 38' not in txt: bad.append('needle-down hold or jolt filter: ' + txt)
        # 3. steeper than the drawing goes, and flatter
        for beta, want, stop in ((72, 'You held 72', 'stops at 60'), (11, 'You held 11', 'stops at 20'), (46, 'within 2', ''), (45, ': the 45', '')):
            await page.locator('.tiltbtn').click(); await page.wait_for_timeout(100)
            feed = asyncio.create_task(page.evaluate(FEED, [beta, 800, 0])); await page.wait_for_timeout(650)
            await page.locator('.tiltov .go').click(); await feed; await page.wait_for_timeout(100)
            txt = await page.locator('.tiltnote').inner_text(); s = await st(page); note(f"held {beta}: {s} | {txt!r}")
            if want not in txt or stop not in txt: bad.append(f'held {beta}: {txt}')
            if beta == 72 and '"angle":60' not in s: bad.append('drawing not held at 60')
            if beta == 11 and '"angle":20' not in s: bad.append('drawing not held at 20')
        if shots: await page.screenshot(path=os.path.join(shots, 'tilt-3-exact.png'))
        # 4. cancel, then leaving the card while armed
        await page.locator('.tiltbtn').click(); await page.wait_for_timeout(100)
        await page.locator('.tiltov .no').click(); await page.wait_for_timeout(80)
        if await page.locator('.tiltov').count(): bad.append('cancel left the overlay up')
        s = await st(page)
        if 'held' in s: bad.append('cancel kept a held value')
        await page.locator('.tiltbtn').click(); await page.wait_for_timeout(100)
        await page.evaluate("entry(0)"); await page.wait_for_timeout(100)
        await page.evaluate(FEED, [30, 120, 0])
        await page.wait_for_timeout(1800)        # past the no-reading timer: nothing may fire on the other card
        if await page.locator('.tiltov').count(): bad.append('overlay survived leaving the card')
        if await pill(page): bad.append('error pill: ' + await pill(page))
        if errs: bad.append('errors: ' + '; '.join(errs[:3]))
        await ctx.close()

        # 5. no readings at all (no sensor, or a view that blocks it)
        ctx, page, errs = await fresh()
        await page.locator('.tiltbtn').click(); await page.wait_for_timeout(1900)
        txt = await page.locator('.tiltov p').inner_text(); note(f"no readings: {txt!r}")
        if 'No tilt reading has arrived' not in txt or await page.locator('.tiltov .go').count(): bad.append('no-sensor message')
        if shots: await page.screenshot(path=os.path.join(shots, 'tilt-4-nosensor.png'))
        await page.locator('.tiltov .no').click(); await page.wait_for_timeout(80)
        if await page.locator('.tiltov').count(): bad.append('close left the overlay up')
        if errs or await pill(page): bad.append('errors with no sensor: ' + '; '.join(errs[:3]) + await pill(page))
        await ctx.close()

        # 6. the iPhone permission step: granted, refused, and thrown
        for mode, expect in (('granted', 'armed'), ('denied', 'No tilt reading was allowed'), ('reject', 'No tilt reading was allowed'), ('throw', 'No tilt reading was allowed')):
            init = "window.__mode=%r; DeviceOrientationEvent.requestPermission=function(){ if(window.__mode==='throw') throw new Error('x'); return window.__mode==='reject'?Promise.reject(new Error('no')):Promise.resolve(window.__mode); };" % mode
            ctx, page, errs = await fresh(init=init)
            await page.locator('.tiltbtn').click(); await page.wait_for_timeout(200)
            up = await page.locator('.tiltov').count(); txt = await page.locator('.tiltnote').inner_text()
            note(f"permission {mode}: overlay {up}, note {txt!r}")
            if (expect == 'armed') != bool(up) or (expect != 'armed' and expect not in txt): bad.append('permission ' + mode)
            if errs or await pill(page): bad.append(f'errors on permission {mode}: ' + '; '.join(errs[:3]) + await pill(page))
            await ctx.close()

        # 7. a laptop has no button
        ctx, page, errs = await fresh(vw=1440, vh=900, touch=False)
        n = await page.locator('.tiltbtn').count(); note(f"laptop: {n} tilt buttons")
        if n: bad.append('tilt button shown without a touch screen')
        await ctx.close()
        await b.close()
    print('TILT ' + ('CLEAN' if not bad else 'FAILED: ' + ' | '.join(bad)))
    return 1 if bad else 0
sys.exit(asyncio.run(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)))
