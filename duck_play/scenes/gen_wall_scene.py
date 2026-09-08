"""Generate a walled arena scene for chase experiments (does NOT touch the
shared scene_pretty.xml used by the web cockpit / RL training).

Physics identical to scene_pretty.xml (robot_allcollisions) EXCEPT:
- an invisible circular wall keeps duck/ball inside;
- the ball uses rolling damping (friction 0.8/0.02/0.03) so a kicked ball
  slows and stops, enabling re-chase of the same ball for multi-touch demos.
"""
from __future__ import annotations
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent                 # duck_play/scenes
SIM_ROOT = HERE.parent.parent                          # /root/microduck_sim
ROBOT_DIR = SIM_ROOT / "microduck_rl/src/mjlab_microduck/robot/microduck"
OUT = ROBOT_DIR / "scene_play_wall.xml"

WALL_R = 1.7
N_SEG = 16
WALL_HALF_H = 3.0    # very tall: contain even lofted kicks
WALL_T = 0.06


def _build_xml() -> str:
    inc = lambda name: f'<include file="{ROBOT_DIR / name}"/>'
    lines = ['<mujoco model="scene_play_wall">',
             '  <compiler angle="radian"/>',
             f'  {inc("robot_allcollisions.xml")}',
             '  <visual><headlight diffuse="0.6 0.6 0.6" ambient="0.4 0.4 0.45"/></visual>',
             '  <worldbody>',
             '    <light pos="2.2 1.8 3.2" dir="-0.5 -0.4 -1" directional="true"/>',
             '    <geom name="floor" type="plane" size="0 0 0.05" pos="0 0 0"/>',
             '    <!-- experiment ball: same 70mm/15g, rolling damping for re-chase -->',
             '    <body name="ball" pos="0.9 0 0.035">',
             '      <freejoint name="ball_free"/>',
             '      <inertial pos="0 0 0" mass="0.015" diaginertia="1.225e-5 1.225e-5 1.225e-5"/>',
             '      <geom name="ball_geom" type="sphere" size="0.035" rgba="1 0.55 0 1" friction="0.8 0.02 0.03"/>',
             '    </body>']
    for i in range(N_SEG):
        ang = 2.0 * math.pi * i / N_SEG
        half_len = WALL_R * math.tan(math.pi / N_SEG) + 0.05
        x = WALL_R * math.cos(ang)
        y = WALL_R * math.sin(ang)
        qw = math.cos(ang / 2.0)
        qz = math.sin(ang / 2.0)
        lines.append(
            f'    <geom name="wall_{i}" type="box" pos="{x:.4f} {y:.4f} {WALL_HALF_H}" '
            f'size="{WALL_T:.4f} {half_len:.4f} {WALL_HALF_H:.4f}" '
            f'quat="{qw:.4f} 0 0 {qz:.4f}" contype="1" conaffinity="1"/>')
    lines.append('  </worldbody>')
    lines.append('</mujoco>')
    return "\n".join(lines) + "\n"


def ensure() -> Path:
    if not OUT.exists():
        OUT.write_text(_build_xml())
    return OUT

