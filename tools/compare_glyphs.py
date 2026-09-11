#!/usr/bin/env python3
"""Compare an accented glyph against its base letter in the GFX Latin 2 faces.

Decodes the .h headers directly (bitmap stream + GFXglyph table), so it shows what
the firmware draws, not what a generator intended. For each pair it prints both
glyphs on a shared frame, the ink that differs, ink outside the advance cell, and
every neighbouring glyph the accented letter touches that the base letter does not.

Slots follow gfxlatin2.cpp utf8tocp(): ASCII at its own code, ISO-8859-2 0xA0-0xFF
at code - 0x20. The Cyrillic face is CP1251 and the weather face replaces letters
with icons, so neither is in the default font list.

  python3 tools/compare_glyphs.py                              # l/ľ and L/Ľ
  python3 tools/compare_glyphs.py --pair s š --pair S Š --words šťastie
  python3 tools/compare_glyphs.py --png /tmp/proof.png DepartureMono5pt8b.h
"""
import argparse, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_FONTS = ["DepartureMono4pt8b.h", "DepartureMono5pt8b.h", "DepartureMonoCondensed5pt8b.h"]
DEFAULT_PAIRS = [("l", "ľ"), ("L", "Ľ")]
DEFAULT_WORDS = ["lľl", "veľký", "koľko", "maľba", "ľudia", "Ľubica", "ĽUBICA"]


def parse(path):
    src = open(path, encoding="utf-8", errors="replace").read()
    bm = re.search(r"Bitmaps\[\]\s*PROGMEM\s*=\s*\{(.*?)\};", src, re.S).group(1)
    gl = re.search(r"Glyphs\[\]\s*PROGMEM\s*=\s*\{(.*?)\};", src, re.S).group(1)
    num = r"\s*(-?\d+)\s*"
    rows = [tuple(map(int, r)) for r in re.findall(r"\{" + ",".join([num] * 6) + r"\}", gl)]
    m = re.search(r"GFXfont\s+\w+\s+PROGMEM\s*=\s*\{[^,]*,[^,]*,\s*(\w+)\s*,\s*(\w+)\s*,\s*(\d+)", src)
    first, last = int(m.group(1), 0), int(m.group(2), 0)
    # Index by position, never by the trailing comments: the customiser labels
    # every slot above 0x7F 'non-printable' or with a Latin-1 name.
    assert len(rows) == last - first + 1, f"{path}: {len(rows)} glyphs for {first:#x}-{last:#x}"
    return {"name": os.path.basename(path), "first": first, "last": last, "glyphs": rows,
            "bitmap": [int(h, 16) for h in re.findall(r"0x[0-9A-Fa-f]{2}", bm)]}


def slot(ch):
    b = ch.encode("iso-8859-2")[0]
    if 0x20 <= b <= 0x7F:
        return b
    if b >= 0xA0:
        return b - 0x20
    raise ValueError(f"{ch!r} has no GFX Latin 2 slot")


def label(code):
    ch = chr(code) if code < 0x80 else bytes([code + 0x20]).decode("iso-8859-2")
    return ch if ch.isprintable() and not ch.isspace() else f"<{code:#04x}>"


