#!/usr/bin/env python3
"""Fail if a face is not stored in slot order, or if two different characters draw the same pixels.

Both classes were found by hand during the 2026-09-11 review (Asgard RE-0069), and neither shows up
in a diff:

  * A glyph whose bytes sit out of slot order is silently emptied by the next Customiser export and
    then draws its neighbour's pixels - see "Keep every glyph's bitmap stored in slot order" in the
    README. This check proves the file is packed in slot order and that replaying that export rule
    reproduces it byte for byte.
  * A glyph identical to a *different* letter passes every base-vs-accent comparison, because it
    does differ from its own base letter. `S` = `Ś`, `Ź` = `Ż`, `ĺ` = `ľ` and `Ô` = `ő` all got
    through that way.

  python3 tools/check_fonts.py                   # all faces; exit 1 on a problem
  python3 tools/check_fonts.py DepartureMono5pt8b.h
  python3 tools/check_fonts.py --write-baseline  # re-record the accepted identical groups

Identical glyphs that are deliberate (accented capitals drawn at lowercase height, `0` = `O`, the
Cyrillic face's reuse of Latin bitmaps) are listed in tools/duplicate-glyphs.baseline, one group per
line as `<font> <slot> <slot> …`. A group that is not listed fails. Update that file deliberately,
never to silence a surprise: check first whether the two slots are the same letter.
"""
import argparse, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from compare_glyphs import parse, pixels  # noqa: E402

FONTS = ["DepartureMono4pt8b.h", "DepartureMono5pt8b.h", "DepartureMonoCondensed5pt8b.h",
         "DepartureWeather4pt8b.h", "DepartureMonoCyrillic5pt8b.h"]
BASELINE = os.path.join(HERE, "duplicate-glyphs.baseline")
nbytes = lambda w, h: (w * h + 7) // 8


def label(fn, slot):
    """The character a slot stands for, for human-readable output only."""
    try:
        if "Cyrillic" in fn:
            return bytes([slot]).decode("cp1251")
        return chr(slot) if slot < 0x80 else bytes([slot + 0x20]).decode("iso-8859-2")
    except (UnicodeDecodeError, ValueError):
        return "?"


def storage_problems(font):
    """Everything wrong with how this face's bitmap is laid out."""
    g, bm = font["glyphs"], font["bitmap"]
    used, problems = [0] * len(bm), []
    for i, r in enumerate(g):
        end = r[0] + nbytes(r[1], r[2])
        if end > len(bm):
            problems.append(f"slot {i + font['first']:#04x} reads past the end of the bitmap")
        for j in range(r[0], min(end, len(bm))):
            used[j] += 1
    inked = sorted((r[0], i) for i, r in enumerate(g) if nbytes(r[1], r[2]))
    for (_, a), (_, b) in zip(inked, inked[1:]):
        if b < a:
            problems.append(f"slot {b + font['first']:#04x} is stored after {a + font['first']:#04x}: out of slot order")
            break
    if used.count(0):
        problems.append(f"{used.count(0)} dead bytes no glyph reads")
    if any(u > 1 for u in used):
        problems.append(f"{sum(u > 1 for u in used)} bytes read by more than one glyph")
    # replay the export rule: each glyph sized from its offset to the next slot's offset
    out, offs = [], []
    for i in range(len(g)):
        start = g[i][0]
        end = g[i + 1][0] if i + 1 < len(g) else len(bm)
        offs.append(len(out))
        out += bm[start:end] if end > start else []
    if out != bm or offs != [r[0] for r in g]:
        problems.append("a re-export would not reproduce this file: some glyph would lose its bytes")
    return problems


def duplicate_groups(font):
    groups = {}
    for slot in range(font["first"], font["last"] + 1):
        px, m = pixels(font, slot)
        if px:
            groups.setdefault((frozenset(px), m["xa"]), []).append(slot)
    return sorted(v for v in groups.values() if len(v) > 1)


def read_baseline():
    accepted = {}
    if not os.path.exists(BASELINE):
        return accepted
    for line in open(BASELINE, encoding="utf-8"):
        line = line.split("#")[0].strip()
        if not line:
            continue
        parts = line.split()
        accepted.setdefault(parts[0], set()).add(tuple(sorted(int(p, 16) for p in parts[1:])))
    return accepted


def write_baseline(fonts):
    with open(BASELINE, "w", encoding="utf-8") as fh:
        fh.write("# Glyph groups that are deliberately pixel-identical, per face.\n"
                 "# Regenerate with: python3 tools/check_fonts.py --write-baseline\n"
                 "# Before adding a line by hand, check the slots are the same letter - a group of two\n"
                 "# DIFFERENT letters is the bug this check exists to catch.\n")
        for fn in fonts:
            font = parse(os.path.join(ROOT, fn))
            groups = duplicate_groups(font)
            if groups:
                fh.write(f"\n# {fn}\n")
            for slots in groups:
                chars = " ".join(f"{label(fn, s)}" for s in slots)
                fh.write(f"{fn} {' '.join(f'{s:02X}' for s in slots)}   # {chars}\n")
    return BASELINE


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("fonts", nargs="*", help="font headers (default: all five)")
    ap.add_argument("--write-baseline", action="store_true", help="re-record the accepted identical groups")
    a = ap.parse_args()
    fonts = [os.path.basename(f) for f in (a.fonts or FONTS)]
    if a.write_baseline:
        print(f"wrote {write_baseline(fonts)}")
        return 0
    accepted, failed = read_baseline(), False
    for fn in fonts:
        font = parse(os.path.join(ROOT, fn))
        problems = storage_problems(font)
        unexpected = [s for s in duplicate_groups(font) if tuple(s) not in accepted.get(fn, set())]
        for p in problems:
            print(f"FAIL {fn}: {p}")
        for slots in unexpected:
            shown = " = ".join(f"{s:02X} {label(fn, s)}" for s in slots)
            print(f"FAIL {fn}: identical glyphs not in the baseline: {shown}")
        failed = failed or bool(problems or unexpected)
        if not problems and not unexpected:
            print(f"ok   {fn}: slot-ordered, {len(font['bitmap'])} bytes, "
                  f"{len(duplicate_groups(font))} identical groups, all expected")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
