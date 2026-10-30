#!/usr/bin/env python3
"""Tests for the E4L JSFX, run with the ysfx-based harness (see run_tests.sh)."""
import os
import subprocess
import sys
import tempfile

import numpy as np

RUNFX = os.path.abspath(sys.argv[1])
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FX = os.path.join(ROOT, "Effects", "E4L")
DATA = os.path.join(ROOT, "Data")
SR = 48000
TMP = tempfile.mkdtemp()
failures = 0


def run(fx, x, *sliders, tempo=120, play=1):
    inp, out = os.path.join(TMP, "in.raw"), os.path.join(TMP, "out.raw")
    x.astype(np.float32).tofile(inp)
    args = [RUNFX, os.path.join(FX, fx), DATA, str(SR), str(len(x)), inp, str(x.shape[1]), out,
            *sliders, "tempo=%g" % tempo, "play=%d" % play]
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr)
    return np.fromfile(out, np.float32).reshape(len(x), -1)


def direction(o):
    """E4L azimuth (clockwise) and elevation from first-order ambiX channels."""
    az = -np.degrees(np.arctan2(o[..., 1], o[..., 3]))
    el = np.degrees(np.arctan2(o[..., 2], np.hypot(o[..., 1], o[..., 3])))
    return az, el


def check(name, cond):
    global failures
    print(("ok   " if cond else "FAIL ") + name)
    failures += 0 if cond else 1


def angle_close(a, b, tol=0.5):
    return abs((a - b + 180) % 360 - 180) < tol


dc = np.ones((2 * SR, 2))

# --- encoding --------------------------------------------------------------
o = run("E4L Mono Panner.jsfx", dc[:4800], "s1=-30", "s3=0.1")[-1]
check("mono panner: SN3D coefficients at az -30 (left)",
      np.allclose(o[:4], [1, 0.5, 0, np.sqrt(3) / 2], atol=1e-4))

o = run("E4L Source Panner.jsfx", np.c_[np.ones(4800), np.zeros(4800)],
        "s2=0", "s11=0.5", "s12=0", "s13=0.5", "s14=0.2")[-1]
az, el = direction(o)
check("source panner XYZ: left channel direction", angle_close(az, 90) and abs(el - 59.04) < 0.1)
check("source panner XYZ: distance gain -1.5 dB/unit",
      abs(o[0] - 10 ** ((np.sqrt(0.34) * 10 - 1) * -1.5 / 20)) < 1e-3)

o = run("E4L Stereo Panner.jsfx", np.c_[np.ones(4800), np.zeros(4800)], "s3=0.1", "s6=20")[-1]
az, el = direction(o)
check("stereo panner: left = az - spread, el + spread (as E4L)", angle_close(az, -30) and abs(el - 20) < 0.1)


def quad_dirs(*sliders):
    dirs = []
    for ch in range(4):
        x = np.zeros((4800, 4)); x[:, ch] = 1
        a, e = direction(run("E4L Quad Panner.jsfx", x, "s3=0.1", *sliders)[-1])
        dirs.append((round(float(a), 1), round(float(e), 1)))
    return dirs


d = quad_dirs()
check("quad LR: FL -45, FR 45, RL -135, RR 135",
      all(angle_close(a, b) for (a, _), b in zip(d, (-45, 45, -135, 135))))
d = quad_dirs("s7=1")
check("quad X: rear pair crossed", angle_close(d[2][0], 135) and angle_close(d[3][0], -135))
d = quad_dirs("s7=2", "s5=40")
check("quad W: spread 40 -> front +-20 (W1), rear +-60 (W2)",
      all(angle_close(a, b) for (a, _), b in zip(d, (-20, 20, -60, 60))))
d = quad_dirs("s7=2", "s5=150")
check("quad W: spread 150 -> front +-135, rear +-165",
      all(angle_close(a, b) for (a, _), b in zip(d, (-135, 135, -165, 165))))

