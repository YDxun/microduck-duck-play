"""Offline benchmark: infer once per frame, sweep classifier thresholds."""
import glob, json, os, sys
sys.path.insert(0, "/root/microduck_sim"); sys.path.insert(0, "/root/microduck_sim/duck_play")
import numpy as np
from PIL import Image
from duck_play.vision.pose_vision import PoseOnnx, classify_gesture_2d

files = sorted(glob.glob("/root/microduck_sim/duck_play/runs/gesture_eval/*.jpg"))
m = PoseOnnx()
preds = []   # (gt, kp or None)
for f in files:
    g = os.path.basename(f).split("_")[0]
    rgb = np.asarray(Image.open(f).convert("RGB"))
    r = m.infer(rgb)
    preds.append((g, r["kp"] if r else None))
print("frames", len(preds))

best = None
grid = []
for sd in [40, 50, 60, 70, 80, 90]:
    for fd in [26, 34, 42, 50, 60, 70]:
        for fdy in [12, 18, 24, 30]:
            for sdy in [22, 30, 40]:
                acc = 0
                for g, kp in preds:
                    if kp is None:
                        p = "none"
                    else:
                        p = classify_gesture_2d(kp, side_thr=sd, fwd_d=fd, fwd_dy=fdy, side_dy=sdy)
                    if p == g:
                        acc += 1
                acc /= len(preds)
                grid.append((acc, sd, fd, fdy, sdy))
grid.sort(reverse=True)
for row in grid[:5]:
    print("acc", round(row[0], 3), "side_thr", row[1], "fwd_d", row[2], "fwd_dy", row[3], "side_dy", row[4])
best = grid[0]
json.dump({"best": list(best)}, open("/root/microduck_sim/duck_play/runs/benchmark_best.json", "w"))
