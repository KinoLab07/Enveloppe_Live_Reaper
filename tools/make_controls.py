#!/usr/bin/env python3
"""Writes Scripts/E4L/Controls/E4L ctl - <TARGET> <ACTION>.lua: one REAPER action per Live Panel
button, so each can be bound to a MIDI note / CC (Actions > Add shortcut). They all run
Scripts/E4L/e4l_control.lua, which reads the target and the action from the file name."""
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "Scripts", "E4L", "Controls")
STUB = '''-- E4L control action: {name}
-- Bind it to a MIDI button: Actions > Show action list > select it > Add... > press the button.
local dir = debug.getinfo(1, "S").source:match("@?(.*[/\\\\])") or ""
dofile(dir .. "../e4l_control.lua").run(debug.getinfo(1, "S").source:match("@?(.*)"))
'''
names = []
for n in range(1, 13):
    for a in ("REC", "PLAY", "PAUSE", "OVERDUB", "CLEAR"):
        names.append("LOOP %d %s" % (n, a))
for n in range(1, 7):
    for a in ("PLAY", "PAUSE"):
        names.append("AUDIO %d %s" % (n, a))
for n in range(1, 5):
    names.append("LIVE %d ON-OFF" % n)
for a in ("PLAY-STOP", "PAUSE", "REC SESSION", "STOP ALL LOOPS", "REC START"):
    names.append("MASTER " + a)

os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT):
    if f.startswith("E4L ctl - ") and f.endswith(".lua"):
        os.remove(os.path.join(OUT, f))
for name in names:
    with open(os.path.join(OUT, "E4L ctl - %s.lua" % name), "w") as f:
        f.write(STUB.format(name=name))
print("wrote %d control actions to %s" % (len(names), OUT))
