"""Builds the Lua table MOCK_FXP (parameter names of every E4L JSFX, in slider order)."""
import glob
import os
import re

def lua_fxp(effects_dir):
    out = []
    for f in sorted(glob.glob(os.path.join(effects_dir, "*.jsfx"))):
        names = []
        for line in open(f, encoding="utf-8"):
            m = re.match(r"slider(\d+):[^>]*>(.*)$", line.strip())
            if m:
                names.append((int(m.group(1)), m.group(2).strip()))
        names.sort()
        items = ",".join("[[%s]]" % n for _, n in names)
        out.append("[ [[%s]] ]={%s}" % (os.path.basename(f), items))
    return "MOCK_FXP = {" + ",\n".join(out) + "}"
