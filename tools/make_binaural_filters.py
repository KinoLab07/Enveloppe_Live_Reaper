#!/usr/bin/env python3
"""
Builds the binaural filters used by "E4L Master Bus" (Binaural 3rd-order decoder).

E4L's "Binaural (3rd-order)" decoder decodes the 16 ambisonics channels to 25 virtual
loudspeakers and convolves each one with an IRCAM Listen HRIR (subject 1052, files in
EnvelopForLive/media/hrtf). Because everything is linear, this script folds the decoder
matrix and the 25 HRIRs into 16 x 2 filters (one per ambisonics channel and ear), so the
JSFX only has to run 16 FFT convolutions instead of 50.

Order weighting (basic / max-rE / in-phase) is NOT baked in: it is a per-order gain,
applied by the JSFX before the convolution.

Usage:
    python3 tools/make_binaural_filters.py /path/to/EnvelopForLive/media/hrtf Data/E4L/hrtf

Output: e4l_binaural_<rate>.wav, 32 channels float32 (channel 2*acn = left ear,
2*acn+1 = right ear), for 44100, 48000, 88200 and 96000 Hz.

GPLv2 or later (same as Envelop for Live).
"""
import glob
import os
import re
import struct
import sys
import wave
from fractions import Fraction

import numpy as np
from scipy.signal import resample_poly

RATES = [44100, 48000, 88200, 96000]


def sh3_ambix(az_rad, el_rad):
    """Real SH, 3rd order, ACN / SN3D. az counter-clockwise (ambiX convention)."""
    p, t = az_rad, el_rad
    cp, sp = np.cos(p), np.sin(p)
    c2p, s2p = np.cos(2 * p), np.sin(2 * p)
    c3p, s3p = np.cos(3 * p), np.sin(3 * p)
    ct, st = np.cos(t), np.sin(t)
    ct2, s2t = ct * ct, 2 * st * ct
    return np.array([
        np.ones_like(p),
        sp * ct, st, cp * ct,
        np.sqrt(3) / 2 * s2p * ct2,
        np.sqrt(3) / 2 * sp * s2t,
        0.5 * (3 * st * st - 1),
        np.sqrt(3) / 2 * cp * s2t,
        np.sqrt(3) / 2 * c2p * ct2,
        np.sqrt(5 / 8) * s3p * ct2 * ct,
        np.sqrt(15) / 2 * s2p * st * ct2,
        np.sqrt(3 / 8) * sp * ct * (5 * st * st - 1),
        0.5 * st * (5 * st * st - 3),
        np.sqrt(3 / 8) * cp * ct * (5 * st * st - 1),
        np.sqrt(15) / 2 * c2p * st * ct2,
        np.sqrt(5 / 8) * c3p * ct2 * ct,
    ])


ORDER = np.array([0, 1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3])


def read_hrirs(folder):
    files = sorted(glob.glob(os.path.join(folder, "IRC_*_T*_P*.wav")))
    if len(files) != 25:
        sys.exit("expected 25 IRCAM HRIR files, found %d" % len(files))
    dirs, irs = [], []
    for f in files:
        m = re.search(r"_T(\d+)_P(\d+)\.wav$", f)
        az = int(m.group(1))          # IRCAM Listen: counter-clockwise, 90 = left
        el = int(m.group(2))
        el = el - 360 if el > 180 else el
        w = wave.open(f)
        assert w.getnchannels() == 2 and w.getsampwidth() == 2
        sr = w.getframerate()
        d = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64) / 32768.0
        irs.append(d.reshape(-1, 2).T)  # (2, n)
        dirs.append((np.radians(az), np.radians(el)))
    return np.array(dirs), np.array(irs), sr


def write_float_wav(path, data, sr):
    """data: (channels, frames) float32, written as WAVE_FORMAT_EXTENSIBLE / IEEE float."""
    nch, n = data.shape
    frames = data.T.astype("<f4").tobytes()
    fmt = struct.pack("<HHIIHHHHIH14s", 0xFFFE, nch, sr, sr * nch * 4, nch * 4, 32,
                      22, 32, 0, 3, b"\x00\x00\x00\x00\x10\x00\x80\x00\x00\xaa\x00\x38\x9b\x71")
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 4 + 8 + len(fmt) + 8 + len(frames)) + b"WAVE")
        f.write(b"fmt " + struct.pack("<I", len(fmt)) + fmt)
        f.write(b"data" + struct.pack("<I", len(frames)) + frames)


def main():
    src, dst = sys.argv[1], sys.argv[2]
    os.makedirs(dst, exist_ok=True)
    dirs, irs, sr0 = read_hrirs(src)
    S = len(dirs)

    # Basic sampling decoder (SN3D): g_s = 1/S * sum_n (2n+1) Y_acn(dir_s) b_acn
    Y = sh3_ambix(dirs[:, 0], dirs[:, 1])            # (16, S)
    D = (2 * ORDER[:, None] + 1) * Y / S             # (16, S)
    H = np.einsum("as,sen->aen", D, irs)             # (16 acn, 2 ears, n)

    # Normalise for a diffuse field: average binaural energy of a source over the
    # sphere (basic weighting) = 1, i.e. similar loudness to the loudspeaker decoders.
    rng = np.random.default_rng(1)
    v = rng.normal(size=(3, 4000)); v /= np.linalg.norm(v, axis=0)
    Yr = sh3_ambix(np.arctan2(v[1], v[0]), np.arcsin(v[2]))   # (16, 4000)
    out = np.einsum("aen,ak->ken", H, Yr)            # (4000, 2, n)
    energy = np.mean(np.sum(out ** 2, axis=(1, 2)))
    H /= np.sqrt(energy)

    for sr in RATES:
        fr = Fraction(sr, sr0)
        h = resample_poly(H, fr.numerator, fr.denominator, axis=2) if sr != sr0 else H.copy()
        L = 512 if sr <= 48000 else 1024
        h = h[:, :, :L] if h.shape[2] >= L else np.pad(h, ((0, 0), (0, 0), (0, L - h.shape[2])))
        fade = 32
        h[:, :, L - fade:] *= np.cos(np.linspace(0, np.pi / 2, fade)) ** 2
        data = h.reshape(32, L).astype(np.float32)   # channel = 2*acn + ear
        path = os.path.join(dst, "e4l_binaural_%d.wav" % sr)
        write_float_wav(path, data, sr)
        print("wrote", path, data.shape)


if __name__ == "__main__":
    main()
