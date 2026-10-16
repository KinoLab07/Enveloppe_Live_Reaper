#!/usr/bin/env python3
"""Runs the REAPER Lua scripts against a mocked REAPER API (tests/mock_reaper.lua).
Requires: pip install lupa"""
import os
import sys

import lupa
abs = abs

from jsfx_params import lua_fxp

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "Scripts", "E4L")
failures = 0


def check(name, cond):
    global failures
    print(("ok   " if cond else "FAIL ") + name)
    failures += 0 if cond else 1


FXP = lua_fxp(os.path.join(HERE, "..", "Effects", "E4L"))
lua = lupa.LuaRuntime()
lua.execute(FXP)
lua.execute(open(os.path.join(HERE, "mock_reaper.lua")).read())
template_path = os.path.join(SCRIPTS, "E4L - Live Looper template.lua").replace("\\", "/")
template = "dofile([[%s]])" % template_path
lua.execute(template)

T = lua.eval("MOCK.T")
tracks = {T[i].name: T[i] for i in range(1, len(T) + 1)}
names = [T[i].name for i in range(1, len(T) + 1)]
check("template creates SYNTH IN, 8 loops, E4L Master and CUE",
      names == ["SYNTH IN"] + ["LOOP %d" % i for i in range(1, 9)] + ["E4L Master", "CUE (headphones)"])
s = tracks["SYNTH IN"]
check("SYNTH IN: armed, monitored, never recorded, no master send",
      s.vals.I_RECARM == 1 and s.vals.I_RECMON == 1 and s.vals.I_RECMODE == 2 and s.vals.B_MAINSEND == 0)
check("SYNTH IN: to headphones (outputs 7-8) and to every loop",
      s.sends[1][1].vals.I_DSTCHAN == 6 and len(s.sends[0]) == 8)
l1 = tracks["LOOP 1"]
check("LOOP: 16 ch, no master send, looper + panner, 16-ch send to E4L Master",
      l1.vals.I_NCHAN == 16 and l1.vals.B_MAINSEND == 0 and l1.fx[1].file == "E4L Looper.jsfx"
      and l1.sends[0][1].dst.name == "E4L Master" and l1.sends[0][1].vals.I_SRCCHAN == 8 << 10)
check("E4L Master decodes to Quad (its own sub off), CUE to binaural",
      tracks["E4L Master"].fx[1].p["Decoder"] == 2
      and tracks["E4L Master"].fx[1].p["Sub Output (channel, 0 = off)"] == 0
      and tracks["CUE (headphones)"].fx[1].p["Decoder"] == 0)
m = lua.eval("MOCK.master")
hw = sorted((int(m.sends[1][i].vals.I_SRCCHAN), int(m.sends[1][i].vals.I_DSTCHAN)) for i in range(1, len(m.sends[1]) + 1))
check("REAPER master: 6 channels, outputs 1-2, 3-4 and mono 5 (sub)",
      m.vals.I_NCHAN == 6 and hw == [(0, 0), (2, 2), (4 | 1024, 4 | 1024)])
check("REAPER master: E4L Sub Out on output 5 (every track feeds the sub)",
      len(m.fx) == 1 and m.fx[1].file == "E4L Sub Out.jsfx" and m.fx[1].p["Sub Output (channel)"] == 5)
lua.execute(template)
T = lua.eval("MOCK.T")
m = lua.eval("MOCK.master")
check("running it again only adds loops (4 more), no second sub plugin or output",
      len(T) == 15 and T[13].name == "LOOP 12" and len(m.fx) == 1 and len(m.sends[1]) == 3)

