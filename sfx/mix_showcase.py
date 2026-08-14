#!/usr/bin/env python3
"""ديمو موسّع — كيبين المؤثرات الجداد فسياق السرد."""
import numpy as np, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mix_demo import load, write_mp3, Mixer, duck, SR, ROOT, SFX

S = lambda n: load(f"{SFX}/{n}")

print("🎛️  كنمزج الديمو الموسّع…")

v1 = load(f"{ROOT}/build/vo_part1.mp3")
v2 = load(f"{ROOT}/build/vo_part2.mp3")
v3 = load(f"{ROOT}/build/vo_part3.mp3")
d1, d2, d3 = len(v1)/SR, len(v2)/SR, len(v3)/SR
print(f"  مقاطع: {d1:.1f}s / {d2:.1f}s / {d3:.1f}s")

# ── خريطة الزمن
t_intro  = 3.0                       # جو + رنة الهاتف
t_v1     = t_intro
t_gap1   = t_v1 + d1 + 0.4           # صفارة + سيارة + باب
t_v2     = t_gap1 + 5.0
t_gap2   = t_v2 + d2 + 0.3           # كاميرا + كيس الأدلة
t_v3     = t_gap2 + 4.2
t_end    = t_v3 + d3 + 4.5
total    = t_end

mx = Mixer(total)

# ═══ الطبقات الجوية (طول الحلقة) ═══
mx.add(S("05_tension_drone.flac"), 0.0, gain=0.26, loop_to=total,
       fade_in=2.0, fade_out=3.5)
mx.add(S("24_wind.flac"), 0.0, gain=0.10, loop_to=total,
       fade_in=3.0, fade_out=3.0)
mx.add(S("22_rain.flac"), 0.0, gain=0.09, loop_to=total*0.55,
       fade_in=2.5, fade_out=5.0)

# ═══ مشهد 1: البلاغ ═══
mx.add(S("01_phone_ring.flac"), 0.3, gain=0.42)      # الهاتف كيرن فالمخفر
mx.add(v1, t_v1, gain=1.0)
# لاسلكي خفيف تحت الكلام
mx.add(S("20_radio_chatter.flac"), t_v1 + 2.5, gain=0.11, fade_in=1.0, fade_out=1.5)
# الحشد كيبان عند "لقاو الناس مجموعين"
mx.add(S("04_crowd.flac"), t_v1 + d1 - 5.0, gain=0.15,
       loop_to=9.0, fade_in=2.5, fade_out=3.0)

# ═══ انتقال: التحرك لمكان الحادث ═══
mx.add(S("28_sub_drop.flac"),    t_gap1 - 0.3, gain=0.30)
mx.add(S("17_car_door.flac"),    t_gap1 + 0.2, gain=0.34)
mx.add(S("16_car_engine.flac"),  t_gap1 + 0.5, gain=0.20, fade_out=2.0)
mx.add(S("10_police_siren.flac"),t_gap1 + 0.8, gain=0.30, fade_out=1.5)
mx.add(S("11_siren_yelp.flac"),  t_gap1 + 2.2, gain=0.16)
mx.add(S("03_footsteps.flac"),   t_gap1 + 3.4, gain=0.28)
mx.add(S("09_door_open.flac"),   t_gap1 + 4.4, gain=0.30)

# ═══ مشهد 2: الشرطة العلمية ═══
mx.add(v2, t_v2, gain=1.0)
mx.add(S("14_camera_shutter.flac"), t_v2 + 1.2, gain=0.20)
mx.add(S("21_evidence_bag.flac"),   t_v2 + 4.5, gain=0.16)
mx.add(S("14_camera_shutter.flac"), t_v2 + 7.0, gain=0.15)
mx.add(S("25_heartbeat.flac"),      t_v2 + d2 - 6.0, gain=0.22,
       loop_to=7.0, fade_in=2.0, fade_out=2.0)
# "والو" → فراغ
mx.add(S("29_whoosh_down.flac"),    t_v2 + d2 - 0.6, gain=0.24)

# ═══ انتقال: 44 يوم ديال الانتظار ═══
mx.add(S("30_clock_wall.flac"),  t_gap2, gain=0.20, loop_to=4.0, fade_out=1.2)
mx.add(S("15_keyboard.flac"),    t_gap2 + 0.5, gain=0.14, fade_out=1.5)
mx.add(S("12_paper_turn.flac"),  t_gap2 + 2.0, gain=0.26)

# ═══ مشهد 3: التقرير ═══
mx.add(v3, t_v3, gain=1.0)
mx.add(S("13_paper_single.flac"), t_v3 + 1.0, gain=0.22)
mx.add(S("26_ticking_pressure.flac"), t_v3 + 3.0, gain=0.15,
       loop_to=d3 - 3.0, fade_in=1.5, fade_out=2.0)
# الكشف: "يمكن ما كانش شخص واحد"
mx.add(S("07_whoosh.flac"),        t_v3 + d3 - 2.4, gain=0.26)
mx.add(S("27_stinger_reveal.flac"),t_v3 + d3 - 0.5, gain=0.40)

# ═══ الخاتمة ═══
mx.add(S("18_handcuffs.flac"), t_v3 + d3 + 1.8, gain=0.26)
mx.add(S("19_cell_door.flac"), t_v3 + d3 + 2.6, gain=0.36)

bed = mx.out()

# ── ducking حسب الصوت
vfull = np.zeros(len(bed))
for v, at in [(v1, t_v1), (v2, t_v2), (v3, t_v3)]:
    s = int(SR*at)
    vfull[s:s+len(v)] += v

bed_only = bed - vfull
bed_only = duck(bed_only, vfull, thresh=0.015, depth=0.46, release=0.5)

final = vfull + bed_only
final = np.tanh(final*1.12)*0.93

write_mp3(f"{ROOT}/samples/demo_full_SFX.mp3", final)
print("✅ سالا.")
