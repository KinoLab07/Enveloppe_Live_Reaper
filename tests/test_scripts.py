#!/usr/bin/env python3
"""Runs the REAPER Lua scripts against a mocked REAPER API (tests/mock_reaper.lua).
Requires: pip install lupa"""
import os
import sys

import lupa

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "Scripts", "E4L")
failures = 0


def check(name, cond):
    global failures
    print(("ok   " if cond else "FAIL ") + name)
    failures += 0 if cond else 1


lua = lupa.LuaRuntime()
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
mouse = lua.eval("function(x, y, cap) gfx.mouse_x = x; gfx.mouse_y = y; gfx.mouse_cap = cap end")
frame()
# row 1 is at y = 84 .. 120; REC button at x = 8 + 306, y + 6
mouse(8 + 306 + 10, 84 + 15, 1); frame(); mouse(0, 0, 0); frame()
check("panel: REC button arms the looper of LOOP 1", param(2, 1, "Record") == 1)
mouse(8 + 306 + 52 + 10, 84 + 40 + 15, 1); frame(); mouse(0, 0, 0); frame()
check("panel: PLAY button of row 2 toggles LOOP 2", param(3, 1, "Play") == 1)
mouse(8 + 234 + 10, 84 + 15, 1); frame(); mouse(0, 0, 0); frame()
check("panel: length button cycles to the next length", param(2, 1, "Length (bars)") == 1)
lua.execute("MOCK_KEY = 32"); frame()
check("panel: space bar toggles REAPER play/stop", list(lua.eval("MOCK_CMDS").values()) == [40044])
lua.execute("MOCK_KEY = 50"); frame()
check("panel: key 2 = REC on loop 2", param(3, 1, "Record") == 1)
# room view: 1100 wide -> room = 396 px at x = 696, y = 84; loop 1 shows its Current Azimuth (-45)
setp(2, 2, "-Current Azimuth", -45)
room, rx, ry = 396, 1100 - 396 - 8, 84
cx, cy, R = rx + room / 2, ry + room / 2, room / 2 - 22
import math
dx, dy = cx + math.sin(math.radians(-45)) * R * 0.78, cy - math.cos(math.radians(-45)) * R * 0.78
mouse(dx, dy, 1); frame()
mouse(cx + 100, cy, 1); frame()        # drag to the right of the listener
mouse(cx + 100, cy, 0); frame()
check("panel: dragging loop 1 in the room sets its azimuth (+90 = right)", param(2, 2, "Azimuth") == 90)

print("\n%d failure(s)" % failures)
sys.exit(1 if failures else 0)
