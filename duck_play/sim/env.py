"""Scene helpers on top of the cloud LocalSim (same MJCF as the web cockpit).
Ball randomization + (future) person proxies & cone waypoints live here.
"""
from __future__ import annotations
import math
import numpy as np


def place_ball(sim, x=0.9, y=0.0, z=0.035):
    """Place ball at world (x,y,z) without touching velocities."""
    d = sim.data
    adr = sim.ball_qpos_adr
    d.qpos[adr:adr + 7] = [x, y, z, 1, 0, 0, 0]
    mujoco_forward(sim)
    return adr


def mujoco_forward(sim):
    import mujoco
    mujoco.mj_forward(sim.model, sim.data)
