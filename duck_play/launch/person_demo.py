#!/usr/bin/env python3
"""L1 person demo: summon -> follow owner -> orbit stranger -> back to owner.

Scenario timeline (kinematic proxies):
  owner   : stands at (1.3, 0) for 6 s (summon), then walks a small course
  stranger: walks across the duck's path between t=8..14 s (triggers orbit)
Run:
  python3 launch/person_demo.py --time 34
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
SIM_ROOT = PKG.parent
for p in (str(SIM_ROOT), str(PKG)):
    if p not in sys.path:
        sys.path.insert(0, p)

from duck_play.behavior.person_follow import PersonFollowController
from duck_play.control.person_runner import PersonRunner
from duck_play.config import PERSON
from duck_play.scenes.gen_person_scene import ensure as ensure_scene


def lerp(a, b, f):
    return a + (b - a) * f


def owner_pos(t: float):
    if t < 6.0:
        return 1.3, 0.0
    if t < 15.0:
        f = (t - 6.0) / 9.0
        return lerp(1.3, -0.6, f), lerp(0.0, 0.9, f)
    if t < 22.0:
        return -0.6, 0.9
    f = min(1.0, (t - 22.0) / 8.0)
    return lerp(-0.6, 0.3, f), lerp(0.9, -0.4, f)


def stranger_pos(t: float):
    if 8.0 <= t <= 14.0:
        f = (t - 8.0) / 6.0
        return 0.6, lerp(-1.8, 1.8, f)
    return -2.6, -2.6


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--time", type=float, default=34.0)
    args = ap.parse_args()

    scene_xml = ensure_scene()
    person_paths = {
        "owner": {"body": "owner", "color": "red", "pos": owner_pos},
        "stranger": {"body": "stranger", "color": "blue", "pos": stranger_pos},
    }
    ctrl = PersonFollowController(dict(PERSON))
    runner = PersonRunner(ctrl, scene_xml, person_paths, cfg=dict(PERSON))
    runner.sim.reset()

    print(f"[person] start time={args.time}s scene={scene_xml.name}", flush=True)
    t0 = time.time()
    last_log = 0.0
    while runner.metrics.t_sim < args.time:
        state, owner_rng = runner.step(runner.metrics.t_sim)
        if runner.metrics.t_sim - last_log >= 0.5:
            st = next((p for p in runner.perception.update().persons if p.label == "stranger"), None)
            print(f"[t={runner.metrics.t_sim:6.2f}s] state={state:<8s} owner={owner_rng:5.2f}m "
                  f"stranger={st.range_m:5.2f}m" if st else
                  f"[t={runner.metrics.t_sim:6.2f}s] state={state:<8s} owner={owner_rng:5.2f}m stranger= far",
                  flush=True)
            last_log = runner.metrics.t_sim
    if getattr(runner, 'recorder', None):
        runner.recorder.finish()
    wall = time.time() - t0
    report = runner.metrics.to_dict()
    report["wall_s"] = round(wall, 3)
    out_dir = PKG / "runs"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"person_{time.strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n[person] done: {json.dumps(report, ensure_ascii=False)}")
    print(f"[person] report -> {out}")


if __name__ == "__main__":
    main()

