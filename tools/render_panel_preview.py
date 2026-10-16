#!/usr/bin/env python3
"""Renders docs/live_panel_preview.png: runs "E4L - Live Panel.lua" against the mocked REAPER
API (tests/mock_reaper.lua) with a few loops in different states and draws its gfx calls.
Requires: pip install lupa pillow"""
import os

import sys

import lupa
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "tests"))
from jsfx_params import lua_fxp  # noqa: E402

lua = lupa.LuaRuntime()
lua.execute(lua_fxp(os.path.join(ROOT, "Effects", "E4L")))
lua.execute(open(os.path.join(ROOT, "tests", "mock_reaper.lua")).read())
lua.execute('MOCK_INPUT = "5,1,1,7,1,5"')
lua.execute("dofile([[%s]])" % os.path.join(ROOT, "Scripts", "E4L", "E4L - Live Looper template.lua"))
lua.execute("""
local E = dofile([[%s]])
E.add_input(3, true, 7)
E.set_loop_input(MOCK.T[4], 2)
local a = E.add_audio("/sounds/pad.wav")
a.vals.B_MUTE = 0
a.fx[1].p["-Current Azimuth"] = 150; a.fx[1].p["-Current Spread"] = 30
local q = E.add_audio("/sounds/pad_quad.wav")
q.vals.B_MUTE = 0
q.fx[1].p["-Current Azimuth"] = 20; q.fx[1].p["-Current Spread"] = 90
""" % os.path.join(ROOT, "Scripts", "E4L", "e4l_lib.lua"))
lua.execute('''
local T = MOCK.T
local ST, BARS, LQN = "-Status (0 empty 1 armed 2 rec 3 play 4 stop 5 pause)", "-Loop Bars", "-Loop Length (QN)"
local function L(i) return T[i+2].fx[1].p end
local function P(i) return T[i+2].fx[2].p end
L(1)[ST]=3; L(1)[BARS]=4; L(1)[LQN]=16; L(1)["Play"]=1; L(1)["Length (bars)"]=2
L(2)[ST]=3; L(2)[BARS]=2; L(2)[LQN]=8;  L(2)["Play"]=1; L(2)["Length (bars)"]=1; L(2)["Overdub"]=1
L(3)[ST]=2; L(3)[BARS]=8; L(3)[LQN]=32; L(3)["-Loop Start (QN)"]=16; L(3)["Length (bars)"]=3
L(4)[ST]=1; L(4)["Length (bars)"]=2
L(5)[ST]=4; L(5)[BARS]=4; L(5)[LQN]=16; L(5)["Length (bars)"]=2
P(1)["-Current Azimuth"]=-60; P(2)["-Current Azimuth"]=40; P(3)["-Current Azimuth"]=135
P(4)["-Current Azimuth"]=-135; P(5)["-Current Azimuth"]=0
P(1)["Azimuth"]=-60; P(1)["Radius"]=0.1; P(1)["Range"]=10; P(1)["Azimuth LFO On/Off"]=1; P(1)["Azimuth LFO Time Mode"]=1
P(1)["Azimuth LFO Sync (bars)"]=5; P(1)["Elevation LFO Frequency (Hz)"]=1; P(1)["Elevation LFO Depth"]=30
MOCK_POS = 21.3
DRAW = {}; local col = {1,1,1,1}; local font = 1
function gfx.set(r,g,b,a) col = {r,g,b,a or 1} end
function gfx.rect(x,y,w,h,f) DRAW[#DRAW+1] = {"rect",x,y,w,h,col[1],col[2],col[3],col[4], f == nil and 1 or f} end
function gfx.line(x1,y1,x2,y2) DRAW[#DRAW+1] = {"line",x1,y1,x2,y2,col[1],col[2],col[3],col[4]} end
function gfx.circle(x,y,r,f) DRAW[#DRAW+1] = {"circle",x,y,r,col[1],col[2],col[3],col[4],f or 0} end
function gfx.setfont(i) if i and i > 0 then font = i end end
function gfx.measurestr(s) if font == 2 then return utf8.len(s)*24, 44 elseif font == 3 then return utf8.len(s)*11, 20 end return utf8.len(s)*7.6, 15 end
function gfx.drawstr(s) DRAW[#DRAW+1] = {"text",gfx.x,gfx.y,s,col[1],col[2],col[3],col[4],font} end
''')
lua.execute("dofile([[%s]])" % os.path.join(ROOT, "Scripts", "E4L", "E4L - Live Panel.lua"))
W, H = 1240, 560
F1 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
F2 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
F3 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 17)


def c(r, g, b, a):
    return (int(r * 255), int(g * 255), int(b * 255), int(a * 255))


def render(out_name):
    lua.execute("DRAW = {}; local f = MOCK_DEFER; MOCK_DEFER = nil; f()")
    D = lua.eval("DRAW")
    img = Image.new("RGB", (W, H), "black")
    d = ImageDraw.Draw(img, "RGBA")
    for i in range(1, len(D) + 1):
        e = list(D[i].values())
        if e[0] == "rect":
            _, x, y, w, h, r, g, b, a, f = e
            d.rectangle([x, y, x + w, y + h], fill=c(r, g, b, a) if f else None, outline=None if f else c(r, g, b, a))
        elif e[0] == "line":
            _, x1, y1, x2, y2, r, g, b, a = e
            d.line([x1, y1, x2, y2], fill=c(r, g, b, a))
        elif e[0] == "circle":
            _, x, y, rr, r, g, b, a, f = e
            d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=c(r, g, b, a) if f else None, outline=c(r, g, b, a))
        elif e[0] == "text":
            _, x, y, s_, r, g, b, a, fo = e
            d.text((x, y), s_, fill=c(r, g, b, a), font=F2 if fo == 2 else F3 if fo == 3 else F1)
    out = os.path.join(ROOT, "docs", out_name)
    img.save(out)
    print("wrote", out)


render("live_panel_preview.png")
# open the movement editor of loop 1 (click on its MOVIMIENTO button)
lua.execute("gfx.mouse_x = 8 + 344 + 320; gfx.mouse_y = 116 + 15; gfx.mouse_cap = 1")
lua.execute("local f = MOCK_DEFER; MOCK_DEFER = nil; f()")
lua.execute("gfx.mouse_cap = 0")
render("live_panel_editor.png")
