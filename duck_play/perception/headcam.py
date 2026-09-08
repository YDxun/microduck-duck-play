"""First-person (head camera) RGB renderer for duck_play.

Mirrors sim_server.render_headcam camera math (orbit camera placed at the
head, looking forward/down) but returns a numpy RGB frame instead of JPEG.
Renderer instances are cached per (model_ptr, width, height).
"""
from __future__ import annotations
import math
import os
os.environ.setdefault("MUJOCO_GL", "egl")
import numpy as np
import mujoco

_RENDERERS = {}


def _renderer(model, w, h):
    key = (id(model), w, h)
    r = _RENDERERS.get(key)
    if r is None:
        r = mujoco.Renderer(model, height=h, width=w)
        _RENDERERS[key] = r
    return r


def render_headcam_rgb(sim, width=320, height=240, pitch_up_deg=None) -> np.ndarray:
    r = _renderer(sim.model, width, height)
    cam = mujoco.MjvCamera()
    cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    d = sim.data
    pos = d.xpos[sim.head_id].copy()
    fwd = d.xmat[sim.head_id].reshape(3, 3)[:, 0].copy()
    fwd /= np.linalg.norm(fwd)
    campos = pos + fwd * 0.09 + np.array([0, 0, 0.03])
    if pitch_up_deg is None:
        pitch_up_deg = float(os.environ.get("DUCK_CAM_PITCH", "30"))
    tilt = math.radians(-pitch_up_deg)  # positive = look up (duck can tilt head)
    v = fwd * math.cos(tilt) + np.array([0.0, 0.0, -1.0]) * math.sin(tilt)
    v /= np.linalg.norm(v)
    L = 0.5
    cam.lookat = campos + v * L
    cam.distance = L
    cam.azimuth = math.degrees(math.atan2(v[1], v[0]))
    cam.elevation = math.degrees(math.asin(float(np.clip(v[2], -1, 1))))
    # IMX219-ish: horizontal 62 deg -> vertical fov at 320x240
    vfov = 2.0 * math.degrees(math.atan(math.tan(math.radians(31.0)) * height / width))
    try:
        cam.fovy = vfov
    except Exception:
        pass
    r.update_scene(d, camera=cam)
    return r.render().copy()



