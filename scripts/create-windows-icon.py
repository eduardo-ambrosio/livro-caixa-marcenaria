"""Gera os arquivos PNG e ICO do aplicativo a partir de uma imagem transparente."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image


ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)
CANVAS_SIZE = 1024
PADDING_RATIO = 0.08


def create_icon(source_path: Path, png_path: Path, ico_path: Path) -> None:
    source = Image.open(source_path).convert("RGBA")
    alpha = source.getchannel("A")
    bounds = alpha.getbbox()
    if bounds is None:
        raise ValueError("A imagem de origem está totalmente transparente.")

    symbol = source.crop(bounds)
    available = round(CANVAS_SIZE * (1 - 2 * PADDING_RATIO))
    symbol.thumbnail((available, available), Image.Resampling.LANCZOS)

    canvas = Image.new("RGBA", (CANVAS_SIZE, CANVAS_SIZE), (0, 0, 0, 0))
    position = (
        (CANVAS_SIZE - symbol.width) // 2,
        (CANVAS_SIZE - symbol.height) // 2,
    )
    canvas.alpha_composite(symbol, position)

    png_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(png_path, "PNG", optimize=True)
    canvas.save(ico_path, "ICO", sizes=[(size, size) for size in ICON_SIZES])


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit(
            "Uso: create-windows-icon.py ORIGEM.png DESTINO.png DESTINO.ico"
        )
    create_icon(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))


if __name__ == "__main__":
    main()
