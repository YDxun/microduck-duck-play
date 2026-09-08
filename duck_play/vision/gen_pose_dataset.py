"""Synthetic dataset v6: renderer-exact keypoint labels via unique-colour marker
render (no pinhole assumption). Balanced gestures + domain randomization.
"""
from __future__ import annotations
import math, random, sys
from pathlib import Path
import numpy as np
os_env = __import__("os")
os_env.environ.setdefault("MUJOCO_GL", "egl")
os_env.environ.setdefault("DUCK_CAM_PITCH", "40")
import mujoco
from PIL import Image, ImageFilter

PKG = Path(__file__).resolve().parent.parent
SIM_ROOT = PKG.parent
for p in (str(SIM_ROOT), str(PKG)):
    if p not in sys.path:
        sys.path.insert(0, p)

import sim_server as _ss
from sim_server import LocalSim
from duck_play.scenes.gen_gesture_scene import ensure as ensure_scene
from duck_play.perception.headcam import render_headcam_rgb
from duck_play.perception.appearance import AppearanceDetector
from duck_play.behavior.pose import PoseManager

OUT = PKG / "runs" / "pose_data"
W, H = 320, 240
GESTURE_POOL = ["right_fwd", "left_fwd", "both_side", "both_fwd", "idle"]

# geom name -> (rgb color, coco idx)
MARKERS = [
    ("owner_head",  (0.0, 1.0, 0.0), 0),
    ("owner_shL_g", (1.0, 0.0, 1.0), 5),
    ("owner_shR_g", (0.0, 1.0, 1.0), 6),
    ("owner_elL_g", (1.0, 1.0, 0.0), 7),
    ("owner_elR_g", (0.0, 0.0, 1.0), 8),
    ("owner_wrL_g", (1.0, 0.5, 0.0), 9),
    ("owner_wrR_g", (1.0, 0.1, 0.6), 10),
]
ALL_PERSON_GEOMS = None


def _all_person_geoms(m):
    out = []
    for i in range(m.ngeom):
        gn = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, i)
        if gn and (gn.startswith("owner") or gn.startswith("stranger")):
            out.append(i)
    return out


def degrade(img, rng):
    img = np.clip(img.astype(np.float32) * rng.uniform(0.6, 1.5), 0, 255)
    if rng.random() < 0.7:
        amp = rng.uniform(6, 20)
        img += (np.random.random(img.shape).astype(np.float32) - 0.5) * amp
    img = np.clip(img, 0, 255).astype(np.uint8)
    if rng.random() < 0.8:
        rad = rng.choice([0.0, 0.4, 0.8, 1.2])
        if rad > 0:
            img = np.asarray(Image.fromarray(img).filter(ImageFilter.GaussianBlur(rad)))
    return img


def save_img(rgb, path, rng):
    Image.fromarray(rgb).convert("RGB").save(str(path), quality=rng.randint(55, 95))


def write_label(path, box, kps):
    line = ["0", f"{box[0]:.5f}", f"{box[1]:.5f}", f"{box[2]:.5f}", f"{box[3]:.5f}"]
    for i in range(17):
        if i in kps:
            x, y = kps[i]
            line += [f"{x:.5f}", f"{y:.5f}", "2"]
        else:
            line += ["0", "0", "0"]
    path.write_text(" ".join(line) + "\n")


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", type=int, default=520)
    ap.add_argument("--val", type=int, default=120)
    ap.add_argument("--seed", type=int, default=3)
    args = ap.parse_args()

    scene = ensure_scene()
    _ss.SCENE_XML = str(scene)
    sim = LocalSim()
    pose = PoseManager(sim, persons=("owner", "stranger"))
    det = AppearanceDetector(min_area=30)
    rng = random.Random(args.seed)
    m = sim.model
    person_geoms = _all_person_geoms(m)

    (OUT / "images/train").mkdir(parents=True, exist_ok=True)
    (OUT / "images/val").mkdir(parents=True, exist_ok=True)
    (OUT / "labels/train").mkdir(parents=True, exist_ok=True)
    (OUT / "labels/val").mkdir(parents=True, exist_ok=True)

    for split, n in (("train", args.train), ("val", args.val)):
        made = 0
        guard = 0
        queue = (GESTURE_POOL * (n // len(GESTURE_POOL) + 2))
        rng.shuffle(queue)
        qi = 0
        while made < n and guard < 4000:
            guard += 1
            sim.reset()
            x = rng.uniform(0.95, 1.45)
            y = rng.uniform(-0.30, 0.30)
            yaw = math.pi + rng.uniform(-0.3, 0.3)
            gesture = queue[qi % len(queue)]
            qi += 1
            pose.set_pose("owner", (x, y), yaw, gesture)
            pose.set_pose("stranger", (-3.0, -3.0), 0.0, "idle")
            # DR: floor + shirt jitter
            fg = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, "floor")
            v = rng.uniform(0.35, 0.75)
            m.geom_rgba[fg] = [v, v, v * rng.uniform(0.9, 1.2), 1]
            tg = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, "owner_torso")
            j = rng.uniform(0.85, 1.0)
            m.geom_rgba[tg] = [0.85 * j, 0.15 * j, 0.12 * j, 1]
            mujoco.mj_forward(m, sim.data)

            rgb = render_headcam_rgb(sim)
            owner = next((p for p in det.detect(rgb) if p.label == "owner"), None)
            if owner is None:
                continue

            # label render: markers coloured, rest black
            saved = {}
            for gid in person_geoms:
                saved[gid] = m.geom_rgba[gid].copy()
                m.geom_rgba[gid] = [0, 0, 0, 1]
            for gname, col, _ in MARKERS:
                gid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, gname)
                m.geom_rgba[gid] = [col[0], col[1], col[2], 1]
            lbl = render_headcam_rgb(sim).astype(np.float32)
            for gid, col in saved.items():
                m.geom_rgba[gid] = col

            kps = {}
            for gname, col, idx in MARKERS:
                cv = np.array(col) * 255
                mask = (np.abs(lbl - cv) < 50).all(2)
                ys, xs = np.where(mask)
                if len(xs) >= 4:
                    kps[idx] = (xs.mean() / W, ys.mean() / H)
            if len(kps) < 3:
                continue
            box = (owner.cx / W - owner.w / (2 * W), owner.cy / H - owner.h / (2 * H),
                   owner.w / W, owner.h / H)
            img_p = OUT / "images" / split / f"g_{made:04d}.jpg"
            lbl_p = OUT / "labels" / split / f"g_{made:04d}.txt"
            save_img(degrade(rgb, rng), img_p, rng)
            write_label(lbl_p, box, kps)
            made += 1
            if made % 50 == 0:
                print(split, "saved", made, flush=True)
        print(split, "done", made, flush=True)

    yaml = f"path: {OUT}\ntrain: images/train\nval: images/val\nnames:\n  0: person\nkpt_shape: [17, 3]\n"
    (OUT / "dataset.yaml").write_text(yaml)
    print("dataset ready:", OUT, flush=True)


if __name__ == "__main__":
    main()


