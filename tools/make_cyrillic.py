#!/usr/bin/env python3
"""Generate DepartureMonoCyrillic5pt8b.h from the corrected Latin 5pt font.

Glyph art here is the source of truth. Bach's hand corrections to the emitted
header (2026-09-09: narrower bowl on Ю/ю, я's leg carried to the left edge, Ґ/ґ dropped one row) are
back-ported into the art below, so regenerating reproduces them rather than
reverting them.

Why generated and not converted from the TTF: the Departure Mono vectors do not
rasterise cleanly at 5pt, and the Latin faces in this repo carry a lot of manual
pixel correction. Re-converting would throw that away and reintroduce the same
artefacts. So Cyrillic letters that are shape-identical to a Latin letter REUSE
that corrected bitmap byte-for-byte (А=A, В=B, Е=E, К=K, М=M, Н=H, О=O, Р=P,
С=C, Т=T, Х=X, а=a, е=e, о=o, р=p, с=c, у=y, х=x, і=i), and only the genuinely
Cyrillic shapes are hand-drawn here, in the same idiom.

Codepage is CP1251, deliberately: it is a standard, so the firmware's UTF-8 ->
byte map can be generated from Python's own codec rather than invented, and
every letter Russian and Ukrainian need has a defined slot (Ё Ґ Є І Ї and their
lowercase). ASCII is included at its natural positions so digits, spaces and
punctuation never force a font switch mid-run.

Metrics follow the Latin face exactly:
    caps            5x7, yOff=-6      lowercase        5x5, yOff=-4
    NO DESCENDERS. DisplayManager::drawRow blanks each 8px row band before
    drawing it, so anything below the baseline is erased by the row beneath --
    Latin g/y already render clipped on this panel. For Cyrillic that is not
    cosmetic: the tail is the ONLY thing distinguishing ц from п and щ from ш,
    so those tails sit ON the baseline row, and Д's legs likewise.
    caps + diacritic 5x10, yOff=-9 with a compressed 5-row letterform
    lc + 1-row mark  5x7, yOff=-6     descenders       extend below baseline
    xAdvance 6 everywhere (monospace), yAdvance 12

Usage: python3 tools/make_cyrillic.py [--preview]
"""
import re, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SRC = os.path.join(REPO, "DepartureMono5pt8b.h")
OUT = os.path.join(REPO, "DepartureMonoCyrillic5pt8b.h")

XADV, YADV = 6, 12


def parse_latin():
    src = open(SRC, encoding="utf-8").read()
    data = [int(x, 16) for x in re.findall(
        r"0x([0-9A-Fa-f]{2})",
        re.search(r"Bitmaps\[\]\s*PROGMEM\s*=\s*\{(.*?)\};", src, re.S).group(1))]
    rows = re.findall(
        r"\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(-?\d+),\s*(-?\d+)\s*\}[^/]*//\s*0x([0-9A-Fa-f]{2})",
        re.search(r"Glyphs\[\]\s*PROGMEM\s*=\s*\{(.*?)\};", src, re.S).group(1))
    G = {}
    for off, w, h, xa, xo, yo, code in rows:
        G[int(code, 16)] = tuple(map(int, (off, w, h, xa, xo, yo)))
    def art(fontbyte):
        off, w, h, xa, xo, yo = G[fontbyte]
        out, bit = [], 0
        for _ in range(h):
            out.append("".join(
                "#" if (data[off + ((bit + x) >> 3)] >> (7 - ((bit + x) & 7))) & 1 else "."
                for x in range(w)))
            bit += w
        return out, (xa, xo, yo)
    return art


A = parse_latin()          # A(fontbyte) -> (art_lines, (xAdv, xOff, yOff))
def latin(ch):
    """Reuse a corrected Latin glyph verbatim. ASCII maps 1:1 to its font byte."""
    return A(ord(ch))


def g(art, yoff, xoff=1):
    return ([l for l in art.strip("\n").split("\n")], (XADV, xoff, yoff))


# ---------------------------------------------------------------- hand-drawn
CAP = -6          # plain capital, 7 rows
CAPD = -9         # capital carrying a diacritic, 10 rows
LOW = -4          # plain lowercase, 5 rows
ASC = -6          # lowercase with an ascender, 7 rows

