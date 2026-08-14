#!/usr/bin/env python3
"""تحضير ثامبنيلات يوتيوب 1280x720 — بلا نص محروق (النص كيتزاد فمحرر خارجي)."""
import os, subprocess
import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = f"{ROOT}/img"
OUT = f"{ROOT}/output/thumbnails"
os.makedirs(OUT, exist_ok=True)

W, H = 1280, 720

# (المصدر, اسم الخرج, بلاصة الفراغ للنص, معالجة)
JOBS = [
    ("thumb_v2_door", "thumb_MAIN_door", "يسار (نص كحل كبير)",
     "eq=contrast=1.20:saturation=1.12:brightness=0.015,"
     "unsharp=5:5:1.0:5:5:0.0,"
     "colorbalance=rs=-0.03:bs=0.05,"
     "vignette=PI/4.8"),

    ("thumb_v2_keyhole", "thumb_ALT_keyhole", "يمين",
     "eq=contrast=1.26:saturation=1.08,"
     "unsharp=5:5:1.0:5:5:0.0,"
     "vignette=PI/4.4"),

    ("thumb_base",  "thumb_01_door_ajar",   "يسار",
     "eq=contrast=1.22:saturation=1.10:brightness=0.01,"
     "unsharp=5:5:0.9:5:5:0.0,"
     "colorbalance=rs=-0.05:bs=0.08:gh=-0.02,"
     "vignette=PI/4.5"),

    ("thumb_alt",   "thumb_02_keyhole",     "يمين",
     "eq=contrast=1.28:saturation=1.05,"
     "unsharp=5:5:1.0:5:5:0.0,"
     "colorbalance=rs=0.04:bs=0.06,"
     "vignette=PI/4.2"),

    ("01_door_closed", "thumb_03_alley",    "يمين",
     "eq=contrast=1.25:saturation=1.15:brightness=0.02,"
     "unsharp=5:5:0.8:5:5:0.0,"
     "colorbalance=rs=-0.04:bs=0.07,"
     "vignette=PI/4.5"),

    ("07_police_lights", "thumb_04_lights", "يسار",
     "eq=contrast=1.20:saturation=1.25,"
     "unsharp=5:5:0.8:5:5:0.0,"
     "vignette=PI/5"),
]


def make(src, name, note, filt):
    inp = f"{IMG}/{src}.png"
    out = f"{OUT}/{name}.jpg"
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,"
          f"crop={W}:{H},{filt},format=yuv420p")
    subprocess.run([FF, "-v", "error", "-y", "-i", inp, "-vf", vf,
                    "-q:v", "2", out], check=True)
    kb = os.path.getsize(out) // 1024
    print(f"  ✓ {name}.jpg  ({kb} KB)  · فراغ النص: {note}")


if __name__ == "__main__":
    print("🖼️  كنحضر الثامبنيلات…")
    for job in JOBS:
        make(*job)
    print(f"✅ سالا — {OUT}")