def pixels(font, code):
    """Ink as a set of (x, y) relative to the cursor and baseline, plus metrics."""
    off, w, h, xa, xo, yo = font["glyphs"][code - font["first"]]
    px, bit = set(), 0
    for j in range(h):
        for i in range(w):
            if font["bitmap"][off + bit // 8] & (0x80 >> (bit % 8)):
                px.add((xo + i, yo + j))
            bit += 1
    return px, {"w": w, "h": h, "xa": xa, "xo": xo, "yo": yo}


def shift(px, dx):
    return {(x + dx, y) for x, y in px}


def near(a, b):
    """Pixels of a that overlap or 8-neighbour-touch any pixel of b."""
    return {(x, y) for x, y in a if any((x + dx, y + dy) in b for dx in (-1, 0, 1) for dy in (-1, 0, 1))}


def frame(*glyphs):
    xs, ys = [0], [0]
    for px, m in glyphs:
        xs += [m["xa"] - 1] + [x for x, _ in px]
        ys += [y for _, y in px]
    return min(xs), max(xs), min(ys), max(ys)


def ascii_pair(bch, ach, base, acc):
    x0, x1, y0, y1 = frame(base, acc)

    def row(g, y):
        px, m = g
        return "".join(("#" if 0 <= x < m["xa"] else "@") if (x, y) in px else
                       ("." if 0 <= x < m["xa"] else " ") for x in range(x0, x1 + 1))

    width = x1 - x0 + 1
    out = [" " * 8 + bch.ljust(width + 3) + ach]
    for y in range(y0, y1 + 1):
        out.append(f"  {'base' if y == 0 else f'{y:+d}':>4}  {row(base, y)}   {row(acc, y)}")
    return "\n".join(out)


def introduced_touches(font, bch, ach):
    """Glyphs that touch the accented letter but not the base letter, before and after it."""
    pb, mb = pixels(font, slot(bch))
    pa, ma = pixels(font, slot(ach))
    before, after = [], []
    for code in range(font["first"] + 1, font["last"] + 1):
        pg, mg = pixels(font, code)
        if not pg:
            continue
        if near(pa, shift(pg, ma["xa"])) and not near(pb, shift(pg, mb["xa"])):
            after.append(code)
        if near(shift(pa, mg["xa"]), pg) and not near(shift(pb, mg["xa"]), pg):
            before.append(code)
    return before, after


def layout(font, text, pairs):
    """Place a word as GFX does; tag accent-only ink and ink touching a neighbour."""
    accents = {a: b for b, a in pairs}
    x, glyphs = 0, []
    for ch in text:
        px, m = pixels(font, slot(ch))
        extra = px - pixels(font, slot(accents[ch]))[0] if ch in accents else set()
        glyphs.append((shift(px, x), shift(extra, x)))
        x += m["xa"]
    ink, accent, touch = set(), set(), set()
    for i, (px, extra) in enumerate(glyphs):
        ink |= px
        accent |= extra
        if i:
            prev = glyphs[i - 1][0]
            touch |= near(px, prev) | near(prev, px)
    return ink, accent, touch, x


def ascii_word(ink, accent, touch, width):
    ys = [y for _, y in ink] + [0]
    return ["".join("X" if p in touch else "*" if p in accent else "#" if p in ink else "."
                    for p in ((x, y) for x in range(width))) for y in range(min(ys), max(ys) + 1)]


def report(font, pairs, words):
    print("=" * 72)
    print(font["name"])
    for bch, ach in pairs:
        base, acc = pixels(font, slot(bch)), pixels(font, slot(ach))
        (pb, mb), (pa, ma) = base, acc
        print(f"\n  {bch} slot {slot(bch):#04x} {mb}")
        print(f"  {ach} slot {slot(ach):#04x} {ma}")
        print(ascii_pair(bch, ach, base, acc))
        order = lambda s: sorted(s, key=lambda p: (p[1], p[0]))
        print(f"    added by {ach}: {order(pa - pb)}")
        print(f"    missing from {ach}: {order(pb - pa) or 'none'}")
        print(f"    advance {mb['xa']} -> {ma['xa']}; {ach} ink outside its cell: "
              f"{order(p for p in pa if not 0 <= p[0] < ma['xa']) or 'none'}")
        before, after = introduced_touches(font, bch, ach)
        print(f"    touches added after {ach}:  {' '.join(map(label, after)) or 'none'}")
        print(f"    touches added before {ach}: {' '.join(map(label, before)) or 'none'}")
    print("\n  words  (# ink, * accent-only ink, X ink touching its neighbour)")
    for w in words:
        ink, accent, touch, width = layout(font, w, pairs)
        print(f"    {w}  {width}px")
        for r in ascii_word(ink, accent, touch, width):
            print("      " + r)


# --- PNG proof sheet --------------------------------------------------------

BG, CELL, OUTSIDE, GRID = (0, 0, 0), (40, 40, 40), (14, 14, 14), (24, 24, 24)
INK, ACCENT, MISSING, TOUCH, BASELINE = (235, 235, 235), (255, 176, 0), (0, 190, 255), (255, 60, 60), (70, 110, 255)


def png(fonts, pairs, words, path):
    from PIL import Image, ImageDraw, ImageFont
    try:
        txt = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 14)
    except OSError:
        txt = ImageFont.load_default()
    S, WS, PAD = 14, 6, 12
    blocks = []

    def text_block(s, colour=(200, 200, 200)):
        img = Image.new("RGB", (int(txt.getlength(s)) + 2 * PAD, 22), BG)
        ImageDraw.Draw(img).text((PAD, 3), s, font=txt, fill=colour)
        return img

    def glyph_panel(d, ox, glyph, other, colour_extra, x0, x1, y0, y1):
        px, m = glyph
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                X, Y = ox + (x - x0) * S, (y - y0) * S
                inside = 0 <= x < m["xa"]
                fill = CELL if inside else OUTSIDE
                if (x, y) in px:
                    fill = colour_extra if (x, y) not in other else INK
                d.rectangle([X, Y, X + S - 1, Y + S - 1], fill=fill, outline=GRID)
                if (x, y) in px and not inside:
                    d.rectangle([X, Y, X + S - 1, Y + S - 1], outline=TOUCH, width=2)
        by = (0 - y0 + 1) * S
        d.line([ox, by, ox + (x1 - x0 + 1) * S, by], fill=BASELINE, width=2)

    blocks.append(text_block("amber: ink only in the accented letter   cyan: ink only in the base letter   "
                             "red: ink outside the advance cell / touching a neighbour   blue: baseline"))
    for font in fonts:
        blocks.append(text_block(font["name"], (255, 255, 255)))
        for bch, ach in pairs:
            base, acc = pixels(font, slot(bch)), pixels(font, slot(ach))
            x0, x1, y0, y1 = frame(base, acc)
            w, h = (x1 - x0 + 1) * S, (y1 - y0 + 2) * S
            img = Image.new("RGB", (2 * PAD + 2 * w + 3 * S + 260, h), BG)
            d = ImageDraw.Draw(img)
            glyph_panel(d, PAD, base, acc[0], MISSING, x0, x1, y0, y1)
            glyph_panel(d, PAD + w + 3 * S, acc, base[0], ACCENT, x0, x1, y0, y1)
            d.text((PAD + 2 * w + 5 * S, S), f"{bch}  advance {base[1]['xa']}\n{ach}  advance {acc[1]['xa']}",
                   font=txt, fill=(200, 200, 200))
            blocks.append(img)
        for word in words:
            ink, accent, touch, width = layout(font, word, pairs)
            ys = [y for _, y in ink] + [0]
            y0, y1 = min(ys), max(ys)
            img = Image.new("RGB", (2 * PAD + max(width * WS, 160) + 120, (y1 - y0 + 2) * WS), BG)
            d = ImageDraw.Draw(img)
            for (x, y) in ink:
                colour = TOUCH if (x, y) in touch else ACCENT if (x, y) in accent else INK
                X, Y = PAD + x * WS, (y - y0) * WS
                d.rectangle([X, Y, X + WS - 1, Y + WS - 1], fill=colour)
            d.text((2 * PAD + max(width * WS, 160), 0), word, font=txt, fill=(160, 160, 160))
            blocks.append(img)
        blocks.append(Image.new("RGB", (1, PAD), BG))
    sheet = Image.new("RGB", (max(b.width for b in blocks), sum(b.height + 4 for b in blocks)), BG)
    y = 0
    for b in blocks:
        sheet.paste(b, (0, y))
        y += b.height + 4
    sheet.save(path)
    print(f"\nwrote {path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("fonts", nargs="*", help="font headers (default: the three Latin text faces)")
    ap.add_argument("--pair", nargs=2, action="append", metavar=("BASE", "ACCENTED"))
    ap.add_argument("--words", nargs="+")
    ap.add_argument("--png", metavar="PATH", help="also write a zoomed proof sheet")
    args = ap.parse_args()
    paths = args.fonts or [os.path.join(ROOT, f) for f in DEFAULT_FONTS]
    pairs = [tuple(p) for p in args.pair] if args.pair else DEFAULT_PAIRS
    words = args.words or (DEFAULT_WORDS if not args.pair else [])
    fonts = [parse(p) for p in paths]
    for font in fonts:
        report(font, pairs, words)
    if args.png:
        png(fonts, pairs, words, args.png)


if __name__ == "__main__":
    main()
