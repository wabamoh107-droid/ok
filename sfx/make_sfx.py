#!/usr/bin/env python3
"""مولّد مؤثرات صوتية للتعليق الصوتي — بلا ملفات خارجية، كلشي مولّد رقمياً."""
import numpy as np, wave, os, struct

SR = 44100
OUT = os.path.join(os.path.dirname(__file__))
rng = np.random.default_rng(7)


def save(name, x, gain=1.0):
    x = np.asarray(x, dtype=np.float64) * gain
    m = np.max(np.abs(x)) or 1.0
    x = x / m * 0.85
    # fade in/out قصير باش نتفاداو الطقطقة
    n = min(int(0.008 * SR), len(x) // 2)
    if n > 0:
        x[:n] *= np.linspace(0, 1, n)
        x[-n:] *= np.linspace(1, 0, n)
    d = (x * 32767).astype(np.int16)
    p = os.path.join(OUT, name)
    with wave.open(p, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(d.tobytes())
    print(f"  ✓ {name}  ({len(x)/SR:.2f}s)")


def t(dur):
    return np.linspace(0, dur, int(SR * dur), endpoint=False)


def env(x, a=0.005, d=0.1, s=0.6, r=0.2):
    """ADSR بسيط"""
    n = len(x); e = np.ones(n)
    na, nd, nr = int(a*SR), int(d*SR), int(r*SR)
    na, nd, nr = min(na, n), min(nd, n), min(nr, n)
    e[:na] = np.linspace(0, 1, na)
    e[na:na+nd] = np.linspace(1, s, nd)[:max(0, n-na)]
    e[na+nd:n-nr] = s
    if nr: e[n-nr:] = np.linspace(e[n-nr-1] if n-nr-1 >= 0 else s, 0, nr)
    return x * e


def lowpass(x, cutoff, order=2):
    """فلتر تمرير منخفض بسيط (one-pole متكرر)"""
    a = np.exp(-2*np.pi*cutoff/SR)
    y = x.copy()
    for _ in range(order):
        out = np.empty_like(y); acc = 0.0
        for i in range(len(y)):
            acc = (1-a)*y[i] + a*acc
            out[i] = acc
        y = out
    return y


def lowpass_fft(x, cutoff, slope=2.0):
    """فلتر سريع بالـ FFT"""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1/SR)
    H = 1.0 / (1.0 + (f / max(cutoff, 1.0))**(2*slope))
    return np.fft.irfft(X * H, n=len(x))


def highpass_fft(x, cutoff, slope=2.0):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1/SR)
    H = 1.0 - 1.0/(1.0 + (f/max(cutoff, 1.0))**(2*slope))
    return np.fft.irfft(X * H, n=len(x))


def bandpass_fft(x, lo, hi):
    return highpass_fft(lowpass_fft(x, hi), lo)


def reverb(x, decay=0.35, mix=0.25, taps=18, spread=0.045):
    """ريفيرب بسيط بتأخيرات متعددة"""
    y = np.zeros(len(x) + int(SR*spread*taps))
    y[:len(x)] += x
    for i in range(1, taps):
        d = int(SR * spread * i * (0.7 + 0.6*rng.random()))
        g = (decay ** i) * mix
        if d < len(y) and g > 0.001:
            end = min(len(y), d + len(x))
            y[d:end] += x[:end-d] * g
    return y


# ═══════════════════════════════════════════════════════
# 1) رنة الهاتف — هاتف أرضي قديم (مخفر الشرطة)
# ═══════════════════════════════════════════════════════
def phone_ring(rings=3):
    """رنة مزدوجة على الطريقة الكلاسيكية: 0.4s رنين / 0.2s سكوت / تكرار"""
    out = []
    for r in range(rings):
        for burst in range(2):
            d = t(0.40)
            # نغمتين متداخلتين + تردد تعديل خفيف
            tone = (np.sin(2*np.pi*440*d) + 0.7*np.sin(2*np.pi*480*d))
            trem = 0.5 + 0.5*np.sin(2*np.pi*20*d)   # اهتزاز الجرس
            sig = tone * trem
            sig = env(sig, a=0.01, d=0.03, s=0.9, r=0.05)
            sig = bandpass_fft(sig, 300, 3000)
            out.append(sig)
            out.append(np.zeros(int(SR*0.20)))
        out.append(np.zeros(int(SR*1.6)))   # سكوت بين الرنات
    x = np.concatenate(out)
    return reverb(x, decay=0.3, mix=0.18)


