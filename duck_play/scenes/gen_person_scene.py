"""Generate an L1 'person' scene: robot + ball + two kinematic mocap humans.

- owner   : red shirt  (the person to follow / summon)
- stranger: blue shirt (to be ignored; orbit when too close)
Mocap bodies are driven kinematically (scripted paths), no physical collision
(contype/conaffinity 0) so L1 control stays clean.
"""
from __future__ import annotations
from pathlib import Path

HERE = Path(__file__).resolve().parent                 # duck_play/scenes
SIM_ROOT = HERE.parent.parent                          # /root/microduck_sim
ROBOT_DIR = SIM_ROOT / "microduck_rl/src/mjlab_microduck/robot/microduck"
OUT = ROBOT_DIR / "scene_person.xml"

SKIN = "0.93 0.76 0.62 1"


def _person(name: str, shirt: str, tag: str, x: float, y: float) -> list[str]:
    return [
        f'    <body name="{name}" mocap="true" pos="{x} {y} 0">',
        f'      <geom name="{name}_legL" type="capsule" fromto="-0.05 0 0.0 -0.05 0 0.45" size="0.035" rgba="0.12 0.12 0.16 1"/>',
        f'      <geom name="{name}_legR" type="capsule" fromto=" 0.05 0 0.0  0.05 0 0.45" size="0.035" rgba="0.12 0.12 0.16 1"/>',
        f'      <geom name="{name}_torso" type="capsule" fromto="0 0 0.45 0 0 1.0" size="0.09" rgba="{shirt}"/>',
        f'      <geom name="{name}_head" type="sphere" pos="0 0 1.12" size="0.11" rgba="{SKIN}"/>',
        f'      <geom name="{name}_tag" type="box" pos="0 0.14 1.0" size="0.05 0.012 0.05" rgba="{tag}"/>',
        '    </body>',
    ]


def _build_xml() -> str:
    lines = [
        '<mujoco model="scene_person">',
        '  <compiler angle="radian"/>',
        f'  <include file="{ROBOT_DIR / "robot_allcollisions.xml"}"/>',
        f'  <include file="{ROBOT_DIR / "ball.xml"}"/>',
        '  <visual><headlight diffuse="0.6 0.6 0.6" ambient="0.4 0.4 0.45"/></visual>',
        '  <worldbody>',
        '    <light pos="2.2 1.8 3.2" dir="-0.5 -0.4 -1" directional="true"/>',
        '    <geom name="floor" type="plane" size="0 0 0.05" pos="0 0 0"/>',
    ]
    lines += _person("owner", "0.85 0.15 0.12 1", "1 1 1 1", 1.3, 0.0)
    lines += _person("stranger", "0.12 0.25 0.75 1", "0 0 0 1", -2.5, -2.5)
    lines.append('  </worldbody>')
    lines.append('</mujoco>')
    return "\n".join(lines) + "\n"


def ensure() -> Path:
    if not OUT.exists():
        OUT.write_text(_build_xml())
    return OUT
