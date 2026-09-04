"""Stage 1 · Image evidence forensics.

Detects two things:
1. Reused evidence — the same (or near-same) photo submitted before by the
   same customer for a different claim.
2. AI-generation suspicion — procedural artefacts (mirror symmetry,
   high-frequency banding) that real phone photos rarely exhibit.

Heuristics are deliberately conservative and every finding is reported as
a *sus*pcion with the measured numbers attached, never a verdict.
"""

from __future__ import annotations

import base64
import binascii
import io
import logging
from pathlib import Path

import imagehash
import numpy as np
from PIL import Image, UnidentifiedImageError

from app.core.models import ImageEvidence

logger = logging.getLogger("refundshield.stage1.image")

REUSE_HASH_DISTANCE = 10          # pHash hamming distance ≤ 10 → near-duplicate
AI_SUSPICION_THRESHOLD = 0.65
_EXIF_KEYS = {"exif", "gps_info", "make", "model"}


class ImageAnalyzer:
    def analyze(
        self,
        *,
        image_base64: str | None,
        image_path: str | None,
        prior_images: list[tuple[str, str]],  # (order_id, image_path) history
    ) -> ImageEvidence:
        ev = ImageEvidence()

        img = self._load(image_base64, image_path)
        if img is None:
            ev.notes.append("No usable evidence image provided.")
            return ev

        ev.provided = True
        phash = imagehash.phash(img)
        ev.perceptual_hash = str(phash)

        # ---- metadata consistency -------------------------------------
        fmt = (img.format or "").lower()
        has_exif = bool(getattr(img, "exif", None)) and len(img.getexif()) > 0
        if fmt == "png" and not has_exif:
            ev.metadata_inconsistent = True
            ev.notes.append(
                "Image has no EXIF metadata (unusual for genuine phone photos)."
            )

        # ---- reuse check ----------------------------------------------
        for prior_order_id, prior_path in prior_images:
            prior = self._load(None, prior_path)
            if prior is None:
                continue
            distance = phash - imagehash.phash(prior)
            similarity = 1.0 - distance / 64.0
            if ev.similarity_to_prior_claim is None or similarity > ev.similarity_to_prior_claim:
                ev.similarity_to_prior_claim = round(similarity, 3)
            if distance <= REUSE_HASH_DISTANCE:
                ev.is_reused = True
                ev.reused_of_order_id = prior_order_id
                ev.notes.append(
                    f"Image is a near-duplicate of evidence from order "
                    f"{prior_order_id} (pHash distance {distance})."
                )
                break

        # ---- AI-artefact suspicion ------------------------------------
        ev.ai_generated_score = self._ai_score(img)
        if ev.ai_generated_score >= AI_SUSPICION_THRESHOLD and not ev.is_reused:
            ev.ai_generated_suspected = True
            ev.notes.append(
                f"AI-generation suspected (artefact score "
                f"{ev.ai_generated_score:.2f}: symmetry/banding)."
            )
        elif ev.ai_generated_score >= AI_SUSPICION_THRESHOLD and ev.is_reused:
            ev.notes.append(
                f"AI-artefact score high ({ev.ai_generated_score:.2f}) but "
                "reuse explains it; not double-flagging."
            )
        return ev

    # ------------------------------------------------------------------
    def score(self, ev: ImageEvidence) -> float:
        """Map evidence to a risk signal in [0, 1]."""
        if not ev.provided:
            # missing evidence on a refund claim is mildly risky
            return 0.25
        s = 0.0
        if ev.is_reused:
            s = max(s, 0.9)
        if ev.ai_generated_suspected:
            s = max(s, 0.7)
        if ev.metadata_inconsistent:
            s = max(s, 0.35)
        if ev.similarity_to_prior_claim is not None and not ev.is_reused:
            # suspicious-but-below-threshold similarity still nudges risk
            if ev.similarity_to_prior_claim >= 0.7:
                s = max(s, 0.5 * ev.similarity_to_prior_claim + 0.1)
        return round(s, 3)

    # ------------------------------------------------------------------
    def _load(self, image_base64: str | None, image_path: str | None):
        try:
            if image_base64:
                raw = base64.b64decode(image_base64, validate=False)
                return Image.open(io.BytesIO(raw)).convert("RGB")
            if image_path and Path(image_path).exists():
                return Image.open(image_path).convert("RGB")
        except (binascii.Error, UnidentifiedImageError, OSError, ValueError) as exc:
            logger.warning("Could not load evidence image: %s", exc)
        return None

    def _ai_score(self, img: Image.Image) -> float:
        """Combine checkerboard-banding and mirror-symmetry artefacts.

        ``banding`` measures rectilinear luminance alternation (an
        up-scaled generative checkerboard), ``symmetry`` measures global
        mirror correlation. Both are calibrated on our synthetic corpora;
        they are heuristics, reported as suspicion only.
        """
        arr = np.asarray(img.convert("L"), dtype=np.float32)

        # 1) banding: best tile-parity contrast over plausible tile sizes
        parity = max(self._parity_contrast(arr, s) for s in (8, 12, 16))
        banding = min(1.0, parity / 0.30)

        # 2) mirror symmetry: |img - flip| low ⇒ suspiciously symmetric
        a = arr / 255.0
        sym_diff = float(np.mean(np.abs(a - np.fliplr(a))))
        symmetry = 1.0 - min(1.0, sym_diff / 0.10)

        return round(float(0.65 * banding + 0.35 * symmetry), 3)

    @staticmethod
    def _parity_contrast(arr: np.ndarray, step: int) -> float:
        h, w = arr.shape
        t = arr[: h // step * step, : w // step * step]
        tiles = t.reshape(h // step, step, w // step, step).mean(axis=(1, 3))
        par = np.indices(tiles.shape).sum(axis=0) % 2
        diff = abs(float(tiles[par == 0].mean() - tiles[par == 1].mean()))
        return diff / (float(tiles.std()) + 1e-6)
