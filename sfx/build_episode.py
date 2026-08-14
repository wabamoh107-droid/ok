#!/usr/bin/env python3
"""بناء الحلقة الكاملة: 10 مقاطع صوتية + مؤثرات."""
import numpy as np, os, sys, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mix_demo import load, write_mp3, Mixer, duck, SR, ROOT, SFX

S = lambda n: load(f"{SFX}/{n}")

print("🎬 كنبني الحلقة الكاملة…")

# ── تحميل المقاطع
parts = []
for f in sorted(glob.glob(f"{ROOT}/build/vo/*.mp3")):
    parts.append(load(f))
print(f"  مقاطع: {len(parts)}")

# ── سكوت بين المقاطع (بحال وقفة مشهد)
GAP = 1.1
INTRO = 3.6          # جو قبل ما يبدا الراوي
OUTRO = 6.0

starts, cur = [], INTRO
for p in parts:
    starts.append(cur)
    cur += len(p)/SR + GAP
total = cur + OUTRO
print(f"  المدة الكاملة: {total/60:.1f} دقيقة")

def at(i, off=0.0):
    """توقيت نسبي داخل مقطع i (0-indexed)"""
    return starts[i] + off

def end(i, off=0.0):
    return starts[i] + len(parts[i])/SR + off

mx = Mixer(total)

# ═══════════════════════════════════════════
#  الطبقات الجوية — طول الحلقة
# ═══════════════════════════════════════════
mx.add(S("05_tension_drone.flac"), 0.0, gain=0.22, loop_to=total,
       fade_in=2.5, fade_out=5.0)
mx.add(S("24_wind.flac"), 0.0, gain=0.075, loop_to=total,
       fade_in=4.0, fade_out=4.0)

# شتا فالثلث الأول (جو ليلي)
mx.add(S("22_rain.flac"), 0.0, gain=0.085, loop_to=end(1),
       fade_in=3.0, fade_out=8.0)
# ورجعة ديال الشتا فمشهد الفيلا
mx.add(S("22_rain.flac"), at(4)+8, gain=0.07, loop_to=60,
       fade_in=5.0, fade_out=8.0)

# ═══════════════════════════════════════════
#  مقطع 1 — الهوك + المقدمة
# ═══════════════════════════════════════════
mx.add(S("03_footsteps.flac"), 0.2,  gain=0.30, fade_in=0.4)   # خطوات كتقرب
mx.add(S("09_door_open.flac"), 2.0,  gain=0.30)                # الباب كيتحل
mx.add(S("02_door_knock.flac"), at(0, 3.0),  gain=0.22)        # "الباب مسدود"
mx.add(S("25_heartbeat.flac"), at(0, 8.0), gain=0.16,
       loop_to=12, fade_in=2.0, fade_out=3.0)                 # "لقاو جوج ضحايا"
mx.add(S("29_whoosh_down.flac"), at(0, 14.0), gain=0.20)
mx.add(S("28_sub_drop.flac"),   at(0, 27.0), gain=0.26)        # "جريمة ثانية"
mx.add(S("06_impact.flac"),     at(0, 40.0), gain=0.30)        # "ما كانش محتاج يكسر الباب"
mx.add(S("07_whoosh.flac"),     at(0, 44.5), gain=0.22)        # دخول المقدمة

# ═══════════════════════════════════════════
#  انتقال 1→2
# ═══════════════════════════════════════════
mx.add(S("28_sub_drop.flac"), end(0)-0.2, gain=0.24)

# ═══════════════════════════════════════════
#  مقطع 2 — البلاغ والوصول
# ═══════════════════════════════════════════
mx.add(S("01_phone_ring.flac"), at(1, 3.0),  gain=0.34)        # الرقم 19
mx.add(S("20_radio_chatter.flac"), at(1, 7.0), gain=0.10,
       fade_in=1.5, fade_out=2.0)
mx.add(S("17_car_door.flac"),   at(1, 10.0), gain=0.26)
mx.add(S("16_car_engine.flac"), at(1, 10.3), gain=0.17, fade_out=2.5)
mx.add(S("10_police_siren.flac"),at(1, 10.8), gain=0.26, fade_out=2.0)
mx.add(S("04_crowd.flac"),      at(1, 15.0), gain=0.15,
       loop_to=16, fade_in=2.5, fade_out=4.0)                 # المتجمهرين
mx.add(S("03_footsteps.flac"),  at(1, 19.0), gain=0.20)
mx.add(S("09_door_open.flac"),  at(1, 21.5), gain=0.24)
mx.add(S("06_impact.flac"),     at(1, 24.0), gain=0.28)        # "تجمد فبلاصتو"
mx.add(S("25_heartbeat.flac"),  at(1, 25.0), gain=0.18,
       loop_to=10, fade_in=1.5, fade_out=3.0)
