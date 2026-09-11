#!/usr/bin/env python3
"""Render a full character-map proof sheet for each GFX font header.

One PNG per font: every slot from first to last in a 16-column grid, decoded from
the header itself, so it shows what the firmware draws rather than what a generator
intended. Each cell is labelled with its slot and the character(s) the firmware sends
to that slot. A strip of sample text at the bottom renders at panel scale.

  python3 tools/font_map.py                              # all fonts -> font-maps/
  python3 tools/font_map.py DepartureMono5pt8b.h --zoom 12

Cell legend
  white       ink
  orange      ink outside the advance cell [0, xAdvance) - it overlaps a neighbour
  red line    baseline (a glyph's bottom row normally sits just above it)
  blue        cursor start (x=0) and xAdvance
  shaded      rows outside ROW_BAND, which a panel text row erases
  dim label   no UTF-8 character reaches this slot through the firmware mapping

Slot labels: the Latin faces follow gfxlatin2.cpp - ASCII at its own code, and
recode()'s ISO-8859-2 value less 0x20 above that, including its deliberate swaps and
the Latin-1 codepoints it passes through. If that source is not found next to this
repo, the plain ISO-8859-2 codec is used and the sheet says so. The Cyrillic face is
CP1251 at its own code.
"""
import argparse, os, re, sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from compare_glyphs import parse, pixels  # noqa: E402

FONTS = ["DepartureMono4pt8b.h", "DepartureMono5pt8b.h", "DepartureMonoCondensed5pt8b.h",
         "DepartureWeather4pt8b.h", "DepartureMonoCyrillic5pt8b.h"]
GFXLATIN2 = os.path.join(ROOT, "..", "spojboard-firmware", "src", "utils", "gfxlatin2.cpp")

# Rows a text row keeps, relative to the baseline, inclusive. spojboard and noticeboard
# draw 8px rows with the baseline on the last one (-7..0); beerboard's band is -6..+1.
ROW_BAND = (-7, 0)
ROW_BAND_NOTE = "shaded rows fall outside -7..0 (spojboard, noticeboard); beerboard keeps -6..+1"

# Weather face: slot -> what the firmwares draw it for (spojboard DisplayManager.cpp
# mapWeatherCodeToIcon and platform arrows; noticeboard picks the letter via [w] markup).
WEATHER_ICONS = {0x61: "sun", 0x62: "sun+cloud", 0x63: "cloud", 0x64: "rain", 0x65: "snow",
                 0x66: "fog", 0x67: "drizzle", 0x74: "storm",
                 0x31: "N", 0x32: "NE/up", 0x33: "E", 0x34: "SE/down", 0x35: "S", 0x36: "SW", 0x37: "W", 0x38: "NW"}

SAMPLES = {
    "latin": ["Příliš žluťoučký kůň úpěl ďábelské ódy", "PŘÍLIŠ ŽLUŤOUČKÝ KŮŇ ÚPĚL ĎÁBELSKÉ ÓDY",
              "Ľúbostné ťahy ôsmich väčších", "Größe Übermäßig ß ẞ", "Zażółć gęślą jaźń ZAŻÓŁĆ",
              "Árvíztűrő tükörfúrógép ÁRVÍZTŰRŐ", "0123456789 12° -3° 14:05 +/-*=?!.,;:()[]'\"&%#@$"],
    "cyrillic": ["Съешь же ещё этих мягких", "французских булок, да выпей чаю",
                 "Чуєш їх, доцю, га? Кумедна ж ти,", "прощайся без ґольфів! ЁЇЄІҐ", "0123456789 12° 14:05"],
    "weather": ["a b c d e f g t", "1 2 3 4 5 6 7 8"],
}

BG, CELL_BG, GAP = (18, 18, 20), (8, 8, 10), (34, 34, 38)
INK, OVER, BASE, ADV, SHADE = (240, 240, 235), (255, 150, 40), (200, 60, 60), (70, 120, 220), (40, 20, 20)
TEXT, DIM = (210, 210, 210), (110, 110, 110)


