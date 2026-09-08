"""Owner-gesture -> duck-action mapping (extensible)."""
GESTURE_TO_ACTION = {
    "right_fwd": "sit",
    "left_fwd":  "roll",
    "both_fwd":  "pick",
    "both_side": "stand_up",
}

# how many seconds a gesture must be stable before firing
GESTURE_HOLD_S = 0.6



