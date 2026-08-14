#!/usr/bin/env python3
"""مزج التعليق الصوتي مع المؤثرات."""
import numpy as np, wave, subprocess, os, sys
import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
SR = 44100
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SFX = os.path.join(ROOT, "sfx")


def load(path, sr=SR):
    """أي ملف صوتي → numpy mono float"""
    raw = subprocess.run(
        [FF, "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(sr), "-"],
        capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


def write_mp3(path, x, sr=SR, bitrate="192k"):
    m = np.max(np.abs(x)) or 1.0
    if m > 0.99:
        x = x / m * 0.99
    raw = x.astype(np.float32).tobytes()
    subprocess.run(
        [FF, "-v", "error", "-y", "-f", "f32le", "-ac", "1", "-ar", str(sr),
         "-i", "-", "-b:a", bitrate, path],
        input=raw, check=True)
    print(f"  ✓ {os.path.basename(path)}  ({len(x)/sr:.1f}s)")


class Mixer:
    def __init__(self, dur):
        self.n = int(SR * dur)
        self.buf = np.zeros(self.n)

    def add(self, x, at, gain=1.0, fade_in=0.0, fade_out=0.0, loop_to=None):
        x = np.asarray(x, dtype=np.float64).copy()
        if loop_to:
            need = int(SR * loop_to)
            if len(x) < need:
                reps = int(np.ceil(need / len(x)))
                x = np.tile(x, reps)
            x = x[:need]
        if fade_in > 0:
            k = min(int(SR * fade_in), len(x))
            x[:k] *= np.linspace(0, 1, k)
        if fade_out > 0:
            k = min(int(SR * fade_out), len(x))
            x[-k:] *= np.linspace(1, 0, k)
        s = int(SR * at)
        if s >= self.n:
            return self
        e = min(self.n, s + len(x))
        self.buf[s:e] += x[:e - s] * gain
        return self

    def out(self):
        return self.buf


def duck(bed, voice, thresh=0.02, depth=0.40, attack=0.03, release=0.45):
    """ducking: كنخفض الخلفية ملي كيهضر الراوي"""
    n = min(len(bed), len(voice))
    # مغلف الصوت
    win = int(SR * 0.02)
    env = np.abs(voice[:n])
    k = np.ones(win) / win
    env = np.convolve(env, k, mode="same")
    over = env > thresh
    g = np.where(over, 1.0 - depth, 1.0)
    # تنعيم بالهجوم/الإفلات
    out = np.empty(n)
    cur = 1.0
    ac = np.exp(-1.0 / (SR * attack))
    rc = np.exp(-1.0 / (SR * release))
    for i in range(n):
        tgt = g[i]
        c = ac if tgt < cur else rc
        cur = tgt + (cur - tgt) * c
        out[i] = cur
    res = bed.copy()
    res[:n] *= out
    return res


if __name__ == "__main__":
    print("🎛️  كنمزج الديمو…")
    voice = load(os.path.join(ROOT, "samples", "demo_hook_30s.mp3"))
    vdur = len(voice) / SR
    print(f"  مدة التعليق: {vdur:.1f}s")

    # المؤثرات
    drone  = load(f"{SFX}/05_tension_drone.flac")
    knock  = load(f"{SFX}/02_door_knock.flac")
    dopen  = load(f"{SFX}/09_door_open.flac")
    steps  = load(f"{SFX}/03_footsteps.flac")
    crowd  = load(f"{SFX}/04_crowd.flac")
    impact = load(f"{SFX}/06_impact.flac")
    whoosh = load(f"{SFX}/07_whoosh.flac")
    phone  = load(f"{SFX}/01_phone_ring.flac")

    intro = 2.2                       # سكوت فالبداية قبل ما يبدا الراوي
    total = intro + vdur + 3.5
    mx = Mixer(total)

    # ── الطبقة الجوية: درون توتر طول الديمو
    mx.add(drone, at=0.0, gain=0.30, loop_to=total, fade_in=1.8, fade_out=2.5)

    # ── الفتح: خطوات كتقرب، من بعد الباب كيتحل
    mx.add(steps,  at=0.0,  gain=0.34, fade_in=0.3)
    mx.add(dopen,  at=1.5,  gain=0.30)

    # ── الصوت
    mx.add(voice, at=intro, gain=1.0)

    # ── "الباب مسدود" ≈ 4.5s → دقات باب
    mx.add(knock,  at=intro + 2.6, gain=0.24)

    # ── حشد خفيف بعيد فالخلفية (الناس المتجمهرين)
    mx.add(crowd,  at=intro + 5.0, gain=0.13, loop_to=vdur - 4.0,
           fade_in=2.0, fade_out=3.0)

    # ── "ولكن داخل الدار" ≈ منتصف → whoosh + impact
    mid = intro + vdur * 0.42
    mx.add(whoosh, at=mid - 1.6, gain=0.26)
    mx.add(impact, at=mid,       gain=0.34)

    # ── الخاتمة: هاتف كيرن (البلاغ الجاي)
    mx.add(phone,  at=intro + vdur + 0.5, gain=0.30)
    mx.add(impact, at=intro + vdur + 0.2, gain=0.26)

    bed = mx.out()

    # ── ducking: نخفض المؤثرات ملي كيهضر الراوي
    vfull = np.zeros(len(bed))
    s = int(SR * intro)
    vfull[s:s + len(voice)] = voice

    bed_only = bed - vfull
    bed_only = duck(bed_only, vfull, thresh=0.015, depth=0.45)

    final = vfull * 1.0 + bed_only

    # ── ليميتر ناعم
    final = np.tanh(final * 1.15) * 0.92

    write_mp3(os.path.join(ROOT, "samples", "demo_hook_30s_SFX.mp3"), final)
    print("✅ سالا.")
