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


# ═══════════════════════════════════════════════════════
#  المجموعة الثانية — مؤثرات إضافية
# ═══════════════════════════════════════════════════════

def police_siren(dur=9.0, kind="wail"):
    """صفارة سيارة الشرطة — wail (متموجة) / yelp (سريعة)"""
    d = t(dur)
    if kind == "wail":
        rate, lo, hi = 0.55, 620, 1250
        m = np.sin(2*np.pi*rate*d)
    else:
        rate, lo, hi = 3.4, 700, 1500
        m = 2*np.abs(((d*rate) % 1.0) - 0.5)*2 - 1
    f = lo + (hi-lo)*(0.5+0.5*m)
    ph = 2*np.pi*np.cumsum(f)/SR
    sig = np.sin(ph) + 0.45*np.sin(2*ph) + 0.2*np.sin(3*ph)
    sig = bandpass_fft(sig, 400, 5200)
    # دوبلر/بعد: كتقرب من بعد كتبعد
    prox = np.exp(-((d - dur*0.5)/(dur*0.30))**2)
    sig *= 0.25 + 0.75*prox
    # طنين محرك خفيف تحت
    eng = lowpass_fft(rng.normal(0, 1, len(d)), 220)*0.35*prox
    x = sig*0.5 + eng
    return reverb(x, decay=0.45, mix=0.30, spread=0.07)


def paper_turn(pages=4):
    """قلبان ديال الورق — ملفات التحقيق"""
    out = []
    for i in range(pages):
        ln = int(SR*(0.34 + 0.16*rng.random()))
        d = np.arange(ln)/SR
        n = rng.normal(0, 1, ln)
        # الحفيف: نويز عالي مموّج
        rustle = bandpass_fft(n, 2200, 11000)
        wob = 0.35 + 0.65*np.abs(np.sin(2*np.pi*(6+5*rng.random())*d + rng.random()*6))
        rustle *= wob
        rustle *= np.hanning(ln)**0.5
        # طقة صغيرة فالآخر (الورقة كتطيح)
        ln2 = int(SR*0.06); d2 = np.arange(ln2)/SR
        flap = bandpass_fft(rng.normal(0, 1, ln2), 900, 5000)*np.exp(-d2*70)
        seg = rustle.copy()
        seg[-ln2:] += flap*0.7
        out.append(seg*(0.7+0.5*rng.random()))
        out.append(np.zeros(int(SR*(0.35+0.45*rng.random()))))
    x = np.concatenate(out)
    return reverb(x, decay=0.25, mix=0.15)


def paper_single():
    """ورقة وحدة كتقلب"""
    return paper_turn(1)


