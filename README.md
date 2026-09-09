# matrix-fonts

Shared Adafruit GFX 8-bit fonts for the xbco LED matrix firmwares
(spojboard, beerboard, noticeboard).

Consumed as a git submodule at `vendor/matrix-fonts/`; each project's
`src/fonts/*.h` is a symlink into here, so `#include "../fonts/X.h"`
keeps working unchanged.

## Encoding

GFX Latin 2: 192 glyphs at codes 0x20-0xDF. `src/utils/gfxlatin2.cpp` in
each firmware maps UTF-8 to these codes. Generated with
fontconvert8-iso8859-2 (see spojboard-firmware/docs/FONTS.md).

## Editing a font

Edit here, commit, then in each consumer:

    git submodule update --remote vendor/matrix-fonts
    git add vendor/matrix-fonts && git commit

The bump is deliberate: it pins the glyphs to a firmware release, so
`git checkout r9 && pio run` reproduces r9's rendering.

## Provenance

Seeded 2026-09-09 from spojboard-firmware @ f8bb829 ("style(fonts):
tweak DepartureMono glyph metrics", 2026-06-24), which had shipped in
OTA releases r8, r9 and r10.

beerboard/noticeboard previously carried a variant differing in two
drawn glyphs, at slots 0xB9 and 0xBA, plus the never-emitted slot 0x90.
spojboard's version was chosen: it is the one with field exposure, and
neither of the other two repos has ever cut a release.
