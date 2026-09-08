"""Detection data types shared by ground-truth and (future) learned detectors."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

@dataclass
class Detection:
    label: str
    cx: float = 0.0          # pixel center x
    cy: float = 0.0          # pixel center y
    w: float = 0.0           # bbox width px
    h: float = 0.0           # bbox height px
    conf: float = 0.0
    range_m: float = math.inf
    bearing_yaw: float = 0.0   # rad, positive = left of duck forward (body frame)
    bearing_pitch: float = 0.0 # rad, positive = up
    xyz_local: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    extra: dict = field(default_factory=dict)

@dataclass
class Perception:
    ball: Optional[Detection] = None
    persons: List[Detection] = field(default_factory=list)
