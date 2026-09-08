"""Dribble-around-cones (带球绕桩) derivative - DESIGN STUB.

Idea: instead of kicking away, keep the ball within a dribble corridor
(|local_y| < gate) while passing waypoints next to cones; the duck should
move so the ball stays in front (small bearing) at moderate speed. Needs a
cone-free but ball-constrained reward/behaviour; will be implemented after
the basic chase loop is validated.
"""
from __future__ import annotations
from ..config import DRIBBLE


class SlalomController:
    def __init__(self, cfg=None):
        self.cfg = dict(DRIBBLE)
        if cfg:
            self.cfg.update(cfg)
        self.waypoint_i = 0
        self.state = "IDLE"

    def reset(self):
        self.waypoint_i = 0
        self.state = "IDLE"