NEW = {
"Б": g("""
#####
#....
#....
####.
#...#
#...#
####.
""", CAP),
"Г": g("""
#####
#....
#....
#....
#....
#....
#....
""", CAP),
"Д": g("""
..###
..#.#
.#..#
.#..#
.#..#
#####
#...#
""", CAP),
"Ж": g("""
#.#.#
#.#.#
.###.
..#..
.###.
#.#.#
#.#.#
""", CAP),
"З": g("""
.###.
#...#
....#
..##.
....#
#...#
.###.
""", CAP),
"И": g("""
#...#
#...#
#..##
#.#.#
##..#
#...#
#...#
""", CAP),
"Й": g("""
.....
.....
.....
.#.#.
.###.
#...#
#..##
#.#.#
##..#
#...#
""", CAPD),
"Л": g("""
.####
.#..#
.#..#
.#..#
.#..#
#...#
#...#
""", CAP),
"П": g("""
#####
#...#
#...#
#...#
#...#
#...#
#...#
""", CAP),
"У": g("""
#...#
#...#
#...#
.#.#.
..#..
..#..
..#..
""", CAP),
"Ф": g("""
..#..
.###.
#.#.#
#.#.#
#.#.#
.###.
..#..
""", CAP),
"Ц": g("""
#...#
#...#
#...#
#...#
#...#
#####
....#
""", CAP),
"Ч": g("""
#...#
#...#
#...#
.####
....#
....#
....#
""", CAP),
"Ш": g("""
#.#.#
#.#.#
#.#.#
#.#.#
#.#.#
#.#.#
#####
""", CAP),
"Щ": g("""
#.#.#
#.#.#
#.#.#
#.#.#
#.#.#
#####
....#
""", CAP),
"Ъ": g("""
##...
.#...
.#...
.###.
.#..#
.#..#
.###.
""", CAP),
"Ы": g("""
#...#
#...#
#...#
##..#
#.#.#
#.#.#
##..#
""", CAP),
"Ь": g("""
#....
#....
#....
####.
#...#
#...#
####.
""", CAP),
"Э": g("""
.###.
#...#
....#
..###
....#
#...#
.###.
""", CAP),
"Ю": g("""
#..#.
#.#.#
#.#.#
###.#
#.#.#
#.#.#
#..#.
""", CAP),
"Я": g("""
.####
#...#
#...#
.####
..#.#
.#..#
#...#
""", CAP),
"Ё": g("""
.....
.....
.....
.#.#.
.....
#####
#....
####.
#....
#####
""", CAPD),
"Є": g("""
.###.
#...#
#....
####.
#....
#...#
.###.
""", CAP),
"Ґ": g("""
.....
....#
#####
#....
#....
#....
#....
#....
""", -7),
"Ї": g("""
.....
.....
.....
.#.#.
.....
#####
..#..
..#..
..#..
#####
""", CAPD),

"б": g("""
..###
.#...
#....
####.
#...#
#...#
####.
""", ASC),
"в": g("""
####.
#...#
####.
#...#
####.
""", LOW),
"г": g("""
#####
#....
#....
#....
#....
""", LOW),
"д": g("""
..###
.#..#
.#..#
#####
#...#
""", LOW),
"ж": g("""
#.#.#
.###.
..#..
.###.
#.#.#
""", LOW),
"з": g("""
.###.
....#
..##.
....#
.###.
""", LOW),
"и": g("""
#...#
#..##
#.#.#
##..#
#...#
""", LOW),
"й": g("""
.#.#.
.###.
#...#
#..##
#.#.#
##..#
#...#
""", ASC),
"к": g("""
#...#
#..#.
###..
#..#.
#...#
""", LOW),
"л": g("""
.####
.#..#
.#..#
.#..#
#...#
""", LOW),
"м": g("""
#...#
##.##
#.#.#
#...#
#...#
""", LOW),
"н": g("""
#...#
#...#
#####
#...#
#...#
""", LOW),
"п": g("""
#####
#...#
#...#
#...#
#...#
""", LOW),
"т": g("""
#####
..#..
..#..
..#..
..#..
""", LOW),
"ф": g("""
..#..
.###.
#.#.#
#.#.#
#.#.#
.###.
..#..
""", CAP),
"ц": g("""
#...#
#...#
#...#
#####
....#
""", LOW),
"ч": g("""
#...#
#...#
.####
....#
....#
""", LOW),
"ш": g("""
#.#.#
#.#.#
#.#.#
#.#.#
#####
""", LOW),
"щ": g("""
#.#.#
#.#.#
#.#.#
#####
....#
""", LOW),
"ъ": g("""
##...
.#...
.###.
.#..#
.###.
""", LOW),
"ы": g("""
#...#
#...#
##..#
#.#.#
##..#
""", LOW),
"ь": g("""
#....
#....
####.
#...#
####.
""", LOW),
"э": g("""
.###.
....#
..###
....#
.###.
""", LOW),
"ю": g("""
#..#.
#.#.#
###.#
#.#.#
#..#.
""", LOW),
"я": g("""
.####
#...#
.####
.#..#
#...#
""", LOW),
"ё": g("""
.#.#.
.....
.###.
#...#
#####
#....
.###.
""", ASC),
"є": g("""
.###.
#....
####.
#....
.###.
""", LOW),
"ґ": g("""
....#
#####
#....
#....
#....
#....
""", -5),
}

