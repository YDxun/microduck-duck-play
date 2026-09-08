"""Tiny metrics accumulator for closed-loop experiments."""
from __future__ import annotations


class Metrics:
    def __init__(self):
        self.t_sim = 0.0
        self.steps = 0
        self.touches = 0          # ball clearly moved during a kick
        self.kick_attempts = 0
        self.resets = 0           # dev-only fall resets
        self.path_len = 0.0       # trunk path length (m)
        self.ball_range = float("inf")
        self.events = []

    def to_dict(self):
        return {
            "t_sim_s": round(self.t_sim, 3),
            "steps": self.steps,
            "touches": self.touches,
            "kick_attempts": self.kick_attempts,
            "resets": self.resets,
            "path_len_m": round(self.path_len, 3),
            "final_ball_range_m": round(self.ball_range, 3) if self.ball_range != float("inf") else None,
            "events": self.events,
        }


class PersonMetrics:
    """Metrics for the L1 person-follow scenario."""
    def __init__(self):
        self.t_sim = 0.0
        self.steps = 0
        self.path_len = 0.0
        self.summon_ok = False
        self.summon_reached_t = None
        self.orbit_events = 0
        self.orbit_time_s = 0.0
        self.dist_owner_sum = 0.0
        self.dist_owner_n = 0
        self.follow_band_s = 0.0       # time owner within follow band
        self.last_state = ""

    def to_dict(self):
        return {
            "t_sim_s": round(self.t_sim, 3),
            "steps": self.steps,
            "path_len_m": round(self.path_len, 3),
            "summon_ok": self.summon_ok,
            "summon_reached_t_s": self.summon_reached_t,
            "orbit_events": self.orbit_events,
            "orbit_time_s": round(self.orbit_time_s, 3),
            "avg_dist_owner_m": round(self.dist_owner_sum / self.dist_owner_n, 3) if self.dist_owner_n else None,
            "follow_band_s": round(self.follow_band_s, 3),
        }
