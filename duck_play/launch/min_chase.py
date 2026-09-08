#!/usr/bin/env python3
"""Minimal closed loop: chase the ball with ground-truth perception, CPU-only.

Run from duck_play/ :
    python3 launch/min_chase.py --time 60 --max-touches 2 --arena
Writes a JSON report under duck_play/runs/.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent      # duck_play
SIM_ROOT = PKG.parent                              # /root/microduck_sim
for p in (str(SIM_ROOT), str(PKG)):
    if p not in sys.path:
        sys.path.insert(0, p)

from duck_play.behavior.chase import ChaseController
from duck_play.control.runner import ChaseRunner
from duck_play.config import CHASE


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--time", type=float, default=10.0, help="max sim seconds")
    ap.add_argument("--max-touches", type=int, default=1)
    ap.add_argument("--randomize-ball", action="store_true")
    ap.add_argument("--arena", action="store_true", help="use walled arena for re-chase")
    ap.add_argument("--auto-restart", action="store_true", help="reset ball each round for multi-round chase")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--kick-side", choices=["auto", "left", "right"], default="auto")
    args = ap.parse_args()

    cfg = dict(CHASE)
    cfg["kick_side"] = args.kick_side
    ctrl = ChaseController(cfg)
    scene_xml = None
    if args.arena:
        from duck_play.scenes.gen_wall_scene import ensure as ensure_scene
        scene_xml = ensure_scene()
    runner = ChaseRunner(ctrl, cfg=cfg, seed=args.seed,
                         randomize_ball=args.randomize_ball, scene_xml=scene_xml)
    runner.sim.reset()
    runner._reset_ball()

    print(f"[chase] start: time={args.time}s max_touches={args.max_touches} "
          f"kick_side={args.kick_side} randomize_ball={args.randomize_ball} "
          f"arena={args.arena}", flush=True)
    t0 = time.time()
    metrics = runner.run(max_time_s=args.time, max_touches=args.max_touches,
                         auto_restart=args.auto_restart)
    wall = time.time() - t0

    report = metrics.to_dict()
    report["wall_s"] = round(wall, 3)
    report["config"] = cfg
    out_dir = PKG / "runs"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"chase_{time.strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n[chase] done: touches={report['touches']} "
          f"kick_attempts={report['kick_attempts']} "
          f"path={report['path_len_m']}m wall={wall}s")
    print(f"[chase] report -> {out}")


if __name__ == "__main__":
    main()



