#!/usr/bin/env python3
"""Compose clean machine reference sheets or labeled director boards with Pillow."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageOps

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


LAYOUTS = {
    "three-view": (1, 3, 3),
    "2x2": (2, 2, 4),
    "3x2": (2, 3, 6),
    "3x3": (3, 3, 9),
}


def choose_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path(r"C:\Windows\Fonts\msyh.ttc"),
        Path(r"C:\Windows\Fonts\msyhbd.ttc"),
        Path(r"C:\Windows\Fonts\arial.ttf"),
    ]
    for path in candidates:
        if path.is_file():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                pass
    return ImageFont.load_default()


def fit_image(source: Image.Image, width: int, height: int, background: tuple[int, int, int]) -> Image.Image:
    image = ImageOps.exif_transpose(source).convert("RGB")
    contained = ImageOps.contain(image, (max(1, width), max(1, height)), Image.Resampling.LANCZOS)
    cell = Image.new("RGB", (width, height), background)
    x = (width - contained.width) // 2
    y = (height - contained.height) // 2
    cell.paste(contained, (x, y))
    return cell


def load_metadata(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    metadata_path = Path(path).expanduser().resolve()
    with metadata_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("metadata JSON must be an object")
    return data


def truncate(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> str:
    if draw.textlength(text, font=font) <= max_width:
        return text
    suffix = "…"
    candidate = text
    while candidate and draw.textlength(candidate + suffix, font=font) > max_width:
        candidate = candidate[:-1]
    return candidate + suffix


def compose(args: argparse.Namespace) -> Path:
    rows, cols, capacity = LAYOUTS[args.layout]
    inputs = [Path(value).expanduser().resolve() for value in args.input]
    if len(inputs) != capacity:
        raise ValueError(f"layout {args.layout} requires exactly {capacity} inputs; got {len(inputs)}")
    missing = [str(path) for path in inputs if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing input images: " + ", ".join(missing))

    labels = args.label or []
    if args.mode == "director" and labels and len(labels) != capacity:
        raise ValueError(f"director labels must be omitted or match input count ({capacity})")

    width, height = args.width, args.height
    if width < 320 or height < 240:
        raise ValueError("board dimensions are too small")
    background = ImageColor.getrgb(args.background)
    canvas = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(canvas)

    machine = args.mode == "machine"
    outer = 0 if machine else max(12, round(min(width, height) * 0.018))
    gap = max(2, round(min(width, height) * (0.006 if machine else 0.012)))
    header = 0 if machine else max(64, round(height * 0.085))
    footer = 0 if machine else (max(42, round(height * 0.052)) if args.metadata_json else 0)
    caption = 0 if machine else max(36, round(height * 0.05))

    grid_x = outer
    grid_y = outer + header
    grid_width = width - 2 * outer
    grid_height = height - 2 * outer - header - footer
    cell_width = (grid_width - gap * (cols - 1)) // cols
    cell_height_total = (grid_height - gap * (rows - 1)) // rows
    image_height = cell_height_total - caption
    if cell_width <= 0 or image_height <= 0:
        raise ValueError("board dimensions cannot hold the requested layout")

    title_font = choose_font(max(22, round(height * 0.034)))
    label_font = choose_font(max(15, round(height * 0.022)))
    meta_font = choose_font(max(12, round(height * 0.017)))

    if not machine:
        title = args.title or "Director Board"
        draw.text((outer, outer), title, fill=(22, 22, 22), font=title_font)
        subtitle = f"{args.layout} · {width}×{height} · {capacity} panels"
        draw.text((outer, outer + round(header * 0.52)), subtitle, fill=(90, 90, 90), font=meta_font)

    for index, path in enumerate(inputs):
        row, col = divmod(index, cols)
        x = grid_x + col * (cell_width + gap)
        y = grid_y + row * (cell_height_total + gap)
        with Image.open(path) as source:
            fitted = fit_image(source, cell_width, image_height, background)
        canvas.paste(fitted, (x, y))
        if not machine:
            draw.rectangle((x, y, x + cell_width - 1, y + image_height - 1), outline=(72, 72, 72), width=2)
            label = labels[index] if labels else f"PANEL {index + 1:02d}"
            label = truncate(draw, label, label_font, cell_width - 16)
            draw.text((x + 8, y + image_height + max(4, caption // 6)), label, fill=(28, 28, 28), font=label_font)

    if not machine and args.metadata_json:
        metadata = load_metadata(args.metadata_json)
        parts = [f"{key}: {value}" for key, value in metadata.items()]
        line = "  |  ".join(parts)
        line = truncate(draw, line, meta_font, width - 2 * outer)
        draw.text((outer, height - outer - footer + max(4, footer // 4)), line, fill=(70, 70, 70), font=meta_font)

    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    suffix = output.suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise ValueError("output extension must be .png, .jpg, .jpeg, or .webp")
    save_kwargs: dict[str, Any] = {}
    if suffix in {".jpg", ".jpeg"}:
        save_kwargs.update(quality=args.quality, subsampling=0)
    elif suffix == ".webp":
        save_kwargs.update(quality=args.quality, method=6)
    canvas.save(output, **save_kwargs)
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layout", choices=LAYOUTS, required=True)
    parser.add_argument("--mode", choices=["machine", "director"], default="director")
    parser.add_argument("--input", action="append", required=True, help="Repeat once per panel")
    parser.add_argument("--output", required=True)
    parser.add_argument("--label", action="append", help="Repeat once per panel")
    parser.add_argument("--title")
    parser.add_argument("--metadata-json")
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--background", default="#ECECEC")
    parser.add_argument("--quality", type=int, default=95)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        output = compose(args)
        with Image.open(output) as result:
            payload = {
                "output": str(output),
                "width": result.width,
                "height": result.height,
                "mode": args.mode,
                "layout": args.layout,
            }
        print(json.dumps(payload, ensure_ascii=False))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
