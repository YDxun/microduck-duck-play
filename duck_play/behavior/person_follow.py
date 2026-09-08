"""Person recognition L1: follow the owner, orbit a nearby stranger,
answer a 'summon' (owner standing) by approaching and holding distance.
"""
from __future__ import annotations
import math
from ..config import PERSON


class PersonFollowController:
    def __init__(self, cfg=None, owner_label="owner", stranger_label="stranger"):
        self.cfg = dict(PERSON)
        if cfg:
            self.cfg.update(cfg)
        self.owner_label = owner_label
        self.stranger_label = stranger_label
        self.state = "SUMMON"     # SUMMON|FOLLOW|ORBIT|SEARCH
        self.state_time = 0.0
        self._summon_close_since = None
        self.summon_ok = False
        self.orbit_count = 0
        self._orbit_start = None

    def _clip(self, v, lo, hi):
        return max(lo, min(hi, v))

    def _face(self, yaw):
        return self._clip(self.cfg["kp_yaw"] * yaw, -1.2, 1.2)

    def _approach_owner(self, rng, yaw):
        cfg = self.cfg
        dv = rng - cfg["follow_dist_m"]
        vx = 0.0
        if dv > cfg["deadband_m"]:
            vx = self._clip(cfg["kp_dist"] * dv, 0.0, 0.55)
        elif dv < -cfg["deadband_m"]:
            vx = self._clip(cfg["kp_dist"] * dv, -0.35, 0.0)
        return vx, self._face(yaw)

    def decide(self, perception, sim, dt):
        """Return (cmd[3], note). Pure decision; no physics."""
        self.state_time += dt
        cfg = self.cfg
        owner = next((p for p in perception.persons if p.label == self.owner_label), None)
        stranger = next((p for p in perception.persons if p.label == self.stranger_label), None)

        if owner is None:
            self.state = "SEARCH"
            return [0.0, 0.0, 0.8], "search"

        rng_o, yaw_o = owner.range_m, owner.bearing_yaw

        # --- orbit a stranger that gets too close ---
        if stranger is not None and stranger.range_m < cfg.get("orbit_trigger_m", 0.9):
            if self.state != "ORBIT":
                self.state = "ORBIT"
                self._orbit_start = self.state_time
                self.orbit_count += 1
            if self.state_time - self._orbit_start > cfg.get("orbit_duration_s", 3.0):
                self.state = "FOLLOW"
            else:
                # keep stranger at +0.7 rad (left-front) while walking forward -> circle
                err = stranger.bearing_yaw - 0.7
                wz = self._clip(cfg["kp_yaw"] * err, -1.2, 1.2)
                return [0.30, 0.0, wz], "orbit"
        elif self.state == "ORBIT":
            self.state = "FOLLOW"

        # --- summon / follow the owner ---
        if self.state in ("SUMMON", "FOLLOW"):
            if rng_o <= cfg["follow_dist_m"] + 0.05:
                if self._summon_close_since is None:
                    self._summon_close_since = self.state_time
                if (not self.summon_ok
                        and self.state_time - self._summon_close_since >= cfg.get("summon_hold_s", 1.2)):
                    self.summon_ok = True
                    self.state = "FOLLOW"
            else:
                self._summon_close_since = None

            vx, wz = self._approach_owner(rng_o, yaw_o)
            note = "summon" if not self.summon_ok else "follow"
            self.state = "SUMMON" if not self.summon_ok else "FOLLOW"
            return [vx, 0.0, wz], note

        return [0.0, 0.0, self._face(yaw_o)], self.state
