"""Third-person demo recorder: offscreen EGL render -> PNG frames -> MP4.

Enabled by env DUCKPLAY_RECORD=<out.mp4>. Captures every 2nd control step
(50 Hz -> 25 fps), reusing the web cockpit's tracking camera look.
"""
from __future__ import annotations
import os
from pathlib import Path

os.environ.setdefault("MUJOCO_GL", "egl")
import numpy as np
import mujoco


class DemoRecorder:
    def __init__(self, sim, out_path, width=None, height=None, fps=25,
                 capture_every=None):
        width = int(os.environ.get("DUCKPLAY_REC_W", width or 640))
        height = int(os.environ.get("DUCKPLAY_REC_H", height or 480))
        capture_every = int(os.environ.get("DUCKPLAY_REC_EVERY", capture_every or 2))
        self.sim = sim
        self.out = Path(out_path)
        self.out.parent.mkdir(parents=True, exist_ok=True)
        self.frame_dir = self.out.parent / (".frames_" + self.out.stem)
        self.frame_dir.mkdir(parents=True, exist_ok=True)
        self.renderer = mujoco.Renderer(sim.model, height=height, width=width)
        self.cam = mujoco.MjvCamera()
        self.mode = os.environ.get("DUCKPLAY_REC_MODE", "track")
        if self.mode == "wide":
            self.cam.type = mujoco.mjtCamera.mjCAMERA_FREE
            self.cam.lookat = [0.55, 0.0, 0.28]
            self.cam.distance = 2.4
            self.cam.azimuth = -55
            self.cam.elevation = -20
        else:
            self.cam.type = mujoco.mjtCamera.mjCAMERA_TRACKING
            self.cam.trackbodyid = sim.trunk_id
            self.cam.distance = 0.62
            self.cam.azimuth = 150
            self.cam.elevation = -16
            self.cam.lookat = [0, 0, 0.08]
        self.idx = 0
        self.frames = 0
        self.capture_every = capture_every
        self.fps = fps

    def step(self):
        self.idx += 1
        if self.idx % self.capture_every != 0:
            return
        r = self.renderer
        r.update_scene(self.sim.data, camera=self.cam)
        rgb = r.render()
        import imageio.v2 as iio
        iio.imwrite(self.frame_dir / f"f{self.frames:06d}.png", rgb)
        self.frames += 1

    def finish(self):
        import subprocess
        import imageio_ffmpeg
        if self.frames == 0:
            return None
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        pattern = str(self.frame_dir / "f%06d.png")
        cmd = [exe, "-y", "-framerate", str(self.fps), "-i", pattern,
               "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(self.out)]
        subprocess.run(cmd, check=True, capture_output=True)
        for f in self.frame_dir.glob("*.png"):
            f.unlink()
        self.frame_dir.rmdir()
        return self.out





