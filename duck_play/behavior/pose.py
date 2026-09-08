"""Kinematic human pose manager for mocap person proxies (articulated arms).

Each arm = upper + lower mocap bodies (straight two-segment chain along the
preset direction) plus shoulder/elbow/wrist marker bodies, so GT keypoints
(shoulder/elbow/wrist) are available as exact MuJoCo state points.
"""
from __future__ import annotations
import math
import numpy as np
import mujoco

UP_LEN = 0.16
LO_LEN = 0.14
SHOULDER_L = np.array([-0.10, 0.0, 0.95])
SHOULDER_R = np.array([0.10, 0.0, 0.95])

GESTURES = {
    "idle":       {"L": [0.0, 0.0, -1.0], "R": [0.0, 0.0, -1.0]},
    "right_fwd":  {"L": [0.0, 0.0, -1.0], "R": [1.0, 0.0, 0.0]},
    "left_fwd":   {"L": [1.0, 0.0, 0.0], "R": [0.0, 0.0, -1.0]},
    "both_fwd":   {"L": [1.0, 0.0, 0.0], "R": [1.0, 0.0, 0.0]},
    "both_side":  {"L": [0.0, 1.0, 0.0], "R": [0.0, -1.0, 0.0]},
}


def _yaw_rot(yaw):
    c, s = math.cos(yaw), math.sin(yaw)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def _quat_align_z(vec):
    v = vec / (np.linalg.norm(vec) + 1e-9)
    z = np.array([0.0, 0.0, 1.0])
    dot = float(np.dot(z, v))
    if abs(dot + 1.0) < 1e-6:
        return np.array([0.0, 1.0, 0.0, 0.0])
    axis = np.cross(z, v)
    axis = axis / (np.linalg.norm(axis) + 1e-9)
    half = math.acos(min(1.0, max(-1.0, dot))) / 2.0
    return np.array([math.cos(half)] + list(axis * math.sin(half)))


class PoseManager:
    def __init__(self, sim, persons=("owner", "stranger")):
        self.sim = sim
        self.m = sim.model
        self.d = sim.data
        self._mocap = {}
        self._parts = {}
        for name in persons:
            self._mocap[name] = {}
            self._parts[name] = {}
            _bid = mujoco.mj_name2id(self.m, mujoco.mjtObj.mjOBJ_BODY, name)
            self._parts[name]["root"] = _bid
            self._mocap[name]["root"] = self.m.body_mocapid[_bid]
            for p in ("armL_u", "armL_l", "armR_u", "armR_l",
                      "shL", "shR", "elL", "elR", "wrL", "wrR"):
                bname = f"{name}_{p}"
                bid = mujoco.mj_name2id(self.m, mujoco.mjtObj.mjOBJ_BODY, bname)
                mid = self.m.body_mocapid[bid]
                self._mocap[name][p] = mid
                self._parts[name][p] = bid
        self.gesture = {p: "idle" for p in persons}
        self._yaw = {p: 0.0 for p in persons}

    def set_pose(self, name, pos_xy, yaw, gesture="idle"):
        self.gesture[name] = gesture
        self._yaw[name] = yaw
        d = self.d
        R = _yaw_rot(yaw)
        root = np.array([pos_xy[0], pos_xy[1], 0.0])
        d.mocap_pos[self._mocap[name]["root"], :] = root
        d.mocap_quat[self._mocap[name]["root"], :] = \
            np.array([math.cos(yaw / 2), 0, 0, math.sin(yaw / 2)])
        pres = GESTURES.get(gesture, GESTURES["idle"])
        for side, sh_local in (("L", SHOULDER_L), ("R", SHOULDER_R)):
            shoulder = root + R @ sh_local
            dirv = R @ (np.array(pres[side]) / (np.linalg.norm(pres[side]) + 1e-9))
            du = dirv
            elbow = shoulder + du * UP_LEN
            wrist = shoulder + du * (UP_LEN + LO_LEN)
            q = _quat_align_z(du)
            d.mocap_pos[self._mocap[name][f"arm{side}_u"], :] = shoulder
            d.mocap_quat[self._mocap[name][f"arm{side}_u"], :] = q
            d.mocap_pos[self._mocap[name][f"arm{side}_l"], :] = elbow
            d.mocap_quat[self._mocap[name][f"arm{side}_l"], :] = q
            for key, p in (("sh", shoulder), ("el", elbow), ("wr", wrist)):
                d.mocap_pos[self._mocap[name][f"{key}{side}"], :] = p
                d.mocap_quat[self._mocap[name][f"{key}{side}"], :] = [1, 0, 0, 0]

    def arm_points(self, name):
        d = self.sim.data
        out = {}
        for side in ("L", "R"):
            out[f"sh{side}"] = d.xpos[self._parts[name][f"sh{side}"]].copy()
            out[f"el{side}"] = d.xpos[self._parts[name][f"el{side}"]].copy()
            out[f"hd{side}"] = d.xpos[self._parts[name][f"wr{side}"]].copy()
        return out

    def classify(self, name):
        pts = self.arm_points(name)
        yaw = self._yaw.get(name, 0.0)
        c, s = math.cos(-yaw), math.sin(-yaw)
        Rinv = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
        best, best_score = "idle", 1e9
        for gname, pres in GESTURES.items():
            score = 0.0
            for side in ("L", "R"):
                vec = Rinv @ (pts[f"hd{side}"] - pts[f"sh{side}"])
                want = np.array(pres[side])
                score += abs(float(np.dot(vec / (np.linalg.norm(vec) + 1e-9),
                                         want / (np.linalg.norm(want) + 1e-9))))
            score = 2.0 - score
            if score < best_score:
                best_score = score
                best = gname
        return best, float(best_score)




