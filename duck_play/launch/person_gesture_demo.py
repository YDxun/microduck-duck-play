#!/usr/bin/env python3
"""Robust person+gesture demo.

Vision mode adds engineering robustness:
 - N-frame temporal confirmation (vote) before acting
 - warmup window at start
 - cooldown after an action + must return to idle before the same/different
   gesture can fire again
 - real-time confusion matrix: expected(ground-truth timeline) vs predicted
"""
from __future__ import annotations
import json, os, sys, time, math
from collections import Counter
from pathlib import Path
import numpy as np
os.environ.setdefault("MUJOCO_GL", "egl")
os.environ.setdefault("DUCK_CAM_PITCH", "40")
import mujoco
import onnxruntime as ort

PKG = Path(__file__).resolve().parent.parent
SIM_ROOT = PKG.parent
for p in (str(SIM_ROOT), str(PKG)):
    if p not in sys.path:
        sys.path.insert(0, p)

import sim_server as _ss
from sim_server import LocalSim, CONTROL_DT, DECIMATION, quat_rotate_inverse
from duck_play.scenes.gen_gesture_scene import ensure as ensure_scene
from duck_play.perception.headcam import render_headcam_rgb
from duck_play.perception.appearance import AppearanceDetector
from duck_play.behavior.pose import PoseManager
from duck_play.behavior.gesture_map import GESTURE_TO_ACTION
from duck_play.control.actions import ActionManager
from duck_play.vision.pose_vision import PoseOnnx, classify_gesture_2d

POLICY_DIR = SIM_ROOT / "microduck/policies"
SESSION = {}


def load_policy(stem):
    if stem not in SESSION:
        fname = "roulade.onnx" if stem == "roulade" else f"{stem}.onnx"
        so = ort.SessionOptions(); so.intra_op_num_threads = 1
        s = ort.InferenceSession(str(POLICY_DIR / fname), sess_options=so,
                                 providers=["CPUExecutionProvider"])
        SESSION[stem] = (s, s.get_inputs()[0].name, s.get_outputs()[0].name)
    return SESSION[stem]


def infer(stem, obs):
    s, i, o = load_policy(stem)
    return s.run([o], {i: obs.reshape(1, -1)})[0].squeeze(0)


def build_obs(sim, cmd):
    d = sim.data
    gravity = quat_rotate_inverse(d.xquat[sim.trunk_id].copy(), np.array([0, 0, -1.0]))
    gyro = d.sensordata[sim.imu_gyro_adr:sim.imu_gyro_adr + 3].astype(np.float32)
    return np.concatenate([
        gyro, gravity.astype(np.float32),
        (d.qpos[sim.joint_qpos_idx] - sim.default_pose).astype(np.float32),
        d.qvel[sim.joint_qvel_idx].astype(np.float32), sim.last_action,
        np.concatenate([cmd, np.zeros(10, dtype=np.float32)]),
    ]).astype(np.float32)


TIMELINE = [
    (0.0, 3.0, "idle"),
    (3.0, 3.5, "right_fwd"),
    (6.5, 2.0, "idle"),
    (8.5, 3.5, "both_fwd"),
    (12.0, 2.0, "idle"),
    (14.0, 3.5, "both_side"),
    (17.5, 2.0, "idle"),
    (19.5, 3.5, "left_fwd"),
    (23.0, 60.0, "idle"),
]


def gesture_at(t):
    for s0, dur, g in TIMELINE:
        if s0 <= t < s0 + dur:
            return g
    return "idle"

