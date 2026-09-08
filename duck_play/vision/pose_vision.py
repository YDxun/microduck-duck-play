"""Pure-vision pose + gesture from duck head-cam RGB via exported YOLO-pose ONNX.

Pipeline: letterbox -> onnx -> person box + COCO-17 keypoints -> 2D gesture
rule classifier. Identity stays with AppearanceDetector (owner shirt colour).
"""
from __future__ import annotations
import math
from pathlib import Path
import numpy as np
import onnxruntime as ort

MODEL = Path(__file__).resolve().parent.parent / "runs" / "pose_model.onnx"
IMG = 480


class PoseOnnx:
    def __init__(self, path=None, conf=0.25):
        so = ort.SessionOptions()
        so.intra_op_num_threads = 1
        self.sess = ort.InferenceSession(str(path or MODEL), sess_options=so,
                                         providers=["CPUExecutionProvider"])
        self.inp = self.sess.get_inputs()[0].name
        self.conf = conf

    def letterbox(self, rgb):
        h, w = rgb.shape[:2]
        scale = min(IMG / w, IMG / h)
        nw, nh = int(round(w * scale)), int(round(h * scale))
        canvas = np.full((IMG, IMG, 3), 114, dtype=np.uint8)
        x0 = (IMG - nw) // 2
        y0 = (IMG - nh) // 2
        canvas[y0:y0 + nh, x0:x0 + nw] = np.asarray(
            __import__("PIL").Image.fromarray(rgb).resize((nw, nh)))
        self._x0 = x0
        self._y0 = y0
        self._scale = scale
        return canvas

    def infer(self, rgb):
        x = self.letterbox(rgb).astype(np.float32) / 255.0
        x = np.transpose(x, (2, 0, 1))[None]
        out = self.sess.run(None, {self.inp: x})[0]  # [1,56,N]
        pred = out[0]
        scores = pred[4, :]
        best = int(np.argmax(scores))
        if scores[best] < self.conf:
            return None
        box = pred[0:4, best]  # cx,cy,w,h in padded px
        kp_raw = pred[5:, best]  # 51
        kp = {}
        for i in range(17):
            cx = kp_raw[i * 3]
            cy = kp_raw[i * 3 + 1]
            c = kp_raw[i * 3 + 2]
            if c > 0.1:
                kp[i] = ((cx - self._x0) / self._scale,
                         (cy - self._y0) / self._scale)
        return {"box": box, "score": float(scores[best]), "kp": kp}


def classify_gesture_2d(kp, side_thr=62.0, fwd_d=46.0, fwd_dy=24.0, side_dy=34.0):
    """2D gestures: forward(toward camera, foreshortened) vs side(T)."""
    def pt(i):
        return kp.get(i)

    def arm(side_idx):
        sh = pt(5 if side_idx == 0 else 6)
        wr = pt(9 if side_idx == 0 else 10)
        if not (sh and wr):
            return None
        import math as _m
        d = _m.hypot(wr[0] - sh[0], wr[1] - sh[1])
        dy = wr[1] - sh[1]
        dx = abs(wr[0] - sh[0])
        fwd = d < fwd_d and abs(dy) < fwd_dy
        side = dx > side_thr and abs(dy) < side_dy
        return {"fwd": fwd, "side": side, "dy": dy}

    L = arm(0)
    R = arm(1)
    lf = bool(L and L["fwd"])
    rf = bool(R and R["fwd"])
    ls = bool(L and L["side"])
    rs = bool(R and R["side"])
    if lf and rf:
        return "both_fwd"
    if rf and not lf:
        return "right_fwd"
    if lf and not rf:
        return "left_fwd"
    if ls and rs:
        return "both_side"
    return "idle"