# a loop from an older version (no stored input choice, SYNTH IN 2 muted) becomes ALL in the panel
lua3 = lupa.LuaRuntime()
lua3.execute(FXP)
lua3.execute(open(os.path.join(HERE, "mock_reaper.lua")).read())
lua3.execute("dofile([[%s]])" % template_path)
lua3.execute("""
local E = dofile([[%s]])
local si2 = E.add_input(3, true, 7)
for i = 0, reaper.GetTrackNumSends(si2, 0) - 1 do reaper.SetTrackSendInfo_Value(si2, 0, i, "B_MUTE", 1) end
for _, lp in ipairs(E.tracks_matching("^LOOP %%d+$")) do lp.ext["P_EXT:E4L_in"] = nil end
""" % os.path.join(SCRIPTS, "e4l_lib.lua").replace("\\", "/"))
lua3.execute("dofile([[%s]])" % os.path.join(SCRIPTS, "E4L - Live Panel.lua").replace("\\", "/"))
check("panel: loops from older versions switch to ALL (the new input is recorded)",
      lua3.eval("MOCK.T[2].name") == "SYNTH IN 2" and lua3.eval("MOCK.T[2].sends[0][1].vals.B_MUTE") == 0)

# "Add sub to master" on an older project whose decoder still feeds the sub itself
lua2 = lupa.LuaRuntime()
lua2.execute(FXP)
lua2.execute(open(os.path.join(HERE, "mock_reaper.lua")).read())
lua2.execute("""
reaper.InsertTrackAtIndex(0)
local tr = reaper.GetTrack(0, 0)
local fx = reaper.TrackFX_AddByName(tr, "JS:E4L/E4L Master Bus.jsfx")
reaper.TrackFX_SetParam(tr, fx, 5, 5)
""")
lua2.execute("dofile([[%s]])" % os.path.join(SCRIPTS, "E4L - Add sub to master.lua").replace("\\", "/"))
m2 = lua2.eval("MOCK.master"); t2 = lua2.eval("MOCK.T")
check("Add sub to master: works on an existing project and turns the decoder's sub off",
      m2.fx[1].file == "E4L Sub Out.jsfx" and m2.vals.I_NCHAN == 6
      and t2[1].fx[1].p["Sub Output (channel, 0 = off)"] == 0)

# --- Live Panel: runs on the template project, buttons and room view drive the plugins
lua.execute("dofile([[%s]])" % os.path.join(SCRIPTS, "E4L - Live Panel.lua").replace("\\", "/"))
frame = lua.eval("function() local f = MOCK_DEFER; MOCK_DEFER = nil; f() end")
param = lua.eval("""function(ti, fi, name)
  local f = MOCK.T[ti].fx[fi]
  return f.p[name] or 0 end""")
setp = lua.eval("""function(ti, fi, name, v) MOCK.T[ti].fx[fi].p[name] = v end""")
fxfile = lua.eval("function(ti, fi) local f = MOCK.T[ti].fx[fi]; return f and f.file or '' end")
mouse = lua.eval("function(x, y, cap) gfx.mouse_x = x; gfx.mouse_y = y; gfx.mouse_cap = cap end")


def click(x, y):
    mouse(x, y, 1); frame(); mouse(x, y, 0); frame()


frame()
W, H, TOP = 1240, 560, 116


