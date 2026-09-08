"""Central config for duck_play chase/person closed-loop experiments.

NOTE: physics/policies are reused from the cloud sim (sim_server.py) so the
closed loop matches the web cockpit exactly (same MJCF, same ONNX, same obs).
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIM_ROOT = HERE.parent                 # /root/microduck_sim
SCENE_XML = SIM_ROOT / "microduck_rl/src/mjlab_microduck/robot/microduck/scene_pretty.xml"
POLICY_DIR = SIM_ROOT / "microduck/policies"

PHYS_DT = 0.005
DECIMATION = 4
CONTROL_DT = PHYS_DT * DECIMATION      # 50 Hz control

# --- chase-ball tuning ---
CHASE = {
    "search_wz_radps": 0.9,
    "align_ang_rad": 0.50,             # beyond this: turn only; inside: turn-and-go
    "kick_range_m": 0.16,              # trigger kick when ball near foot (validated geometry)
    "approach_stop_m": 0.30,
    "vx_max": 0.6,
    "wz_max": 1.2,
    "kp_yaw": 1.6,                     # proportional gain yaw -> wz
    "kp_vx": 1.6,                      # gain (range - kick_range) -> vx
    "approach_min_vx": 0.20,           # avoid gait deadband while approaching
    "side_switch_range_m": 0.45,       # inside this, steer ball onto chosen foot side
    "side_offset_m": 0.042,            # lateral target from validated kick fixture
    "touch_speed_thresh": 0.5,         # ball speed m/s during kick => touched
    "touch_dist_thresh": 0.30,         # ball displacement m over a kick cycle => touched
    "upright_thresh": 0.5,
    "kick_timeout_s": 6.0,
    "kick_side": "auto",               # auto | left | right
    "allow_reset_on_fall": True,       # dev-only; False for fair eval
    "reset_delay_s": 2.0,
}

# --- person-follow L1 ---
PERSON = {
    "follow_dist_m": 0.8,
    "min_dist_m": 0.5,
    "deadband_m": 0.10,
    "kp_dist": 1.2,
    "kp_yaw": 1.6,
    "orbit_trigger_m": 0.9,            # stranger closer than this -> orbit
    "orbit_duration_s": 3.0,           # how long to circle around the stranger
    "summon_hold_s": 1.2,              # hold near owner before marking summon done
}

# --- dribble/slalom derivative (stub config for future waypoint task) ---
DRIBBLE = {
    "cone_x": [1.5, 2.4, 3.3],
    "cone_offset_y": [0.0, -0.4, 0.4],
    "gate_width_m": 0.9,
}


