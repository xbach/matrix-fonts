#!/usr/bin/env python3
"""Render a proof sheet for the Cyrillic 5pt font: 1x pixels and a zoomed grid.

Draws through the same glyph data the firmware would, so what you see is what
the panel draws — including the 128x32 panel-width strips at the bottom, which
are the only view that answers "is this legible at size".
"""
import importlib.util, os
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("mk", os.path.join(HERE, "make_cyrillic.py"))
mk = importlib.util.module_from_spec(spec); spec.loader.exec_module(mk)
G = mk.build()
BASE, ROW = 9, 12          # baseline row, line height


W_LIM, H_LIM = 10**6, 10**6


def draw_text(px, text, ox, oy, colour=(255, 255, 255)):
    x = ox
    for ch in text:
        try: code = ch.encode("cp1251")[0]
        except Exception: x += 6; continue
        if code not in G: x += 6; continue
        art, (xa, xo, yo) = G[code]
        top = BASE + yo
        for i, line in enumerate(art):
            for j, c in enumerate(line):
                if c != "#":
                    continue
                X, Y = x + xo + j, oy + top + i
                if 0 <= X < W_LIM and 0 <= Y < H_LIM:      # clip like the panel does
                    px[X, Y] = colour
        x += xa
    return x


def sheet():
    lines = [
        ("АБВГДЕЁЖЗИЙКЛМНОП", (255,255,255)),
        ("РСТУФХЦЧШЩЪЫЬЭЮЯ",  (255,255,255)),
        ("абвгдеёжзийклмноп", (160,220,255)),
        ("рстуфхцчшщъыьэюя",  (160,220,255)),
        ("ҐЄІЇ ґєії  0123456789", (255,200,120)),
        ("Спокойная ночь", (120,255,160)),
        ("Океан Ельзи",   (120,255,160)),
        ("Їжак ґедзь Євро", (120,255,160)),
        ("Prilis zlutoucky", (200,200,200)),
    ]
    W, H = 130, ROW * len(lines) + 4
    img = Image.new("RGB", (W, H), (0, 0, 0))
    px = img.load()
    for i, (t, c) in enumerate(lines):
        draw_text(px, t, 1, 2 + i * ROW, c)
    return img


def panel_strips():
    """Exactly 128x32 — one real panel frame per strip, 4 rows of 8px."""
    frames = [
        ["Спокойная ночь", "Kino", "Океан Ельзи", "Обійми"],
        ["ЁЖИК ЩУКА ЪЫЬ",  "фывапролджэ", "ЯЧСМИТЬБЮ", "Їжак ґедзь Євро"],
    ]
    out = []
    for f in frames:
        global W_LIM, H_LIM
        W_LIM, H_LIM = 128, 32
        img = Image.new("RGB", (128, 32), (0, 0, 0)); px = img.load()
        for r, t in enumerate(f):
            draw_text(px, t, 0, r * 8 + 7 - BASE)   # ROW_H=8, baseline 7 within the row
        W_LIM, H_LIM = 10**6, 10**6
        out.append(img)
    return out


if __name__ == "__main__":
    s = sheet()
    scale = 6
    big = s.resize((s.width * scale, s.height * scale), Image.NEAREST)
    d = ImageDraw.Draw(big)
    for gx in range(0, big.width, scale):
        d.line([(gx, 0), (gx, big.height)], fill=(28, 28, 28))
    for gy in range(0, big.height, scale):
        d.line([(0, gy), (big.width, gy)], fill=(28, 28, 28))
    big.save(os.path.join(HERE, "..", "preview-cyrillic-5pt.png"))

    strips = panel_strips()
    SC = 5
    total = Image.new("RGB", (128 * SC, len(strips) * (32 * SC + 8)), (18, 18, 18))
    for i, st in enumerate(strips):
        total.paste(st.resize((128 * SC, 32 * SC), Image.NEAREST), (0, i * (32 * SC + 8)))
    total.save(os.path.join(HERE, "..", "preview-cyrillic-panel.png"))
    print("wrote preview-cyrillic-5pt.png and preview-cyrillic-panel.png")