def rowh(n):
    return max(26, min(40, (H - TOP - 6) // n))


def row_y(i, n):          # top of row i (1-based) with n rows
    return TOP + (i - 1) * rowh(n) + 15


n = 12
BX = 8 + 344
click(BX + 10, row_y(1, n))
check("panel: REC arms the looper of LOOP 1", param(2, 1, "Record") == 1)
click(BX + 70 + 10, row_y(2, n))
check("panel: PLAY of row 2 toggles LOOP 2", param(3, 1, "Play") == 1)
click(8 + 212 + 10, row_y(1, n))
check("panel: length button cycles to the next length", param(2, 1, "Length (bars)") == 1)
lua.execute("MOCK_KEY = 32"); frame()
check("panel: space bar = STOP and back to bar 1 (loops and audio restart from their beginning)",
      lua.eval("MOCK_PLAY") == 0 and lua.eval("MOCK_CURSOR") == 0)
lua.execute("MOCK_CURSOR = 12")
lua.execute("MOCK_KEY = 32"); frame()
check("panel: space bar again = PLAY", lua.eval("MOCK_PLAY") == 1)
lua.execute("MOCK_KEY = 50"); frame()
check("panel: key 2 = record on loop 2", param(3, 1, "Record") == 1)

import math
room = min(H - TOP - 6, int(W * 0.32)); rx, ry = W - room - 8, TOP
cx, cy, R = rx + room / 2, ry + room / 2, room / 2 - 22
setp(2, 2, "-Current Azimuth", -45)
dx, dy = cx + math.sin(math.radians(-45)) * R * 0.78, cy - math.cos(math.radians(-45)) * R * 0.78
mouse(dx, dy, 1); frame(); mouse(cx + 100, cy, 1); frame(); mouse(cx + 100, cy, 0); frame()
check("panel: dragging loop 1 in the room sets its azimuth (+90 = right)", param(2, 2, "Azimuth") == 90)

# movement editor of loop 1
click(BX + 308 + 10, row_y(1, n))
lw = W - room - 24
colw = (lw - 40) // 2
c1, c2 = 8 + 10, 8 + 30 + colw
y_rot = TOP + 84 + 42 + 40 + 40 + 30          # top of "AUTOMATIC ROTATION"
click(c1 + 20, y_rot + 26 + 10)                # ACTIVADO
check("editor: AUTOMATIC ROTATION turns the azimuth LFO on", param(2, 2, "Azimuth LFO On/Off") == 1)
click(c1 + colw - 20, y_rot + 26 + 30 + 10)    # "Al tempo"
check("editor: Tempo sync = LFO synced to the bars", param(2, 2, "Azimuth LFO Time Mode") == 1)
y_pres = TOP + 84 + 26 + 46 + 40 + 26 + 26     # Mono panner: no stereo width section
bw = (colw - 6) / 3
click(c2 + 2 * (bw + 3) + 10, y_pres + 28 + 10)
check("editor: preset Right swing sets azimuth 90, swing ±45",
      param(2, 2, "Azimuth") == 90 and param(2, 2, "Azimuth LFO Mode") == 1 and param(2, 2, "Azimuth LFO Depth") == 45)
lua.execute("function gfx.showmenu() return 2 end")
click(8 + 100 + 20, TOP + 42 + 10)
lua.execute("function gfx.showmenu() return 0 end")
check("editor: the effect menu replaces Mono Panner by Stereo Panner, keeping the settings",
      fxfile(2, 2) == "E4L Stereo Panner.jsfx" and param(2, 2, "Azimuth") == 90 and param(2, 2, "Azimuth LFO Depth") == 45)
lua.execute("MOCK_KEY = 27"); frame()          # Esc closes the editor

# --- toolbar
names = lua.eval("function() local t = {} for i, tr in ipairs(MOCK.T) do t[i] = tr.name end return t end")
name_list = lambda: list(names().values())
TB = 80 + 10
xs, x = [], 8
for w in (80, 84, 84, 140, 140, 130):
    xs.append(x + 10); x += w + 6
click(xs[0], TB)
check("toolbar: + LOOP adds LOOP 13 before E4L Master",
      "LOOP 13" in name_list() and name_list().index("LOOP 13") < name_list().index("E4L Master"))
lua.execute("function reaper.GetUserInputs() return true, '3,2' end")
click(xs[2], TB)
tr_index = lambda name: name_list().index(name) + 1
si2 = tr_index("SYNTH IN 2")
nsend = lua.eval("function(i) return #MOCK.T[i].sends[0] end")
smute = lua.eval("function(i, k) return MOCK.T[i].sends[0][k].vals.B_MUTE or 0 end")
recin = lua.eval("function(i) return MOCK.T[i].vals.I_RECINPUT end")
check("toolbar: + INPUT adds SYNTH IN 2 (input 3-4 stereo), feeding the 13 loops (they record ALL inputs)",
      name_list()[1] == "SYNTH IN 2" and recin(si2) == 1024 + 2 and nsend(si2) == 13 and smute(si2, 1) == 0)
n = 13
si1 = tr_index("SYNTH IN")
click(8 + 290 + 10, row_y(1, n))                 # input button of loop 1: ALL -> IN 1
check("panel: input button ALL -> IN 1 mutes SYNTH IN 2 for LOOP 1",
      smute(si2, 1) == 1 and smute(si1, 1) == 0)
click(8 + 290 + 10, row_y(1, n))                 # IN 1 -> IN 2
check("panel: input button IN 1 -> IN 2 records only SYNTH IN 2",
      smute(si2, 1) == 0 and smute(si1, 1) == 1)
click(8 + 290 + 10, row_y(1, n))                 # IN 2 -> ALL
check("panel: input button IN 2 -> ALL records both inputs",
      smute(si2, 1) == 0 and smute(si1, 1) == 0)
click(xs[1], TB)                                 # + AUDIO (mock file dialog -> /sounds/pad.wav, 7.9 s)
a1 = tr_index("AUDIO 1")
item = lua.eval("function(i) local it = MOCK.T[i].items[1]; return it.vals.D_POSITION, it.vals.B_LOOPSRC, it.take.vals.D_PLAYRATE, it.take.vals.B_PPITCH, MOCK.T[i].vals.B_MUTE end")
pos, loopsrc, rate, ppitch, muted = item(a1)
check("toolbar: + AUDIO adds AUDIO 1: looped item at bar 1, 7.9 s fitted to 4 bars (pitch kept), muted",
      pos == 0 and loopsrc == 1 and abs(rate - 7.9 / 8) < 1e-9 and ppitch == 1 and muted == 1)
n = 14
click(BX + 70 + 10, row_y(14, n))                # PLAY on the audio row (quantised)
check("audio row: PLAY waits for the next bar", lua.eval("MOCK.T[%d].vals.B_MUTE" % a1) == 1)
lua.execute("MOCK_POS = MOCK_POS + 2.0"); frame()   # next bar (2 s per bar at 120 BPM)
check("audio row: ... and unmutes on the next bar", lua.eval("MOCK.T[%d].vals.B_MUTE" % a1) == 0)
# loop PAUSE button
click(BX + 112 + 10, row_y(1, n))
check("loop row: PAUSE presses the looper's Pause", param(tr_index("LOOP 1"), 1, "Pause") == 1)
click(BX + 112 + 10, row_y(1, n))
check("loop row: PAUSE again releases it (the loop continues on the next bar)", param(tr_index("LOOP 1"), 1, "Pause") == 0)
# audio PAUSE / RESUME (AUDIO 1: 4 bars = 8 s at 120 BPM, playing)
lua.execute("E4LT = dofile([[%s]])" % os.path.join(SCRIPTS, "e4l_lib.lua").replace("\\", "/"))
apos = lua.eval("function(i, t) return E4LT.audio_pos(MOCK.T[i], t) end")
lua.execute("MOCK_POS = 15.0"); frame()          # the file started at 12 s (PLAY above): 3.0 s in
click(BX + 112 + 10, row_y(14, n))                # PAUSE there (its bar 2)
check("audio row: PAUSE silences it at once and remembers where it was",
      lua.eval("MOCK.T[%d].vals.B_MUTE" % a1) == 1 and abs(float(lua.eval("MOCK.T[%d].ext['P_EXT:E4L_pause']" % a1)) - 3.0) < 1e-6)
lua.execute("MOCK_POS = 15.5"); frame()
click(BX + 112 + 10, row_y(14, n))                # PAUSE again: continue on the next bar (16 s)
check("audio row: PAUSE again -> on the next bar (16 s) the file continues from its bar 2 (2.0 s)",
      abs(apos(a1, 16.0) - 2.0) < 1e-6 and lua.eval("MOCK.T[%d].vals.B_MUTE" % a1) == 1)
lua.execute("MOCK_POS = 16.1"); frame()
check("audio row: ... it comes back in on that bar", lua.eval("MOCK.T[%d].vals.B_MUTE" % a1) == 0
      and lua.eval("MOCK.T[%d].ext['P_EXT:E4L_pause']" % a1) == "")
# audio PLAY: stop on the next bar, then PLAY again starts the file from its beginning
click(BX + 56 + 10, row_y(14, n))
lua.execute("MOCK_POS = 18.1"); frame()
lua.execute("MOCK_POS = 19.0"); frame()
click(BX + 56 + 10, row_y(14, n))
check("audio row: PLAY after a stop starts the file from its beginning on the next bar (20 s)",
      lua.eval("MOCK.T[%d].vals.B_MUTE" % a1) == 1 and abs(apos(a1, 20.0)) < 1e-6)
lua.execute("MOCK_POS = 20.1"); frame()
check("audio row: ... and comes in on that bar", lua.eval("MOCK.T[%d].vals.B_MUTE" % a1) == 0)
lua.execute("MOCK_KEY = 32"); frame()
check("master STOP: back to bar 1 with every audio file at its beginning",
      lua.eval("MOCK_PLAY") == 0 and abs(apos(a1, 0.0)) < 1e-6)
lua.execute("MOCK_KEY = 32"); frame()
check("+ AUDIO builds the item directly (no InsertMedia, which can stop the transport)",
      lua.eval("MOCK_INSERTMEDIA_USED") is False and lua.eval("MOCK.T[%d].items[1].file" % a1) == "/sounds/pad.wav")
# something stops the transport while the file dialog is open -> the panel restarts it
lua.execute("MOCK_PLAYBTN = 0; function reaper.GetUserFileNameForRead() MOCK_PLAY = 0; return true, '/sounds/b.wav' end")
click(xs[1], TB)
check("+ AUDIO: if the transport stopped meanwhile, it is restarted (loops keep sounding)",
      lua.eval("MOCK_PLAYBTN") == 1 and lua.eval("MOCK_PLAY") == 1 and "AUDIO 2" in name_list())
lua.execute("MOCK_PLAYBTN = 0; MOCK_TEXT = {}; function reaper.GetUserFileNameForRead() return true, '/sounds/broken.wav' end")
click(xs[1], TB)
check("+ AUDIO: an unreadable file is reported, transport untouched, panel still running",
      "could not read" in lua.eval("status_text_for_test()") and lua.eval("MOCK_PLAYBTN") == 0
      and lua.eval("MOCK_DEFER") is not None)
lua.execute("""MOCK_DROP = {'/sounds/drums.aif', '/docs/notes.txt'}
function gfx.getdropfile(i) if i < 0 then MOCK_DROP = {} return 0 end
  if MOCK_DROP[i + 1] then return 1, MOCK_DROP[i + 1] end return 0 end
MOCK_TEXT = {}""")
frame(); frame()
check("drag & drop: an audio file dropped on the panel becomes an AUDIO track (no file window)",
      "AUDIO 3" in name_list() and "AUDIO 4" not in name_list() and lua.eval("#MOCK_DROP") == 0
      and "Not an audio file: notes.txt" in lua.eval("status_text_for_test()"))
lua.execute("gfx.getdropfile = nil")
lua.execute("MOCK_TEXT = {}; function reaper.GetUserFileNameForRead() error('boom') end")
click(xs[1], TB)
check("toolbar: an error inside an action does not kill the panel",
      "boom" in lua.eval("status_text_for_test()") and lua.eval("MOCK_DEFER") is not None)

# the panner follows the channels of the file, placed on the speakers
a1 = tr_index("AUDIO 1")
check("stereo file -> Stereo Panner, L/R on the front speakers (az 0, spread 45)",
      fxfile(a1, 1) == "E4L Stereo Panner.jsfx" and param(a1, 1, "Azimuth") == 0 and param(a1, 1, "Azimuth Spread") == 45)
lua.execute("""MOCK_DROP = {'/s/pad_quad.wav', '/s/voice_mono.wav', '/s/room_8ch.wav'}
function gfx.getdropfile(i) if i < 0 then MOCK_DROP = {} return 0 end
  if MOCK_DROP[i + 1] then return 1, MOCK_DROP[i + 1] end return 0 end""")
frame(); frame()
lua.execute("gfx.getdropfile = nil")
aq, am, a8 = tr_index("AUDIO 4"), tr_index("AUDIO 5"), tr_index("AUDIO 6")
check("quad file -> Quad Panner, each channel on its speaker (spread 90, LR mode)",
      fxfile(aq, 1) == "E4L Quad Panner.jsfx" and param(aq, 1, "Azimuth") == 0
      and param(aq, 1, "Azimuth Spread") == 90 and param(aq, 1, "Azimuth Spread Mode") == 0)
check("mono file -> Mono Panner", fxfile(am, 1) == "E4L Mono Panner.jsfx")
check("8-channel file -> Multi-Panner, 8 inputs in a circle, the others off",
      fxfile(a8, 1) == "E4L Multi-Panner.jsfx" and param(a8, 1, "Input 2 Azimuth") == 45
      and param(a8, 1, "Input 8 Active") == 1 and param(a8, 1, "Input 9 Active") == 0)

# DELETE on an audio row: first click asks SURE?, the second deletes the track
rows = [x for x in name_list() if x.startswith("LOOP ") or x.startswith("AUDIO ")]
nrows = len(rows)
i5 = rows.index("AUDIO 5") + 1
click(BX + 176 + 10, row_y(i5, nrows))
check("audio row: first click on DELETE only asks (SURE?)", "AUDIO 5" in name_list())
click(BX + 176 + 10, row_y(i5, nrows))
check("audio row: second click on DELETE deletes the track",
      "AUDIO 5" not in name_list() and "AUDIO 4" in name_list() and "AUDIO 6" in name_list())
frame()
lua.execute("function reaper.GetUserInputs() return true, 'Piece 1' end")
click(xs[3], TB)
check("toolbar: SAVE TEMPLATE saves E4L_Templates/Piece 1.RPP",
      list(lua.eval("MOCK_SAVED").values()) == ["/res/E4L_Templates/Piece 1.RPP"])
lua.execute("MOCK_FILES = {'Piece 1.RPP', 'Piece 2.RPP'}; function gfx.showmenu() return 2 end")
click(xs[4], TB)
lua.execute("function gfx.showmenu() return 0 end")
check("toolbar: LOAD TEMPLATE opens the chosen song",
      list(lua.eval("MOCK_OPENED").values()) == ["/res/E4L_Templates/Piece 2.RPP"])
lua.execute("MOCK_INPUT = nil; function reaper.GetUserInputs(t, n, cap, def) return true, def end")
click(xs[5], TB)
check("toolbar: NEW TEMPLATE = new project with the live template (8 loops), panel not duplicated",
      name_list().count("LOOP 8") == 1 and "LOOP 9" not in name_list() and "E4L Master" in name_list()
      and lua.eval("MOCK_DEFER") is not None)

lua.execute('reaper.SetExtState("E4L_LivePanel", "quit", "1")')
frame()
check("panel: closes itself when the updater asks (quit flag)",
      lua.eval("MOCK_DEFER") is None and lua.eval('reaper.GetExtState("E4L_LivePanel", "quit")') == "")

print("\n%d failure(s)" % failures)
sys.exit(1 if failures else 0)