mx.add(S("14_camera_shutter.flac"), at(1, 37.0), gain=0.17)    # الشرطة العلمية
mx.add(S("21_evidence_bag.flac"),   at(1, 42.0), gain=0.14)
mx.add(S("14_camera_shutter.flac"), at(1, 50.0), gain=0.14)
mx.add(S("07_whoosh.flac"), end(1)-1.6, gain=0.24)             # "غادي تبدا المفاجأة"

# ═══════════════════════════════════════════
#  مقطع 3 — البحث بلا نتيجة
# ═══════════════════════════════════════════
mx.add(S("26_ticking_pressure.flac"), at(2, 8.0), gain=0.13,
       loop_to=14, fade_in=2.0, fade_out=2.5)
mx.add(S("29_whoosh_down.flac"), at(2, 22.0), gain=0.22)       # "والو"
mx.add(S("13_paper_single.flac"), at(2, 30.0), gain=0.18)
mx.add(S("06_impact.flac"),  at(2, 36.0), gain=0.24)           # الماريو مقلوب
mx.add(S("27_stinger_reveal.flac"), end(2)-8.0, gain=0.24)     # "هما اللي فتحو الباب"

# ═══════════════════════════════════════════
#  مقطع 4 — التحقيق والانتظار
# ═══════════════════════════════════════════
mx.add(S("15_keyboard.flac"), at(3, 2.0), gain=0.12, fade_out=2.0)
mx.add(S("12_paper_turn.flac"), at(3, 8.0), gain=0.18)
mx.add(S("04_crowd.flac"), at(3, 12.0), gain=0.10,
       loop_to=8, fade_in=2.0, fade_out=3.0)                  # الجيران خرجو
mx.add(S("20_radio_chatter.flac"), at(3, 33.0), gain=0.09,
       fade_in=1.5, fade_out=2.0)
mx.add(S("30_clock_wall.flac"), end(3)-14.0, gain=0.17,
       loop_to=13, fade_in=2.0, fade_out=2.0)                 # 44 يوم
mx.add(S("13_paper_single.flac"), end(3)-1.4, gain=0.22)       # التقرير خرج

# ═══════════════════════════════════════════
#  مقطع 5 — القضية الثانية
# ═══════════════════════════════════════════
mx.add(S("27_stinger_reveal.flac"), at(4, 5.0), gain=0.26)     # "ما كانش شخص واحد"
mx.add(S("28_sub_drop.flac"), at(4, 9.0), gain=0.26)           # 7 شهور من بعد
mx.add(S("01_phone_ring.flac"), at(4, 12.0), gain=0.28)        # بلاغ جديد
mx.add(S("10_police_siren.flac"), at(4, 18.0), gain=0.20, fade_out=2.0)
mx.add(S("17_car_door.flac"), at(4, 21.0), gain=0.20)
mx.add(S("06_impact.flac"), at(4, 33.0), gain=0.26)            # الماريو مقلوب (تاني)
mx.add(S("07_whoosh.flac"), at(4, 38.0), gain=0.22)            # "غادي يكون عندهم خيط"
mx.add(S("01_phone_ring.flac"), end(4)-16.0, gain=0.26)        # ما جاوباتش
mx.add(S("30_clock_wall.flac"), end(4)-12.0, gain=0.15,
       loop_to=8, fade_in=1.5, fade_out=2.0)
mx.add(S("02_door_knock.flac"), end(4)-6.0, gain=0.26)         # دقات / صونات
mx.add(S("25_heartbeat.flac"), end(4)-4.0, gain=0.18,
       loop_to=6, fade_in=1.0, fade_out=2.0)

# ═══════════════════════════════════════════
#  مقطع 6 — الريحة والبنّاي
# ═══════════════════════════════════════════
mx.add(S("16_car_engine.flac"), at(5, 2.0), gain=0.15, fade_out=2.5)
mx.add(S("09_door_open.flac"),  at(5, 5.0), gain=0.26)
mx.add(S("06_impact.flac"),     at(5, 7.0), gain=0.26)
mx.add(S("03_footsteps.flac"),  at(5, 12.0), gain=0.18)        # كيدور فالفيلا
mx.add(S("26_ticking_pressure.flac"), at(5, 22.0), gain=0.12,
       loop_to=12, fade_in=2.0, fade_out=2.5)
mx.add(S("07_whoosh.flac"),     at(5, 34.0), gain=0.20)
mx.add(S("03_footsteps.flac"),  at(5, 38.0), gain=0.16)        # خرج للشارع
mx.add(S("14_camera_shutter.flac"), at(5, 41.0), gain=0.13)    # كاميرات المراقبة
mx.add(S("29_whoosh_down.flac"), at(5, 45.0), gain=0.20)       # "ما كايناش"
mx.add(S("27_stinger_reveal.flac"), end(5)-9.0, gain=0.22)     # الشاهد

