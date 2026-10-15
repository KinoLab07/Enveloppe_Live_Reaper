#!/usr/bin/env python3
"""Runs the REAPER Lua scripts against a mocked REAPER API (tests/mock_reaper.lua).
Requires: pip install lupa"""
import os
import sys

import lupa

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
ROW0, RH = 84, 35          # 12 loops in a 560 px window -> 35 px rows
BX = 8 + 292
click(BX + 10, ROW0 + 15)
check("panel: GRABAR arms the looper of LOOP 1", param(2, 1, "Record") == 1)
click(BX + 70 + 10, ROW0 + RH + 15)
check("panel: SONAR of row 2 toggles LOOP 2", param(3, 1, "Play") == 1)
click(8 + 212 + 10, ROW0 + 15)
check("panel: length button cycles to the next length", param(2, 1, "Length (bars)") == 1)
lua.execute("MOCK_KEY = 32"); frame()
check("panel: space bar toggles REAPER play/stop", list(lua.eval("MOCK_CMDS").values()) == [40044])
lua.execute("MOCK_KEY = 50"); frame()
check("panel: key 2 = record on loop 2", param(3, 1, "Record") == 1)

import math
W, H = 1240, 560
room = min(H - 90, int(W * 0.32)); rx, ry = W - room - 8, 84
cx, cy, R = rx + room / 2, ry + room / 2, room / 2 - 22
setp(2, 2, "-Current Azimuth", -45)
dx, dy = cx + math.sin(math.radians(-45)) * R * 0.78, cy - math.cos(math.radians(-45)) * R * 0.78
mouse(dx, dy, 1); frame(); mouse(cx + 100, cy, 1); frame(); mouse(cx + 100, cy, 0); frame()
check("panel: dragging loop 1 in the room sets its azimuth (+90 = right)", param(2, 2, "Azimuth") == 90)

# movement editor of loop 1
click(BX + 256 + 10, ROW0 + 15)
lw = W - room - 24
colw = (lw - 40) // 2
c1, c2 = 8 + 10, 8 + 30 + colw
y_rot = 84 + 84 + 42 + 40 + 40 + 30          # top of "GIRO AUTOMÁTICO"
click(c1 + 20, y_rot + 26 + 10)                # ACTIVADO
check("editor: GIRO AUTOMÁTICO turns the azimuth LFO on", param(2, 2, "Azimuth LFO On/Off") == 1)
click(c1 + colw - 20, y_rot + 26 + 30 + 10)    # "Al tempo"
check("editor: «Al tempo» = LFO synced to the bars", param(2, 2, "Azimuth LFO Time Mode") == 1)
# preset "Vaivén derecha" (row 2, col 3 of the presets)
y_pres = 84 + 84 + 26 + 46 + 40 + 26 + 26   # Mono panner: no stereo width section
bw = (colw - 6) / 3
click(c2 + 2 * (bw + 3) + 10, y_pres + 28 + 10)
check("editor: preset «Vaivén derecha» sets azimuth 90, swing ±45",
      param(2, 2, "Azimuth") == 90 and param(2, 2, "Azimuth LFO Mode") == 1 and param(2, 2, "Azimuth LFO Depth") == 45)
# change the effect to Stereo through the menu (mock menu returns 2)
lua.execute("function gfx.showmenu() return 2 end")
click(8 + 100 + 20, 84 + 42 + 10)
lua.execute("function gfx.showmenu() return 0 end")
check("editor: the effect menu replaces Mono Panner by Stereo Panner, keeping the settings",
      fxfile(2, 2) == "E4L Stereo Panner.jsfx" and param(2, 2, "Azimuth") == 90 and param(2, 2, "Azimuth LFO Depth") == 45)

print("\n%d failure(s)" % failures)
sys.exit(1 if failures else 0)
