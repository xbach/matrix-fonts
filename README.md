# matrix-fonts

Shared Adafruit GFX 8-bit bitmap fonts for the xbco LED matrix firmwares.

These are `PROGMEM` C headers, not font files — each one is a packed glyph
bitstream plus a `GFXglyph` metrics table, `#include`d straight into the
firmware and compiled into the binary. They live here because three projects
were carrying byte-divergent copies of the same four fonts.

## Fonts

| File | Size | Used for |
|---|---|---|
| `DepartureMono4pt8b.h` | 4pt | compact text, line numbers, status messages |
| `DepartureMono5pt8b.h` | 5pt | destinations, ETAs, primary text |
| `DepartureMonoCondensed5pt8b.h` | 5pt narrow | long destinations, secondary ETAs |
| `DepartureWeather4pt8b.h` | 4pt | weather glyphs |
| `DepartureMonoCyrillic5pt8b.h` | 5pt | Russian and Ukrainian — **CP1251**, not Latin 2 |

## Encoding

**GFX Latin 2**: 192 glyphs at codes `0x20`-`0xDF`, covering printable ASCII plus
Latin Extended-A for Czech, German, Polish and Hungarian diacritics. Consuming
firmware converts UTF-8 to these codes in `src/utils/gfxlatin2.cpp` before
drawing, since Adafruit GFX itself assumes 7-bit ASCII.

Full explanation of the scheme, the UTF-8 decoder and how to generate a new font:
**[spojboard-firmware/docs/FONTS.md](https://github.com/xbach/spojboard-firmware/blob/main/docs/FONTS.md)**
— and the [Fonts & Character Support](https://github.com/xbach/spojboard-firmware#fonts--character-support)
section of its README.

## The Cyrillic font

`DepartureMonoCyrillic5pt8b.h` is **generated** — `python3 tools/make_cyrillic.py`. Do not hand-edit
it; edit the glyph art in the generator and regenerate.

**It is a second font, not a replacement.** The four Latin faces are finished and nothing here
touches them. A Cyrillic run is drawn by switching font, which is why this file carries **ASCII at
its natural positions** as well: digits, spaces and punctuation then never force a switch mid-run,
and only accented-Latin-beside-Cyrillic splits a run.

**Encoding is CP1251**, deliberately. It is a standard, so the firmware's UTF-8 → byte map can be
generated from Python's own codec instead of invented, and every letter Russian *and* Ukrainian need
has a defined slot (Ё Ґ Є І Ї and lowercase).

**Glyphs are derived from the corrected Latin faces, not re-converted from the TTF.** The Departure
Mono vectors do not rasterise cleanly at 5pt and the Latin faces here carry a lot of manual pixel
correction; re-converting would discard it. So the 19 Cyrillic letters that are shape-identical to a
Latin one reuse that bitmap byte-for-byte (А=A, В=B, Е=E, К=K, М=M, Н=H, О=O, Р=P, С=C, Т=T, Х=X,
І=I, а=a, е=e, о=o, р=p, с=c, у=y, х=x) and only the remaining ~60 are drawn.

### No descenders — and for Cyrillic that is a correctness rule, not a style choice

`DisplayManager::drawRow` blanks each 8px row band before drawing it, so anything below the baseline
is erased by the row beneath. Latin `g`, `y` and `j` already render clipped on this panel.

For Cyrillic that would be a legibility **bug**: the tail is the only thing distinguishing **ц from
п** and **щ from ш**. So those tails sit ON the baseline row, and Д's legs likewise. The generator
asserts this — no hand-drawn glyph may have `yOff + height > 1`.

The one exception is `у`, which reuses Latin `y` and inherits its clipped descender. That is safe:
`у` without its tail still reads as `у`, where `ц` without its tail is a different letter.

### Previews

`preview-cyrillic-5pt.png` is a zoomed proof sheet; `preview-cyrillic-panel.png` renders real
128x32 frames at the panel's own 8px row pitch, which is the only view that answers whether a glyph
is legible at size. Regenerate both with `python3 tools/preview_png.py`.

## How projects consume this

As a git submodule at `vendor/matrix-fonts/`, with each `src/fonts/*.h` a symlink
into it, so existing `#include "../fonts/X.h"` lines keep working:

```
src/fonts/DepartureMono5pt8b.h -> ../../vendor/matrix-fonts/DepartureMono5pt8b.h
```

The symlink target is repo-relative so a clean CI checkout resolves it, and
`.gitmodules` uses the relative URL `../matrix-fonts`, which git resolves against
the superproject's own remote.

Consumers:

- **[spojboard-firmware](https://github.com/xbach/spojboard-firmware)** — transit
  departure board. The canonical source of these glyphs.
- **beerboard-firmware** — tap list display (not published).
- **noticeboard-firmware** — Home Assistant notification panel (not published).

Checkout must be recursive, or the headers are missing:

```bash
git clone --recurse-submodules …
# in CI: actions/checkout@v4 with submodules: true
```

## Editing a font

Edit here, commit, push — then adopt it per project. **Never `cp` over a
`src/fonts/*.h` symlink in a consumer**; that replaces the link with a real file
and silently re-forks the fonts.

```bash
# here
git commit -am "fix(fonts): …" && git push

# in each consuming project
git submodule update --remote vendor/matrix-fonts
git add vendor/matrix-fonts && git commit -m "chore(fonts): bump matrix-fonts"
```

The per-project bump is deliberate rather than friction: it pins glyphs to a
firmware release, so `git checkout r9 && pio run` reproduces exactly what r9
rendered. A font shared by live reference would silently change the output of
every historical build.

Regenerating from the typeface needs
[fontconvert8-iso8859-2](https://github.com/petrbrouzda/fontconvert8-iso8859-2)
(see FONTS.md above); individual glyphs are then tuned with the
[Adafruit GFX Font Customiser](https://tchapi.github.io/Adafruit-GFX-Font-Customiser/).

## Provenance

Glyphs are rasterised from **[Departure Mono](https://departuremono.com)** by
Helena Zhang & Tobias Fried ([source](https://github.com/rektdeckard/departure-mono)),
then converted to the 8-bit ISO-8859-2 range and hand-tuned.

Seeded 2026-09-09 from `spojboard-firmware@f8bb829` ("style(fonts): tweak
DepartureMono glyph metrics", 2026-06-24), which had shipped in OTA releases r8,
r9 and r10.

beerboard and noticeboard previously carried a variant differing in **two drawn
glyphs** — slots `0xB9` (š) and `0xBA` (ş) in the 5pt regular font — plus the
never-emitted slot `0x90`. spojboard's drawing was adopted: it is the only one
with field exposure, and neither other project has ever cut a release.

## License

**GPL-3.0**, matching the consuming firmware — see [LICENSE](LICENSE).

The upstream Departure Mono typeface is MIT (© 2024 Helena Zhang & Tobias Fried);
its notice is reproduced in full in **[THIRD-PARTY.md](THIRD-PARTY.md)**, as MIT
requires. MIT permits the GPL-3.0 relicensing of this derived work.
