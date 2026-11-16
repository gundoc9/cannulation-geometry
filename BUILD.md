# How this app is built

`index.html` is **generated**, not hand-edited. It is a single self-contained
file: fonts embedded as base64, no network requests of any kind. Editing the
built file directly is how silent regressions get in — change the sources and
rebuild.

## Sources

| File | What it is |
|---|---|
| `template2.html` | The page: layout, CSS, head metadata, all canvas renderers, interaction |
| `cards.py` | The content: 16 terms, their prose, tables, controls, sources, links |
| `fonts.json` | The four font faces (Big Shoulders, Instrument Sans ×2, Geist Mono), subsetted to the app's charset, as base64 woff data URIs |
| `build2.py` | The build. Injects cards and fonts into the template, runs build gates |
| `gates_cards.py` | Content gates over `cards.py` |
| `harness2.js` | The suite, phone width (390 px) |
| `harness_wide.js` | The same suite at tablet width (588 px) |

## Rebuild

    python3 gates_cards.py     # content gates
    python3 build2.py          # writes cannulation-geometry-vN.html
    node harness2.js           # phone-width suite
    node harness_wide.js       # tablet-width suite
    python3 qa-census.py index.html   # in Chrome: every card state at sixteen screen sizes
    python3 qa-drag.py index.html     # in Chrome: real pointer drags at phone, tablet and laptop sizes
    python3 qa-tilt.py index.html     # in Chrome: the tilt check on Judging the angle, every branch

All seven must pass before a build ships. The version number comes from the
template's `VERSION` constant; the build writes the matching
`cannulation-geometry-vN.html` and records the name in `.latest`, which both
harnesses read (so the filename lives in exactly one place). The built file
carries the full deployable `<head>` — rename it to `index.html` and commit;
nothing needs re-adding.

The build and the two suites need Python 3 and Node and no packages. The two browser checks
need Playwright for Python and Chrome; they run against the built `index.html`, with `cards.py`
beside it.

## What the gates cover

`build2.py` — self-contained (no external `src` or `<link>` loads; navigation
links are allowed), fonts present, accessibility attributes, credentials
string, both source DOIs present, the deployable head tags (web-app, touch
icon, Open Graph, Twitter), the table-block renderer, no colour literals
written at draw sites (every colour must come from a named token), and the
error pill's masked-error guard: the on-page reporter speaks only for errors
it can attribute to a line, and stays silent on masked cross-origin noise.

`harness2.js` / `harness_wide.js` — for every card, at both widths: nothing
drawn outside the window, every control changes the picture, required labels
present, on-canvas marks agree with the stated arithmetic, every thumbnail
draws at index size, pointer drags map to the value they claim, and geometry
stays clear of the readout band.

`qa-census.py` — in Chrome, with the embedded faces: for every card, every control option
and the in-between positions of every drag, at sixteen screen sizes from a 320 px phone to a
16-inch laptop, it measures each piece of text on the canvas, repaints with text switched off
and looks at what lies under each one. It fails on a label across a drawn line, a label over
another label, a label outside the window, and any script error. Labels drawn with a rim
(`htxt`) are meant to be able to cross a faint line; they are listed and not failed.

`qa-drag.py` — drags with a real pointer and checks that the value lands under it, at phone,
tablet and laptop sizes.

`qa-tilt.py` — the tilt check on Judging the angle, fed made-up tilt readings: a steady hold, a
hold with the needle end down and a jolt at the tap, holds beyond the drawing's range, cancel,
leaving the card part way, no readings at all, the iPhone permission step granted, refused and
failing, and no button on a screen without touch. A real handset is still the only proof that
the sensor answers; this checks everything around it.

The harness renders through a recording 2D context that enforces the real
API's constraints — a negative arc radius throws exactly where WebKit throws.
A stub that records without validating hides every constraint the real API
enforces; that blind spot shipped two faults before it was closed.

## Rules this build learned the hard way

- One designer change per version, against a held snapshot. A rejected batch
  of six changes cannot be attributed to any one of them.
- Assert every patch anchor. An unmatched edit is a silent regression, not a
  no-op — and an unchanged output size after a "fix" means the patch missed.
- A gate must never hold a literal for anything the source defines: not a
  drawn string, not a beat time, not a filename.
- Buttons do not inherit `color` or `font`. The harness cannot see UA styling.
- Judge every layout decision at phone scale, from rendered font metrics.
- Any new picture kind is designed as a viewed still at phone scale before it
  is ported to canvas. The suites check bounds and arithmetic; they cannot
  see composition.
- One phone size proves nothing about the next. A label that clears every line
  at 390 px was struck through at 375 and at 588, and on a phone `vh` is the
  height with the toolbars away, so a 58vh window was shorter than its picture
  on every iPhone smaller than the largest. Positions that depend on scale are
  judged by the census at every size, never by eye at one.
- A window is never shorter than its picture needs. A short screen scrolls;
  it does not squeeze the drawing into the readout.
- On wide screens the picture is drawn at its tested width and scaled up.
  A pointer position is divided by that scale before it reaches a drag
  function, or the drag lands short of the finger.

## Licence

Sources are published for transparency and teaching. The licence in
`LICENSE` (CC BY-NC-ND 4.0) still governs: share with attribution,
non-commercially, without modification.
