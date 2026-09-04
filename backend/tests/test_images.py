"""Tests for the synthetic evidence-image factory."""

from pathlib import Path

import imagehash
from PIL import Image

from app.data.images import generate_evidence_image


def _hash(p: Path) -> imagehash.ImageHash:
    return imagehash.phash(Image.open(p))


def test_unique_image_is_created(tmp_path: Path) -> None:
    out = tmp_path / "a.png"
    generate_evidence_image(out, seed=1, kind="unique")
    assert out.exists()
    assert Image.open(out).size == (256, 256)


def test_copy_is_byte_identical(tmp_path: Path) -> None:
    src = tmp_path / "src.png"
    dup = tmp_path / "dup.png"
    generate_evidence_image(src, seed=2, kind="unique")
    generate_evidence_image(dup, seed=3, kind="copy", source_path=src)
    assert src.read_bytes() == dup.read_bytes()


def test_noise_is_near_duplicate(tmp_path: Path) -> None:
    src = tmp_path / "src.png"
    noisy = tmp_path / "noisy.png"
    generate_evidence_image(src, seed=4, kind="unique")
    generate_evidence_image(noisy, seed=5, kind="noise", source_path=src)
    distance = _hash(src) - _hash(noisy)
    assert distance <= 8, f"noise image too different: distance={distance}"


def test_noise_is_not_identical(tmp_path: Path) -> None:
    src = tmp_path / "src.png"
    noisy = tmp_path / "noisy.png"
    generate_evidence_image(src, seed=6, kind="unique")
    generate_evidence_image(noisy, seed=7, kind="noise", source_path=src)
    assert src.read_bytes() != noisy.read_bytes()


def test_reuse_kinds_require_source(tmp_path: Path) -> None:
    import pytest

    with pytest.raises(ValueError):
        generate_evidence_image(tmp_path / "x.png", seed=8, kind="copy")


def test_ai_image_is_distinct_from_base_scene(tmp_path: Path) -> None:
    base = tmp_path / "base.png"
    ai = tmp_path / "ai.png"
    generate_evidence_image(base, seed=9, kind="unique")
    generate_evidence_image(ai, seed=9, kind="ai")
    distance = _hash(base) - _hash(ai)
    assert distance > 0, "AI artefacts should alter the image"
