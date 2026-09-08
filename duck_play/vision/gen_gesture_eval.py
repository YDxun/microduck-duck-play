"""Labeled offline eval frames: filename = gesture_idx.jpg."""
from __future__ import annotations
import math, os, random, sys
from pathlib import Path
os.environ.setdefault("MUJOCO_GL", "egl")
os.environ.setdefault("DUCK_CAM_PITCH", "40")
sys.path.insert(0, "/root/microduck_sim"); sys.path.insert(0, "/root/microduck_sim/duck_play")
import mujoco
from PIL import Image
import sim_server as _ss
from sim_server import LocalSim
from duck_play.scenes.gen_gesture_scene import ensure
from duck_play.perception.headcam import render_headcam_rgb
from duck_play.behavior.pose import PoseManager, GESTURES

OUT = Path("/root/microduck_sim/duck_play/runs/gesture_eval")
OUT.mkdir(parents=True, exist_ok=True)
_ss.SCENE_XML = str(ensure())
sim = LocalSim(); sim.reset()
pose = PoseManager(sim, persons=("owner", "stranger"))
rng = random.Random(7)
per = 30
for g in GESTURES:
    for i in range(per):
        sim.reset()
        x = rng.uniform(1.0, 1.3)
        y = rng.uniform(-0.25, 0.25)
        yaw = math.pi + rng.uniform(-0.2, 0.2)
        pose.set_pose("owner", (x, y), yaw, g)
        pose.set_pose("stranger", (-3.0, -3.0), 0.0, "idle")
        mujoco.mj_forward(sim.model, sim.data)
        rgb = render_headcam_rgb(sim)
        Image.fromarray(rgb).convert("RGB").save(str(OUT / f"{g}_{i:03d}.jpg"), quality=92)
print("eval frames:", len(list(OUT.glob('*.jpg'))))