# Cyrillic letters whose corrected Latin twin is reused verbatim
REUSE = {"А":"A","В":"B","Е":"E","К":"K","М":"M","Н":"H","О":"O","Р":"P",
         "С":"C","Т":"T","Х":"X","І":"I",
         "а":"a","е":"e","о":"o","р":"p","с":"c","у":"y","х":"x","і":"i"}


def build():
    glyphs = {}
    for b in range(0x20, 0x7F):                      # ASCII, verbatim
        glyphs[b] = latin(chr(b))
    for ch, src in REUSE.items():
        glyphs[ch.encode("cp1251")[0]] = latin(src)
    for ch, spec in NEW.items():
        glyphs[ch.encode("cp1251")[0]] = spec
    return glyphs


def emit(glyphs):
    first, last = 0x20, 0xFF
    bitmaps, table = [], []
    for code in range(first, last + 1):
        if code not in glyphs:
            table.append((len(bitmaps), 0, 0, XADV, 0, 0, None))
            continue
        art, (xa, xo, yo) = glyphs[code]
        w = max(len(l) for l in art) if art else 0
        h = len(art)
        off = len(bitmaps)
        bits = "".join(l.ljust(w, ".") for l in art)
        for i in range(0, len(bits), 8):
            chunk = bits[i:i + 8].ljust(8, ".")
            bitmaps.append(int("".join("1" if c == "#" else "0" for c in chunk), 2))
        table.append((off, w, h, xa, xo, yo, code))

    L = []
    L.append("// Generated by tools/make_cyrillic.py — do not hand-edit.")
    L.append("// Codepage: CP1251 (ASCII 0x20-0x7E at natural positions + Cyrillic).")
    L.append("// Latin-shaped Cyrillic letters reuse the corrected DepartureMono 5pt bitmaps.")
    L.append("")
    L.append("const uint8_t DepartureMono_Cyrillic5pt8bBitmaps[] PROGMEM = {")
    for i in range(0, len(bitmaps), 12):
        L.append("  " + " ".join(f"0x{b:02X}," for b in bitmaps[i:i + 12]))
    L.append("};")
    L.append("")
    L.append("const GFXglyph DepartureMono_Cyrillic5pt8bGlyphs[] PROGMEM = {")
    for i, (off, w, h, xa, xo, yo, code) in enumerate(table):
        note = ""
        if code is not None:
            try:
                ch = bytes([code]).decode("cp1251")
                note = f"  // 0x{code:02X} '{ch}'"
            except Exception:
                note = f"  // 0x{code:02X}"
        else:
            note = "  // unused"
        comma = "," if i < len(table) - 1 else ""
        L.append(f"  {{ {off:5d}, {w:3d}, {h:3d}, {xa:3d}, {xo:3d}, {yo:4d} }}{comma}{note}")
    L.append("};")
    L.append("")
    L.append("const GFXfont DepartureMono_Cyrillic5pt8b PROGMEM = {")
    L.append("    (uint8_t*)DepartureMono_Cyrillic5pt8bBitmaps,")
    L.append("    (GFXglyph*)DepartureMono_Cyrillic5pt8bGlyphs,")
    L.append(f"    0x{first:02X}, 0x{last:02X}, {YADV}}};")
    L.append("")
    L.append(f"// Approx. {len(bitmaps) + len(table) * 7} bytes")
    open(OUT, "w", encoding="utf-8").write("\n".join(L) + "\n")
    return len(bitmaps), len(table)


def preview(glyphs, text):
    rows = [""] * 12
    for ch in text:
        try:
            code = ch.encode("cp1251")[0]
        except Exception:
            continue
        if code not in glyphs:
            continue
        art, (xa, xo, yo) = glyphs[code]
        w = max(len(l) for l in art) if art else 0
        cell = ["." * (w + 1) for _ in range(12)]
        top = 9 + yo                      # baseline at row 9
        for i, line in enumerate(art):
            if 0 <= top + i < 12:
                cell[top + i] = line.ljust(w, ".") + "."
        for r in range(12):
            rows[r] += cell[r]
    return "\n".join(rows)


if __name__ == "__main__":
    G = build()
    nb, ng = emit(G)
    print(f"wrote {OUT}")
    print(f"  {ng} glyph slots, {nb} bitmap bytes")
    if "--preview" in sys.argv:
        for line in ("Спокойная ночь", "Океан Ельзи", "Ёжик Щука フ".replace("フ",""),
                     "ЪЫЬЭЮЯ ъыьэюя", "Їжак ґедзь Євро"):
            print(f"\n{line}")
            print(preview(G, line))