# ═══════════════════════════════════════════════════════
# 2) دق الباب — 3 دقات على باب خشبي
# ═══════════════════════════════════════════════════════
def door_knock(knocks=3):
    out = []
    for i in range(knocks):
        d = t(0.28)
        # ضربة: نويز + رنين خشبي منخفض
        noise = rng.normal(0, 1, len(d))
        thump = np.sin(2*np.pi*95*d) + 0.6*np.sin(2*np.pi*150*d) + 0.3*np.sin(2*np.pi*220*d)
        sig = 0.55*thump + 0.45*noise
        e = np.exp(-d*26)
        sig = sig * e
        sig = lowpass_fft(sig, 1400)
        out.append(sig)
        out.append(np.zeros(int(SR*(0.26 + 0.05*rng.random()))))
    x = np.concatenate(out)
    return reverb(x, decay=0.4, mix=0.30, spread=0.03)


# ═══════════════════════════════════════════════════════
# 3) خطوات المفتش — حذاء على أرضية صلبة
# ═══════════════════════════════════════════════════════
def footsteps(steps=8, pace=0.55, hard=True):
    out = []
    for i in range(steps):
        d = t(0.13)
        noise = rng.normal(0, 1, len(d))
        # الكعب: نقرة حادة، من بعد جسم منخفض
        click = noise * np.exp(-d*160)
        body = (np.sin(2*np.pi*110*d) + 0.5*np.sin(2*np.pi*170*d)) * np.exp(-d*40)
        sig = 0.65*click + 0.45*body
        sig = bandpass_fft(sig, 120, 5200 if hard else 2200)
        sig *= 0.75 + 0.5*rng.random()      # تنويع القوة
        out.append(sig)
        gap = pace * (0.88 + 0.24*rng.random()) - 0.13
        out.append(np.zeros(max(1, int(SR*gap))))
    x = np.concatenate(out)
    return reverb(x, decay=0.45, mix=0.35, spread=0.05)


# ═══════════════════════════════════════════════════════
# 4) صوت المتجمهرين — حشد ديال الناس، همهمة
# ═══════════════════════════════════════════════════════
def crowd(dur=8.0, density=26):
    n = int(SR*dur)
    base = rng.normal(0, 1, n)
    base = bandpass_fft(base, 180, 1100)
    # تموّج بطيء = موجات ديال الهمهمة
    slow = np.zeros(n)
    for f, a in [(0.13, 1.0), (0.31, 0.6), (0.07, 0.8), (0.52, 0.35)]:
        slow += a*np.sin(2*np.pi*f*np.arange(n)/SR + rng.random()*6.28)
    slow = 0.55 + 0.45*(slow/np.max(np.abs(slow)))
    bed = base * slow * 0.5

    # أصوات فردية متفرقة (بحال شي واحد كيهضر قريب)
    for _ in range(density):
        st = int(rng.random()*(n - SR))
        ln = int(SR*(0.25 + 0.7*rng.random()))
        d = np.arange(ln)/SR
        f0 = 95 + rng.random()*130
        # تشكيل شبه صوتي
        v = np.zeros(ln)
        for h in range(1, 7):
            v += (1.0/h)*np.sin(2*np.pi*f0*h*d + rng.random()*6.28)
        wob = 1 + 0.06*np.sin(2*np.pi*(3+4*rng.random())*d)
        v *= wob
        v *= np.hanning(ln)
        v = bandpass_fft(v, 200, 1600)
        amp = 0.10 + 0.16*rng.random()
        bed[st:st+ln] += v*amp
    return reverb(bed, decay=0.5, mix=0.28, spread=0.06)


# ═══════════════════════════════════════════════════════
# 5) طبقة توتر — درون منخفض للخلفية
# ═══════════════════════════════════════════════════════
def tension_drone(dur=12.0, root=52.0):
    d = t(dur)
    x = np.zeros(len(d))
    for f, a in [(root, 1.0), (root*1.5, 0.35), (root*2, 0.25),
                 (root*2.997, 0.14), (root*4, 0.08)]:
        det = 1 + 0.0016*np.sin(2*np.pi*0.08*d + rng.random()*6.28)
        x += a*np.sin(2*np.pi*f*det*d)
    # نويز خفيف بحال هواء
    air = lowpass_fft(rng.normal(0, 1, len(d)), 400) * 0.12
    x = x*0.5 + air
    # تنفّس بطيء
    x *= 0.62 + 0.38*np.sin(2*np.pi*0.055*d - np.pi/2)
    fade = int(SR*1.5)
    x[:fade] *= np.linspace(0, 1, fade)
    x[-fade:] *= np.linspace(1, 0, fade)
    return x


