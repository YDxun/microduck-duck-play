"""Episodic policy manager: run non-locomotion policies (sit/stand/pick/roll)
for a fixed duration then hand back to stand/walk. Extensible ACTION table.
"""
from __future__ import annotations
import numpy as np

# action name -> (policy stem, duration seconds, command flag)
ACTION_TABLE = {
    "sit":      ("alpha_sitstand", 2.5, [1.0, 0.0, 0.0]),
    "stand_up": ("alpha_stand", 1.5, [0.0, 0.0, 0.0]),
    "pick":     ("alpha_ground_pick", 2.0, [0.0, 0.0, 0.0]),
    "roll":     ("alpha_roulade", 2.2, [0.0, 0.0, 0.0]),
}
# map onnx stems to real filenames where needed
POLICY_ALIAS = {"alpha_roulade": "roulade"}


class ActionManager:
    def __init__(self, table=None):
        self.table = dict(ACTION_TABLE if table is None else table)
        self.name = None
        self.elapsed = 0.0
        self.duration = 0.0
        self.policy = None
        self.cmd = None
        self.events = []

    @property
    def busy(self):
        return self.name is not None

    def policy_stem(self):
        if not self.policy:
            return None
        return POLICY_ALIAS.get(self.policy, self.policy)

    def request(self, name):
        if name not in self.table:
            return False
        if self.busy:
            return False
        self.name = name
        self.policy, self.duration, self.cmd = self.table[name]
        self.elapsed = 0.0
        self.events.append({"type": "action_start", "action": name,
                            "policy": self.policy})
        return True

    def select(self, dt, command, upright):
        """Return (policy_stem, eff_cmd). While an episode runs -> zero cmd."""
        if self.busy:
            self.elapsed += dt
            if self.elapsed >= self.duration:
                self.events.append({"type": "action_done", "action": self.name,
                                    "elapsed": round(self.elapsed, 3)})
                self.name = self.policy = self.cmd = None
                self.elapsed = 0.0
            else:
                stem = self.policy_stem()
                return stem, np.asarray(self.cmd or [0, 0, 0], np.float32)
        # idle: stand if no velocity command
        if np.linalg.norm(command) < 0.05:
            return "alpha_stand", np.zeros(3, dtype=np.float32)
        return "alpha_walking", np.asarray(command, np.float32)