def rain(dur=12.0, heavy=False):
    """شتا — خلفية جو"""
    n = int(SR*dur)
    base = rng.normal(0, 1, n)
    hi = bandpass_fft(base, 1200, 9000)*(0.55 if heavy else 0.38)
    lo = lowpass_fft(rng.normal(0, 1, n), 500)*(0.30 if heavy else 0.16)
    x = hi + lo
    # قطرات متفرقة
    for _ in range(int(dur*(28 if heavy else 14))):
        st = int(rng.random()*(n-SR//8))
        ln = int(SR*0.035); d = np.arange(ln)/SR
        dr = bandpass_fft(rng.normal(0, 1, ln), 2500, 9000)*np.exp(-d*160)
        x[st:st+ln] += dr*(0.15+0.25*rng.random())
    # تموّج بطيء
    sl = 0.75+0.25*np.sin(2*np.pi*0.06*np.arange(n)/SR)
    return x*sl


def camera_shutter(shots=3):
    """كاميرا الشرطة العلمية"""
    out = []
    for i in range(shots):
        ln = int(SR*0.10); d = np.arange(ln)/SR
        a = bandpass_fft(rng.normal(0, 1, ln), 1500, 9000)*np.exp(-d*140)
        b = bandpass_fft(rng.normal(0, 1, ln), 800, 4000)*np.exp(-d*90)
        clk = a*0.8 + np.roll(b, int(SR*0.022))*0.6
        # شحن الفلاش
        ln2 = int(SR*0.55); d2 = np.arange(ln2)/SR
        whine = np.sin(2*np.pi*(2600+2400*d2/0.55)*d2)*np.exp(-d2*3.2)*0.10
        out.append(clk)
        out.append(whine)
        out.append(np.zeros(int(SR*(0.5+0.4*rng.random()))))
    x = np.concatenate(out)
    return reverb(x, decay=0.35, mix=0.22)


def keyboard_typing(dur=6.0):
    """كتابة المحضر"""
    n = int(SR*dur); x = np.zeros(n)
    i = int(SR*0.1)
    while i < n - SR//5:
        ln = int(SR*0.045); d = np.arange(ln)/SR
        k = bandpass_fft(rng.normal(0, 1, ln), 1200, 7500)*np.exp(-d*190)
        th = np.sin(2*np.pi*180*d)*np.exp(-d*120)*0.4
        x[i:i+ln] += (k+th)*(0.6+0.6*rng.random())
        i += int(SR*(0.075+0.11*rng.random()))
        if rng.random() < 0.08:
            i += int(SR*(0.3+0.5*rng.random()))
    return reverb(x, decay=0.25, mix=0.16)


def car_engine(dur=8.0, start=True):
    """محرك سيارة — تشغيل ومشي"""
    d = t(dur)
    if start:
        crank = np.zeros(len(d))
        for k in range(4):
            st = int(SR*(0.12*k)); ln = int(SR*0.11)
            if st+ln < len(d):
                dd = np.arange(ln)/SR
                crank[st:st+ln] += lowpass_fft(rng.normal(0,1,ln),700)*np.exp(-dd*22)
        idle_at = 0.55
    else:
        crank = np.zeros(len(d)); idle_at = 0.0
    rpm = 26 + 6*np.sin(2*np.pi*0.35*d) + 2*rng.normal(0,1,len(d)).cumsum()/len(d)
    ph = 2*np.pi*np.cumsum(rpm)/SR
    eng = np.sin(ph)+0.6*np.sin(2*ph)+0.35*np.sin(3*ph)+0.2*np.sin(5*ph)
    eng = lowpass_fft(eng, 900)
    noise = lowpass_fft(rng.normal(0,1,len(d)), 1400)*0.30
    x = (eng*0.5+noise)
    g = np.clip((d-idle_at)/0.4, 0, 1)
    x *= g
    x += crank*0.8
    return x


def car_door():
    """باب سيارة كيتسد"""
    ln = int(SR*0.5); d = np.arange(ln)/SR
    thud = (np.sin(2*np.pi*72*d)+0.6*np.sin(2*np.pi*110*d)+0.3*np.sin(2*np.pi*165*d))
    thud *= np.exp(-d*17)
    clk = bandpass_fft(rng.normal(0,1,ln),1200,6000)*np.exp(-d*130)*0.5
    x = lowpass_fft(thud, 900)+clk
    return reverb(x, decay=0.35, mix=0.22)


def handcuffs():
    """قيود — لحظة الاعتقال"""
    out=[]
    for i in range(2):
        ln=int(SR*0.28); d=np.arange(ln)/SR
        rat=np.zeros(ln)
        for k in range(9):
            st=int(SR*0.012*k)
            if st+400<ln:
                dd=np.arange(400)/SR
                rat[st:st+400]+=bandpass_fft(rng.normal(0,1,400),2000,10000)*np.exp(-dd*300)
        ring=np.sin(2*np.pi*3100*d)*np.exp(-d*26)*0.25
        out.append(rat*0.9+ring)
        out.append(np.zeros(int(SR*0.35)))
    x=np.concatenate(out)
    return reverb(x, decay=0.3, mix=0.25)


def cell_door():
    """باب زنزانة معدني كيتسد — للخاتمة"""
    ln=int(SR*0.35); d=np.arange(ln)/SR
    slide=bandpass_fft(rng.normal(0,1,ln),400,3000)*(0.3+0.7*np.hanning(ln))
    ln2=int(SR*2.2); d2=np.arange(ln2)/SR
    clang=(np.sin(2*np.pi*160*d2)+0.7*np.sin(2*np.pi*247*d2)+0.5*np.sin(2*np.pi*393*d2)
           +0.3*np.sin(2*np.pi*611*d2))
    clang*=np.exp(-d2*3.0)
    boom=np.sin(2*np.pi*58*d2)*np.exp(-d2*5.5)*0.9
    x=np.concatenate([slide*0.4, clang*0.55+boom])
    return reverb(x, decay=0.55, mix=0.40, spread=0.08)


def heartbeat(beats=6, bpm=64):
    """دقات القلب — لحظات التوتر"""
    per=60.0/bpm
    out=[]
    for i in range(beats):
        seg=np.zeros(int(SR*per))
        for off,amp,dec in [(0.0,1.0,13),(0.30,0.72,17)]:
            st=int(SR*off); ln=int(SR*0.30)
            if st+ln<=len(seg):
                dd=np.arange(ln)/SR
                b=(np.sin(2*np.pi*48*dd)+0.5*np.sin(2*np.pi*74*dd))*np.exp(-dd*dec)
                seg[st:st+ln]+=lowpass_fft(b,320)*amp
        out.append(seg)
    return np.concatenate(out)


def radio_chatter(dur=7.0):
    """لاسلكي الشرطة — كلام غير مفهوم + تشويش"""
    n=int(SR*dur); x=np.zeros(n)
    i=int(SR*0.3)
    while i<n-SR:
        # بيب الفتح
        ln0=int(SR*0.06); d0=np.arange(ln0)/SR
        x[i:i+ln0]+=np.sin(2*np.pi*1500*d0)*np.exp(-d0*30)*0.35
        i+=ln0
        # كلام مشوّش
        ln=int(SR*(0.7+1.1*rng.random())); d=np.arange(ln)/SR
        f0=110+rng.random()*70
        v=np.zeros(ln)
        for h in range(1,9):
            v+=(1.0/h)*np.sin(2*np.pi*f0*h*d+rng.random()*6.28)
        mod=0.4+0.6*np.abs(np.sin(2*np.pi*(4+4*rng.random())*d))
        v*=mod
        v=bandpass_fft(v,400,2800)          # نطاق الراديو
        v+=bandpass_fft(rng.normal(0,1,ln),500,3000)*0.18
        v=np.tanh(v*2.2)*0.5                 # تشبع
        if i+ln<n: x[i:i+ln]+=v*0.55
        i+=ln
        # بيب السد + سكوت
        ln1=int(SR*0.05); d1=np.arange(ln1)/SR
        if i+ln1<n: x[i:i+ln1]+=np.sin(2*np.pi*1100*d1)*np.exp(-d1*40)*0.3
        i+=ln1+int(SR*(0.5+0.9*rng.random()))
    return x


def wind(dur=12.0):
    """ريح — جو ليلي"""
    n=int(SR*dur)
    base=rng.normal(0,1,n)
    x=np.zeros(n); step=4096
    for i in range(0,n,step):
        seg=base[i:i+step]
        if len(seg)<8: break
        p=i/n
        c=300+700*(0.5+0.5*np.sin(2*np.pi*0.9*p))
        x[i:i+len(seg)]=bandpass_fft(seg,80,c)
    sl=np.zeros(n)
    for f,a in [(0.05,1.0),(0.13,0.6),(0.027,0.8)]:
        sl+=a*np.sin(2*np.pi*f*np.arange(n)/SR+rng.random()*6.28)
    sl=0.35+0.65*(0.5+0.5*sl/np.max(np.abs(sl)))
    return x*sl*0.7


def stinger_reveal(dur=4.0):
    """ستينغر الكشف — لحظة الحقيقة"""
    d=t(dur)
    sub=np.sin(2*np.pi*38*d)*np.exp(-d*1.5)
    swell=np.sin(2*np.pi*np.cumsum(np.linspace(60,180,len(d)))/SR)
    swell*=np.clip(d/0.5,0,1)*np.exp(-d*1.1)
    # وتر قاتم
    ch=np.zeros(len(d))
    for f in [110,131,165,196]:
        ch+=np.sin(2*np.pi*f*d+rng.random()*6.28)
    ch*=np.exp(-d*1.8)*0.25
    metal=bandpass_fft(rng.normal(0,1,len(d)),2000,7000)*np.exp(-d*6)*0.2
    x=sub*0.8+swell*0.4+ch+metal
    return reverb(x, decay=0.55, mix=0.35, spread=0.08)


def sub_drop():
    """سقطة باص — للانتقالات القوية"""
    d=t(2.8)
    f=np.linspace(85,26,len(d))
    x=np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-d*1.5)
    x+=np.sin(2*np.pi*np.cumsum(f*2)/SR)*np.exp(-d*3.5)*0.3
    return lowpass_fft(x,320)


def ticking_pressure(dur=10.0):
    """تكتكة متسارعة — تصاعد التوتر"""
    n=int(SR*dur); x=np.zeros(n)
    i=0; gap=0.55
    while i<n-SR//4:
        ln=int(SR*0.05); d=np.arange(ln)/SR
        cl=bandpass_fft(rng.normal(0,1,ln),1600,8000)*np.exp(-d*200)
        x[i:i+ln]+=cl*(0.7+0.5*(i/n))
        i+=int(SR*gap)
        gap=max(0.14, gap*0.93)
    return reverb(x, decay=0.3, mix=0.2)


def evidence_bag():
    """كيس الأدلة البلاستيكي"""
    ln=int(SR*1.1); d=np.arange(ln)/SR
    x=bandpass_fft(rng.normal(0,1,ln),3000,13000)
    wob=np.abs(np.sin(2*np.pi*9*d))*0.6+0.4
    burst=np.exp(-((d-0.15)/0.12)**2)+0.7*np.exp(-((d-0.55)/0.18)**2)+0.5*np.exp(-((d-0.85)/0.1)**2)
    return x*wob*burst*0.8


def clock_wall(dur=10.0):
    """ساعة حائط — انتظار طويل"""
    return clock_tick(dur)




if __name__ == "__main__":
    print("🎚️  كنولّد المؤثرات الصوتية…")
    print("\n— المجموعة 1: الأساسيات —")
    save("01_phone_ring.wav",     phone_ring(3))
    save("02_door_knock.wav",     door_knock(3))
    save("03_footsteps.wav",      footsteps(9, 0.58))
    save("04_crowd.wav",          crowd(9.0))
    save("05_tension_drone.wav",  tension_drone(14.0))
    save("06_impact.wav",         impact())
    save("07_whoosh.wav",         whoosh())
    save("08_clock_tick.wav",     clock_tick(8.0))
    save("09_door_open.wav",      door_open())

    print("\n— المجموعة 2: الشرطة والتحقيق —")
    save("10_police_siren.wav",   police_siren(9.0, "wail"))
    save("11_siren_yelp.wav",     police_siren(5.0, "yelp"))
    save("12_paper_turn.wav",     paper_turn(4))
    save("13_paper_single.wav",   paper_single())
    save("14_camera_shutter.wav", camera_shutter(3))
    save("15_keyboard.wav",       keyboard_typing(6.0))
    save("16_car_engine.wav",     car_engine(8.0, True))
    save("17_car_door.wav",       car_door())
    save("18_handcuffs.wav",      handcuffs())
    save("19_cell_door.wav",      cell_door())
    save("20_radio_chatter.wav",  radio_chatter(7.0))
    save("21_evidence_bag.wav",   evidence_bag())

    print("\n— المجموعة 3: الجو والتوتر —")
    save("22_rain.wav",           rain(12.0, False))
    save("23_rain_heavy.wav",     rain(10.0, True))
    save("24_wind.wav",           wind(12.0))
    save("25_heartbeat.wav",      heartbeat(7, 62))
    save("26_ticking_pressure.wav", ticking_pressure(10.0))

    print("\n— المجموعة 4: الانتقالات —")
    save("27_stinger_reveal.wav", stinger_reveal(4.0))
    save("28_sub_drop.wav",       sub_drop())
    save("29_whoosh_down.wav",    whoosh(1.9, rise=False))
    save("30_clock_wall.wav",     clock_wall(10.0))

    print("\n✅ سالا — 30 مؤثر.")