# ═══════════════════════════════════════════
#  مقطع 7 — البحث 23 يوم + نجية
# ═══════════════════════════════════════════
mx.add(S("30_clock_wall.flac"), at(6, 14.0), gain=0.16,
       loop_to=10, fade_in=2.0, fade_out=2.0)
mx.add(S("26_ticking_pressure.flac"), at(6, 22.0), gain=0.14,
       loop_to=8, fade_in=1.5, fade_out=2.0)
mx.add(S("06_impact.flac"),  at(6, 27.0), gain=0.26)           # اليوم 24
mx.add(S("16_car_engine.flac"), at(6, 33.0), gain=0.12, fade_out=2.0)
mx.add(S("12_paper_turn.flac"), at(6, 42.0), gain=0.16)        # السوابق
mx.add(S("15_keyboard.flac"), at(6, 48.0), gain=0.11, fade_out=2.0)
mx.add(S("25_heartbeat.flac"), end(6)-12.0, gain=0.19,
       loop_to=11, fade_in=2.0, fade_out=2.0)                 # الاستجواب
mx.add(S("27_stinger_reveal.flac"), end(6)-1.8, gain=0.34)     # "نجية اعترفات"

# ═══════════════════════════════════════════
#  مقطع 8 — الخطة
# ═══════════════════════════════════════════
mx.add(S("28_sub_drop.flac"), at(7, 0.3), gain=0.24)
mx.add(S("26_ticking_pressure.flac"), at(7, 10.0), gain=0.12,
       loop_to=16, fade_in=2.0, fade_out=3.0)
mx.add(S("02_door_knock.flac"), at(7, 30.0), gain=0.24)        # "كتفتح ليها الباب"
mx.add(S("09_door_open.flac"),  at(7, 33.0), gain=0.26)
mx.add(S("06_impact.flac"),     at(7, 36.0), gain=0.26)        # الزوج كيدخل
mx.add(S("25_heartbeat.flac"),  at(7, 37.0), gain=0.20,
       loop_to=9, fade_in=1.0, fade_out=2.5)
mx.add(S("07_whoosh.flac"),     end(7)-8.0, gain=0.22)
mx.add(S("27_stinger_reveal.flac"), end(7)-5.5, gain=0.34)     # الربط بالقضية الأولى

# ═══════════════════════════════════════════
#  مقطع 9 — الحل والحكم
# ═══════════════════════════════════════════
mx.add(S("13_paper_single.flac"), at(8, 1.0), gain=0.16)
mx.add(S("29_whoosh_down.flac"),  at(8, 14.0), gain=0.22)      # "الثقة"
mx.add(S("06_impact.flac"),       at(8, 15.0), gain=0.30)
mx.add(S("18_handcuffs.flac"),    at(8, 22.0), gain=0.28)      # الاعتقال
mx.add(S("16_car_engine.flac"),   at(8, 24.0), gain=0.12, fade_out=2.0)
mx.add(S("28_sub_drop.flac"),     at(8, 28.0), gain=0.26)      # الحكم
mx.add(S("19_cell_door.flac"),    at(8, 29.5), gain=0.34)

# ═══════════════════════════════════════════
#  مقطع 10 — الخاتمة
# ═══════════════════════════════════════════
mx.add(S("07_whoosh.flac"), at(9)-0.8, gain=0.18)
mx.add(S("30_clock_wall.flac"), at(9, 4.0), gain=0.11,
       loop_to=14, fade_in=2.5, fade_out=4.0)
mx.add(S("27_stinger_reveal.flac"), at(9, 8.0), gain=0.24)     # "كانت… الثقة"
mx.add(S("09_door_open.flac"), at(9, 14.0), gain=0.20)         # الضحية فتحات الباب
mx.add(S("06_impact.flac"), at(9, 20.0), gain=0.22)            # السؤال

# ═══════════════════════════════════════════
#  المزج النهائي
# ═══════════════════════════════════════════
bed = mx.out()
vfull = np.zeros(len(bed))
for p, s in zip(parts, starts):
    i = int(SR*s)
    vfull[i:i+len(p)] += p

bed_only = bed - vfull
print("  كندير ducking…")
bed_only = duck(bed_only, vfull, thresh=0.015, depth=0.47, release=0.55)

final = vfull + bed_only

# fade in/out نهائي
fi = int(SR*2.0); fo = int(SR*4.0)
final[:fi] *= np.linspace(0, 1, fi)
final[-fo:] *= np.linspace(1, 0, fo)

final = np.tanh(final*1.12)*0.93

out = f"{ROOT}/output/الحلقة_ملف_الثقة_المكسورة.mp3"
os.makedirs(os.path.dirname(out), exist_ok=True)
write_mp3(out, final)

# نسخة صوت نقي بلا مؤثرات
vo_fi = vfull.copy()
vo_fi = np.tanh(vo_fi*1.05)*0.95
write_mp3(f"{ROOT}/output/الحلقة_صوت_فقط.mp3", vo_fi)

print(f"✅ سالا — {total/60:.1f} دقيقة")