def stranger_at(t):
    """Stranger walks by on the owner side while owner rests (idle window)."""
    if 6.6 <= t <= 8.2:
        f = (t - 6.6) / 1.6
        return (1.0, -0.85 + 0.45 * f), "right_fwd"
    return (-3.0, -3.0), "idle"


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--time", type=float, default=40.0)
    ap.add_argument("--vision", action="store_true")
    ap.add_argument("--vote", type=int, default=4, help="N-frame confirmation")
    ap.add_argument("--warmup", type=float, default=2.5)
    ap.add_argument("--post", type=float, default=1.5)
    ap.add_argument("--no-act", action="store_true", help="evaluate recognition only")
    args = ap.parse_args()

    scene = ensure_scene()
    _ss.SCENE_XML = str(scene)
    sim = LocalSim()
    sim.reset()
    pose = PoseManager(sim, persons=("owner", "stranger"))
    detector = AppearanceDetector()
    actions = ActionManager()
    pose_onnx = PoseOnnx() if args.vision else None
    recorder = None
    if os.environ.get("DUCKPLAY_RECORD"):
        from duck_play.recording.recorder import DemoRecorder
        recorder = DemoRecorder(sim, os.environ["DUCKPLAY_RECORD"])

    cand = None
    cand_votes = 0
    last_label = "idle"
    last_fired = None
    last_fire_t = -1e9
    cm = Counter()
    log = {"mode": "vision" if args.vision else "gt", "actions": [],
           "confusion": []}
    t_sim = 0.0
    step_n = 0

    print(f"[gesture] start mode={'vision' if args.vision else 'gt'} "
          f"vote={args.vote} warmup={args.warmup} post={args.post}", flush=True)
    last_print = 0.0
    while t_sim < args.time:
        d = sim.data
        pose.set_pose("owner", (1.1, 0.0), math.pi, gesture_at(t_sim))
        _sp, _sg = stranger_at(t_sim)
        pose.set_pose("stranger", _sp, 0.0, _sg)
        mujoco.mj_forward(sim.model, d)

        is_det = (step_n % 6 == 0)
        if is_det:
            rgb = render_headcam_rgb(sim)
            dets = detector.detect(rgb)
            exp = gesture_at(t_sim)
            if pose_onnx is not None:
                res = pose_onnx.infer(rgb)
                pred = classify_gesture_2d(res["kp"]) if res else "none"
            else:
                pred, _ = pose.classify("owner")
            cm[(exp, pred)] += 1
            log["confusion"].append({"t": round(t_sim, 2), "exp": exp, "pred": pred})
            if pose_onnx is not None:
                if pred == cand:
                    cand_votes += 1
                else:
                    cand = pred
                    cand_votes = 1

        if pose_onnx is not None:
            confirmed = (cand if cand_votes >= args.vote else None)
            # require returning to idle before allowing next fire
            if confirmed == "idle":
                last_fired = None
            if (confirmed and confirmed != "idle" and not actions.busy
                    and confirmed != last_fired
                    and t_sim > args.warmup
                    and t_sim - last_fire_t > args.post):
                act = GESTURE_TO_ACTION.get(confirmed)
                if act and not args.no_act and actions.request(act):
                    last_fired = confirmed
                    last_fire_t = t_sim
                    log["actions"].append({"t": round(t_sim, 2), "action": act,
                                           "gesture": confirmed})
                    print(f"[action] t={t_sim:5.2f} {act} (vision={confirmed})",
                          flush=True)
            gesture_for_log = confirmed or "idle"
        else:
            g, _ = pose.classify("owner")
            gesture_for_log = g
            act = GESTURE_TO_ACTION.get(g)
            if act and not actions.busy and not args.no_act and act not in {a["action"] for a in log["actions"]}:
                if actions.request(act):
                    log["actions"].append({"t": round(t_sim, 2), "action": act,
                                           "gesture": g})
                    print(f"[action] t={t_sim:5.2f} {act} (gt={g})", flush=True)

        policy, eff_cmd = actions.select(CONTROL_DT, np.zeros(3, np.float32), 1.0)
        obs = build_obs(sim, eff_cmd)
        act_out = infer(policy, obs)
        sim.last_action = act_out.copy()
        d.ctrl[:] = sim.default_pose + act_out
        for _ in range(DECIMATION):
            mujoco.mj_step(sim.model, d)
        if recorder:
            recorder.step()
        t_sim += CONTROL_DT
        step_n += 1
        if t_sim - last_print >= 2.0:
            print(f"[t={t_sim:5.2f}] gesture={gesture_for_log:<9s} "
                  f"actions={[a['action'] for a in log['actions']]}", flush=True)
            last_print = t_sim

    if recorder:
        recorder.finish()
    # confusion summary
    summary = {}
    for (exp, pred), cnt in cm.items():
        summary.setdefault(exp, {})[pred] = cnt
    total = sum(cm.values())
    correct = sum(c for (e, p), c in cm.items() if e == p)
    log["cm"] = summary
    log["cm_acc"] = round(correct / total, 3) if total else None
    out_dir = PKG / "runs"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"gesture_{time.strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(log, ensure_ascii=False, indent=2))
    print("\n[cm] accuracy:", log["cm_acc"])
    print("[cm] per-expected:", json.dumps(summary, ensure_ascii=False))
    print("[gesture] actions:", [a["action"] for a in log["actions"]])
    print(f"[gesture] report -> {out}")


if __name__ == "__main__":
    main()




