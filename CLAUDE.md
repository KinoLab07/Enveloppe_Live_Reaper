# Envelop for REAPER – project memory

Port of **Envelop for Live** (E4L 12.2.6, Max for Live, GPLv2,
https://github.com/EnvelopSound/EnvelopForLive) to REAPER as JSFX plug-ins + Lua scripts.
Licence: GPLv2 (same as E4L). Repo: KinoLab07/enveloppe_live_reaper.

## The user and how they work
- Speaks **Spanish**: answer in Spanish. Everything in the repo (code, UI, README, PDF guide)
  is in **English**.
- Uses a **Mac** with REAPER and an **Avid Mbox Pro (3rd gen)**: outputs 1-4 quad speakers,
  output 5 the **sub** (receives everything), headphones on the Mbox headphone output via
  outputs **7-8** (binaural CUE). An **analog synth** comes in on input 1 (more inputs with
  + INPUT). The synth level tends to be hot (clipping at 0 dBFS seen in a recording).
- Musical goal: Ableton-style **live looping** of the synth, monitored on headphones before
  sending to the room, every loop / audio file spatialised in **quad** with E4L movements.
- **Everything on `main`**, no branches. Commit and push to main after each change; the user
  updates with the script **E4L - Update from GitHub** (downloads main as a zip and copies
  Effects/E4L, Data/E4L, Scripts/E4L and docs/*.pdf into REAPER's resource folder).
- After an update that changes JSFX, the user must reopen the project (the updater offers it;
  loops recorded in memory are lost) and re-record loops to test looper changes.
- The user tests on the real setup and reports by ear; ask for a rendered WAV when a sound
  problem is unclear (they can upload files). Measure, don't guess.

## Layout
- `Effects/E4L/*.jsfx` – plug-ins. Shared code: `e4l_ambix.jsfx-inc` (3rd-order ambiX
  ACN/SN3D encoding, E4L distance model, LFOs), `e4l_gfx.jsfx-inc`.
  - Panners: Mono, Stereo, Quad, Multi (16 inputs), Source. Publish hidden sliders
    60 `-Current Azimuth`, 61 `-Current Elevation`, 62 `-Current Spread` (Stereo/Quad) for the panel.
  - `E4L Master Bus` – decoders (binaural via HRTF FIR in `Data/E4L/hrtf`, stereo, quad,
    5.1, 7.1, 5.1.2, 7.1.4, ambiX), optional sub.
  - `E4L Sub Out` – on the REAPER master, sub to output 5.
  - `E4L Looper` – bar-synced looper (see below).
  - `E4L Sync Out` – on track `SYNC OUT` (no master send, out 1 → Mbox output 6): reset pulse
    for the user's analog sequencer on the bar where a loop starts recording (looper publishes
    the armed bar line in `gmem[0]`, stamp in `gmem[1]`, namespace `E4L_SYNC`), on start from
    STOP, optionally every N bars; clock on out 2; optional MIDI. "Output 1 sends = Clock" swaps
    outputs (user's sequencer has ONLY a clock input; first pulse exactly at playback start).
    Panel SYNC menu: settings / move the pulses to another output (warns if speakers use it).
    The user moved to another audio interface and patched the clock to its output 1 – check that
    the speakers are not on output 1 of that card. Untested on the real synth yet.
    Findings so far: the user's sequencer free-runs on its INTERNAL clock (keeps going with the
    cable unplugged) – it must be switched to external clock (model still unknown). The user
    reported SEND A PULSE "never works": the window button now triggers the pulse from the audio
    thread (gfx_req), shows an OUT 1 light only when a pulse really leaves, and warns when the
    plug-in's audio is not running (REAPER stopped without "Run FX when stopped").
- `Scripts/E4L/` – `e4l_lib.lua` (shared), `E4L - Live Panel.lua` (the single-window UI),
  `E4L - New live project.lua`, `E4L - Live Looper template.lua`, `E4L - Add sub to master.lua`,
  `E4L - Update from GitHub.lua`, helpers.
- `docs/build_guide.py` → `docs/E4L_REAPER_Guide.pdf` (reportlab, English). Rebuild after
  changing behaviour. `tools/render_panel_preview.py` → panel PNGs used by the guide.
- Live project tracks: `SYNTH IN`, `SYNTH IN 2`… (monitor only, to headphones), `LOOP n`
  (Looper + panner), `AUDIO n` (looped file + panner), `E4L Master` (Master Bus, Quad),
  `CUE (headphones)` (binaural → outputs 7-8), `SYNC OUT` (E4L Sync Out → output 6).

## Behaviour decided with the user (keep it)
- Loops record **ALL** inputs by default; the row button cycles ALL / IN 1 / IN 2…
- **Master** (panel header): STOP / space = stop and back to bar 1 (loops and audio files start
  from their beginning); PAUSE = freeze, PLAY continues where it was. Movements (LFOs) freeze on
  pause and continue; after STOP they start from 0 (panners use `ext_noinit`).
- **Loop row**: PLAY = from the loop's beginning on the next bar (or stop on the next bar);
  PAUSE = silent at once, PAUSE again = continue **at once from the exact point** (tape-like,
  moves off the bar grid; PLAY puts it back). User chose this explicitly.
- **Audio row**: PLAY = from the file's beginning on the next bar; PAUSE = silent at once,
  resume on the next bar from the bar where it was paused (user said this is perfect). The
  file position is moved (take D_STARTOFFS) only while the track is muted. DELETE = click twice.
- + AUDIO / drag & drop from Finder: panner follows the file's channels (mono → Mono,
  stereo → Stereo with L/R on speakers 1-2, quad → Quad on the 4 speakers, 5+ → Multi).
  Items are built with PCM_Source_CreateFromFile, never InsertMedia (it stopped the transport).
- Toolbar actions run under pcall and restart the transport if it stopped.
- The updater runs its shell job in the background (ExecProcess was blocking REAPER).

## Looper seam (hard-won, read before touching)
- Start/stop: output ramp `Start / Stop Fade` (30 ms).
- Seam: the end of the loop crossfades (`Loop Seam Crossfade`, 50 ms) into the pre-roll
  (input just before recording, kept in a ring buffer). Seam buffers XF1 (first pass) / XF2.
- Steady tones whose cycles do not fit the loop jump in phase at the seam; a crossfade then
  either dips (~-10 dB) or, with level compensation, makes a pitch blip that is bad in the bass.
  **Fix in place**: record 2048 frames past the loop, search (chunked per block, Pearson
  correlation, coarse then fine) the shift d ≤ half a cycle that aligns the end with the
  pre-roll, and read the loop as L + d frames (a few cents, spread over the loop; the rest of
  the first pass is bent so even the first seam is aligned). Only if r > 0.9 and
  |d| ≤ 0.6% of L; otherwise d = 0. Cubic interpolation. `Seam Level Compensation`
  (Auto by pitch / Off / Full) only matters when no phase match is found.

## JSFX / REAPER pitfalls
- EEL2: no scientific notation (`1e-9` fails), use 0.000000001.
- ysfx (tests) supports only sliders 1-64 in practice → published sliders at 60-62.
- `slider_automate(2^(n-1))` / `sliderchange()` to publish; hidden sliders start with `-`.
- Without `ext_noinit = 1`, REAPER re-runs @init every time playback starts.
- `play_state`: 0 stopped, 1 playing, 2 paused, 5 recording, 6 rec-paused.
- Azimuth in E4L is clockwise (+90 = right); ambiX is counter-clockwise.

## Tests (run them before every push)
- `bash tests/run_tests.sh` – builds ysfx + `tests/runfx.cpp` (once, into tests/build) and
  runs `tests/test_e4l.py` (JSFX). `fx2=… out2=…` runs a second plug-in in the same process
  (shared gmem, sliders prefixed `B.`). runfx events: `name@sample=value` (slider),
  `ps@sample=state` (play state), `beat@sample=qn` (move transport); events apply at the start
  of the 256-sample block containing that sample.
- `python3 tests/test_scripts.py` – Lua scripts against the REAPER mock (`tests/mock_reaper.lua`,
  run with lupa; parameter names parsed from the JSFX by `tests/jsfx_params.py`).
- Both must print `0 failure(s)`.

## Commits
End messages with the attribution lines given by the environment. Push with
`git push -u origin main`.
