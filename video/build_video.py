#!/usr/bin/env python3
"""
بناء فيديو الحلقة:
  - لقطة كل 10 ثواني
  - حركة Ken Burns (زوم/بان) على كل لقطة باش الفيديو ما يكونش ممل
  - انتقالات crossfade
  - تنويعات (قصّة، اتجاه، درجة لون) باش نفس الصورة ما تبانش مكررة
"""
import os, subprocess, math, json, random
import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = f"{ROOT}/img"
WORK = f"{ROOT}/build/video"
os.makedirs(WORK, exist_ok=True)

W, H, FPS = 1920, 1080, 30
SHOT = 10.0          # مدة اللقطة
XF = 0.8             # مدة الانتقال
AUDIO = f"{ROOT}/output/EPISODE_FULL_SFX.mp3"

# ═══════════════════════════════════════════════════
#  خريطة المشاهد — أي صورة فأي وقت
#  (بداية_الثانية, نهاية_الثانية, [قائمة الصور])
# ═══════════════════════════════════════════════════
TIMELINE = [
    # ── الهوك: الباب، الدخول، اللغز
    (0,    45,  ["01_door_closed", "02_keyhole", "03_hallway", "09_police_tape"]),
    # ── المقدمة + الدار البيضاء
    (45,   90,  ["04_casablanca_night", "05_case_file", "01_door_closed", "03_hallway"]),
    # ── ركزو معايا / بداية القضية
    (90,  167,  ["05_case_file", "04_casablanca_night", "02_keyhole", "09_police_tape",
                 "01_door_closed", "03_hallway"]),
    # ── البلاغ + الوصول
    (167, 235,  ["06_phone_station", "07_police_lights", "08_crowd", "09_police_tape"]),
    # ── دخول العميد + المعاينة
    (235, 275,  ["03_hallway", "10_gloves", "09_police_tape", "02_keyhole"]),
    # ── الشرطة العلمية / البحث
    (275, 340,  ["10_gloves", "02_keyhole", "03_hallway", "05_case_file"]),
    # ── دار مرتبة / الماريو / بلا اقتحام
    (340, 376,  ["01_door_closed", "02_keyhole", "03_hallway", "09_police_tape"]),
    # ── التحقيق + الشهود
    (376, 440,  ["19_interrogation", "18_shop_street", "08_crowd", "05_case_file"]),
    # ── العائلة / الطرق مسدودة / الانتظار
    (440, 482,  ["05_case_file", "10_gloves", "04_casablanca_night", "03_hallway"]),
    # ── التقرير + القضية الثانية
    (482, 560,  ["05_case_file", "04_casablanca_night", "06_phone_station",
                 "07_police_lights", "09_police_tape"]),
    # ── الفيلا
    (560, 610,  ["01_door_closed", "03_hallway", "02_keyhole", "10_gloves"]),
    # ── الريحة + البحث على الكاميرات
    (610, 714,  ["03_hallway", "10_gloves", "18_shop_street", "04_casablanca_night",
                 "02_keyhole", "09_police_tape"]),
    # ── الشاهد + البحث 23 يوم
    (714, 790,  ["18_shop_street", "08_crowd", "04_casablanca_night", "05_case_file"]),
    # ── نجية + الاستجواب
    (790, 840,  ["19_interrogation", "05_case_file", "10_gloves", "02_keyhole"]),
    # ── الخطة
    (840, 900,  ["01_door_closed", "02_keyhole", "03_hallway", "16_gold_jewelry"]),
    # ── الربط + الحل
    (900, 960,  ["05_case_file", "09_police_tape", "10_gloves", "02_keyhole"]),
    # ── الحكم
    (960, 1010, ["19_interrogation", "05_case_file", "04_casablanca_night"]),
    # ── الخاتمة
    (1010, 1064,["01_door_closed", "04_casablanca_night", "02_keyhole", "05_case_file"]),
]