# ═══════════════════════════════════════════════════════
# 6) ضربة صدمة — impact للانتقالات
# ═══════════════════════════════════════════════════════
def impact(dur=2.6):
    d = t(dur)
    sweep = np.sin(2*np.pi*np.cumsum(np.linspace(140, 34, len(d)))/SR)
    sub = np.sin(2*np.pi*41*d)
    noise = lowpass_fft(rng.normal(0, 1, len(d)), 900)
    x = 0.55*sweep + 0.30*sub + 0.30*noise
    x *= np.exp(-d*2.4)
    return reverb(x, decay=0.5, mix=0.30, spread=0.07)


# ═══════════════════════════════════════════════════════
# 7) ووش انتقالي — riser/whoosh
# ═══════════════════════════════════════════════════════
def whoosh(dur=1.9, rise=True):
    d = t(dur)
    noise = rng.normal(0, 1, len(d))
    x = np.zeros(len(d))
    step = 2048
    for i in range(0, len(d), step):
        seg = noise[i:i+step]
        if len(seg) < 8: break
        p = i/len(d)
        c = 350 + 5200*(p if rise else (1-p))**1.6
        x[i:i+len(seg)] = bandpass_fft(seg, max(120, c*0.35), c)
    shape = (d/dur)**1.7 if rise else np.exp(-d*2.6)
    x *= shape
    return reverb(x, decay=0.35, mix=0.22)


# ═══════════════════════════════════════════════════════
# 8) تكتكة ساعة — للحظات الانتظار
# ═══════════════════════════════════════════════════════
def clock_tick(dur=8.0):
    n = int(SR*dur); x = np.zeros(n)
    i = 0; k = 0
    while i < n - SR//4:
        ln = int(SR*0.05); d = t(0.05)
        cl = rng.normal(0, 1, ln)*np.exp(-d*220)
        cl = bandpass_fft(cl, 1800, 7000)
        cl *= 1.0 if k % 2 == 0 else 0.72
        x[i:i+ln] += cl
        i += int(SR*0.5); k += 1
    return reverb(x, decay=0.3, mix=0.2)


# ═══════════════════════════════════════════════════════
# 9) باب كيتحل — صرير + قفل
# ═══════════════════════════════════════════════════════
def door_open():
    # كليك ديال القفل
    ln = int(SR*0.09); d = t(0.09)
    click = rng.normal(0, 1, ln)*np.exp(-d*130)
    click = bandpass_fft(click, 900, 6500)
    gap = np.zeros(int(SR*0.18))
    # صرير
    ln2 = int(SR*1.35); d2 = t(1.35)
    f = 320 + 180*np.sin(2*np.pi*0.8*d2) + 90*np.sin(2*np.pi*2.3*d2)
    cre = np.sin(2*np.pi*np.cumsum(f)/SR)
    cre *= (0.35 + 0.65*np.abs(np.sin(2*np.pi*3.1*d2)))
    cre *= np.hanning(ln2)**0.6
    cre = bandpass_fft(cre, 250, 3200)*0.5
    # سدّان خفيف
    ln3 = int(SR*0.4); d3 = t(0.4)
    thud = (np.sin(2*np.pi*80*d3)+0.5*np.sin(2*np.pi*120*d3))*np.exp(-d3*15)
    thud = lowpass_fft(thud, 700)*0.8
    x = np.concatenate([click, gap, cre, thud])
    return reverb(x, decay=0.4, mix=0.28)


if __name__ == "__main__":
    print("🎚️  كنولّد المؤثرات الصوتية…")
    save("01_phone_ring.wav",   phone_ring(3))
    save("02_door_knock.wav",   door_knock(3))
    save("03_footsteps.wav",    footsteps(9, 0.58))
    save("04_crowd.wav",        crowd(9.0))
    save("05_tension_drone.wav", tension_drone(14.0))
    save("06_impact.wav",       impact())
    save("07_whoosh.wav",       whoosh())
    save("08_clock_tick.wav",   clock_tick(8.0))
    save("09_door_open.wav",    door_open())
    print("✅ سالا.")
