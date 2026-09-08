"""Person scene with articulated two-segment arms (mocap) for gesture realism.

Each person = root body (legs+torso+head, shirt color=identity) + per arm two
mocap bodies: {name}_arm{S}_u (upper, shoulder->elbow) and {name}_arm{S}_l
(lower, elbow->wrist). Joint world positions are read back for GT keypoints.
"""
from __future__ import annotations
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIM_ROOT = HERE.parent.parent
ROBOT_DIR = SIM_ROOT / "microduck_rl/src/mjlab_microduck/robot/microduck"
OUT = ROBOT_DIR / "scene_person_gesture.xml"

SKIN = "0.93 0.76 0.62 1"
UP_LEN = 0.16   # upper arm length
LO_LEN = 0.14   # forearm length


def _person_lines(name: str, shirt: str, x: float, y: float) -> list[str]:
    lines = [
        f'    <body name="{name}" mocap="true" pos="{x} {y} 0">',
        f'      <geom name="{name}_legL" type="capsule" fromto="-0.05 0 0.0 -0.05 0 0.45" size="0.035" rgba="0.12 0.12 0.16 1"/>',
        f'      <geom name="{name}_legR" type="capsule" fromto=" 0.05 0 0.0  0.05 0 0.45" size="0.035" rgba="0.12 0.12 0.16 1"/>',
        f'      <geom name="{name}_torso" type="capsule" fromto="0 0 0.45 0 0 1.0" size="0.09" rgba="{shirt}"/>',
        f'      <geom name="{name}_head" type="sphere" pos="0 0 1.12" size="0.11" rgba="{SKIN}"/>',
        '    </body>',
    ]
    for side in ("L", "R"):
        sx = -0.10 if side == "L" else 0.10
        for part, ln in (("u", UP_LEN), ("l", LO_LEN)):
            bname = f"{name}_arm{side}_{part}"
            lines.append(
                f'    <body name="{bname}" mocap="true" pos="{x + sx} {y} 0.95">'
                f'      <geom name="{bname}_g" type="capsule" fromto="0 0 0 0 0 {ln}" '
                f'size="0.033" rgba="{shirt}"/>'
                '    </body>')
        # shoulder + elbow + wrist joint markers (visible bulges for appearance)
        lines.append(
            f'    <body name="{name}_sh{side}" mocap="true" pos="{x + sx} {y} 0.95">'
            f'      <geom name="{name}_sh{side}_g" type="sphere" size="0.075" rgba="{shirt}"/>'
            '    </body>')
        lines.append(
            f'    <body name="{name}_el{side}" mocap="true" pos="{x + sx} {y} 0.95">'
            f'      <geom name="{name}_el{side}_g" type="sphere" size="0.075" rgba="{SKIN}"/>'
            '    </body>')
        lines.append(
            f'    <body name="{name}_wr{side}" mocap="true" pos="{x + sx} {y} 1.05">'
            f'      <geom name="{name}_wr{side}_g" type="sphere" size="0.085" rgba="{SKIN}"/>'
            '    </body>')
    return lines


def _build_xml() -> str:
    lines = [
        '<mujoco model="scene_person_gesture">',
        '  <compiler angle="radian"/>',
        f'  <include file="{ROBOT_DIR / "robot_allcollisions.xml"}"/>',
        f'  <include file="{ROBOT_DIR / "ball.xml"}"/>',
        '  <visual><headlight diffuse="0.8 0.8 0.8" ambient="0.6 0.6 0.66"/></visual>',
        '  <worldbody>',
        '    <light pos="2.2 1.8 3.2" dir="-0.5 -0.4 -1" directional="true"/>',
        '    <light pos="0.2 0.0 1.5" dir="1 0 -0.4" directional="true" diffuse="0.55 0.55 0.55"/>',
        '    <geom name="floor" type="plane" size="0 0 0.05" pos="0 0 0"/>',
    ]
    lines += _person_lines("owner", "0.85 0.15 0.12 1", 1.3, 0.0)
    lines += _person_lines("stranger", "0.12 0.25 0.75 1", -2.0, 1.4)
    lines.append('  </worldbody>')
    lines.append('</mujoco>')
    return "\n".join(lines) + "\n"


def ensure() -> Path:
    if not OUT.exists():
        OUT.write_text(_build_xml())
    return OUT