# حركات Ken Burns — (نوع, وصف)
MOVES = [
    ("zoom_in_c",    "زوم داخل، مركز"),
    ("zoom_out_c",   "زوم خارج، مركز"),
    ("pan_left",     "بان لليسار مع زوم خفيف"),
    ("pan_right",    "بان لليمين مع زوم خفيف"),
    ("pan_up",       "بان لفوق"),
    ("pan_down",     "بان لتحت"),
    ("zoom_in_tl",   "زوم داخل نحو فوق-يسار"),
    ("zoom_in_br",   "زوم داخل نحو تحت-يمين"),
    ("push_slow",    "دفع بطيء جداً"),
]

# تنويعات بصرية باش نفس الصورة ما تعاودش نفس الإحساس
LOOKS = [
    "eq=contrast=1.06:saturation=0.92:gamma=0.98",
    "eq=contrast=1.12:saturation=0.80:gamma=0.95",
    "eq=contrast=1.02:saturation=1.05:gamma=1.02",
    "eq=contrast=1.15:saturation=0.70:gamma=0.92,colorbalance=rs=-0.04:bs=0.06",
    "eq=contrast=1.08:saturation=0.88,colorbalance=rs=0.05:bs=-0.03",
    "hue=s=0.35,eq=contrast=1.18:gamma=0.94",   # شبه أبيض وأسود
]


def zoompan_expr(move, frames):
    """كيرجع (z, x, y) ديال فلتر zoompan"""
    n = frames
    if move == "zoom_in_c":
        z = f"1.00+0.14*on/{n}"
        x, y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif move == "zoom_out_c":
        z = f"1.16-0.14*on/{n}"
        x, y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif move == "pan_left":
        z = f"1.14+0.03*on/{n}"
        x, y = f"(iw-iw/zoom)*(1-on/{n})", "ih/2-(ih/zoom/2)"
    elif move == "pan_right":
        z = f"1.14+0.03*on/{n}"
        x, y = f"(iw-iw/zoom)*(on/{n})", "ih/2-(ih/zoom/2)"
    elif move == "pan_up":
        z = f"1.15+0.03*on/{n}"
        x, y = "iw/2-(iw/zoom/2)", f"(ih-ih/zoom)*(1-on/{n})"
    elif move == "pan_down":
        z = f"1.15+0.03*on/{n}"
        x, y = "iw/2-(iw/zoom/2)", f"(ih-ih/zoom)*(on/{n})"
    elif move == "zoom_in_tl":
        z = f"1.00+0.16*on/{n}"
        x, y = f"(iw-iw/zoom)*0.18", f"(ih-ih/zoom)*0.18"
    elif move == "zoom_in_br":
        z = f"1.00+0.16*on/{n}"
        x, y = f"(iw-iw/zoom)*0.82", f"(ih-ih/zoom)*0.82"
    else:  # push_slow
        z = f"1.02+0.07*on/{n}"
        x, y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    return z, x, y


def build_shot_list():
    """كيبني لائحة اللقطات: (صورة, مدة, حركة, لوك)"""
    shots = []
    rng = random.Random(20260814)
    last_img = None
    move_pool = []
    for (t0, t1, imgs) in TIMELINE:
        span = t1 - t0
        n = max(1, round(span / SHOT))
        dur = span / n
        # ندورو على الصور بلا ما نعاودو نفس وحدة مرتين وراء بعضهم
        seq = []
        pool = list(imgs)
        for i in range(n):
            cand = [c for c in pool if c != last_img] or pool
            pick = cand[i % len(cand)]
            seq.append(pick)
            last_img = pick
        for img in seq:
            if not move_pool:
                move_pool = MOVES[:]
                rng.shuffle(move_pool)
            move = move_pool.pop()[0]
            look = LOOKS[rng.randrange(len(LOOKS))]
            shots.append({"img": img, "dur": round(dur, 3),
                          "move": move, "look": look})
    return shots


