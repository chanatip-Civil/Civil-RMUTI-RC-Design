"""Create the Windows icon (``packaging/build/app.ico``) from the program logo.

Usage::

    python packaging/make_icon.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
LOGO = ROOT / "app" / "gui" / "resources" / "rmuti_logo.png"
OUTPUT = ROOT / "packaging" / "build" / "app.ico"
SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def make_icon(source: Path = LOGO, output: Path = OUTPUT) -> Path:
    """Write a multi-resolution .ico file and return its path."""
    image = Image.open(source).convert("RGBA")
    side = max(image.size)
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(image, ((side - image.width) // 2, (side - image.height) // 2), image)
    output.parent.mkdir(parents=True, exist_ok=True)
    square.save(output, format="ICO", sizes=SIZES)
    return output


if __name__ == "__main__":
    print(f"Icon written to {make_icon()}")
