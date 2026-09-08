"""Ground-truth perception: reads MuJoCo state directly (no rendering).

Used to bring up the closed loop first. A learned detector will later replace
Perception.ball by consuming rendered RGB (head camera) — same Detection schema.
"""
from __future__ import annotations
import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # /root/microduck_sim
import numpy as np
from sim_server import quat_rotate_inverse
from .detections import Detection, Perception

# pinhole approximation matching render_headcam(320x240, ~60deg vertical fov)
_CAM_W, _CAM_H = 320, 240
_FOVY_DEG = 60.0
_F = _CAM_H / (2.0 * math.tan(math.radians(_FOVY_DEG / 2.0)))


class GroundTruthPerception:
    """Ball (+person proxies later) in duck trunk frame, straight from MuJoCo."""

    def __init__(self, sim):
        self.sim = sim
        self.person_proxies = []   # list of (body_id, label, color)

    def add_person_proxy(self, body_id: int, label: str, color: str):
        self.person_proxies.append((body_id, label, color))

    def update(self) -> Perception:
        d = self.sim.data
        trunk = d.xpos[self.sim.trunk_id]
        # world -> trunk-local (x forward, y left, z up)
        local = quat_rotate_inverse(d.xquat[self.sim.trunk_id].copy(),
                                    d.xpos[self.sim.ball_body].copy() - trunk)
        rng = float(np.linalg.norm(local))
        yaw = float(math.atan2(local[1], local[0]))
        pitch = float(math.atan2(local[2], math.hypot(local[0], local[1])))
        det = Detection(label="ball", range_m=rng, bearing_yaw=yaw,
                        bearing_pitch=pitch, xyz_local=tuple(map(float, local)))
        # pseudo-bbox so downstream code can stay detector-agnostic
        if local[0] > 0.08:
            det.cx = _CAM_W / 2 + _F * float(local[1] / local[0])
            det.cy = _CAM_H / 2 - _F * float(local[2] / local[0])
            det.w = det.h = max(8.0, 0.4 * _F / float(local[0]))
        persons = []
        for body_id, label, color in self.person_proxies:
            plocal = quat_rotate_inverse(d.xquat[self.sim.trunk_id].copy(),
                                         d.xpos[body_id].copy() - trunk)
            persons.append(Detection(label=label, range_m=float(np.linalg.norm(plocal)),
                                     bearing_yaw=float(math.atan2(plocal[1], plocal[0])),
                                     bearing_pitch=float(math.atan2(plocal[2], math.hypot(plocal[0], plocal[1]))),
                                     xyz_local=tuple(map(float, plocal)),
                                     extra={"color": color}))
        return Perception(ball=det, persons=persons)
