# Enveloppe Live Reaper

A port of **[Envelop for Live (E4L)](https://github.com/EnvelopSound/EnvelopForLive)**, Envelop's
spatial audio (ambisonics) toolkit for Ableton Live, to **REAPER**, plus a live looping set-up
for performing with a synth in **quadraphony**.

E4L's Max for Live devices (`.amxd`) only run inside Ableton Live. Here they are rewritten as
**JSFX**, REAPER's native plug-in format: nothing to compile, they run on macOS, Windows and
Linux, and every parameter can be automated with REAPER envelopes.

On top of the port there is a **live performance set-up**: an Ableton-style bar-synced looper,
a one-window **Live Panel** to play and move every loop, a subwoofer output, binaural
headphone monitoring and a one-click updater.

![E4L Live Panel](docs/live_panel_preview.png)

> User guide (PDF): [`docs/E4L_REAPER_Guide.pdf`](docs/E4L_REAPER_Guide.pdf).

---

## Contents

- [What is included](#what-is-included)
- [How it works](#how-it-works)
- [Installation](#installation)
- [Quick start: a live project](#quick-start-a-live-project)
- [The Live Panel](#the-live-panel)
- [Movement (the E4L LFOs)](#movement-the-e4l-lfos)
- [Plug-in reference](#plug-in-reference)
- [Scripts](#scripts)
- [Conventions](#conventions)
- [Differences from E4L](#differences-from-e4l)
- [Repository layout and tests](#repository-layout-and-tests)
- [License and credits](#license-and-credits)

---

## What is included

### Plug-ins (`Effects/E4L`)

| Plug-in | Port of | What it does |
|---|---|---|
| **E4L Source Panner** | E4L Source Panner | Mono/stereo source, polar or XYZ position, spread, distance |
| **E4L Mono Panner** | E4L Mono Panner | One point, with azimuth and elevation LFOs |
| **E4L Stereo Panner** | E4L Stereo Panner | Left/right points, with azimuth, elevation and spread LFOs |
| **E4L Quad Panner** | E4L Quad Panner | Four inputs, LR / X / W spread modes, four LFOs |
| **E4L Multi-Panner** | E4L Multi-Panner | Up to 16 inputs with their own offsets, plus azimuth/elevation and scale LFOs |
| **E4L Master Bus** | E4L Master Bus (decoders) | Binaural (3rd order, IRCAM HRIRs), stereo, quad, octo, 5.1, 7.1, 5.1.2, 7.1.4, ambiX pass-through, optional sub output |
| **E4L Looper** | *(new)* | Bar-synced live looper: record / play / overdub / clear, quantised to the bar |
| **E4L Sub Out** | *(new)* | On REAPER's master: sends the sum of everything to a subwoofer output |

All of them work in **3rd order ambisonics, 16 channels, ambiX (ACN / SN3D)**, the same format
as E4L and compatible with the IEM Plug-in Suite, SPARTA and others.

### Scripts (`Scripts/E4L`)

| Script | What it does |
|---|---|
| **E4L - New live project** | New project + live template + Live Panel, in one click |
| **E4L - Live Looper template** | Builds the live set-up (synth input, loops, quad master, headphone cue, sub) |
| **E4L - Live Panel** | One dockable window to play everything (see below) |
| **E4L - Update from GitHub** | Downloads the latest version from this repository and installs it |
| E4L - Setup session | Spatialises the selected tracks (no looper): 16 channels, panner, send to the master bus |
| E4L - Add sub to master | Adds the subwoofer output to an existing project |
| E4L - Loop REC / PLAY-STOP (selected tracks), E4L - Loops STOP all | Actions for keyboard shortcuts or MIDI |

### Not ported (yet)

Spinner, HOA Transform, Multi-Delay, Spatial Slicer, Brownian Delay, Delay Boids, AuraVerb,
B-Format convolution reverb, the LED / OSC devices. Things REAPER already does (routing between
tracks, recording, export, metering) are done with REAPER itself.

---

## How it works

```
Analog synth ─► SYNTH IN ──────────────────────────────────────► headphones (outputs 7-8)
                   │                                                    ▲
                   ▼                                                    │
              LOOP 1..n  (E4L Looper + E4L Panner) ─┐                  │
              AUDIO 1..n (looped file + E4L Panner) ─┴─► E4L Master ───┴── CUE (binaural)
                                                         (Master Bus = Quad)
                                                              │
                                                              ▼
                                                        REAPER master ─► outputs 1-4 (speakers)
                                                        + E4L Sub Out ─► output 5 (subwoofer)
```

- Every source track carries an **E4L panner** that encodes it into 16 ambisonics channels
  (where the sound comes from). All of them are sent to the **E4L Master** track.
- **E4L Master Bus** decodes the ambisonics mix to the speakers. Changing one option (quad,
  binaural, 5.1, 7.1.4…) changes the whole output; panners and automation stay the same.
- **CUE** decodes the same mix to binaural for the headphones, so you hear the loops in 3D while
  you play. The synth input goes to the headphones only, never to the speakers, until you record it.
- **E4L Sub Out** on REAPER's master sends everything that reaches the master to the sub.

Quad speaker order (as in E4L, clockwise): **1** front-left (−45°), **2** front-right (+45°),
**3** rear-right (+135°), **4** rear-left (−135°).

---

## Installation

1. Download this repository (**Code › Download ZIP**) and unzip it.
2. In REAPER open the resource folder: action list (`?`), search **resource path**, run
   *Show REAPER resource path in explorer/finder*
   (macOS: `~/Library/Application Support/REAPER`, Windows: `%APPDATA%\REAPER`).
3. Copy the folders **`Effects`**, **`Data`** and **`Scripts`** into it, **merging** with the
   existing folders:
   - `Effects/E4L` – the plug-ins
   - `Data/E4L` – HRTF filters for the binaural decoder
   - `Scripts/E4L` – the scripts
4. In REAPER's FX browser press **F5** (Mac laptops: **fn + F5**). The plug-ins show up as `JS: E4L …`.
5. Load the scripts once: *Actions › Show action list › New action › Load ReaScript…*
   (at least **E4L - New live project**, **E4L - Live Panel** and **E4L - Update from GitHub**).

### Updating

Run **E4L - Update from GitHub**. It downloads the latest `main` (curl + unzip on macOS/Linux,
PowerShell on Windows), replaces only `Effects/E4L`, `Data/E4L` and `Scripts/E4L`, tells you when
you are already up to date, restarts the Live Panel and offers to reopen the project so the new
plug-ins are loaded.

---

## Quick start: a live project

1. Set up the audio interface (*Settings › Audio › Device*) with outputs 1-4 for the speakers.
2. Run **E4L - New live project**. In the dialog:

   | Field | Default | Notes |
   |---|---|---|
   | Loop tracks to add | 8 | |
   | Synth input (first channel) | 1 | interface input of the synth |
   | Synth input: 1 mono 2 stereo | 1 | |
   | Headphones output (first channel) | 7 | outputs 7-8; set the interface's headphone source to them |
   | Loop panner: 1 Mono 2 Stereo | 1 | |
   | Sub output (0 = none) | 5 | |

   It creates `SYNTH IN`, `LOOP 1-8`, `E4L Master` (quad) and `CUE (headphones)`, configures the
   master (outputs 1-2, 3-4 and the sub on 5), measures the recording latency compensation and
   opens the Live Panel.
3. Set the **tempo and time signature** (double-click them in the transport bar).
4. Press **play** (space bar). The running project is the "global loop": every loop follows its bars.
5. Play the synth (headphones only), then press **REC** on a loop: it waits for the next bar,
   records the chosen number of bars and starts playing it, spatialised, on the speakers.

**Headphones on an Avid Mbox Pro (3rd gen):** each headphone output has its own mix. In the Mbox
control panel, set *Headphones A* to the computer's outputs 7-8.

**Note:** recorded loops live in the plug-in's memory. They are **not saved** with the project
(set-ups, positions and movements are). Render the project to keep a performance.

---

## The Live Panel

One window, dockable in REAPER (right-click the top area), to play the whole set-up without
opening any plug-in.

- **Header:** big bar . beat counter, beats of the bar, a 4-bar phrase indicator, **IN** level
  meters for every interface input, tempo, play/stop, stop all loops.
- **Toolbar:**
  - **+ LOOP** – another loop track.
  - **+ AUDIO** – a pre-recorded file on a new `AUDIO n` track, looped from bar 1. If it is close
    to a whole number of bars it is fitted to the tempo (pitch preserved). It starts muted and
    enters on the next bar with **PLAY**. Files can also be dragged from the Finder onto the
    panel. The panner follows the file: mono → Mono Panner, stereo → Stereo Panner (L/R on
    speakers 1-2), quad → Quad Panner (each channel on its speaker), 5+ channels →
    Multi-Panner. **DELETE** (click twice) removes the track.
  - **+ INPUT** – another interface input (`SYNTH IN 2`…). Loops record **ALL** inputs by
    default; each loop's input button switches between **ALL**, **IN 1**, **IN 2**…
  - **SAVE / LOAD TEMPLATE** – save / load the set-up (tracks, inputs, audio files,
    positions, movements, tempo) in `E4L_Templates` inside the resource folder, to move from one
    piece to the next.
  - **NEW TEMPLATE** – a new live project from scratch.
- **One row per loop:** state (empty, waiting, recording, playing, stopped), length (1-32 bars),
  input (**ALL** / **IN n**), **REC**, **PLAY**, **OVERDUB**, **CLEAR**, **MOVEMENT** (movement
  editor) and the position inside the loop. Record, play and stop are
  quantised to the next bar.
- **Room view**, seen from above: the four speakers and one dot per loop, moving live with its
  animations. Drag a dot to move that loop.
- **Keys:** space = play/stop, 1-9 = record on loop 1-9, 0 = stop all loops, Esc = close the editor.

### Movement editor

![Movement editor](docs/live_panel_editor.png)

The **MOVEMENT** button of each loop opens all its spatial controls in the same window:

- **E4L effect menu:** one point (Mono Panner), two points (Stereo Panner) or fixed position
  (Source Panner). Switching keeps the position and animations.
- **Position:** direction ("45° right"), height and distance (shown as dB of attenuation).
- **Automatic rotation:** full turn or swing, free speed ("1 turn every 10 s") or synced to the
  tempo ("1 turn every 4 bars"), clockwise / counter-clockwise, swing depth.
- **Up and down:** the elevation LFO (barely audible in quad: there are no speakers above).
- **Stereo width:** spread and "breathing" (spread LFO).
- **Quick movements:** still, slow turn, 4-bar turn, whirl, front swing, right swing.

---

## Movement (the E4L LFOs)

The Mono, Stereo, Quad and Multi panners keep E4L's LFOs and parameters:

| Parameter | Meaning |
|---|---|
| Azimuth LFO Mode | *Cycle*: full 360° turns · *Sin*: swing ± *Depth* around *Azimuth* |
| Elevation LFO Polarity | *Unipolar*: 0 to *Depth* upwards · *Bipolar*: ± *Depth* |
| Time Mode | *Freq*: Hz × *Rate* (negative rate = other direction) · *Sync*: tempo synced |
| Sync (bars) | 1/4, 1/2, 1, 2, 3, 4, 6, 8, 16, 32, 64 bars per cycle |
| Direction | Clockwise / Counter (Sync mode) |
| Spread LFOs | (Stereo, Quad) open and close the image |
| Scale LFOs | (Multi-Panner) expand and contract the whole group; depth −1 to 1 |

In *Sync* mode, while REAPER plays, the LFO phase is locked to the project position (like E4L's
`phasor~ @lock 1`): the movement is identical on every playback and in the render. Any parameter
can also be automated with envelopes or REAPER's parameter modulation.

---

## Plug-in reference

**E4L Looper:** Length (1-32 bars), Record, Play, Overdub, Clear, Loop Volume, Input Thru,
Recording Latency Compensation (set automatically from the interface latency), Loop Seam
Crossfade (default 50 ms; the end of the loop crossfades into the sound that preceded the
recording, so steady tones loop without a click) and Start / Stop Fade (default 30 ms). REAPER
must be playing. After STOP, PLAY starts the loops from their beginning on the current bar; after
PAUSE they continue where they were. In the Live Panel, STOP (or the space bar) also goes back to
bar 1 so audio files restart too; PAUSE keeps the position. Maximum loop length about 5 minutes at 48 kHz. Hidden read-only parameters publish its
state for the Live Panel.

**E4L Master Bus:** Decoder, Order Weighting (*In-phase (E4L)* by default, recommended for quad;
*max-rE*; *Basic*), Ambisonics Order, input/output gain, optional Sub Output channel, level and
low-pass. Binaural uses the 25 IRCAM Listen HRIRs shipped with E4L, folded into 16 FIR filters
(`tools/make_binaural_filters.py`); latency 512 samples (1024 at 88.2/96 kHz), compensated by REAPER.

**E4L Sub Out** (on the master): sub output channel, which master channels to sum (1-4 quad, 1-2,
1-6), level, optional 24 dB/oct low-pass, mute.

**Quad Panner spread modes** (as in E4L): *LR* square, *X* rear pair crossed, *W* fan
(E4L's non-linear W1/W2 curves).

---

## Scripts

All scripts are Lua ReaScripts; `e4l_lib.lua` and `e4l_looper_common.lua` are shared code, not
actions. The live template, the panel and the updater keep their settings in the project
(`E4L` project ext-state) and in REAPER's ext-state (`E4L_LivePanel`, `E4L_Update`).

---

## Conventions

- **Azimuth** (as in E4L): 0 = front, +90 = right, −90 = left, ±180 = back (clockwise).
- **Elevation:** 0 = ear level, +90 = above.
- **Distance:** `distance = Radius × Range`. Inside 1 unit the source becomes omnidirectional;
  beyond it, −1.5 dB per unit. With E4L's defaults (Radius 1, Range 10) a source is 13.5 dB down;
  use Radius = 1/Range (0.1) for full level (the live template does).
- **XYZ** (Source Panner): X = right, Y = front, Z = up.
- **Stereo spread** (as in E4L): left = azimuth − spread and elevation + elevation spread; right
  the opposite.

---

## Differences from E4L

- E4L uses the ICST Ambisonics externals, whose source is not available. The same maths is
  implemented (SN3D/ACN encoding, sampling decoders with order weighting), but decoder levels are
  energy-normalised and may differ slightly from E4L.
- LFOs are computed every 32 samples with linear interpolation (E4L: every 10 ms).
- OSC and Envelop's LED control are not included.

---

## Repository layout and tests

```
Effects/E4L/    JSFX plug-ins (+ e4l_ambix.jsfx-inc, e4l_gfx.jsfx-inc)
Data/E4L/hrtf/  binaural filters (44.1, 48, 88.2, 96 kHz)
Scripts/E4L/    ReaScripts
docs/           user guide (PDF), its generator, panel previews
tools/          binaural filter generator, panel preview renderer
tests/          automated tests
```

`tests/run_tests.sh` builds [ysfx](https://github.com/jpcima/ysfx) (an open-source JSFX runtime)
and tests the plug-ins without REAPER: encoding, LFOs, tempo sync, decoders, sub output, and the
looper's timing (bar quantisation, latency compensation, overdub, re-record).
`tests/test_scripts.py` runs the Lua scripts (template, panel, toolbar, movement editor, updater
hand-off) against a mocked REAPER API (requires `pip install lupa`).

---

## License and credits

**GNU GPL v2 or later** (see `LICENSE`), the same license as Envelop for Live, since this is a
derivative work of E4L.

- Envelop for Live © Envelop (envelop.us), Mark C. Slee and contributors. If E4L is useful to you,
  consider [supporting Envelop](https://envelop.us/memberships).
- HRTFs: IRCAM Listen database (subject 1052), as shipped with E4L.
- Encoding and decoding modelled on the ICST Ambisonics tools (ZHdK).
