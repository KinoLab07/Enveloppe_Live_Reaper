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
template = open(os.path.join(SCRIPTS, "E4L - Live Looper template.lua")).read()
lua.execute(template)

T = lua.eval("MOCK.T")
tracks = {T[i].name: T[i] for i in range(1, len(T) + 1)}
names = [T[i].name for i in range(1, len(T) + 1)]
check("template creates SYNTH IN, 8 loops, E4L Master and CUE",
      names == ["SYNTH IN"] + ["LOOP %d" % i for i in range(1, 9)] + ["E4L Master", "CUE (auriculares)"])
s = tracks["SYNTH IN"]
check("SYNTH IN: armed, monitored, never recorded, no master send",
      s.vals.I_RECARM == 1 and s.vals.I_RECMON == 1 and s.vals.I_RECMODE == 2 and s.vals.B_MAINSEND == 0)
check("SYNTH IN: to headphones (outputs 5-6) and to every loop",
      s.sends[1][1].vals.I_DSTCHAN == 4 and len(s.sends[0]) == 8)
l1 = tracks["LOOP 1"]
check("LOOP: 16 ch, no master send, looper + panner, 16-ch send to E4L Master",
      l1.vals.I_NCHAN == 16 and l1.vals.B_MAINSEND == 0 and l1.fx[1].file == "E4L Looper.jsfx"
      and l1.sends[0][1].dst.name == "E4L Master" and l1.sends[0][1].vals.I_SRCCHAN == 8 << 10)
check("E4L Master decodes to Quad, CUE to binaural",
      tracks["E4L Master"].fx[1].p["Decoder"] == 2 and tracks["CUE (auriculares)"].fx[1].p["Decoder"] == 0)
m = lua.eval("MOCK.master")
check("REAPER master: 4 channels to outputs 1-2 and 3-4",
      m.vals.I_NCHAN == 4 and sorted(m.sends[1][i].vals.I_DSTCHAN for i in (1, 2)) == [0, 2])
lua.execute(template)
T = lua.eval("MOCK.T")
check("running it again only adds loops (4 more)", len(T) == 15 and T[13].name == "LOOP 12")

print("\n%d failure(s)" % failures)
sys.exit(1 if failures else 0)
