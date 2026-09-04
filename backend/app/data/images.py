"""Synthetic evidence-image factory.

Creates small deterministic PNGs so Stage 1's image forensics has real
pixels to hash. Transform kinds map to the generator's personas:
- ``copy``     -> exact reuse (crude fraud)
- ``noise``    -> near-duplicate reuse
- ``recolor``  -> lightly disguised reuse
- ``unique``   -> honest re-shoot of the order scene
- ``ai``       -> AI-flavoured procedural artefacts
"""

from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

SIZE = 256


def _base_scene(seed: int) -> Image.Image:
    """A believable 'product photo' stand-in: gradient + product-ish shapes."""
    rng = random.Random(seed)
    top = (rng.randint(30, 80), rng.randint(40, 90), rng.randint(50, 110))
    bottom = (rng.randint(120, 200), rng.randint(110, 190), rng.randint(100, 180))
    img = Image.new("RGB", (SIZE, SIZE))
    px = img.load()
    for y in range(SIZE):
        t = y / (SIZE - 1)
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        for x in range(SIZE):
            px[x, y] = (r, g, b)
    draw = ImageDraw.Draw(img)
    # 'product' box
    cx, cy = rng.randint(80, 176), rng.randint(90, 170)
    w, h = rng.randint(40, 90), rng.randint(30, 70)
    shade = (rng.randint(40, 90), rng.randint(40, 90), rng.randint(50, 100))
    draw.rounded_rectangle(
        [cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2],
        radius=8,
        fill=shade,
        outline=(230, 230, 235),
        width=2,
    )
    # label
    draw.ellipse(
        [cx - 12, cy - 12, cx + 12, cy + 12],
        fill=(235, 235, 240),
    )
    # soft shadow
    img = img.filter(ImageFilter.GaussianBlur(0.6))
    return img


def _ai_artefacts(img: Image.Image, seed: int) -> Image.Image:
    """Procedural artefacts that mimic common generative tells."""
    rng = random.Random(seed)
    overlay = Image.new("L", (SIZE, SIZE), 0)
    od = ImageDraw.Draw(overlay)
    step = rng.choice([8, 12, 16])  # checkerboard banding
    for i in range(0, SIZE, step):
        for j in range(0, SIZE, step):
            if (i // step + j // step) % 2 == 0:
                od.rectangle([i, j, i + step, j + step], fill=255)
    # suspiciously perfect symmetry
    flipped = img.transpose(Image.FLIP_LEFT_RIGHT)
    img = Image.blend(img, flipped, 0.35)
    # darken alternating tiles (checkerboard banding artefact)
    darkened = img.point(lambda v: max(0, v - rng.randint(18, 26)))
    img = Image.composite(darkened, img, overlay)
    return img


def _add_noise(img: Image.Image, seed: int, strength: int = 14) -> Image.Image:
    rng = random.Random(seed)
    px = img.load()
    for _ in range(SIZE * SIZE // 6):
        x, y = rng.randrange(SIZE), rng.randrange(SIZE)
        r, g, b = px[x, y]
        d = rng.randint(-strength, strength)
        px[x, y] = (max(0, min(255, r + d)), max(0, min(255, g + d)), max(0, min(255, b + d)))
    return img


def generate_evidence_image(
    out_path: str | Path,
    *,
    seed: int,
    kind: str = "unique",
    source_path: str | Path | None = None,
) -> Path:
    """Generate one evidence image at ``out_path``.

    kind:
        unique   – fresh scene (honest claim / new fraudster)
        copy     – byte-identical reuse of source
        noise    – noisy near-duplicate of source
        recolor  – hue-shifted reuse of source
        ai       – AI-artefact style scene (no source needed)
    """
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    if kind in ("copy", "noise", "recolor"):
        if source_path is None:
            raise ValueError(f"kind={kind!r} requires source_path")
        src = Image.open(source_path).convert("RGB")
        if kind == "copy":
            img = src
        elif kind == "noise":
            img = _add_noise(src, seed, strength=10)
        else:  # recolor
            r, g, b = src.split()
            img = Image.merge("RGB", (b, r, g))
    elif kind == "ai":
        img = _ai_artefacts(_base_scene(seed), seed)
    else:  # unique
        img = _base_scene(seed)

    img.save(out, format="PNG")
    return out