x = np.zeros((4800, 16)); x[:, 2] = 1
o = run("E4L Multi-Panner.jsfx", x, "s1=10", "s3=0.1", "s5=0.5", "s59=60", "s60=30", "s6=2")[-1]
az, el = direction(o)
check("multi-panner: input 3 at 10 + 60*0.5 = 40, elevation 30*2 = 60", angle_close(az, 40) and abs(el - 60) < 0.1)
o = run("E4L Multi-Panner.jsfx", x, "s58=0")[-1]
check("multi-panner: inactive input is silent", np.abs(o).max() < 1e-6)

def final_sliders(fx, x, *sliders):
    args = [RUNFX, os.path.join(FX, fx), DATA, str(SR), str(len(x)), os.path.join(TMP, "in.raw"),
            str(x.shape[1]), os.path.join(TMP, "out.raw"), *sliders, "tempo=120", "play=1"]
    x.astype(np.float32).tofile(args[5])
    err = subprocess.run(args, capture_output=True, text=True).stderr
    return {int(k[6:]): float(v) for k, v in (l.split("=") for l in err.splitlines() if l.startswith("slider"))}


sl = final_sliders("E4L Quad Panner.jsfx", np.zeros((SR // 2, 4)), "s1=30", "s5=120", "s3=0.1")
check("quad panner publishes its position and width for the Live Panel",
      abs(sl[60] - 30) < 0.5 and abs(sl[62] - 120) < 0.5)
sl = final_sliders("E4L Stereo Panner.jsfx", np.zeros((SR // 2, 2)), "s1=-20", "s5=45", "s3=0.1")
check("stereo panner publishes its width for the Live Panel", abs(sl[60] + 20) < 0.5 and abs(sl[62] - 45) < 0.5)

# --- LFOs ------------------------------------------------------------------
o = run("E4L Mono Panner.jsfx", dc, "s3=0.1", "s10=1", "s11=0", "s13=1")
az, _ = direction(o)
check("azimuth LFO cycle 1 Hz", angle_close(az[SR // 4], 90) and angle_close(az[3 * SR // 4], -90))

# random wander: the point goes around INSIDE the room (direction and distance change)
def wander_track(o):
    az, _ = direction(o)
    d = np.sqrt(np.hypot(o[:, 1], o[:, 3]) / np.maximum(np.abs(o[:, 0]), 1e-9))   # inside: g = d^2
    return az, d
dc3 = np.ones((6 * SR, 1))
o = run("E4L Mono Panner.jsfx", dc3, "s3=0.1", "s45=1", "s47=2")
az, d = wander_track(o)
k = np.arange(SR, 6 * SR, 2400)
check("random wander: the sound visits many directions and distances inside the room",
      np.ptp(np.unwrap(np.radians(az[k]))) > 2 and d[k].max() <= 1.01 and d[k].std() > 0.1)
step = np.abs(np.diff(o[:, 0]))
check("random wander: the path is smooth (no jumps)", step.max() < 0.001)
o = run("E4L Mono Panner.jsfx", dc3, "s3=0.1", "s45=1", "s47=2", "s49=0.3")
_, d = wander_track(o)
check("random wander: Area 0.3 keeps it near the centre", d[k].max() <= 0.31)
o = run("E4L Mono Panner.jsfx", dc3, "s3=0.1", "s45=1", "s47=2", "ps@96000=2", "ps@192000=1")
check("random wander: frozen while paused",
      np.allclose(o[100000], o[190000]) and not np.allclose(o[200000], o[100000]))
q1 = np.zeros((3 * SR, 4)); q1[:, 0] = 1       # only the front-left channel
o = run("E4L Quad Panner.jsfx", q1, "s3=0.1", "s45=1", "s47=2")
check("random wander: the quad panner wanders too (all four points move)",
      np.ptp(o[SR:, 1]) > 0.1)

# PAUSE freezes the movement and PLAY continues from there; STOP + PLAY starts from 0
o = run("E4L Mono Panner.jsfx", dc, "s3=0.1", "s10=1", "s11=0", "s13=1", "ps@12032=2", "ps@36096=1")
az, _ = direction(o)
check("movement: PAUSE keeps the position, PLAY continues from it",
      angle_close(az[30000], az[12100], 2) and angle_close(az[36096 + 12000], az[12032] + 90, 3))
o = run("E4L Mono Panner.jsfx", dc, "s3=0.1", "s10=1", "s11=0", "s13=1", "ps@12032=0", "ps@36096=1")
az, _ = direction(o)
check("movement: after STOP, PLAY starts the rotation from the beginning",
      angle_close(az[36096 + 400], 0, 4) and angle_close(az[36096 + 12000], 90, 3))
o = run("E4L Mono Panner.jsfx", dc, "s3=0.1", "s10=1", "s11=1", "s13=1", "s17=45")
az, _ = direction(o)
check("azimuth LFO sin depth 45", angle_close(az[SR // 4], 45) and angle_close(az[3 * SR // 4], -45))

o = run("E4L Mono Panner.jsfx", dc, "s3=0.1", "s10=1", "s12=1", "s15=2", tempo=120, play=1)
az, _ = direction(o)
check("azimuth LFO synced to 1 bar @120 BPM", angle_close(az[SR // 2], 90, 1) and angle_close(az[SR], 180, 1))

o = run("E4L Mono Panner.jsfx", dc, "s3=0.1", "s20=1", "s23=1", "s27=60")
_, el = direction(o)
check("elevation LFO unipolar 0..60", abs(el[SR // 2] - 60) < 0.5 and abs(el[0]) < 0.5)

o = run("E4L Mono Panner.jsfx", dc, "s3=0.1", "s2=80", "s20=1", "s21=1", "s23=1", "s27=30")
az, el = direction(o)
check("elevation folds over the pole", angle_close(az[SR // 4], 180) and abs(el[SR // 4] - 70) < 0.5)

# --- looper (120 BPM, 4/4: one bar = 2 s = 96000 samples) -------------------
ramp = np.stack([np.arange(10 * SR) * 1e-6, -np.arange(10 * SR) * 1e-6], 1)
j = np.arange(1000, 95000)
LP = "E4L Looper.jsfx"
EXACT = ("s14=1", "s15=1")   # 1 ms fades: compare the loop sample by sample
o = run(LP, ramp, *EXACT, "s1=0", "s2=1")
check("looper: records bar 1, plays it in sync from bar 2 and loops",
      np.abs(o[:96000]).max() == 0 and np.allclose(o[96000 + j], ramp[j]) and np.allclose(o[192000 + j], ramp[j]))
o = run(LP, ramp, *EXACT, "s1=0", "s2@30000=1")
check("looper: REC pressed mid-bar waits for the next bar",
      np.abs(o[:192000]).max() == 0 and np.allclose(o[192000 + j], ramp[96000 + j]))
o = run(LP, ramp, *EXACT, "s1=0", "s2=1", "s8=10")
check("looper: latency compensation 10 ms = 480 samples", np.allclose(o[96000 + j, 0], ramp[j + 480, 0]))
o = run(LP, ramp, *EXACT, "s1=0", "s2=1", "s3@250000=0", "s3@300000=1")
check("looper: STOP and PLAY are quantised to the bar and stay in phase",
      np.abs(o[289500:384000]).max() == 0 and np.allclose(o[385000:470000, 0], ramp[1000:86000, 0]))
# clicks: a sine that does not fit the loop (worst case for the seam)
t = np.arange(10 * SR) / SR
sine = np.stack([0.5 * np.sin(2 * np.pi * 220.3 * t)] * 2, 1)
step = 2 * np.pi * 220.3 / SR * 0.5 * 1.5          # largest normal sample-to-sample change, + margin
o = run(LP, sine, "s1=0", "s2=1", "s8=10", "s3@250000=0")   # 10 ms latency comp., as on a real interface
d = np.abs(np.diff(o[:, 0]))
check("looper: no click when the loop starts after recording (fade-in)",
      d[95990:96300].max() < step and abs(o[96000, 0]) < step)
check("looper: no click at the loop seam (end crossfades into the pre-roll)",
      d[191900:192100].max() < step)
check("looper: no click on STOP (fade-out)", d[287900:290000].max() < step)
# a steady, unmodulated bass tone (55.3 Hz, period 18 ms): the seam must not bend the wave
bass = np.stack([0.5 * np.sin(2 * np.pi * 55.3 * t)] * 2, 1)
# (REC pressed during bar 1 while the tone already sounds: records bar 2, seam at 288000)
def click_db(y, at):        # energy above 2 kHz around `at`, relative to the total (dB)
    seg = y[at - 4096:at + 1024]
    S = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2
    return 10 * np.log10(S[np.fft.rfftfreq(len(seg), 1 / SR) > 2000].sum() / S.sum() + 1e-20)
o = run(LP, bass, "s1=0", "s2@30000=1", "s8=10")[:, 0]
check("looper: steady bass tone, no click at the seam (50 ms crossfade)",
      click_db(o, 288000) < click_db(o, 250000) + 15)

# higher steady tone (440 Hz)
def seam_dip(o, f, at):
    w = int(SR / f)
    lv = [np.abs(o[i:i + w, 0]).max() for i in range(at - 3000, at + 500, w // 4)]
    return 20 * np.log10(min(lv) / np.abs(o[at - 20000:at - 10000, 0]).max())
mid = np.stack([0.5 * np.sin(2 * np.pi * 440.7 * t)] * 2, 1)
# Steady tones: the looper finds the shift (at most half a cycle) that puts the end of the
# loop in phase with its start and reads the loop that much longer / shorter, so neither seam
# dips (2-bar loop recorded in bars 2-3, seams at 288000 and 384000).
def analytic(y):
    N = len(y); X = np.fft.fft(y); h = np.zeros(N); h[0] = 1; h[1:N // 2] = 2; h[N // 2] = 1
    return np.fft.ifft(X * h)
def seam_level(o, at, amp):
    z = analytic(o[at - 6000:at + 3000, 0])[1000:-1000]
    return 20 * np.log10(np.abs(z).min() / amp)
def pitch(o, a, b):
    z = analytic(o[a:b, 0]); f = np.diff(np.unwrap(np.angle(z))) * SR / (2 * np.pi)
    return np.median(f[500:-500])
for f in (55.3, 98.37, 220.3, 440.7, 1500.9):
    o = run(LP, np.stack([0.5 * np.sin(2 * np.pi * f * t)] * 2, 1), "s1=0", "s2@30000=1", "s8=10")
    d1, d2 = seam_level(o, 288000, 0.5), seam_level(o, 384000, 0.5)
    cents = 1200 * np.log2(pitch(o, 330000, 370000) / f)
    check("looper: steady %.0f Hz tone, both seams even (%.1f / %.1f dB), speed %+.1f cents"
          % (f, d1, d2, cents), d1 > -0.6 and d2 > -0.6 and abs(cents) < 11)
saw = sum(np.sin(2 * np.pi * k * 110.3 * t) / k for k in range(1, 40))
saw = np.stack([0.5 * saw / np.abs(saw).max()] * 2, 1)
o = run(LP, saw, "s1=0", "s2@30000=1", "s8=10")[:, 0]
check("looper: steady sawtooth (110 Hz, many harmonics), no click at either seam",
      click_db(o, 288000) < click_db(o, 250000) + 6 and click_db(o, 384000) < click_db(o, 250000) + 6)
noise = np.random.default_rng(1).normal(size=(10 * SR, 2)) * 0.2
o = run(LP, noise, "s1=0", "s2@30000=1", "s8=10")
check("looper: a non-periodic sound keeps its exact speed (no shift)",
      np.allclose(o[300000:380000], o[204000:284000], atol=1e-6))
o = run(LP, mid, "s1=0", "s2@30000=1", "s8=10", "s17=2")
check("looper: compensation Full still works (440 Hz, dip %.1f dB)" % seam_dip(o, 440.7, 288000),
      seam_dip(o, 440.7, 288000) > -3)

# transport: STOP then PLAY starts the loops from their beginning; PAUSE continues
o = run(LP, ramp, *EXACT, "s1=1", "s2=1", "ps@300000=0", "beat@310016=4", "ps@310016=1")
check("looper: after STOP, PLAY (here from bar 2) starts the loop from its beginning",
      np.allclose(o[310016 + 3000:310016 + 90000, 0], ramp[3000:90000, 0]))
o = run(LP, ramp, *EXACT, "s1=1", "s2=1", "ps@300032=2", "ps@340000=1")
check("looper: after PAUSE, PLAY continues where it was",
      np.allclose(o[343000:380000, 0], ramp[111000:148000, 0], atol=1e-4))
# per-loop PAUSE (2-bar loop recorded in bars 1-2, playing from 192000): paused at 250112,
# 58112 samples into the loop; PAUSE off at 300032 -> continues at once from that exact point
o = run(LP, ramp, *EXACT, "s1=1", "s2=1", "s16@250112=1", "s16@300032=0")
check("looper: PAUSE silences the loop at once",
      np.abs(o[250500:300032]).max() == 0)
check("looper: PAUSE off continues at once from the exact point where it was paused",
      np.allclose(o[300032 + 500:300032 + 90000, 0], ramp[58112 + 500:58112 + 90000, 0]))
ramp14 = np.stack([np.arange(14 * SR) * 1e-6, -np.arange(14 * SR) * 1e-6], 1)
o = run(LP, ramp14, *EXACT, "s1=1", "s2=1", "s16@300032=1", "s16@400128=0")
check("looper: ... also from the second bar of the loop (108032 samples in), then it wraps",
      np.allclose(o[400128 + 500:400128 + 80000, 0], ramp14[108032 + 500:108032 + 80000, 0])
      and np.allclose(o[400128 + 83968 + 500:400128 + 83968 + 50000, 0], ramp14[500:50000, 0]))
o = run(LP, ramp14, *EXACT, "s1=1", "s2=1", "s16@300032=1", "s3@400128=1")
check("looper: PLAY while paused starts the loop from its beginning on the next bar",
      np.allclose(o[480000 + 1000:480000 + 90000, 0], ramp14[1000:90000, 0]))
# 2-bar loop recorded in bars 2-3, playing from bar 4; its STOP at bar 5, PLAY again at bar 6:
# in phase it would play its 2nd bar there, from the beginning it plays its 1st
o = run(LP, ramp14, *EXACT, "s1=1", "s2@30000=1", "s3@300032=0", "s3@400128=1")
check("looper: PLAY after its STOP starts it from its beginning",
      np.allclose(o[480000 + 1000:480000 + 90000, 0], ramp14[96000 + 1000:96000 + 90000, 0]))
o = run(LP, ramp, *EXACT, "s1=0", "s2=1", "s4@192000=1", "s4@288000=0")
check("looper: overdub adds a layer", np.allclose(o[288000 + j, 0], ramp[j, 0] + ramp[192000 + j, 0], atol=1e-5))
o = run(LP, ramp, *EXACT, "s1=0", "s2=1", "s2@200000=1")
check("looper: re-record keeps the old loop until the new one starts",
      np.allclose(o[200500:287000, 0], ramp[8500:95000, 0]) and np.allclose(o[385000:470000, 0], ramp[289000:374000, 0]))
o = run(LP, ramp, *EXACT, "s1=0", "s2=1", "s5@250000=1")
check("looper: clear", np.abs(o[250300:]).max() == 0)

# --- sync out (reset pulses for an external sequencer) ------------------------
SY = "E4L Sync Out.jsfx"
def run2(fx, x, fx2, *sliders):
    """fx then fx2 in the same process (like two tracks: gmem is shared)."""
    inp, out, out2 = (os.path.join(TMP, n) for n in ("in.raw", "out.raw", "out2.raw"))
    x.astype(np.float32).tofile(inp)
    args = [RUNFX, os.path.join(FX, fx), DATA, str(SR), str(len(x)), inp, str(x.shape[1]), out,
            "fx2=" + os.path.join(FX, fx2), "out2=" + out2, *sliders, "tempo=120", "play=1"]
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr)
    o1 = np.fromfile(out, np.float32).reshape(len(x), -1)
    return o1, np.fromfile(out2, np.float32).reshape(len(x), -1)
def pulses(ch):
    on = np.flatnonzero((ch[1:] != 0) & (ch[:-1] == 0)) + 1
    return ([0] if ch[0] != 0 else []) + list(on)
sil = np.zeros((6 * SR, 2))
# REC pressed mid-bar (sample 30000) on a 1-bar looper: the recording starts at bar 2 (96000)
_, so = run2(LP, sil, SY, "s1=0", "s2@30000=1")
check("sync out: reset when REAPER starts (0) and on the bar where the loop starts recording (96000)",
      pulses(so[:, 0]) == [0, 96000] and np.all(so[96000:96480, 0] == 1) and so[96480, 0] == 0)
so, _ = run2(SY, np.zeros((6 * SR, 1)), LP, "B.s1=0", "B.s2@30000=1")
check("sync out: same pulse when the sync track is processed before the looper",
      pulses(so[:, 0]) == [0, 96000])
_, so = run2(LP, sil, SY, "s1=0", "s2@30000=1", "s2@60000=0")
check("sync out: REC cancelled before the bar -> no reset", pulses(so[:, 0]) == [0])
_, so = run2(LP, sil, SY, "s1=0", "s2@30000=1", "B.s7=-5")
check("sync out: timing offset -5 ms -> the pulse leaves 240 samples earlier", pulses(so[:, 0])[1] == 96000 - 240)
_, so = run2(LP, sil, SY, "s1=0", "B.s2=0", "B.s3=2")
check("sync out: reset every 2 bars (start reset off)", pulses(so[:, 0]) == [0, 192000])
_, so = run2(LP, sil, SY, "s1=0", "B.s2=1", "ps@120064=2", "ps@150016=1", "ps@200192=0", "beat@250112=0", "ps@250112=1")
check("sync out: resuming from PAUSE does not reset, starting from STOP does",
      pulses(so[:, 0]) == [0, 250112])
_, so = run2(LP, sil, SY, "s1=0", "B.s2=0", "B.s8=3")
pc = pulses(so[:, 1])
check("sync out: clock 1/16 on output 2 (from the very start, every 6000 samples at 120 BPM)",
      pc[:4] == [0, 6000, 12000, 18000] and np.all(np.diff(pc) == 6000))
# sequencer with only a clock input: "Output 1 sends = Clock" (1/16 when no rate is chosen)
_, so = run2(LP, sil, SY, "s1=0", "s2@30000=1", "B.s12=1")
pc = pulses(so[:, 0])
check("sync out: Output 1 = Clock -> 1/16 clock on output 1 from the start, resets on output 2",
      pc[:3] == [0, 6000, 12000] and np.all(np.diff(pc) == 6000) and len(pc) == 6 * SR // 6000
      and pulses(so[:, 1]) == [0, 96000] and np.all(so[0:480, 0] == 1))
# pause in the middle of a step: no extra pulse, the steps go on where they were
_, so = run2(LP, sil, SY, "s1=0", "B.s12=1", "B.s2=0", "ps@120064=2", "ps@150016=1")
pc = pulses(so[:, 0])
before = [p for p in pc if p < 120064]; after = [p for p in pc if p >= 150016]
check("sync out: clock through a PAUSE: no extra pulse, the next one where the step was due",
      before[-1] == 120000 and after[0] == 150016 + (126000 - 120064) and np.all(np.diff(after) == 6000))
_, so = run2(LP, sil, SY, "s1=0", "B.s12=1", "B.s2=0", "ps@120064=0", "beat@150016=0", "ps@150016=1")
pc = pulses(so[:, 0])
check("sync out: clock after STOP + PLAY from bar 1: a pulse right on the start",
      150016 in pc and [p for p in pc if p > 150016][0] == 150016 + 6000)
_, so = run2(LP, sil, SY, "s1=0", "B.s13=1", "B.s5=0.8")
seg = so[48000:96000, 0]
check("sync out: voltmeter test, square 50 Hz at the pulse level on output 1",
      np.allclose(np.abs(seg), 0.8) and abs(np.mean(seg)) < 0.01 and len(pulses(np.maximum(seg, 0))) in (50, 51))
_, so = run2(LP, sil, SY, "s1=0", "B.s2=0", "B.s10@48128=1", "B.s6=1", "B.s4=2")
check("sync out: test button sends one pulse (negative polarity, 2 ms)",
      pulses(so[:, 0]) == [48128] and np.all(so[48128:48128 + 96, 0] == -1) and so[48128 + 96, 0] == 0)

# --- decoders --------------------------------------------------------------
noise = np.random.default_rng(0).normal(size=(2 * SR, 1)).repeat(2, 1) * 0.1
for az_in, louder in ((-90, 0), (90, 1)):
    enc = run("E4L Mono Panner.jsfx", noise, "s1=%d" % az_in, "s3=0.1")
    for dec, name in ((0, "binaural"), (1, "stereo")):
        out = run("E4L Master Bus.jsfx", enc, "s1=%d" % dec)[4800:]
        rms = np.sqrt((out[:, :2] ** 2).mean(0))
        check("%s: source at %d is louder on the %s" % (name, az_in, "left" if louder == 0 else "right"),
              rms[louder] > 2 * rms[1 - louder])

enc = run("E4L Mono Panner.jsfx", noise, "s1=0", "s3=0.1")
out = run("E4L Master Bus.jsfx", enc, "s1=7")[4800:]
rms = np.sqrt((out ** 2).mean(0))
check("7.1.4: front source loudest on C, LFE = W * 0.707",
      rms[2] == rms[:12].max() and abs(rms[3] - 0.1 * 0.707) < 0.005)

enc = run("E4L Mono Panner.jsfx", noise, "s1=135", "s3=0.1")
out = run("E4L Master Bus.jsfx", enc, "s1=2", "s6=5")[4800:]
rms = np.sqrt((out ** 2).mean(0))
check("quad + sub: rear-right source on output 3, sub on output 5 = W * 0.707",
      rms[2] == rms[:4].max() and abs(rms[4] - 0.1 * 0.707) < 0.003)
out = run("E4L Master Bus.jsfx", enc, "s1=2", "s6=5", "s8=100")[4800:]
spec = np.abs(np.fft.rfft(out[:, 4])); f = np.fft.rfftfreq(len(out), 1 / SR)
check("sub low-pass 100 Hz removes the highs", spec[f > 1000].mean() < 0.01 * spec[(f > 20) & (f < 60)].mean())
out = run("E4L Master Bus.jsfx", enc, "s1=0", "s6=5")[4800:]
check("binaural ignores the sub output", np.abs(out[:, 4]).max() == 0)

quad = np.zeros((SR, 6)); quad[:, :4] = noise[:SR, :1] * np.array([1.0, 0.5, 0.25, 0.1])
out = run("E4L Sub Out.jsfx", quad)
check("master sub: output 5 = 0.5 x (sum of channels 1-4), channels 1-4 untouched",
      np.allclose(out[:, 4], 0.5 * quad[:, :4].sum(1), atol=1e-6) and np.allclose(out[:, :4], quad[:, :4]))
out = run("E4L Sub Out.jsfx", quad, "s4=100")[4800:]
spec = np.abs(np.fft.rfft(out[:, 4])); f = np.fft.rfftfreq(len(out), 1 / SR)
check("master sub: low-pass 100 Hz", spec[f > 1000].mean() < 0.01 * spec[(f > 20) & (f < 60)].mean())

imp = np.zeros((4096, 16)); imp[0, 0] = 1
out = run("E4L Master Bus.jsfx", imp, "s1=0")
check("binaural latency = 512 samples (reported as PDC)", np.argmax(np.abs(out[:, 0]) > 1e-6) >= 512)

print("\n%d failure(s)" % failures)
sys.exit(1 if failures else 0)
