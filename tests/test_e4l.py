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

# --- LFOs ------------------------------------------------------------------
o = run("E4L Mono Panner.jsfx", dc, "s3=0.1", "s10=1", "s11=0", "s13=1")
az, _ = direction(o)
check("azimuth LFO cycle 1 Hz", angle_close(az[SR // 4], 90) and angle_close(az[3 * SR // 4], -90))

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
o = run(LP, ramp, "s1=0", "s2=1")
check("looper: records bar 1, plays it in sync from bar 2 and loops",
      np.abs(o[:96000]).max() == 0 and np.allclose(o[96000 + j], ramp[j]) and np.allclose(o[192000 + j], ramp[j]))
o = run(LP, ramp, "s1=0", "s2@30000=1")
check("looper: REC pressed mid-bar waits for the next bar",
      np.abs(o[:192000]).max() == 0 and np.allclose(o[192000 + j], ramp[96000 + j]))
o = run(LP, ramp, "s1=0", "s2=1", "s8=10")
check("looper: latency compensation 10 ms = 480 samples", np.allclose(o[96000 + j, 0], ramp[j + 480, 0]))
o = run(LP, ramp, "s1=0", "s2=1", "s3@250000=0", "s3@300000=1")
check("looper: STOP and PLAY are quantised to the bar and stay in phase",
      np.abs(o[288100:384000]).max() == 0 and np.allclose(o[385000:470000, 0], ramp[1000:86000, 0]))
o = run(LP, ramp, "s1=0", "s2=1", "s4@192000=1", "s4@288000=0")
check("looper: overdub adds a layer", np.allclose(o[288000 + j, 0], ramp[j, 0] + ramp[192000 + j, 0], atol=1e-5))
o = run(LP, ramp, "s1=0", "s2=1", "s2@200000=1")
check("looper: re-record keeps the old loop until the new one starts",
      np.allclose(o[200500:287000, 0], ramp[8500:95000, 0]) and np.allclose(o[385000:470000, 0], ramp[289000:374000, 0]))
o = run(LP, ramp, "s1=0", "s2=1", "s5@250000=1")
check("looper: clear", np.abs(o[250300:]).max() == 0)

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

imp = np.zeros((4096, 16)); imp[0, 0] = 1
out = run("E4L Master Bus.jsfx", imp, "s1=0")
check("binaural latency = 512 samples (reported as PDC)", np.argmax(np.abs(out[:, 0]) > 1e-6) >= 512)

print("\n%d failure(s)" % failures)
sys.exit(1 if failures else 0)
