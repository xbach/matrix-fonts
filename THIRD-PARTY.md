# Third-party notices

## Departure Mono

The glyph shapes in this repository are rasterised from the **Departure Mono**
typeface. Upstream: <https://departuremono.com> — <https://github.com/rektdeckard/departure-mono>

Departure Mono is distributed under the MIT License, reproduced in full below as
that license requires. The MIT terms cover the upstream typeface; the conversion
work, hand-tuned glyph metrics and ISO-8859-2 layout in this repository are
GPL-3.0 (see LICENSE), which MIT permits.

```
MIT License

Copyright (c) 2024 Helena Zhang & Tobias Fried

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Conversion toolchain

Not redistributed here, but these produced the files and are the tools you need
to regenerate them:

- [fontconvert8-iso8859-2](https://github.com/petrbrouzda/fontconvert8-iso8859-2)
  by Petr Brouzda — the 8-bit `fontconvert` fork that emits the 0x20-0xDF range,
  with Apple Silicon fixes.
- [Michel Deslierres](https://sigmdel.ca/michel/program/misc/gfxfont_8bit_en.html)
  — the GFX Latin 8-bit scheme and the original UTF-8 to ISO-8859-2 conversion code.
- [Adafruit GFX Font Customiser](https://tchapi.github.io/Adafruit-GFX-Font-Customiser/)
  by tchapi — for hand-tuning individual glyphs after conversion.
