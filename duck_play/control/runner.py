"""50 Hz closed-loop runner reusing the cloud sim's own brain parts.

Replicates sim_server.local_step() exactly (same obs layout, same ctrl
application, same LocalKick state machine) but commands come from a behavior
controller instead of the web UI. CPU-only inference -> safe to run while the
GPU is busy with a parallel RL training job.
"""
from __future__ import annotations
import os, sys, math
os.environ.setdefault("MUJOCO_GL", "egl")
import numpy as np
import mujoco

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # /root/microduck_sim
from sim_server import (LocalSim, PolicyBank, LocalKick,
                        CONTROL_DT, DECIMATION, quat_rotate_inverse)
from ..config import CHASE
from ..perception.ground_truth import GroundTruthPerception
from ..eval.metrics import Metrics


class ChaseRunner:
    def __init__(self, controller, cfg=None, seed=0, randomize_ball=False,
                 scene_xml=None):
        if scene_xml is not None:
            import sim_server as _ss
            _ss.SCENE_XML = str(scene_xml)
        self.sim = LocalSim()
        self.policies = PolicyBank()
        self.kick = LocalKick()
        self.perception = GroundTruthPerception(self.sim)
        self.controller = controller
        self.cfg = dict(CHASE)
        if cfg:
            self.cfg.update(cfg)
        self.metrics = Metrics()
        self.rng = np.random.default_rng(seed)
        self.randomize_ball = randomize_ball
        self._kick_was_active = False
        self._ball_peak_speed = 0.0
        self._kick_start_pos = None
        self._last_xy = self.sim.data.xpos[self.sim.trunk_id, :2].copy()
        self._ball_prev = self.sim.data.xpos[self.sim.ball_body].copy()
        self._down_t0 = None
        self.recorder = None
        if os.environ.get("DUCKPLAY_RECORD"):
            from ..recording.recorder import DemoRecorder
            self.recorder = DemoRecorder(self.sim, os.environ["DUCKPLAY_RECORD"])

    def _ball_speed(self):
        d = self.sim.data
        pos = d.xpos[self.sim.ball_body].copy()
        sp = float(np.linalg.norm(pos - self._ball_prev) / CONTROL_DT)
        self._ball_prev = pos
        return sp

    def _reset_ball(self):
        d = self.sim.data
        adr = self.sim.ball_qpos_adr
        if self.randomize_ball:
            r = float(self.rng.uniform(0.5, 1.4))
            a = float(self.rng.uniform(-0.6, 0.6))
            d.qpos[adr:adr + 7] = [r * math.cos(a), r * math.sin(a), 0.035, 1, 0, 0, 0]
        else:
            d.qpos[adr:adr + 7] = [0.9, 0.0, 0.035, 1, 0, 0, 0]

    def step(self):
        sim, d = self.sim, self.sim.data
        gravity = quat_rotate_inverse(d.xquat[sim.trunk_id].copy(), np.array([0, 0, -1.0]))
        gyro = d.sensordata[sim.imu_gyro_adr:sim.imu_gyro_adr + 3].astype(np.float32)
        upright = float(-gravity[2])
        speed = float(np.linalg.norm(d.qvel[:2]))
        gyro_n = float(np.linalg.norm(gyro))

        perception = self.perception.update()

        if upright < self.cfg["upright_thresh"]:
            self.controller.state = "DOWN"
            if self._down_t0 is None:
                self._down_t0 = self.metrics.t_sim
            if (self.cfg.get("allow_reset_on_fall")
                    and self.metrics.t_sim - self._down_t0 > self.cfg.get("reset_delay_s", 2.0)):
                sim.reset()
                self._reset_ball()
                self.controller.state = "SEARCH"
                self.metrics.resets += 1
                self._down_t0 = None
            cmd = np.zeros(3, dtype=np.float32)
            kick_req = None
        else:
            self._down_t0 = None
            cmd, kick_req, _ = self.controller.decide(perception, sim, CONTROL_DT)

        if kick_req and self.kick.name is None and upright > self.cfg["upright_thresh"]:
            res = self.kick.request(kick_req, self.policies.sessions, fallen=(upright < 0.5))
            if res.get("status") == "accepted":
                self.controller.mark_kick_started()
                self._ball_peak_speed = 0.0
                self._kick_start_pos = self.sim.data.xpos[self.sim.ball_body].copy()

        policy, eff_cmd = self.kick.select(CONTROL_DT, np.asarray(cmd, np.float32),
                                           speed, gyro_n, upright)

        obs = np.concatenate([
            gyro,
            gravity.astype(np.float32),
            (d.qpos[sim.joint_qpos_idx] - sim.default_pose).astype(np.float32),
            d.qvel[sim.joint_qvel_idx].astype(np.float32),
            sim.last_action,
            np.concatenate([eff_cmd, np.zeros(10, dtype=np.float32)]),
        ]).astype(np.float32)
        action = self.policies.infer(policy, obs)
        sim.last_action = action.copy()
        d.ctrl[:] = sim.default_pose + action
        for _ in range(DECIMATION):
            mujoco.mj_step(sim.model, d)

        self.metrics.t_sim += CONTROL_DT
        self.metrics.steps += 1

        bs = self._ball_speed()
        if self.kick.name:
            self._ball_peak_speed = max(self._ball_peak_speed, bs)

        xy = d.xpos[sim.trunk_id, :2].copy()
        self.metrics.path_len += float(np.linalg.norm(xy - self._last_xy))
        self._last_xy = xy

        if self._kick_was_active and self.kick.name is None:
            disp = 0.0
            if self._kick_start_pos is not None:
                disp = float(np.linalg.norm(self.sim.data.xpos[self.sim.ball_body]
                                            - self._kick_start_pos))
            touched = (disp > self.cfg.get("touch_dist_thresh", 0.3)
                       or self._ball_peak_speed > self.cfg["touch_speed_thresh"])
            self.controller.mark_kick_done(touched)
            self.metrics.kick_attempts += 1
            if touched:
                self.metrics.touches += 1
            self.metrics.events.append({"t": round(self.metrics.t_sim, 3),
                                        "touched": touched,
                                        "ball_disp_m": round(disp, 3)})
        self._kick_was_active = self.kick.name is not None

        self.metrics.ball_range = perception.ball.range_m if perception.ball else float("inf")
        return policy, self.controller.state

    def run(self, max_time_s=10.0, max_touches=1, log_interval_s=1.0,
            auto_restart=False):
        last_log = 0.0
        prev_touches = 0
        rounds = []
        while (self.metrics.t_sim < max_time_s and self.metrics.touches < max_touches):
            _, state = self.step()
            if self.recorder:
                self.recorder.step()
            if self.metrics.touches > prev_touches:
                rounds.append({"round": len(rounds) + 1,
                               "t_sim": round(self.metrics.t_sim, 3),
                               "touches": self.metrics.touches})
                prev_touches = self.metrics.touches
                if auto_restart and self.metrics.touches < max_touches:
                    self.sim.reset()
                    self._reset_ball()
                    self._ball_prev = self.sim.data.xpos[self.sim.ball_body].copy()
                    self._last_xy = self.sim.data.xpos[self.sim.trunk_id, :2].copy()
                    self.controller.state = "SEARCH"
            if self.metrics.t_sim - last_log >= log_interval_s:
                print(f"[t={self.metrics.t_sim:6.2f}s] state={state:<12s} "
                      f"ball={self.metrics.ball_range:5.2f}m "
                      f"touches={self.metrics.touches} kicks={self.metrics.kick_attempts} "
                      f"rounds={len(rounds)} path={self.metrics.path_len:5.2f}m",
                      flush=True)
                last_log = self.metrics.t_sim
        self.metrics.rounds = rounds
        if self.recorder:
            out = self.recorder.finish()
            print(f"[rec] video -> {out}", flush=True)
        return self.metrics