def load_font(size):
    for p in ("/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            pass
    return ImageFont.load_default()


def recode_table(path):
    """Unicode codepoint -> ISO code, read from recode()'s switch.

    Every `return` closes the pending run of `case` labels, whatever it returns: the
    disabled INVALIDATE_OVERWRITTEN_LATIN_1_CHARS block ends in a non-literal return,
    and carrying its labels forward would attach eight Latin-1 codepoints to Ą.
    """
    try:
        src = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return None
    table, pending = {}, []
    for m in re.finditer(r"case\s+(0x[0-9A-Fa-f]+)\s*:|return\b([^;]*);", src):
        if m.group(1):
            pending.append(int(m.group(1), 16))
            continue
        value = m.group(2).strip()
        if re.fullmatch(r"0x[0-9A-Fa-f]+", value):
            for cp in pending:
                table[cp] = int(value, 16)
        pending = []
    return table or None


def iso_char(slot):
    return chr(slot) if slot < 0x80 else bytes([slot + 0x20]).decode("iso-8859-2")


def latin_maps(table):
    """(slot -> label chars, char -> slot, unreachable slots) for the Latin faces."""
    to_slot = {chr(cp): cp for cp in range(0x20, 0x80)}
    if table:
        for cp, code in table.items():
            if 0xA0 <= code <= 0xFF:
                to_slot[chr(cp)] = code - 0x20
        for cp in range(0xA0, 0x100):          # Latin-1 codepoints recode() passes through
            if cp not in table:
                to_slot.setdefault(chr(cp), cp - 0x20)
    else:
        for code in range(0xA0, 0x100):
            to_slot[bytes([code]).decode("iso-8859-2")] = code - 0x20
    by_slot = {}
    for ch, slot in to_slot.items():
        by_slot.setdefault(slot, []).append(ch)
    labels, unreachable = {}, set()
    for slot in range(0x20, 0xE0):
        chars = by_slot.get(slot, [])
        if not chars:
            labels[slot], _ = [iso_char(slot)], unreachable.add(slot)
            continue
        iso = iso_char(slot)
        # the ISO-8859-2 letter first, then letters recode() maps explicitly, then passthrough
        chars.sort(key=lambda ch: (ch != iso, not (table and ord(ch) in table), ord(ch)))
        labels[slot] = chars[:2]
    return labels, to_slot, unreachable


def cyrillic_maps():
    labels, to_slot = {}, {}
    for code in range(0x20, 0x100):
        try:
            ch = bytes([code]).decode("cp1251")
        except UnicodeDecodeError:
            continue
        labels[code] = [ch]
        to_slot[ch] = code
    return labels, to_slot, set()


def show(ch):
    if ch == " ":
        return "SP"
    if ch == "\x7f":
        return "DEL"
    if not ch.isprintable() or ch.isspace():
        return f"U+{ord(ch):04X}"
    return ch


def frame(font):
    xs0, xs1, ys0, ys1 = [0], [1], [0], [0]
    for c in range(font["first"], font["last"] + 1):
        px, m = pixels(font, c)
        xs1.append(m["xa"])
        for x, y in px:
            xs0.append(x); xs1.append(x + 1); ys0.append(y); ys1.append(y)
    return min(xs0), max(xs1), min(ys0), max(ys1)


def draw_glyph(d, font, code, ox, oy, z, fr, band, gap=True):
    x0, x1, y0, y1 = fr
    px, m = pixels(font, code)
    if band:
        for y in range(y0, y1 + 1):
            if not band[0] <= y <= band[1]:
                d.rectangle([ox, oy + (y - y0) * z, ox + (x1 - x0) * z - 1, oy + (y - y0 + 1) * z - 1], fill=SHADE)
    for x, y in px:
        X, Y = ox + (x - x0) * z, oy + (y - y0) * z
        colour = INK if 0 <= x < m["xa"] else OVER
        inset = 1 if gap and z >= 6 else 0
        d.rectangle([X, Y, X + z - 1 - inset, Y + z - 1 - inset], fill=colour)
    return m


def sheet(fn, zoom, out_dir, table, band):
    font = parse(os.path.join(ROOT, fn))
    kind = "cyrillic" if "Cyrillic" in fn else ("weather" if "Weather" in fn else "latin")
    labels, to_slot, unreachable = cyrillic_maps() if kind == "cyrillic" else latin_maps(table)
    fr = frame(font)
    x0, x1, y0, y1 = fr
    gw, gh = (x1 - x0) * zoom, (y1 - y0 + 1) * zoom
    f_hex, f_ch, f_head = load_font(11), load_font(14), load_font(16)
    cw, ch_ = max(gw + 16, 84), gh + 44
    first_row, last_row = font["first"] // 16, font["last"] // 16
    left, top = 56, 96
    samples = SAMPLES[kind]
    sz = max(2, zoom // 3)
    line_h = (y1 - y0 + 3) * sz
    W = left + 16 * cw + 16
    H = top + (last_row - first_row + 1) * ch_ + (len(samples) * line_h + 48 if samples else 16)
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    enc = {"latin": "Latin 2: slot = recode() ISO-8859-2 value - 0x20" + ("" if table else " (plain ISO-8859-2 codec: gfxlatin2.cpp not found)"),
           "cyrillic": "CP1251 at its own code; empty slots are letters gfxcyr.cpp maps but this face does not draw",
           "weather": "Latin 2 slots; the firmwares draw only the labelled icons and arrows from this face"}[kind]
    d.text((left, 14), f"{fn}   slots {font['first']:#04x}-{font['last']:#04x} ({len(font['glyphs'])})   bitmap {len(font['bitmap'])} bytes", fill=TEXT, font=f_head)
    d.text((left, 38), enc, fill=DIM, font=f_hex)
    d.text((left, 56), "white ink · orange ink outside the advance cell · red baseline · blue cursor start / xAdvance · dim label: unreachable"
           + (f" · {ROW_BAND_NOTE}" if band else ""), fill=DIM, font=f_hex)
    for col in range(16):
        d.text((left + col * cw + cw // 2 - 4, top - 18), f"{col:X}", fill=DIM, font=f_hex)

    degree = pixels(font, 0x90)[0] if kind != "cyrillic" else None
    for code in range(font["first"], font["last"] + 1):
        r, c = code // 16 - first_row, code % 16
        cx, cy = left + c * cw, top + r * ch_
        if c == 0:
            d.text((8, cy + gh // 2), f"0x{code // 16:X}_", fill=DIM, font=f_hex)
        d.rectangle([cx + 2, cy, cx + cw - 3, cy + ch_ - 6], fill=CELL_BG, outline=GAP)
        gx, gy = cx + (cw - gw) // 2, cy + 6
        m = draw_glyph(d, font, code, gx, gy, zoom, fr, band)
        by = gy + (0 - y0 + 1) * zoom
        d.line([gx - 3, by, gx + gw + 2, by], fill=BASE, width=1)
        for ax in (0, m["xa"]):
            X = gx + (ax - x0) * zoom
            d.line([X, gy - 3, X, gy + gh + 2], fill=ADV, width=1)
        empty = m["w"] == 0 or m["h"] == 0
        lab = " ".join(show(x) for x in labels.get(code, [])) or "·"
        if kind == "weather" and code in WEATHER_ICONS:
            lab = f"{chr(code)} {WEATHER_ICONS[code]}"
        elif code == 0xB0 and degree and pixels(font, 0xB0)[0] == degree:
            lab = "° raw"
        if empty:
            lab += " (empty)"
        dim = empty or code in unreachable
        d.text((cx + 6, cy + gh + 12), f"{code:02X}", fill=DIM, font=f_hex)
        d.text((cx + 26, cy + gh + (12 if len(lab) > 5 else 9)), lab, fill=DIM if dim else TEXT, font=f_hex if len(lab) > 5 else f_ch)

    if samples:
        sy = top + (last_row - first_row + 1) * ch_ + 16
        d.text((left, sy), f"samples at {sz}x (red box: character with no slot)", fill=DIM, font=f_hex)
        sy += 16
        for text in samples:
            x = left
            for chr_ in text:
                slot = to_slot.get(chr_)
                if slot is None or not font["first"] <= slot <= font["last"]:
                    d.rectangle([x, sy, x + 4 * sz, sy + (y1 - y0) * sz], outline=(120, 40, 40))
                    x += 5 * sz
                    continue
                m = draw_glyph(d, font, slot, x, sy, sz, fr, band, gap=False)
                x += m["xa"] * sz
            sy += line_h

    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, os.path.splitext(fn)[0] + ".png")
    img.save(out)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("fonts", nargs="*", help="font headers (default: all five)")
    ap.add_argument("--zoom", type=int, default=8)
    ap.add_argument("--out-dir", default=os.path.join(ROOT, "font-maps"))
    ap.add_argument("--gfxlatin2", default=GFXLATIN2, help="recode() source used for the Latin slot labels")
    a = ap.parse_args()
    table = recode_table(a.gfxlatin2)
    if table is None:
        print(f"warning: {a.gfxlatin2} not found, labelling Latin slots with the plain ISO-8859-2 codec", file=sys.stderr)
    for fn in a.fonts or FONTS:
        print(sheet(os.path.basename(fn), a.zoom, a.out_dir, table, ROW_BAND))


if __name__ == "__main__":
    main()
