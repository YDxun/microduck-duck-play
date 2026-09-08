#!/usr/bin/env python3
"""M1 composite narrative: duck finds the owner, then brings (kicks) the ball
towards the owner.  Stages: FIND_OWNER -> GET_BEHIND -> KICK_TO_OWNER.
Optional recording via env DUCKPLAY_RECORD=out.mp4 (+ _EVERY/_W/_H).
"""
from __future__ import annotations
import json, math, os, sys, time
from pathlib import Path
import numpy as np
os.environ.setdefault("MUJOCO_GL", "egl")
import mujoco

PKG = Path(__file__).resolve().parent.parent
SIM_ROOT = PKG.parent
for p in (str(SIM_ROOT), str(PKG)):
    if p not in sys.path:
        sys.path.insert(0, p)

import sim_server as _ss
from sim_server import LocalSim, PolicyBank, LocalKick, CONTROL_DT, DECIMATION, quat_rotate_inverse
from duck_play.perception.ground_truth import GroundTruthPerception
from duck_play.scenes.gen_wall_scene import ensure as ensure_wall

ROBOT_DIR = SIM_ROOT / "microduck_rl/src/mjlab_microduck/robot/microduck"
OWNER_POS = (1.6, 0.6)
BALL_START = (0.9, 0.0)


def ensure_composite_scene() -> Path:
    wall = ensure_wall().read_text()
    owner_lines = [
        '    <body name="owner" mocap="true" pos="1.6 0.6 0">',
        '      <geom name="owner_legL" type="capsule" fromto="-0.05 0 0.0 -0.05 0 0.45" size="0.035" rgba="0.12 0.12 0.16 1"/>',
        '      <geom name="owner_legR" type="capsule" fromto=" 0.05 0 0.0  0.05 0 0.45" size="0.035" rgba="0.12 0.12 0.16 1"/>',
        '      <geom name="owner_torso" type="capsule" fromto="0 0 0.45 0 0 1.0" size="0.09" rgba="0.85 0.15 0.12 1"/>',
        '      <geom name="owner_head" type="sphere" pos="0 0 1.12" size="0.11" rgba="0.93 0.76 0.62 1"/>',
        '    </body>',
    ]
    out = wall.replace('  </worldbody>', "\n".join(owner_lines) + "\n  </worldbody>")
    target = ROBOT_DIR / "scene_composite.xml"
    if not target.exists():
        target.write_text(out)
    return target


