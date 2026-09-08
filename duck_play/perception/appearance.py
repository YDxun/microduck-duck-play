"""Appearance-based person detection + identity on first-person RGB.

Segments the shirt color of each enrolled identity in HSV, returns bounding
boxes + identity. This is the 'appearance model' (color histogram matching);
swap point for a learned ReID/face model is the DetectedPerson interface.
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass


@dataclass
class DetectedPerson:
    label: str
    cx: float
    cy: float
    w: float
    h: float
    conf: float
    bearing_rad: float = 0.0


def _rgb_to_hsv(rgb):
    r, g, b = rgb / 255.0
    mx, mn = max(r, g, b), min(r, g, b)
    v = mx
    c = mx - mn
    s = 0.0 if mx == 0 else c / mx
    if c == 0:
        h = 0.0
    else:
        if mx == r:
            h = 60 * (((g - b) / c) % 6)
        elif mx == g:
            h = 60 * ((b - r) / c + 2)
        else:
            h = 60 * ((r - g) / c + 4)
    return np.array([h / 2.0, s * 255.0, v * 255.0])  # opencv-like HSV range


class AppearanceDetector:
    """Detect enrolled identities by shirt color in the head-cam RGB frame."""

    def __init__(self, enrolled=None, hsv_tol=(20, 130, 140), min_area=80):
        # default enrollment: owner red shirt, stranger blue shirt
        self.enrolled = enrolled or {
            "owner": _rgb_to_hsv(np.array([217, 38, 31])),
            "stranger": _rgb_to_hsv(np.array([31, 64, 191])),
        }
        self.hsv_tol = np.array(hsv_tol)
        self.min_area = min_area

    def detect(self, rgb: np.ndarray) -> list[DetectedPerson]:
        hsv = self._to_hsv(rgb)
        h, w = rgb.shape[:2]
        focal = (h / 2.0) / np.tan(np.radians(22.5))  # ~45 deg vertical fov
        out = []
        for label, center in self.enrolled.items():
            dh = np.abs(hsv[:, :, 0] - center[0])
            dh = np.minimum(dh, 180.0 - dh)  # hue wrap
            ds = np.abs(hsv[:, :, 1] - center[1])
            dv = np.abs(hsv[:, :, 2] - center[2])
            mask = (dh < self.hsv_tol[0]) & (ds < self.hsv_tol[1]) & (dv < self.hsv_tol[2])
            ys, xs = np.where(mask)
            if len(xs) < self.min_area:
                continue
            x0, x1 = xs.min(), xs.max()
            y0, y1 = ys.min(), ys.max()
            cx = (x0 + x1) / 2.0
            cy = (y0 + y1) / 2.0
            area = float(len(xs))
            conf = min(1.0, area / 4000.0)
            bearing = float(np.arctan2(cx - w / 2.0, focal))
            out.append(DetectedPerson(label, float(cx), float(cy),
                                      float(x1 - x0), float(y1 - y0), conf, bearing))
        return out

    @staticmethod
    def _to_hsv(rgb: np.ndarray) -> np.ndarray:
        # fast vectorized rgb->hsv (opencv convention not needed exactly)
        r = rgb[:, :, 0].astype(np.float32) / 255.0
        g = rgb[:, :, 1].astype(np.float32) / 255.0
        b = rgb[:, :, 2].astype(np.float32) / 255.0
        mx = np.maximum(np.maximum(r, g), b)
        mn = np.minimum(np.minimum(r, g), b)
        c = mx - mn
        s = np.where(mx == 0, 0.0, c / np.maximum(mx, 1e-6))
        h = np.zeros_like(mx)
        idx = (mx == r) & (c != 0)
        h[idx] = 60 * (((g[idx] - b[idx]) / c[idx]) % 6)
        idx = (mx == g) & (c != 0)
        h[idx] = 60 * ((b[idx] - r[idx]) / c[idx] + 2)
        idx = (mx == b) & (c != 0)
        h[idx] = 60 * ((r[idx] - g[idx]) / c[idx] + 4)
        v = mx
        out = np.stack([h / 2.0, s * 255.0, v * 255.0], axis=-1)
        return out.astype(np.uint8)

