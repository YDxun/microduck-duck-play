"""L1 person scenario runner: same physics/policy stack as ChaseRunner but
persons are kinematic mocap proxies driven by scripted paths.
"""
from __future__ import annotations
import os, sys
os.environ.setdefault("MUJOCO_GL", "egl")
import numpy as np
import mujoco

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sim_server as _ss
from sim_server import LocalSim, PolicyBank, LocalKick, CONTROL_DT, DECIMATION, quat_rotate_inverse
from ..config import PERSON
from ..perception.ground_truth import GroundTruthPerception
from ..eval.metrics import PersonMetrics


class PersonRunner:
    def __init__(self, controller, scene_xml, person_paths, cfg=None):
        """person_paths: {label: {"body": name, "color": str, "pos": fn(t)->(x,y)}}"""
        _ss.SCENE_XML = str(scene_xml)
        self.sim = LocalSim()
        self.policies = PolicyBank()
        self.kick = LocalKick()            # only used for stand/walk policy select
        self.perception = GroundTruthPerception(self.sim)
        self.controller = controller
        self.cfg = dict(PERSON)
        if cfg:
            self.cfg.update(cfg)
        self.metrics = PersonMetrics()
        self.person_paths = person_paths
        self._mocap = {}
        m = self.sim.model
        for label, info in person_paths.items():
            bid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, info["body"])
            mid = m.body_mocapid[bid]
            self._mocap[label] = (bid, mid)
            self.perception.add_person_proxy(bid, label, info["color"])
        self._last_xy = self.sim.data.xpos[self.sim.trunk_id, :2].copy()
        self.recorder = None
        if os.environ.get("DUCKPLAY_RECORD"):
            from ..recording.recorder import DemoRecorder
            self.recorder = DemoRecorder(self.sim, os.environ["DUCKPLAY_RECORD"])

    def _set_mocap(self, t):
        d = self.sim.data
        for label, (bid, mid) in self._mocap.items():
            x, y = self.person_paths[label]["pos"](t)
            d.mocap_pos[mid, 0] = x
            d.mocap_pos[mid, 1] = y
            d.mocap_pos[mid, 2] = 0.0
            d.mocap_quat[mid, :] = [1.0, 0.0, 0.0, 0.0]

    def step(self, t):
        self._set_mocap(t)
        sim, d = self.sim, self.sim.data
        gravity = quat_rotate_inverse(d.xquat[sim.trunk_id].copy(), np.array([0, 0, -1.0]))
        gyro = d.sensordata[sim.imu_gyro_adr:sim.imu_gyro_adr + 3].astype(np.float32)
        upright = float(-gravity[2])

        perception = self.perception.update()
        cmd, _note = self.controller.decide(perception, sim, CONTROL_DT)
        policy, eff_cmd = self.kick.select(CONTROL_DT, np.asarray(cmd, np.float32),
                                           float(np.linalg.norm(d.qvel[:2])),
                                           float(np.linalg.norm(gyro)), upright)

        obs = np.concatenate([
            gyro, gravity.astype(np.float32),
            (d.qpos[sim.joint_qpos_idx] - sim.default_pose).astype(np.float32),
            d.qvel[sim.joint_qvel_idx].astype(np.float32), sim.last_action,
            np.concatenate([eff_cmd, np.zeros(10, dtype=np.float32)]),
        ]).astype(np.float32)
        action = self.policies.infer(policy, obs)
        sim.last_action = action.copy()
        d.ctrl[:] = sim.default_pose + action
        for _ in range(DECIMATION):
            mujoco.mj_step(sim.model, d)

        self.metrics.t_sim += CONTROL_DT
        self.metrics.steps += 1
        xy = d.xpos[sim.trunk_id, :2].copy()
        self.metrics.path_len += float(np.linalg.norm(xy - self._last_xy))
        self._last_xy = xy

        owner = next((p for p in perception.persons if p.label == "owner"), None)
        if owner is not None:
            self.metrics.dist_owner_sum += owner.range_m
            self.metrics.dist_owner_n += 1
            band = self.cfg["follow_dist_m"]
            if band * 0.7 <= owner.range_m <= band + 0.25:
                self.metrics.follow_band_s += CONTROL_DT
        if self.controller.state == "ORBIT":
            self.metrics.orbit_time_s += CONTROL_DT
        self.metrics.orbit_events = self.controller.orbit_count
        self.metrics.summon_ok = self.controller.summon_ok
        if self.controller.summon_ok and self.metrics.summon_reached_t is None:
            self.metrics.summon_reached_t = round(self.metrics.t_sim, 3)
        if self.recorder:
            self.recorder.step()
        self.metrics.last_state = self.controller.state
        owner_rng = owner.range_m if owner is not None else float("inf")
        return self.controller.state, owner_rng