def wrap_pi(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


class CompositeRunner:
    def __init__(self):
        scene = ensure_composite_scene()
        _ss.SCENE_XML = str(scene)
        self.sim = LocalSim()
        self.policies = PolicyBank()
        self.kick = LocalKick()
        self.perception = GroundTruthPerception(self.sim)
        m = self.sim.model
        owner_body = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "owner")
        self._owner_mid = m.body_mocapid[owner_body]
        self.perception.add_person_proxy(owner_body, "owner", "red")
        self.stage = "FIND_OWNER"
        self.stage_t = 0.0
        self.kick_done = False
        self.ball2owner0 = None
        self.metrics = {"stages": [], "delivered": False, "ball2owner_start": None,
                        "ball2owner_end": None, "t_find_owner": None, "t_kick": None}

    def heading(self):
        h = self.sim.data.xmat[self.sim.trunk_id].reshape(3, 3)
        return math.atan2(h[1, 0], h[0, 0])

    def drive_to(self, target, dist_thresh, gain=1.5, max_v=0.5):
        dx = target[0] - self.sim.data.xpos[self.sim.trunk_id, 0]
        dy = target[1] - self.sim.data.xpos[self.sim.trunk_id, 1]
        dist = math.hypot(dx, dy)
        want = math.atan2(dy, dx)
        err = wrap_pi(want - self.heading())
        wz = max(-1.2, min(1.2, 1.6 * err))
        vx = max(0.0, min(max_v, gain * dist))
        return [vx, 0.0, wz], dist <= dist_thresh

    def stage_step(self, perception):
        sim = self.sim
        ball = perception.ball
        owner = next((p for p in perception.persons if p.label == "owner"), None)
        if owner is None or ball is None:
            return [0.0, 0.0, 0.0], None
        bp = np.array(sim.data.xpos[sim.ball_body, :2])
        ob = mujoco.mj_name2id(sim.model, mujoco.mjtObj.mjOBJ_BODY, "owner")
        op = np.array(sim.data.xpos[ob, :2])

        if self.stage == "FIND_OWNER":
            if owner.range_m <= 0.8:
                self.metrics["t_find_owner"] = round(self.stage_t, 3)
                self.metrics["stages"].append({"stage": "FIND_OWNER", "t": self.stage_t})
                self.stage = "GET_BEHIND"
                return [0.0, 0.0, 0.0], None
            vx = max(0.18, min(0.5, 1.2 * (owner.range_m - 0.8)))
            wz = 1.6 * owner.bearing_yaw
            return [vx, 0.0, max(-1.2, min(1.2, wz))], None

        if self.stage == "GET_BEHIND":
            u = op - bp
            u = u / (np.linalg.norm(u) + 1e-9)
            pvec = np.array([-u[1], u[0]])
            stand = bp - u * 0.10 + pvec * 0.05
            cmd, reached = self.drive_to(stand, 0.08, gain=1.4)
            if reached:
                self.metrics["stages"].append({"stage": "GET_BEHIND", "t": self.stage_t})
                self.stage = "KICK_TO_OWNER"
                self.ball2owner0 = float(np.linalg.norm(bp - op))
                self.metrics["ball2owner_start"] = round(self.ball2owner0, 3)
            return cmd, None

        if not self.kick_done:
            if ball.range_m <= 0.15:
                self.metrics["t_kick"] = round(self.stage_t, 3)
                self.metrics["stages"].append({"stage": "KICK_TO_OWNER", "t": self.stage_t})
                return [0.0, 0.0, 0.0], "kickR"
            vx = 0.32
            wz = 1.6 * ball.bearing_yaw
            return [vx, 0.0, max(-1.2, min(1.2, wz))], None
        wz = 1.6 * owner.bearing_yaw
        return [0.0, 0.0, max(-1.2, min(1.2, wz))], None

    def step(self):
        sim, d = self.sim, self.sim.data
        d.mocap_pos[self._owner_mid, :2] = OWNER_POS
        d.mocap_pos[self._owner_mid, 2] = 0.0
        d.mocap_quat[self._owner_mid, :] = [1, 0, 0, 0]
        gravity = quat_rotate_inverse(d.xquat[sim.trunk_id].copy(), np.array([0, 0, -1.0]))
        gyro = d.sensordata[sim.imu_gyro_adr:sim.imu_gyro_adr + 3].astype(np.float32)
        upright = float(-gravity[2])
        perception = self.perception.update()
        cmd, kick_req = self.stage_step(perception)
        if kick_req and self.kick.name is None and upright > 0.5:
            res = self.kick.request(kick_req, self.policies.sessions, fallen=False)
            if res.get("status") == "accepted":
                self.kick_done = True
        policy, eff_cmd = self.kick.select(CONTROL_DT, np.asarray(cmd, np.float32),
                                           float(np.linalg.norm(d.qvel[:2])),
                                           float(np.linalg.norm(gyro)), upright)
        obs = np.concatenate([
            gyro, gravity.astype(np.float32),
            (d.qpos[sim.joint_qpos_idx] - sim.default_pose).astype(np.float32),
            d.qvel[sim.joint_qvel_idx].astype(np.float32), sim.last_action,
            np.concatenate([eff_cmd, np.zeros(10, dtype=np.float32)]),
        ]).astype(np.float32)
        act = self.policies.infer(policy, obs)
        sim.last_action = act.copy()
        d.ctrl[:] = sim.default_pose + act
        for _ in range(DECIMATION):
            mujoco.mj_step(sim.model, d)
        self.stage_t += CONTROL_DT
        return perception, policy


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--time", type=float, default=60.0)
    args = ap.parse_args()

    r = CompositeRunner()
    recorder = None
    if os.environ.get("DUCKPLAY_RECORD"):
        from duck_play.recording.recorder import DemoRecorder
        recorder = DemoRecorder(r.sim, os.environ["DUCKPLAY_RECORD"])
    r.sim.reset()
    adr = r.sim.ball_qpos_adr
    r.sim.data.qpos[adr:adr + 3] = [BALL_START[0], BALL_START[1], 0.035]
    op = np.array(OWNER_POS)
    print(f"[composite] start time={args.time}s owner={OWNER_POS} ball={BALL_START}", flush=True)
    last = 0.0
    while r.stage_t < args.time:
        perception, _pol = r.step()
        if recorder:
            recorder.step()
        bp = np.array(r.sim.data.xpos[r.sim.ball_body, :2])
        b2o = float(np.linalg.norm(bp - op))
        if r.stage_t - last >= 0.5:
            print(f"[t={r.stage_t:6.2f}s] stage={r.stage:<14s} "
                  f"duck2owner={perception.persons[0].range_m:5.2f}m "
                  f"duck2ball={perception.ball.range_m:5.2f}m ball2owner={b2o:5.2f}m",
                  flush=True)
            last = r.stage_t
        if r.stage == "KICK_TO_OWNER" and r.kick_done and r.kick.name is None:
            break
    if recorder:
        recorder.finish()
    bp = np.array(r.sim.data.xpos[r.sim.ball_body, :2])
    r.metrics["ball2owner_end"] = round(float(np.linalg.norm(bp - op)), 3)
    r.metrics["delivered"] = (r.metrics["ball2owner_end"] is not None
                              and r.metrics["ball2owner_start"] is not None
                              and r.metrics["ball2owner_end"] < 0.85
                              and r.metrics["ball2owner_end"] < r.metrics["ball2owner_start"] - 0.15)
    out_dir = PKG / "runs"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"composite_{time.strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(r.metrics, ensure_ascii=False, indent=2))
    print("\n[composite] result:", json.dumps(r.metrics, ensure_ascii=False))
    print(f"[composite] report -> {out}")


if __name__ == "__main__":
    main()
