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
      names == ["SYNTH IN"] + ["LOOP %d" % i for i in range(1, 9)] + ["E4L Master", "CUE (auriculares)"])
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
      and tracks["CUE (auriculares)"].fx[1].p["Decoder"] == 0)
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
check("panel: GRABAR arms the looper of LOOP 1", param(2, 1, "Record") == 1)
click(BX + 70 + 10, row_y(2, n))
check("panel: SONAR of row 2 toggles LOOP 2", param(3, 1, "Play") == 1)
click(8 + 212 + 10, row_y(1, n))
check("panel: length button cycles to the next length", param(2, 1, "Length (bars)") == 1)
lua.execute("MOCK_KEY = 32"); frame()
check("panel: space bar toggles REAPER play/stop", 40044 in list(lua.eval("MOCK_CMDS").values()))
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
click(BX + 256 + 10, row_y(1, n))
lw = W - room - 24
colw = (lw - 40) // 2
c1, c2 = 8 + 10, 8 + 30 + colw
y_rot = TOP + 84 + 42 + 40 + 40 + 30          # top of "GIRO AUTOMÁTICO"
click(c1 + 20, y_rot + 26 + 10)                # ACTIVADO
check("editor: GIRO AUTOMÁTICO turns the azimuth LFO on", param(2, 2, "Azimuth LFO On/Off") == 1)
click(c1 + colw - 20, y_rot + 26 + 30 + 10)    # "Al tempo"
check("editor: «Al tempo» = LFO synced to the bars", param(2, 2, "Azimuth LFO Time Mode") == 1)
y_pres = TOP + 84 + 26 + 46 + 40 + 26 + 26     # Mono panner: no stereo width section
bw = (colw - 6) / 3
click(c2 + 2 * (bw + 3) + 10, y_pres + 28 + 10)
check("editor: preset «Vaivén derecha» sets azimuth 90, swing ±45",
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
for w in (80, 84, 96, 166, 156, 148):
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
check("toolbar: + ENTRADA adds SYNTH IN 2 (input 3-4 stereo), sending muted to the 13 loops",
      name_list()[1] == "SYNTH IN 2" and recin(si2) == 1024 + 2 and nsend(si2) == 13 and smute(si2, 1) == 1)
n = 13
l1 = tr_index("LOOP 1")
click(8 + 290 + 10, row_y(1, n))                 # ENT button of loop 1 -> input 2
check("panel: ENT button switches LOOP 1 to SYNTH IN 2",
      smute(si2, 1) == 0 and smute(tr_index("SYNTH IN"), 1) == 1)
click(xs[1], TB)                                 # + AUDIO (mock file dialog -> /sounds/pad.wav, 7.9 s)
a1 = tr_index("AUDIO 1")
item = lua.eval("function(i) local it = MOCK.T[i].items[1]; return it.vals.D_POSITION, it.vals.B_LOOPSRC, it.take.vals.D_PLAYRATE, it.take.vals.B_PPITCH, MOCK.T[i].vals.B_MUTE end")
pos, loopsrc, rate, ppitch, muted = item(a1)
check("toolbar: + AUDIO adds AUDIO 1: looped item at bar 1, 7.9 s fitted to 4 bars (pitch kept), muted",
      pos == 0 and loopsrc == 1 and abs(rate - 7.9 / 8) < 1e-9 and ppitch == 1 and muted == 1)
n = 14
click(BX + 70 + 10, row_y(14, n))                # SONAR on the audio row (quantised)
check("audio row: SONAR waits for the next bar", lua.eval("MOCK.T[%d].vals.B_MUTE" % a1) == 1)
lua.execute("MOCK_POS = MOCK_POS + 2.0"); frame()   # next bar (2 s per bar at 120 BPM)
check("audio row: ... and unmutes on the next bar", lua.eval("MOCK.T[%d].vals.B_MUTE" % a1) == 0)
lua.execute("function reaper.GetUserInputs() return true, 'Tema 1' end")
click(xs[3], TB)
check("toolbar: GUARDAR TEMPLATE saves E4L_Templates/Tema 1.RPP",
      list(lua.eval("MOCK_SAVED").values()) == ["/res/E4L_Templates/Tema 1.RPP"])
lua.execute("MOCK_FILES = {'Tema 1.RPP', 'Tema 2.RPP'}; function gfx.showmenu() return 2 end")
click(xs[4], TB)
lua.execute("function gfx.showmenu() return 0 end")
check("toolbar: CARGAR TEMPLATE opens the chosen song",
      list(lua.eval("MOCK_OPENED").values()) == ["/res/E4L_Templates/Tema 2.RPP"])
lua.execute("MOCK_INPUT = nil; function reaper.GetUserInputs(t, n, cap, def) return true, def end")
click(xs[5], TB)
check("toolbar: NUEVO TEMPLATE = new project with the live template (8 loops), panel not duplicated",
      name_list().count("LOOP 8") == 1 and "LOOP 9" not in name_list() and "E4L Master" in name_list()
      and lua.eval("MOCK_DEFER") is not None)

lua.execute('reaper.SetExtState("E4L_LivePanel", "quit", "1")')
frame()
check("panel: closes itself when the updater asks (quit flag)",
      lua.eval("MOCK_DEFER") is None and lua.eval('reaper.GetExtState("E4L_LivePanel", "quit")') == "")

print("\n%d failure(s)" % failures)
sys.exit(1 if failures else 0)