def ensure_images(shots):
    """كيتحقق من وجود الصور، وإلا كيعوض بأقرب موجودة"""
    have = {os.path.splitext(f)[0] for f in os.listdir(IMG) if f.endswith(".png")}
    missing = sorted({s["img"] for s in shots} - have)
    if missing:
        print(f"  ⚠ ناقصين {len(missing)} صورة: {', '.join(missing)}")
        fallback = sorted(have)
        for i, s in enumerate(shots):
            if s["img"] not in have:
                s["img"] = fallback[i % len(fallback)]
    return shots


def render_shot(i, s):
    """كيرندري لقطة وحدة لملف mp4"""
    out = f"{WORK}/shot_{i:04d}.mp4"
    if os.path.exists(out):
        return out
    frames = max(2, int(round(s["dur"] * FPS)))
    z, x, y = zoompan_expr(s["move"], frames)
    src = f"{IMG}/{s['img']}.png"

    fd = 0.45
    fo = max(0.0, s["dur"] - fd)
    vf = (
        # كنكبر الصورة قبل الزوم باش الحركة تكون ناعمة
        f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,"
        f"crop={W*2}:{H*2},"
        f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={W}x{H}:fps={FPS},"
        f"{s['look']},"
        f"vignette=PI/4.2,"
        f"noise=alls=6:allf=t+u,"
        f"fade=t=in:st=0:d={fd},fade=t=out:st={fo:.3f}:d={fd},"
        f"format=yuv420p"
    )
    subprocess.run([
        FF, "-v", "error", "-y", "-loop", "1", "-i", src,
        "-t", f"{s['dur']:.3f}", "-vf", vf, "-r", str(FPS),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", out
    ], check=True)
    return out


def concat_fast(files):
    """لصق بلا إعادة ترميز — concat demuxer"""
    lst = f"{WORK}/list.txt"
    with open(lst, "w") as f:
        for c in files:
            f.write(f"file '{c}'\n")
    out = f"{WORK}/merged.mp4"
    subprocess.run([FF, "-v", "error", "-y", "-f", "concat", "-safe", "0",
                    "-i", lst, "-c", "copy", out], check=True)
    return out


_dur_cache = {}
def probe_dur(path):
    if path in _dur_cache:
        return _dur_cache[path]
    r = subprocess.run([FF, "-hide_banner", "-i", path],
                       capture_output=True, text=True).stderr
    for line in r.split("\n"):
        if "Duration:" in line:
            t = line.split("Duration:")[1].split(",")[0].strip()
            hh, mm, ss = t.split(":")
            d = int(hh)*3600 + int(mm)*60 + float(ss)
            _dur_cache[path] = d
            return d
    raise RuntimeError("no duration " + path)


if __name__ == "__main__":
    print("🎬 كنبني الفيديو…")
    shots = ensure_images(build_shot_list())
    total = sum(s["dur"] for s in shots)
    print(f"  لقطات: {len(shots)}  ·  مجموع: {total/60:.1f} دقيقة")
    json.dump(shots, open(f"{WORK}/shots.json", "w"), ensure_ascii=False, indent=1)

    print("  كنرندري اللقطات…")
    files = []
    for i, s in enumerate(shots):
        files.append(render_shot(i, s))
        if (i+1) % 20 == 0:
            print(f"    {i+1}/{len(shots)}")
    print(f"    {len(shots)}/{len(shots)} ✓")

    print("  كنلصق…")
    merged = concat_fast(files)

    print("  كنضيف الصوت…")
    out = f"{ROOT}/output/EPISODE_VIDEO.mp4"
    subprocess.run([
        FF, "-v", "error", "-y", "-i", merged, "-i", AUDIO,
        "-map", "0:v", "-map", "1:a",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "160k",
        "-shortest", "-movflags", "+faststart", out
    ], check=True)
    print(f"✅ سالا: {out}")
