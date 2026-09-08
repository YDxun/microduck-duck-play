"""Visibility scan: choose camera pitch + person distance so that all gesture
keypoints stay inside the duck head-cam frame (dynamic head pitch allowed)."""
from __future__ import annotations
import json, math, sys, os
os.environ.setdefault("MUJOCO_GL", "egl")
sys.path.insert(0, "/root/microduck_sim"); sys.path.insert(0, "/root/microduck_sim/duck_play")
import mujoco
import sim_server as _ss
from sim_server import LocalSim
from duck_play.scenes.gen_gesture_scene import ensure
from duck_play.perception.headcam import render_headcam_rgb
from duck_play.behavior.pose import PoseManager, GESTURES
import numpy as np

_ss.SCENE_XML = str(ensure())
sim = LocalSim(); sim.reset()
pose = PoseManager(sim, persons=("owner", "stranger"))
m = sim.model
MARKERS = [("owner_head", (0.0,1.0,0.0)), ("owner_shL_g",(1.0,0.0,1.0)), ("owner_shR_g",(0.0,1.0,1.0)),
           ("owner_elL_g",(1.0,1.0,0.0)), ("owner_elR_g",(0.0,0.0,1.0)),
           ("owner_wrL_g",(1.0,0.5,0.0)), ("owner_wrR_g",(1.0,0.1,0.6))]
PITCHES = [20, 30, 40, 50, 60]
DISTS = [0.7, 1.0, 1.4, 1.8, 2.2]
GESTS = list(GESTURES.keys())

def person_geoms():
    out=[]
    for i in range(m.ngeom):
        gn = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, i)
        if gn and (gn.startswith("owner") or gn.startswith("stranger")):
            out.append(i)
    return out
PG = person_geoms()

def visible(x, pitch, gesture):
    pose.set_pose("owner", (x, 0.0), math.pi, gesture)
    pose.set_pose("stranger", (-3.0, -3.0), 0.0, "idle")
    mujoco.mj_forward(m, sim.data)
    saved={}
    for gid in PG:
        saved[gid]=m.geom_rgba[gid].copy(); m.geom_rgba[gid]=[0,0,0,1]
    for gn,col in MARKERS:
        gid=mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, gn)
        m.geom_rgba[gid]=[col[0],col[1],col[2],1]
    os.environ["DUCK_CAM_PITCH"]=str(pitch)
    lbl = render_headcam_rgb(sim).astype(np.float32)
    for gid,col in saved.items(): m.geom_rgba[gid]=col
    cnt=0
    for gn,col in MARKERS:
        cv=np.array(col)*255
        mask=(np.abs(lbl-cv)<50).all(2)
        if int(mask.sum())>=4: cnt+=1
    return cnt

result={}
print("pitch\\dist", "\t".join(map(str,DISTS)))
for p in PITCHES:
    row=[]
    for x in DISTS:
        counts={g: visible(x,p,g) for g in GESTS}
        row.append(min(counts.values()))
        result.setdefault(str(p),{})[str(x)]=counts
    print(p, "\t".join(map(str,row)))
json.dump(result, open("runs/visibility_scan.json","w"), indent=1)
print("saved runs/visibility_scan.json")
