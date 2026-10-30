#!/usr/bin/env python3
"""Builds docs/E4L_REAPER_Guide.pdf (user guide)."""
import math
import os

from reportlab.graphics.shapes import Circle, Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
pdfmetrics.registerFont(TTFont("DV", os.path.join(FONT_DIR, "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DVB", os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")))
_ital = "/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf"
pdfmetrics.registerFont(TTFont("DVI", _ital if os.path.exists(_ital) else os.path.join(FONT_DIR, "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DVM", os.path.join(FONT_DIR, "DejaVuSansMono.ttf")))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DVB", italic="DVI", boldItalic="DVB")

ACCENT = colors.HexColor("#1f6f8b")
ACCENT_LIGHT = colors.HexColor("#e6f2f6")
WARN = colors.HexColor("#fff4e0")
WARN_BORDER = colors.HexColor("#e0a040")
TIP = colors.HexColor("#eaf6ea")
TIP_BORDER = colors.HexColor("#5aa05a")
GREY = colors.HexColor("#555555")
SPK = [colors.HexColor(c) for c in ("#2f7fd0", "#d0602f", "#c0902f", "#3f9f6f")]

S = {
    "title": ParagraphStyle("title", fontName="DVB", fontSize=24, leading=30, textColor=ACCENT,
                            alignment=TA_CENTER, spaceAfter=6),
    "subtitle": ParagraphStyle("subtitle", fontName="DV", fontSize=13, leading=18, textColor=GREY,
                               alignment=TA_CENTER, spaceAfter=4),
    "h1": ParagraphStyle("h1", fontName="DVB", fontSize=16, leading=21, textColor=ACCENT,
                         spaceBefore=10, spaceAfter=8, keepWithNext=1),
    "h2": ParagraphStyle("h2", fontName="DVB", fontSize=12.5, leading=17, textColor=colors.black,
                         spaceBefore=10, spaceAfter=5, keepWithNext=1),
    "body": ParagraphStyle("body", fontName="DV", fontSize=10, leading=14.5, spaceAfter=5),
    "bullet": ParagraphStyle("bullet", fontName="DV", fontSize=10, leading=14.5, leftIndent=14,
                             bulletIndent=3, spaceAfter=2),
    "step": ParagraphStyle("step", fontName="DV", fontSize=10, leading=14.5, leftIndent=20,
                           bulletIndent=0, spaceAfter=4),
    "cell": ParagraphStyle("cell", fontName="DV", fontSize=9, leading=12),
    "cellb": ParagraphStyle("cellb", fontName="DVB", fontSize=9, leading=12, textColor=colors.white),
    "box": ParagraphStyle("box", fontName="DV", fontSize=9.5, leading=13.5),
    "small": ParagraphStyle("small", fontName="DV", fontSize=8.5, leading=12, textColor=GREY),
    "toc": ParagraphStyle("toc", fontName="DV", fontSize=11, leading=18, leftIndent=10),
}


def P(text, style="body"):
    return Paragraph(text, S[style])


def bullets(items):
    return [Paragraph(t, S["bullet"], bulletText="•") for t in items]


def steps(items, start=1):
    return [Paragraph(t, S["step"], bulletText="%d." % (i + start)) for i, t in enumerate(items)]


def box(flowables, kind="tip", title=None):
    bg, border = (TIP, TIP_BORDER) if kind == "tip" else (WARN, WARN_BORDER) if kind == "warn" \
        else (ACCENT_LIGHT, ACCENT)
    content = []
    if title:
        content.append(Paragraph("<b>%s</b>" % title, S["box"]))
    content += [Paragraph(f, S["box"]) if isinstance(f, str) else f for f in flowables]
    t = Table([[content]], colWidths=[170 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("LINEBEFORE", (0, 0), (0, -1), 3, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return KeepTogether([Spacer(1, 3), t, Spacer(1, 6)])


def table(rows, widths, header=True):
    data = []
    for r, row in enumerate(rows):
        data.append([Paragraph(c, S["cellb" if header and r == 0 else "cell"]) for c in row])
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1 if header else 0)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbbbbb")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), ACCENT)]
        style += [("BACKGROUND", (0, r), (-1, r), colors.HexColor("#f4f8fa"))
                  for r in range(2, len(rows), 2)]
    t.setStyle(TableStyle(style))
    return KeepTogether([t, Spacer(1, 8)])


# ---------------------------------------------------------------- diagrams
def flow_diagram():
    W, H = 170 * mm, 70 * mm
    d = Drawing(W, H)

    def node(x, y, w, h, title, sub, fill):
        d.add(Rect(x, y, w, h, rx=6, ry=6, fillColor=fill, strokeColor=ACCENT, strokeWidth=1))
        d.add(String(x + w / 2, y + h - 15, title, fontName="DVB", fontSize=9, textAnchor="middle"))
        for i, line in enumerate(sub):
            d.add(String(x + w / 2, y + h - 28 - 11 * i, line, fontName="DV", fontSize=7.5,
                         textAnchor="middle", fillColor=GREY))

    def arrow(x1, y1, x2, y2, label=None):
        d.add(Line(x1, y1, x2, y2, strokeColor=ACCENT, strokeWidth=1.4))
        a = math.atan2(y2 - y1, x2 - x1)
        p = [x2, y2, x2 - 7 * math.cos(a - 0.4), y2 - 7 * math.sin(a - 0.4),
             x2 - 7 * math.cos(a + 0.4), y2 - 7 * math.sin(a + 0.4)]
        d.add(Polygon(p, fillColor=ACCENT, strokeColor=ACCENT))
        if label:
            d.add(String((x1 + x2) / 2, (y1 + y2) / 2 + 6, label, fontName="DV", fontSize=7,
                         textAnchor="middle", fillColor=ACCENT))

    tw, th = 108, 42
    ys = [H - th - 2, H / 2 - th / 2, 4]
    names = [("Track 1", ["Stereo Panner", "16 channels"]), ("Track 2", ["Mono Panner", "16 channels"]),
             ("Track 3 …", ["Panner + LFO", "16 channels"])]
    for y, (t, s) in zip(ys, names):
        node(0, y, tw, th, t, s, colors.HexColor("#f4f8fa"))
    mx, mw, mh = 172, 122, 62
    my = H / 2 - mh / 2
    node(mx, my, mw, mh, "\"E4L Master\" track", ["E4L Master Bus", "Decoder = Quad", "16 channels"],
         ACCENT_LIGHT)
    for y in ys:
        arrow(tw, y + th / 2, mx, my + mh / 2, None)
    d.add(String((tw + mx) / 2 + 4, H / 2 + 6, "sends 1-16", fontName="DV", fontSize=7,
                 textAnchor="middle", fillColor=ACCENT))
    ox, ow, oh = 352, 128, 62
    node(ox, my, ow, oh, "REAPER master", ["4 channels (+ sub)", "Outputs 1-2 and 3-4", "of the interface"],
         colors.HexColor("#f4f8fa"))
    arrow(mx + mw, my + mh / 2, ox, my + mh / 2, "channels 1-4")
    return d


def speaker_diagram():
    W, H = 170 * mm, 92 * mm
    d = Drawing(W, H)
    cx, cy, R = W / 2, H / 2 - 2, 31 * mm
    d.add(Circle(cx, cy, R, fillColor=None, strokeColor=colors.HexColor("#bbbbbb"), strokeWidth=1,
                 strokeDashArray=[3, 3]))
    d.add(Circle(cx, cy, 9, fillColor=colors.HexColor("#dddddd"), strokeColor=GREY))
    d.add(Polygon([cx - 4, cy + 8, cx + 4, cy + 8, cx, cy + 15], fillColor=GREY, strokeColor=GREY))
    d.add(String(cx, cy - 22, "listener", fontName="DV", fontSize=7.5, textAnchor="middle",
                 fillColor=GREY))
    for ang, lab in ((0, "0° (front)"), (90, "+90°"), (180, "±180°"), (-90, "−90°")):
        a = math.radians(ang)
        x, y = cx + (R + 12) * math.sin(a), cy + (R + 12) * math.cos(a)
        d.add(String(x, y - 3, lab, fontName="DV", fontSize=7.5, textAnchor="middle", fillColor=GREY))
    spk = [(-45, "Output 1", "front left", "−45°"), (45, "Output 2", "front right", "+45°"),
           (135, "Output 3", "rear right", "+135°"), (-135, "Output 4", "rear left", "−135°")]
    for i, (ang, out, name, deg) in enumerate(spk):
        a = math.radians(ang)
        x, y = cx + R * math.sin(a), cy + R * math.cos(a)
        d.add(Rect(x - 8, y - 8, 16, 16, fillColor=SPK[i], strokeColor=colors.white, strokeWidth=1))
        d.add(String(x, y - 3.5, str(i + 1), fontName="DVB", fontSize=9, textAnchor="middle",
                     fillColor=colors.white))
        tx = x + (22 if ang > 0 else -22)
        anchor = "start" if ang > 0 else "end"
        d.add(String(tx, y + 4, "%s  (%s)" % (out, deg), fontName="DVB", fontSize=8.5,
                     textAnchor=anchor, fillColor=SPK[i]))
        d.add(String(tx, y - 7, name, fontName="DV", fontSize=8, textAnchor=anchor, fillColor=GREY))
    d.add(String(cx + R + 52, cy + R - 2, "Positive azimuth = clockwise", fontName="DVI",
                 fontSize=7.5, textAnchor="middle", fillColor=ACCENT))
    return d


def live_diagram():
    W, H = 170 * mm, 86 * mm
    d = Drawing(W, H)

    def node(x, y, w, h, title, sub, fill, edge=ACCENT):
        d.add(Rect(x, y, w, h, rx=6, ry=6, fillColor=fill, strokeColor=edge, strokeWidth=1))
        d.add(String(x + w / 2, y + h - 14, title, fontName="DVB", fontSize=8.5, textAnchor="middle"))
        for i, line in enumerate(sub):
            d.add(String(x + w / 2, y + h - 26 - 10 * i, line, fontName="DV", fontSize=7,
                         textAnchor="middle", fillColor=GREY))

    def arrow(pts, color=ACCENT, label=None, lx=None, ly=None):
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            d.add(Line(x1, y1, x2, y2, strokeColor=color, strokeWidth=1.3))
        (x1, y1), (x2, y2) = pts[-2], pts[-1]
        a = math.atan2(y2 - y1, x2 - x1)
        d.add(Polygon([x2, y2, x2 - 7 * math.cos(a - 0.4), y2 - 7 * math.sin(a - 0.4),
                       x2 - 7 * math.cos(a + 0.4), y2 - 7 * math.sin(a + 0.4)],
                      fillColor=color, strokeColor=color))
        if label:
            d.add(String(lx, ly, label, fontName="DV", fontSize=6.8, fillColor=color))

    HP = colors.HexColor("#8a4fbf")
    node(0, 118, 92, 64, "Analog synth", ["input of the", "interface"], colors.HexColor("#f4f8fa"))
    node(122, 118, 92, 64, "SYNTH IN", ["monitored", "(not recorded)"], colors.HexColor("#f4f8fa"))
    for k in range(3):
        node(250, 196 - k * 48, 104, 40, ["LOOP 1", "LOOP 2", "LOOP …"][k],
             ["E4L Looper", "+ E4L Panner"], ACCENT_LIGHT)
    node(386, 118, 95, 64, "E4L Master", ["Master Bus = Quad", "outputs 1-4 + sub 5", "(speakers)"],
         ACCENT_LIGHT)
    node(122, 4, 92, 44, "Headphones", ["outputs 7-8 →", "headphone jack"], colors.HexColor("#f3ecf9"), HP)
    node(250, 4, 104, 44, "CUE (headphones)", ["Master Bus = Binaural"], colors.HexColor("#f3ecf9"), HP)
    arrow([(92, 150), (122, 150)])
    for k in range(3):
        y = 216 - k * 48
        arrow([(214, 150), (232, 150), (232, y), (250, y)])
        arrow([(354, y), (370, y), (370, 150), (386, 150)])
    arrow([(168, 118), (168, 48)], HP, "live synth", 172, 80)
    arrow([(250, 26), (214, 26)], HP)
    arrow([(433, 118), (433, 72), (302, 72), (302, 48)], HP, "copy of the loops", 330, 76)
    return d


def lfo_diagram():
    W, H = 170 * mm, 38 * mm
    d = Drawing(W, H)
    panels = [("Cycle: full turn", "cycle"), ("Sin: swing ± Depth", "sin"),
              ("Sync: 1 turn every N bars", "sync")]
    pw = W / 3
    for i, (title, kind) in enumerate(panels):
        x0 = i * pw + 8
        d.add(String(x0 + (pw - 16) / 2, H - 10, title, fontName="DVB", fontSize=8,
                     textAnchor="middle", fillColor=ACCENT))
        gx, gy, gw, gh = x0, 6, pw - 16, H - 24
        d.add(Rect(gx, gy, gw, gh, fillColor=colors.HexColor("#f7f7f7"),
                   strokeColor=colors.HexColor("#cccccc")))
        pts = []
        for k in range(101):
            t = k / 100
            if kind == "cycle":
                v = (2 * t) % 1
            elif kind == "sin":
                v = 0.5 + 0.45 * math.sin(2 * math.pi * 2 * t)
            else:
                v = (4 * t) % 1
            pts.append((gx + t * gw, gy + 4 + v * (gh - 8)))
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            if abs(y2 - y1) < gh / 2:
                d.add(Line(x1, y1, x2, y2, strokeColor=SPK[i], strokeWidth=1.6))
        if kind == "sync":
            for b in range(1, 4):
                bx = gx + b * gw / 4
                d.add(Line(bx, gy, bx, gy + gh, strokeColor=colors.HexColor("#bbbbbb"),
                           strokeDashArray=[2, 2]))
    return d


# ---------------------------------------------------------------- content
def build(path):
    here = os.path.dirname(os.path.abspath(__file__))
    st = []
    st += [Spacer(1, 40 * mm), P("Enveloppe Live Reaper", "title"),
           P("Envelop for Live (E4L) in REAPER: quadraphonic spatialisation and live looping", "subtitle"),
           Spacer(1, 6), P("Installation and user guide", "subtitle"), Spacer(1, 22 * mm)]
    st.append(box([
        "This guide explains, step by step, how to set up a REAPER project where <b>every audio "
        "track moves around four speakers</b> with its own movement automation, a <b>master that "
        "decodes to quadraphony</b> (plus a subwoofer), and an <b>Ableton-style live looper</b> to "
        "build a piece from a synth, all controlled from one window.",
        "Project repository: <b>github.com/KinoLab07/enveloppe_live_reaper</b>",
    ], kind="info"))
    st.append(Spacer(1, 10 * mm))
    st.append(P("<b>Contents</b>", "h2"))
    for t in ["1. What is included", "2. How it works (the idea in one drawing)",
              "3. Installing in REAPER", "4. Setting up a project for quadraphony",
              "5. Adding audio tracks and positioning them", "6. Movement automation",
              "7. Headphones and export", "8. Live looping, Ableton style (analog synth)",
              "9. Troubleshooting", "10. Quick parameter reference"]:
        st.append(P(t, "toc"))
    st.append(PageBreak())

    # 1
    st.append(P("1. What is included", "h1"))
    st.append(P("<b>Envelop for Live (E4L)</b> is a set of Ableton Live devices for mixing in "
                "surround sound (ambisonics). Those devices only run inside Ableton, so they were "
                "<b>rewritten as native REAPER plug-ins</b> (JSFX). They run on macOS and Windows, "
                "need nothing else installed, and every control can be automated."))
    st.append(table([
        ["Plug-in / script", "What it is for"],
        ["<b>E4L Master Bus</b>", "On the spatial master track. Turns the spatial mix into the "
         "speaker signals: <b>Quad</b>, binaural (headphones), stereo, 5.1, 7.1, 7.1.4 and more."],
        ["<b>E4L Mono Panner</b>", "Moves a mono source in space, with movement LFOs."],
        ["<b>E4L Stereo Panner</b>", "Moves a stereo source (left and right apart), with movement "
         "and width LFOs."],
        ["<b>E4L Quad Panner</b>", "Moves audio that is already 4-channel, with LFOs."],
        ["E4L Source Panner", "Fixed position in degrees or X/Y/Z (no LFO)."],
        ["E4L Multi-Panner", "Up to 16 channels of one track."],
        ["<b>E4L Looper</b>", "Bar-synced live looper (record, play, overdub, clear)."],
        ["<b>E4L Sub Out</b>", "On REAPER's master: sends everything to the subwoofer output."],
        ["<b>E4L - New live project</b>", "Script: new project with the whole live set-up and the panel."],
        ["<b>E4L - Live Panel</b>", "Script: one window to play the loops and move them."],
        ["<b>E4L - Update from GitHub</b>", "Script: installs the latest version."],
        ["E4L - Setup session", "Script: spatialises selected tracks (no looper)."],
    ], [48, 122]))
    st += bullets([
        "Automated tests check that the sound comes out where it should, that the LFOs turn at the "
        "right speed, that tempo sync works and that the looper records exactly on the bar.",
        "License: <b>GNU GPL v2 or later</b>, the same as E4L, since this is a derivative work. "
        "You can use, modify and share it as long as the license is kept and Envelop is credited.",
    ])

    # 2
    st.append(P("2. How it works (the idea in one drawing)", "h1"))
    st.append(P("Every audio track carries an <b>E4L panner</b>. The panner does not send the "
                "sound straight to the speakers but to an intermediate <b>16-channel</b> format "
                "(ambisonics) that describes <i>where</i> the sound comes from. All tracks are sent "
                "to the <b>\"E4L Master\"</b> track, where the <b>E4L Master Bus</b> turns it into "
                "the 4 speaker signals."))
    st.append(flow_diagram())
    st.append(Spacer(1, 4))
    st.append(box([
        "Thanks to this intermediate format the same project can be heard in quadraphony, on "
        "headphones or on another system by changing <b>one option</b> of the Master Bus. The "
        "tracks' automation does not change."], kind="info", title="Why 16 channels?"))
    st.append(P("Speaker layout", "h2"))
    st.append(P("Place the four speakers in a square, at the same distance from the listener, "
                "and connect them to the outputs of the audio interface like this:"))
    st.append(speaker_diagram())
    st.append(box([
        "E4L's order goes <b>round the circle, clockwise</b>: 1 front left, 2 front right, "
        "<b>3 rear right</b>, <b>4 rear left</b>. Many systems use another order (1 FL, 2 FR, "
        "3 RL, 4 RR): if that is your case, wire the speakers following this drawing."],
        kind="warn", title="Mind outputs 3 and 4"))
    st.append(P("Angles are measured as in E4L: <b>0°</b> is the front, <b>+90°</b> the right, "
                "<b>−90°</b> the left and <b>±180°</b> the back."))
    st.append(PageBreak())

    # 3
    st.append(P("3. Installing in REAPER", "h1"))
    st.append(P("Download", "h2"))
    st += steps([
        "Open <b>github.com/KinoLab07/enveloppe_live_reaper</b> and press the green "
        "<b>Code › Download ZIP</b> button.",
        "Unzip it. You will see the folders <b>Effects</b>, <b>Data</b> and <b>Scripts</b>.",
    ])
    st.append(P("Open REAPER's resource folder", "h2"))
    st.append(P("It is where REAPER keeps its plug-ins and scripts. Three ways to open it:"))
    st += bullets([
        "In REAPER press <b>?</b> (action list), type <b>resource path</b> and double-click "
        "<b>Show REAPER resource path in explorer/finder</b>.",
        "<b>macOS:</b> in the Finder press <b>Cmd + Shift + G</b> and type "
        "<b>~/Library/Application Support/REAPER</b>.",
        "<b>Windows:</b> press <b>Win + R</b>, type <b>%APPDATA%\\REAPER</b> and press Enter.",
    ])
    st.append(P("The right folder contains, among others, the folders <b>Effects</b>, <b>Data</b> "
                "and <b>Scripts</b>, and a <b>reaper.ini</b> file."))
    st.append(P("Copy the files", "h2"))
    st += steps([
        "Close REAPER.",
        "Copy <b>Effects</b>, <b>Data</b> and <b>Scripts</b> from the zip into the resource "
        "folder. When asked about <b>folders</b>, choose <b>merge</b>; about <b>files</b>, choose "
        "<b>replace</b>. Never replace a whole folder, or you will lose your other plug-ins.",
        "Open REAPER, open the FX browser (<b>FX</b> button of a track) and press <b>F5</b> "
        "(Mac laptops: <b>fn + F5</b>). Type <b>E4L</b>: the <b>JS: E4L …</b> plug-ins appear.",
    ])
    st.append(P("Load the scripts (once)", "h2"))
    st += steps([
        "Open <b>Actions › Show action list…</b> (or press <b>?</b>).",
        "Bottom right: <b>New action…</b> › <b>Load ReaScript…</b>",
        "In the resource folder choose <b>Scripts/E4L/E4L - New live project.lua</b> and press "
        "<b>Open</b>. Repeat with <b>E4L - Live Panel.lua</b> and <b>E4L - Update from GitHub.lua</b> "
        "(and any other script you want to use).",
        "Optional: with a script selected press <b>Add…</b> (bottom left) and press a key, e.g. "
        "<b>Shift + E</b>, to run it with a shortcut.",
    ])
    st.append(box([
        "Run <b>E4L - Update from GitHub</b> whenever there is a new version. It downloads it from "
        "GitHub and replaces the plug-ins, scripts, filters and this guide in the resource folder, "
        "without touching your other plug-ins. It tells you when you are already up to date.",
        "Then it <b>closes and reopens the Live Panel</b> by itself and offers to <b>reopen the "
        "project</b>, which is how the new plug-ins are loaded (loops recorded in memory are lost). "
        "The updated guide is in <b>Data/E4L</b> inside the resource folder.",
        "Only if a <b>new</b> plug-in does not show up in the FX browser: with that window active "
        "press <b>F5</b> (<b>fn + F5</b> on a Mac laptop)."],
        title="Updating (macOS and Windows)"))
    st.append(PageBreak())

    # 4
    st.append(P("4. Setting up a project for quadraphony", "h1"))
    st.append(P("This section explains the set-up by hand, for normal (non-looping) projects. "
                "For live looping, <b>E4L - New live project</b> does all of it in one click "
                "(section 8)."))
    st.append(P("Step A: the audio interface", "h2"))
    st += steps([
        "Open <b>Settings › Audio › Device</b> (Windows: <b>Options › Preferences › Audio › Device</b>).",
        "Choose your interface and make sure at least <b>outputs 1 to 4</b> are enabled.",
    ])
    st.append(P("Step B: REAPER's master to 4 channels", "h2"))
    st += steps([
        "On the <b>MASTER</b> track press <b>Route</b> (or right-click the master › <b>Routing</b>).",
        "At the top, in <b>Track channels</b>, choose <b>4</b> (or <b>6</b> with a sub on output 5).",
        "In <b>Audio Hardware Outputs</b> keep the existing output: channels <b>1/2 → outputs 1/2</b>.",
        "Press <b>Add new hardware output</b>, choose <b>outputs 3/4</b> and set its source to "
        "channels <b>3/4</b>.",
    ])
    st.append(P("Step C: the \"E4L Master\" track with a script", "h2"))
    st += steps([
        "Select the audio tracks to spatialise (click the name; <b>Cmd/Ctrl + click</b> for several).",
        "Run <b>E4L - Setup session</b> (press <b>?</b>, search \"E4L\", double-click).",
        "Type the panner number and press <b>OK</b>: <b>1</b> Stereo, <b>2</b> Mono, 3 Source, "
        "<b>4</b> Quad, 5 Multi.",
    ])
    st.append(P("The script creates the <b>\"E4L Master\"</b> track with <b>E4L Master Bus</b> and "
                "gives every selected track <b>16 channels</b>, the panner, its master send "
                "<b>off</b> and a 16-channel send to \"E4L Master\"."))
    st.append(P("Step D: the Master Bus in quadraphony", "h2"))
    st += steps([
        "On \"E4L Master\" open <b>E4L Master Bus</b> (<b>FX</b> button).",
        "Set <b>Decoder</b> to <b>Quad</b>.",
        "Keep <b>Order Weighting</b> on <b>In-phase (E4L)</b> and <b>Ambisonics Order</b> on "
        "<b>3rd order</b>.",
    ])
    st.append(box([
        "The Quad decoder was measured with the three <i>Order Weighting</i> options. "
        "<b>In-phase (E4L)</b> is the best for four speakers: when a sound turns the level stays "
        "almost constant and no speaker gets an inverted signal. With <i>Basic</i> or "
        "<i>max-rE</i> the level drops a lot between speakers."], title="Why \"In-phase\"?"))
    st.append(P("Check", "h2"))
    st += bullets([
        "\"E4L Master\" has <b>16 channels</b> and its master send <b>on</b>.",
        "Audio tracks have <b>16 channels</b>, the <b>master send off</b> and a send to "
        "\"E4L Master\" with <b>Audio: 1-16 → 1-16</b>.",
        "When playing, <b>4 bars</b> move on the master meter.",
    ])

    # 5
    st.append(P("5. Adding audio tracks and positioning them", "h1"))
    st.append(P("Which panner?", "h2"))
    st.append(table([
        ["Kind of audio", "Plug-in", "Notes"],
        ["Mono (a voice, an instrument)", "<b>E4L Mono Panner</b>", "One moving point."],
        ["Stereo", "<b>E4L Stereo Panner</b>", "Two points (L/R) moving together; their distance "
         "is the <i>Azimuth Spread</i>."],
        ["Already 4 channels", "<b>E4L Quad Panner</b>", "Four points moving together; audio on "
         "channels 1-4 of the track."],
    ], [50, 45, 75]))
    st.append(P("The basic controls", "h2"))
    st.append(table([
        ["Control", "What it does", "For quadraphony"],
        ["<b>Azimuth</b>", "Direction in degrees: 0 front, +90 right, −90 left, ±180 back.",
         "−45 = speaker 1, +45 = speaker 2, +135 = speaker 3, −135 = speaker 4."],
        ["<b>Radius</b> and <b>Range</b>", "Distance: Radius × Range. Further = quieter "
         "(−1.5 dB per unit).", "<b>Radius = 0.1</b> with Range 10 for full level."],
        ["<b>Elevation</b>", "Height in degrees.", "Keep it at <b>0</b>: quad has no speakers above."],
        ["<b>Azimuth Spread</b>", "(Stereo/Quad) Width between the channels.", "Stereo: 30 = "
         "narrow; 45 = L and R on speakers 1 and 2 with Azimuth 0."],
        ["<b>Azimuth Spread Mode</b>", "(Quad) LR = square; X = rear pair crossed; W = fan.",
         "With LR and spread 90 each channel goes to its speaker."],
    ], [32, 70, 68]))
    st.append(box([
        "With the factory values (Radius 1, Range 10) the sound is <b>13.5 dB down</b>: that is how "
        "E4L works, it treats it as \"far\". For normal level set <b>Radius to 0.1</b>. You can "
        "automate Radius to bring the sound closer and further."], kind="warn", title="Too quiet?"))

    # 6
    st.append(P("6. Movement automation", "h1"))
    st.append(P("There are two ways to move a sound, and they can be combined:"))
    st += bullets([
        "<b>Built-in LFOs</b> (as in E4L): automatic repeating movements (turns, swings, tempo-synced "
        "movements). Just switch them on. The Live Panel's <b>MOVEMENT</b> editor shows them with "
        "plain names (section 8).",
        "<b>REAPER envelopes</b>: you draw the path on the timeline, point by point.",
    ])
    st.append(KeepTogether([P("6.1 Built-in LFOs", "h2"), lfo_diagram()]))
    st.append(table([
        ["Azimuth LFO control", "What it does"],
        ["<b>Azimuth LFO On/Off</b>", "Switches the automatic movement on or off."],
        ["<b>Mode</b>", "<b>Cycle</b>: full 360° turns around the 4 speakers. <b>Sin</b>: swings "
         "around <i>Azimuth</i>, ± <i>Depth</i> degrees."],
        ["<b>Time Mode</b>", "<b>Freq</b>: speed in Hz (turns per second). <b>Sync</b>: synced to "
         "the project tempo."],
        ["<b>Frequency</b> and <b>Rate</b>", "(Freq) Speed = Frequency × Rate. A negative Rate turns "
         "the other way. Example: 0.1 Hz × 0.5 = one turn every 20 s."],
        ["<b>Sync (bars)</b>", "(Sync) Bars per turn: 1/4, 1/2, 1, 2, 3, 4, 6, 8, 16, 32, 64."],
        ["<b>Direction</b>", "(Sync) Clockwise or Counter."],
        ["<b>Depth</b>", "(Sin) Swing width in degrees."],
        ["<b>Azimuth</b>", "With the LFO on: start point (Cycle) or centre of the swing (Sin)."],
    ], [48, 122]))
    st.append(P("Ready-made recipes", "h2"))
    st.append(table([
        ["Movement", "Settings"],
        ["Slow turn around the room", "LFO On · Mode <b>Cycle</b> · Time Mode <b>Freq</b> · "
         "Frequency <b>0.1</b> · Rate <b>1</b> (10 s per turn). Other way: Rate −1."],
        ["One turn every 4 bars", "LFO On · Mode <b>Cycle</b> · Time Mode <b>Sync</b> · Sync "
         "<b>4</b> · Direction as you like."],
        ["Swing between the two front speakers", "Azimuth <b>0</b> · LFO On · Mode <b>Sin</b> · "
         "Depth <b>45</b> · Frequency 0.25 (4 s there and back)."],
        ["Swing front to back on the right", "Azimuth <b>90</b> · Mode <b>Sin</b> · Depth <b>45</b> "
         "(45° to 135°, between speakers 2 and 3)."],
        ["Side to side through the front", "Azimuth <b>0</b> · Mode <b>Sin</b> · Depth <b>90</b>."],
        ["A stereo source that \"breathes\"", "Stereo Panner · <b>Azimuth Spread LFO On</b> · "
         "Frequency 0.2 · Depth 30."],
    ], [60, 110]))
    st.append(box([
        "In <b>Sync</b> mode, while REAPER plays, the movement is locked to the project position: "
        "the sound is always in the same place at the same bar, on every playback and in the render."],
        title="Tempo sync"))
    st.append(P("6.2 REAPER envelopes (drawing the path)", "h2"))
    st += steps([
        "On the track press the <b>envelope</b> button (the curve icon next to <b>FX</b>).",
        "Find the <b>E4L</b> panner and tick <b>Azimuth</b>. An automation lane appears.",
        "<b>Click</b> on the lane to add points, <b>drag</b> them to move them. Top = +180°, "
        "middle = 0° (front), bottom = −180°.",
        "Right-click a point to change the curve shape (linear, smooth, square…).",
        "Same for other parameters: <b>Radius</b> (closer / further), <b>Azimuth Spread</b> (width).",
    ])
    st.append(P("<b>Recording the movement live:</b> set the track's automation mode (usually "
                "<b>Trim/Read</b>) to <b>Latch</b>, play and move <b>Azimuth</b> with the mouse; "
                "then set it back to <b>Read</b>."))
    st.append(box([
        "+180° and −180° are the same point (back). A line from +170 to −170 goes through every "
        "value in between, so the sound <b>goes round through the front</b>. For full turns use the "
        "LFO in <b>Cycle</b> mode, or a point at +180 followed by −180 with a <b>square</b> shape."],
        kind="warn", title="Crossing the back"))
    st.append(P("6.3 Combining LFOs and envelopes", "h2"))
    st += bullets([
        "Automate <b>Azimuth LFO On/Off</b> so the turn starts at bar 9 and stops at bar 17.",
        "Automate <b>Azimuth LFO Frequency</b> so the turn speeds up little by little.",
        "Automate <b>Azimuth</b> with the LFO in <b>Sin</b> so the centre of the swing travels.",
        "REAPER's <b>Parameter modulation</b> (in the plug-in: <b>Param › Parameter modulation</b>) "
        "can also drive any control, e.g. from the level of another track.",
    ])
    st.append(PageBreak())

    # 7
    st.append(P("7. Headphones and export", "h1"))
    st.append(P("Preview on headphones", "h2"))
    st.append(P("Without the four speakers at hand, set the <b>E4L Master Bus</b> <b>Decoder</b> to "
                "<b>Binaural (3rd-order)</b>: outputs 1-2 then carry a 3D headphone mix (front, back "
                "and sides). <b>Set it back to Quad</b> before exporting or using the speakers. "
                "(The live set-up of section 8 already has a separate binaural CUE track.)"))
    st.append(P("Exporting the quadraphonic file", "h2"))
    st += steps([
        "<b>File › Render…</b>", "<b>Source:</b> Master mix.", "<b>Channels:</b> <b>4</b> "
        "(<b>6</b> to include the sub on channel 5).", "<b>WAV</b> format, then <b>Render</b>.",
    ])
    st.append(P("Channel order (E4L): <b>1</b> front left, <b>2</b> front right, <b>3</b> rear right, "
                "<b>4</b> rear left."))

    # 8
    st.append(PageBreak())
    st.append(P("8. Live looping, Ableton style (analog synth)", "h1"))
    st.append(P("Compose live: you play the synth and hear it <b>only on the headphones</b>. When "
                "you like a sound you record it into a <b>loop of N bars</b> that starts <b>exactly "
                "on the next bar</b>, in sync with the \"global loop\" (the project's tempo and bars). "
                "From then on it plays on the speakers, in its own position, with its own movement."))
    st.append(live_diagram())
    st.append(Spacer(1, 6))
    st.append(P("Before you start: headphones and sub (Mbox Pro)", "h2"))
    st.append(P("The headphones need a mix <b>different</b> from the speakers'. The set-up sends the "
                "headphone mix to <b>outputs 7-8</b> of the interface, which feed no speaker. On an "
                "<b>Avid Mbox Pro (3rd gen)</b> each headphone output (A and B) has its own mix, set "
                "in the driver's control panel:"))
    st += steps([
        "In REAPER open <b>Settings › Audio › Device</b> and open the interface's control panel, "
        "or open the <b>Mbox Pro Control Panel</b> directly.",
        "In the output settings, set <b>Headphones A</b> (and B if used) to what comes from the "
        "computer on <b>outputs 7-8</b>. Exact names depend on the driver version.",
        "Check that outputs <b>1-4</b> (speakers) and <b>5</b> (sub) carry what comes from the "
        "computer on those same outputs.",
        "The Mbox master volume affects every output; to make it control the headphones only, "
        "untick <i>Master Vol.</i> for the other outputs in <b>Output Setup</b>.",
    ])
    st.append(box([
        "The set-up puts <b>E4L Sub Out</b> on <b>REAPER's master</b>: the sum of <b>everything "
        "that reaches the master</b> also goes to <b>output 5</b>, so <b>any track you add</b> "
        "feeds the sub.",
        "In the plug-in: <b>Sub Level</b> and <b>Sub Low-pass</b> (0 = no filter, if the sub has its "
        "own crossover; otherwise 80-120 Hz).",
        "For an existing project run <b>E4L - Add sub to master</b> and type the sub output (5).",
    ], kind="info", title="The sub (output 5)"))
    st.append(P("Creating the live project", "h2"))
    st.append(P("Run <b>E4L - New live project</b>: a new project, the whole live set-up and the "
                "<b>Live Panel</b>, in one click (the same as running <b>E4L - Live Looper template</b> "
                "and then <b>E4L - Live Panel</b>). Fill in the dialog and press <b>OK</b>:"))
    st.append(table([
        ["Field", "What to type", "Default"],
        ["Loop tracks to add", "How many loop tracks.", "8"],
        ["Synth input (first channel)", "Interface input where the synth is connected.", "1"],
        ["Synth input: 1 mono 2 stereo", "1 if the synth has one output, 2 if it has two.", "1"],
        ["Headphones output (first channel)", "First output for the headphones.", "7 (outputs 7-8)"],
        ["Loop panner: 1 Mono 2 Stereo", "Panner of each loop: Mono for a mono synth.", "1"],
        ["Sub output (0 = none)", "Subwoofer output; it gets the sum of everything.", "5"],
    ], [52, 88, 30]))
    st.append(P("It creates <b>SYNTH IN</b>, <b>LOOP 1…8</b>, <b>E4L Master</b> (quad) and "
                "<b>CUE (headphones)</b>, sets up the master (outputs 1-2, 3-4, sub on 5) and "
                "measures your interface's <b>recording latency compensation</b>. Each loop starts in "
                "a different place in the room (−45°, 45°, 135°, −135°…)."))
    st.append(P("Playing live, step by step", "h2"))
    st += steps([
        "Set the <b>tempo</b> and <b>time signature</b> (box below).",
        "Press <b>PLAY</b> in the panel (or the space bar). The running project is the "
        "\"global loop\": every loop follows its bars.",
        "Play the synth: you hear it on the headphones. Nothing goes to the speakers yet. The "
        "<b>IN</b> meters at the top of the panel show that the input reaches REAPER.",
        "On a loop row choose the length (click it: 1, 2, 4, 8, 16 or 32 bars) and press <b>REC</b>.",
        "The state shows <b>WAITING</b>; on the next bar it becomes <b>RECORDING</b> (red) and "
        "records exactly the chosen bars.",
        "Then it switches to <b>PLAYING</b> (green) by itself: the loop plays on the speakers and "
        "on the headphones (CUE).",
        "For the next sound use the next loop: each layer on its own track, in its own place.",
    ])
    st.append(box([
        "<b>Transport bar</b> (below the tracks): on the right you see the tempo (<b>BPM</b>, e.g. "
        "120) and the time signature (e.g. <b>4/4</b>). <b>Double-click</b> them to type a new value, "
        "or drag the BPM up and down.",
        "<b>Project settings:</b> <b>File › Project settings…</b>: <i>Project BPM</i> and "
        "<i>Time signature</i>.",
        "<b>Tap tempo:</b> the action <i>Transport: Tap tempo</i>.",
        "<b>Metronome:</b> the metronome button in the transport bar. To hear it on the headphones "
        "only, send it to outputs 7-8 in <b>Settings › Metronome</b>.",
        "Set the tempo <b>before</b> recording loops: changing it later speeds up or slows down the "
        "recorded loops (and changes their pitch).",
    ], kind="info", title="Setting the tempo and time signature"))
    st.append(P("The Live Panel: everything in one window", "h2"))
    _img = os.path.join(here, "live_panel_preview.png")
    if os.path.exists(_img):
        st.append(Image(_img, width=170 * mm, height=170 * mm * 560 / 1240))
        st.append(Spacer(1, 4))
    st += bullets([
        "<b>Top:</b> the <b>bar . beat</b> counter, the beats of the bar (the first one in orange), "
        "a <b>4-bar phrase</b> indicator, the <b>IN</b> input meters, the tempo, PLAY/STOP, PAUSE and "
        "<b>STOP ALL LOOPS</b>.",
        "<b>STOP</b> (or the space bar) stops and goes back to bar 1: on PLAY every loop and audio "
        "file starts again from its beginning, like Ableton. <b>PAUSE</b> keeps the position: PLAY "
        "continues exactly where it was.",
        "<b>Toolbar:</b> <b>+ LOOP</b>, <b>+ AUDIO</b>, <b>+ INPUT</b>, <b>SAVE TEMPLATE</b>, "
        "<b>LOAD TEMPLATE</b>, <b>NEW TEMPLATE</b> (see below), <b>+ SYNC</b> (reset pulse for an "
        "external sequencer, see below).",
        "<b>Syncing an analog sequencer:</b> the <b>SYNC OUT</b> track (added with <b>+ SYNC</b>; new "
        "projects do not have it) sends a short pulse to output 6 of the Mbox on the bar where a loop starts "
        "recording, and when REAPER starts from STOP. Patch output 6 to the <b>RESET</b> input of the "
        "sequencer: the sequence starts on step 1 exactly with the loop. In its window (button "
        "<b>SYNC</b>): <b>SEND A RESET</b> to test the cable, pulse length, level, polarity, a timing "
        "offset, reset every N bars, a clock on output 2 and MIDI Start / clock. If the sequencer "
        "does not react, try a longer pulse or Polarity = Negative (interface outputs give little "
        "voltage).",
        "<b>Sequencer with only a CLOCK input:</b> in the SYNC settings set <b>Output 1 sends = Clock "
        "pulses</b> and the <b>Clock Rate</b> to one pulse per step (usually 1/16). The clock starts "
        "exactly where REAPER starts: put the sequencer on step 1, press PLAY, and with a sequence of "
        "1, 2 or 4 bars every loop starts on step 1. To use another output: <b>SYNC</b> › <b>Send the "
        "pulses to output…</b> (it warns you if the speakers already use it).",
        "<b>One row per loop:</b> state (EMPTY, WAITING, RECORDING, PLAYING, STOPPED, PAUSED; it blinks "
        "while waiting for the bar), length, input (<b>ALL</b> or <b>IN n</b>), <b>REC</b>, <b>PLAY</b>, "
        "<b>PAUSE</b>, <b>OVERDUB</b>, <b>CLEAR</b>, <b>MOVEMENT</b> and the position inside the loop.",
        "<b>The room seen from above:</b> the 4 numbered speakers and one dot per loop (green "
        "playing, red recording), moving live with the animations. <b>Drag a dot</b> to move that loop.",
        "<b>Keys:</b> <b>Space</b> = play/stop · <b>1-9</b> = record on loop 1-9 · <b>0</b> = stop all "
        "loops · <b>Esc</b> = close the movement editor.",
        "<b>Right-click the top area</b> to <b>dock</b> the panel inside REAPER.",
    ])
    st.append(table([
        ["Loop button", "What it does"],
        ["<b>REC</b>", "Records on the next bar. On a loop that already has audio it records a new "
         "one; the old one keeps playing until the new recording starts."],
        ["<b>PLAY</b>", "Starts the loop from its beginning on the next bar, or stops it on the next bar."],
        ["<b>PAUSE</b>", "Silences the loop at once. Press it again: it continues at once from the exact "
                         "point where it was paused, like a tape (it moves against the bars by the time it "
                         "was paused). PLAY puts it back on the bars, from its beginning."],
        ["<b>OVERDUB</b>", "While on, what you play is added on top of the loop."],
        ["<b>CLEAR</b>", "Erases the loop."],
        ["<b>ALL / IN n</b>", "Which interface input the loop records: <b>ALL</b> (every input, the "
         "default) or only <b>IN 1</b>, <b>IN 2</b>… Click to change."],
        ["<b>MOVEMENT</b>", "Opens the movement editor of the loop."],
    ], [40, 130]))
    st.append(P("Pre-recorded audio, more inputs and more loops", "h2"))
    st += bullets([
        "<b>+ AUDIO</b>: choose a file (wav, aif, mp3…). A new <b>AUDIO n</b> track is created, "
        "spatialised like a loop. The file starts at bar 1 and repeats; if it lasts almost a whole "
        "number of bars it is fitted to the tempo without changing its pitch. It starts "
        "<b>STOPPED</b>: press <b>PLAY</b> and it comes in from its beginning on the next bar (same to take it "
        "out). <b>PAUSE</b> works as on the loops: silent at once, then it continues from the bar where it "
        "was paused. It "
        "has its own <b>MOVEMENT</b> button. You can also drag files from the Finder onto the panel.",
        "The effect follows the channels of the file: <b>mono</b> = one point; <b>stereo</b> = two "
        "points, L and R on speakers 1 and 2; <b>quad</b> = four points, each channel on its own "
        "speaker (channel order FL, FR, RL, RR); <b>5 or more</b> channels = Multi-Panner, in a "
        "circle. The room view shows one small dot per channel. Turning the direction or the "
        "automatic rotation turns the whole image.",
        "<b>DELETE</b> on an audio row: click once (it turns into <b>SURE?</b>) and again within "
        "3 seconds. Cmd+Z in REAPER brings it back.",
        "<b>+ INPUT</b>: type the interface channel and mono/stereo. A new <b>SYNTH IN 2</b> (then "
        "3…) is created; it also goes to the headphones and has its own <b>IN</b> meter. Loops set "
        "to <b>ALL</b> record it straight away.",
        "<b>+ LOOP</b>: another loop track at the end, ready to record.",
    ])
    st.append(P("Templates: save, load and move to the next piece", "h2"))
    st += bullets([
        "<b>SAVE TEMPLATE</b>: give it a name; it is saved in <b>E4L_Templates</b> (in REAPER's "
        "resource folder) with its tracks, inputs, audio files, positions, movements and tempo.",
        "<b>LOAD TEMPLATE</b>: lists the saved templates and opens the one you choose (REAPER asks "
        "first if the current one has unsaved changes).",
        "<b>NEW TEMPLATE</b>: a new live project from scratch.",
        "For a concert: prepare one template per piece. Live, at the end of a piece press <b>LOAD "
        "TEMPLATE</b> and choose the next one. Switching causes a short audio gap, and <b>loops "
        "recorded live are not saved</b>: each template starts with empty loops.",
    ])
    st.append(P("The movement editor", "h2"))
    _img2 = os.path.join(here, "live_panel_editor.png")
    if os.path.exists(_img2):
        st.append(Image(_img2, width=170 * mm, height=170 * mm * 560 / 1240))
        st.append(Spacer(1, 4))
    st.append(table([
        ["Part of the editor", "What it does"],
        ["<b>E4L effect</b> (menu)", "<b>One point</b> (Mono Panner), <b>Two points, left and "
         "right</b> (Stereo Panner) or <b>Fixed position</b> (Source Panner, no animation). "
         "Switching keeps the position and the animations."],
        ["<b>Position</b>", "<b>Direction</b> (e.g. \"45° right\"), <b>Height</b> and "
         "<b>Distance</b> (shown as dB of attenuation)."],
        ["<b>Automatic rotation</b>", "ON/OFF · <b>Full turn</b> or <b>Swing</b> · <b>Free speed</b> "
         "(\"1 turn every 10 s\") or <b>Tempo sync</b> (\"one turn every 4 bars\") · "
         "<b>Clockwise / Counter-clockwise</b> · <b>Swing depth</b>."],
        ["<b>Up and down</b>", "Height animation: <b>Up only</b> or <b>Up and down</b>, speed and "
         "depth (barely audible in quad: no speakers above)."],
        ["<b>Stereo width</b>", "(Two points only) <b>Left / right spread</b> and <b>Breathing</b>: "
         "the image opens and closes by itself."],
        ["<b>Quick movements</b>", "One click: <b>Still</b>, <b>Slow turn</b>, <b>4-bar turn</b>, "
         "<b>Whirl</b>, <b>Front swing</b>, <b>Right swing</b>."],
    ], [45, 125]))
    st.append(P("Keyboard and MIDI control", "h2"))
    st += bullets([
        "<b>One button per loop (best with a controller):</b> in a track's <b>E4L Looper</b> press "
        "<b>Param › Learn</b>, choose <b>Record</b> (or <b>Play</b>) and press the controller "
        "button. Repeat for each loop.",
        "<b>Keyboard:</b> load <b>E4L - Loop REC (selected tracks)</b>, <b>E4L - Loop PLAY-STOP "
        "(selected tracks)</b> and <b>E4L - Loops STOP all</b> and give them keys (Actions › Add).",
    ])
    st.append(box([
        "• REAPER must be <b>playing</b>: the looper follows the project position. Do not use "
        "REAPER's repeat unless its length is a multiple of the loops' length.",
        "• Loops <b>live in the plug-in's memory</b> while REAPER is open: <b>they are not saved "
        "with the project</b>. Render (section 7) to keep a performance.",
        "• Maximum loop length: about 5 minutes at 48 kHz (plenty for 32 bars).",
        "• To hear the synth without the computer's latency, use your interface's <b>direct "
        "monitoring</b> and turn the SYNTH IN track down.",
        "• If a loop is slightly early or late, adjust <b>Recording Latency Compensation</b> in its "
        "E4L Looper (more ms if it sounds late).",
        "• Steady, unmodulated tones (drones, bass): a wave whose cycles do not fit the loop exactly "
        "would jump in phase at the seam. Right after recording, the looper finds the shift (at most "
        "half a cycle) that puts the end in phase with the start and reads the loop that much longer "
        "or shorter: a few cents, spread over the whole loop, and a seam without dip or click. Sounds "
        "that are not periodic keep their exact speed. Keep the note sounding a moment before "
        "REC starts: the crossfade uses that sound.",
    ], kind="warn", title="Good to know"))

    # 9
    st.append(PageBreak())
    st.append(P("9. Troubleshooting", "h1"))
    st.append(table([
        ["Problem", "Solution"],
        ["The E4L plug-ins do not show up", "Check that <b>Effects/E4L</b> is inside the resource "
         "folder and press <b>F5</b> (fn + F5) in the FX browser."],
        ["Nothing is heard", "The track must have <b>16 channels</b> and a send to \"E4L Master\"; "
         "\"E4L Master\" must have its <b>master send</b> on. Check that Radius is not too high."],
        ["Too quiet", "Set <b>Radius</b> to 0.1 (section 5)."],
        ["Only 2 speakers play", "REAPER's master needs <b>4 channels</b> (6 with the sub) and "
         "hardware outputs 1/2 and 3/4 (section 4, step B). The Master Bus must be on <b>Quad</b>."],
        ["The rear speakers are swapped", "Output 3 = rear <b>right</b>, output 4 = rear <b>left</b>. "
         "Swap those two cables."],
        ["The sound is also heard unspatialised", "The track's <b>master send</b> is on: switch it "
         "off (Route › Master send)."],
        ["A second input is heard but not recorded", "The loop's input button must show <b>ALL</b> "
         "or the right <b>IN n</b>. Check the <b>IN</b> meter of that input at the top of the panel."],
        ["The looper says \"Press play in REAPER\"", "Press PLAY: the looper only records and plays "
         "while the project runs."],
        ["The synth comes out of the speakers", "SYNTH IN must have its master send off, and the "
         "looper's <b>Input Thru</b> must be off."],
        ["The synth is not on the headphones", "SYNTH IN must be armed (red button) with "
         "monitoring on; in the Mbox panel the headphones must take outputs 7-8 (section 8)."],
        ["The sub is silent", "REAPER's master needs <b>E4L Sub Out</b>, 6 channels and a mono "
         "hardware output to output 5: <b>E4L - Add sub to master</b> sets it all up."],
        ["The panel did not change after an update", "Close the panel and run <b>E4L - Live Panel</b> "
         "again (the new updater does it by itself)."],
        ["A script shows an error", "Copy the error text or take a screenshot and send it."],
        ["Master Bus says \"HRIR filters not found\"", "Binaural only: <b>Data/E4L/hrtf</b> is "
         "missing in the resource folder."],
    ], [52, 118]))

    # 10
    st.append(PageBreak())
    st.append(KeepTogether([P("10. Quick parameter reference", "h1"),
                            P("E4L Master Bus", "h2"), table([
        ["Parameter", "Values", "Recommended here"],
        ["Decoder", "Binaural, Stereo, Quad, Octo, 5.1, 7.1, 5.1.2, 7.1.4, AmbiX", "<b>Quad</b>"],
        ["Order Weighting", "In-phase (E4L), max-rE, Basic", "<b>In-phase (E4L)</b>"],
        ["Ambisonics Order", "3rd order (16 ch), 1st order (4 ch)", "<b>3rd order</b>"],
        ["Input / Output Gain", "−70 to +6 dB", "0 dB"],
        ["Sub Output", "Decoder's own sub (0 = off)", "<b>0</b>: the sub is on the master (E4L Sub Out)"],
    ], [40, 80, 50])]))
    st.append(P("E4L Mono / Stereo / Quad Panner", "h2"))
    st.append(table([
        ["Group", "Parameters"],
        ["Position", "Azimuth (−180…180), Elevation (−90…90), Radius (0…1), Range (1…40)"],
        ["Width (Stereo/Quad)", "Azimuth Spread, Elevation Spread, Azimuth Spread Mode (Quad)"],
        ["Azimuth LFO", "On/Off, Mode (Cycle/Sin), Time Mode (Freq/Sync), Frequency, Rate, Sync, "
         "Direction, Depth"],
        ["Elevation LFO", "On/Off, Polarity (Unipolar/Bipolar), Time Mode, Frequency, Rate, Sync, "
         "Direction, Depth"],
        ["Spread LFOs (Stereo/Quad)", "On/Off, Mode (Freq/Sync), Frequency, Sync, Depth"],
    ], [45, 125]))
    st.append(P("E4L Sub Out (on REAPER's master)", "h2"))
    st.append(table([
        ["Parameter", "Values", "Recommended"],
        ["Sub Output (channel)", "1 to 16", "<b>5</b>"],
        ["Sum of", "Channels 1-4 (quad), 1-2 or 1-6", "<b>1-4</b>"],
        ["Sub Level (dB)", "−40 to +12", "0 dB; adjust by ear"],
        ["Sub Low-pass (Hz)", "0 = off, or 40-250", "0 if the sub has a crossover; else 80-120"],
        ["Sub", "On / Muted", "On"],
    ], [45, 70, 55]))
    st.append(P("E4L Looper", "h2"))
    st.append(table([
        ["Parameter", "Values"],
        ["Length (bars)", "1, 2, 4, 8, 16, 32"],
        ["Record / Play / Overdub / Clear", "Buttons, quantised to the bar"],
        ["Loop Volume (dB)", "−60 to +12"],
        ["Input Thru", "Off / On"],
        ["Recording Latency Compensation (ms)", "0 to 500 (set automatically)"],
        ["Loop Seam Crossfade (ms)", "1 to 170 (50)"],
        ["Seam Level Compensation", "Auto (by pitch) / Off / Full"],
        ["Start / Stop Fade (ms)", "1 to 200 (30)"],
    ], [60, 110]))
    st.append(P("E4L Sync Out", "h2"))
    st.append(table([
        ["Parameter", "Values"],
        ["Reset when a loop starts recording", "On / Off (On)"],
        ["Reset when REAPER starts from STOP", "On / Off (On)"],
        ["Reset every N bars", "Off, 1, 2, 4, 8, 16 bars"],
        ["Pulse Length (ms) / Level / Polarity", "1-100 (10) / 0-1 (1) / Positive, Negative"],
        ["Timing Offset (ms)", "−50 to +50 (negative = earlier)"],
        ["Clock Rate", "Off, 1/4, 1/8 (2 PPQN), 1/16 (4 PPQN), 1/32, 24 PPQN"],
        ["Output 1 sends", "Reset pulses / Clock pulses (then the clock is 1/16 by default)"],
        ["MIDI", "Off, Start on reset, Start + clock 24 PPQN"],
        ["Voltmeter Test Signal", "Off / Square 50 Hz (meter on AC) / DC held (meter on DC)"],
    ], [60, 110]))
    st.append(Spacer(1, 8))
    st.append(P("Envelop for Live © Envelop (envelop.us), Mark C. Slee and contributors. REAPER port "
                "under the GNU GPL v2 or later. HRTFs: IRCAM Listen. If E4L is useful to you, consider "
                "supporting Envelop at envelop.us/memberships.", "small"))

    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFont("DV", 8)
        canvas.setFillColor(GREY)
        if doc.page > 1:
            canvas.drawString(20 * mm, 287 * mm, "Enveloppe Live Reaper · User guide")
            canvas.drawRightString(190 * mm, 10 * mm, "Page %d" % doc.page)
            canvas.setStrokeColor(colors.HexColor("#dddddd"))
            canvas.line(20 * mm, 285 * mm, 190 * mm, 285 * mm)
        canvas.restoreState()

    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=18 * mm, bottomMargin=16 * mm,
                            title="Enveloppe Live Reaper - User guide",
                            author="KinoLab07", subject="Installing and using the E4L plug-ins in REAPER")
    doc.build(st, onFirstPage=on_page, onLaterPages=on_page)


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "E4L_REAPER_Guide.pdf")
    build(out)
    print("wrote", out)
