#!/usr/bin/env python3
"""Builds docs/E4L_Quick_Guide.pdf: a short visual guide (pictures of the Live Panel with
numbered marks, a few words each). Run tools/render_panel_preview.py first (it draws
docs/live_panel_preview.png and docs/live_panel_editor.png at 2x).
Requires: pip install reportlab pillow"""
import os
import tempfile

from PIL import Image as PImage, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOCS = os.path.join(ROOT, "docs")
OUT = os.path.join(DOCS, "E4L_Quick_Guide.pdf")
TMP = tempfile.mkdtemp()
K = 2                                   # the panel pictures are drawn at 2x

FD = "/usr/share/fonts/truetype/dejavu"
pdfmetrics.registerFont(TTFont("DV", os.path.join(FD, "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DVB", os.path.join(FD, "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DVB", italic="DV", boldItalic="DVB")

ACCENT = colors.HexColor("#1f6f8b")
MARK = (235, 60, 90)                    # colour of the numbered marks
MARK_C = colors.Color(MARK[0] / 255, MARK[1] / 255, MARK[2] / 255)
DARK = colors.HexColor("#1c1c22")
S = {
    "title": ParagraphStyle("t", fontName="DVB", fontSize=30, leading=36, textColor=ACCENT),
    "sub": ParagraphStyle("s", fontName="DV", fontSize=14, leading=19, textColor=colors.HexColor("#555555")),
    "h": ParagraphStyle("h", fontName="DVB", fontSize=22, leading=27, textColor=ACCENT, spaceAfter=6),
    "body": ParagraphStyle("b", fontName="DV", fontSize=11.5, leading=15.5),
    "leg": ParagraphStyle("l", fontName="DV", fontSize=11, leading=14.5),
    "num": ParagraphStyle("n", fontName="DVB", fontSize=11, leading=15, textColor=colors.white,
                          alignment=1),
    "step": ParagraphStyle("st", fontName="DV", fontSize=12, leading=16, alignment=1),
    "stepn": ParagraphStyle("sn", fontName="DVB", fontSize=26, leading=30, textColor=ACCENT, alignment=1),
    "small": ParagraphStyle("sm", fontName="DV", fontSize=9.5, leading=13, textColor=colors.HexColor("#555555")),
}
BADGE_FONT = ImageFont.truetype(os.path.join(FD, "DejaVuSans-Bold.ttf"), 30)


def P(t, s="body"):
    return Paragraph(t, S[s])


# ------------------------------------------------------------------ pictures with marks
def marked(src, box, marks, name, frames=(), pad=(0, 0, 0, 0)):
    """Crop `box` (x0, y0, x1, y1 in panel pixels) of a panel picture, add white margins
    pad = (left, top, right, bottom) and put numbered marks at (n, x, y) panel pixels (in the
    picture or in the margins, so they do not hide what they point at).
    frames: rectangles (x0, y0, x1, y1) outlined in red."""
    im = PImage.open(os.path.join(DOCS, src)).convert("RGB")
    x0, y0, x1, y1 = box
    pl, pt, pr, pb = pad
    im = im.crop((x0 * K, y0 * K, x1 * K, y1 * K))
    can = PImage.new("RGB", ((x1 - x0 + pl + pr) * K, (y1 - y0 + pt + pb) * K), "white")
    can.paste(im, (pl * K, pt * K))
    d = ImageDraw.Draw(can)
    ox, oy = x0 - pl, y0 - pt                 # panel pixel at the canvas origin
    for a, b, c_, e in frames:
        d.rounded_rectangle([(a - ox) * K, (b - oy) * K, (c_ - ox) * K, (e - oy) * K], radius=10,
                            outline=MARK, width=6)
    for n, x, y in marks:
        r = 24
        cx, cy = (x - ox) * K, (y - oy) * K
        d.ellipse([cx - r - 3, cy - r - 3, cx + r + 3, cy + r + 3], fill=(255, 255, 255))
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=MARK)
        d.text((cx, cy), str(n), fill=(255, 255, 255), font=BADGE_FONT, anchor="mm")
    p = os.path.join(TMP, name + ".png")
    can.save(p)
    return p, can.size[0] / can.size[1]


def pic(path_aspect, width):
    p, a = path_aspect
    return Image(p, width=width, height=width / a)


def legend(items, width):
    """items: (n, text) – a numbered list beside the picture."""
    rows = [[P(str(n), "num"), P(t, "leg")] for n, t in items]
    t = Table(rows, colWidths=[11 * mm, width - 11 * mm])
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
          ("LEFTPADDING", (1, 0), (1, -1), 7)]
    for i in range(len(rows)):
        st.append(("BACKGROUND", (0, i), (0, i), MARK_C))
    t.setStyle(TableStyle(st))
    return t


def side(picture, leg, pw=170 * mm, lw=92 * mm):
    t = Table([[picture, leg]], colWidths=[pw + 4 * mm, lw])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    return t


def steps(items, width=267 * mm):
    """A row of big numbered step cards."""
    n = len(items)
    cw = width / n
    cells = [[P(str(i + 1), "stepn"), P(t, "step")] for i, t in enumerate(items)]
    inner = [Table([[c[0]], [c[1]]], colWidths=[cw - 8 * mm]) for c in cells]
    t = Table([inner], colWidths=[cw] * n)
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, ACCENT), ("INNERGRID", (0, 0), (-1, -1), 0.8, ACCENT),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eef6f9")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    return t


def note(text):
    t = Table([[P(text, "body")]], colWidths=[267 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff4e0")),
                           ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#e0a040")),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 6),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return t


# panel geometry (panel pixels, 1240 x 680; rows start at y 116, 40 px each)
def row(i):
    return 116 + (i - 1) * 40 + 18


PANEL = "live_panel_preview.png"
EDITOR = "live_panel_editor.png"

st = []

# 1 ------------------------------------------------------------------ cover
st.append(P("E4L for REAPER", "title"))
st.append(P("Quick guide · live looping in quad with Envelop movements", "sub"))
st.append(Spacer(1, 5 * mm))
st.append(pic(marked(PANEL, (0, 0, 1240, 680), [], "cover"), 175 * mm))
st.append(Spacer(1, 4 * mm))
st.append(steps([
    "Run <b>E4L - Update from GitHub</b><br/>(Actions › Show action list, search “E4L”)",
    "Run <b>E4L - New live project</b><br/>(Enter to accept the dialog)",
    "Set the <b>tempo</b> and press <b>space</b> (play)",
    "Press <b>REC</b> on a loop and play the synth",
]))
st.append(PageBreak())

# 2 ------------------------------------------------------------------ the panel at a glance
st.append(P("The Live Panel at a glance", "h"))
st.append(side(
    pic(marked(PANEL, (0, 0, 1240, 680), [
        (1, -18, 30), (2, 790, 50), (3, -18, 94), (4, -18, row(3)), (5, -18, row(6) + 20),
        (6, -18, row(8)), (7, 1258, 290), (8, 1258, 570)], "glance", pad=(36, 0, 36, 0)), 170 * mm),
    legend([
        (1, "<b>Where you are</b>: bar . beat, the beats, the 4-bar phrase, input levels."),
        (2, "<b>● REC</b> the session · <b>PLAY/STOP</b> (back to bar 1) · <b>PAUSE</b> · "
            "<b>STOP ALL LOOPS</b>."),
        (3, "<b>Toolbar</b>: add loops, files, inputs, live inputs, sync; templates; REC mode."),
        (4, "<b>Loops</b>: one row each."),
        (5, "<b>Audio files</b>: looped files."),
        (6, "<b>Live inputs</b>: VCV Rack or a synth, played (not looped) in the room."),
        (7, "<b>The room</b> seen from above: speakers 1-4 and one dot per track. Drag a dot to move it."),
        (8, "<b>Reverb</b>: one room reverb for everything."),
    ], 92 * mm)))
st.append(Spacer(1, 4 * mm))
st.append(P("Open it: Actions › Show action list › <b>E4L - Live Panel</b>. Dock it with a right-click "
            "on its top area. Keys: <b>space</b> play/stop · <b>1-9</b> REC on loop 1-9 · <b>0</b> stop "
            "all loops · <b>Esc</b> close the editor.", "small"))
st.append(PageBreak())

# 3 ------------------------------------------------------------------ record a loop
st.append(P("Record a loop", "h"))
st.append(side(
    pic(marked(PANEL, (0, 112, 880, 316), [
        (1, 166, 96), (2, 258, 96), (3, 324, 96), (4, 379, 96),
        (5, 435, 96), (6, 494, 96), (7, 566, 96), (8, 631, 96),
        (9, 705, 96), (10, 812, 96)], "loops", pad=(0, 32, 0, 0)), 165 * mm),
    legend([
        (1, "<b>State</b>: empty, waiting, recording, playing, stopped, paused."),
        (2, "<b>Length</b>: 1-32 bars or <b>FREE</b> (REC again ends it)."),
        (3, "<b>Input</b>: ALL or IN 1, IN 2…"),
        (4, "<b>REC</b>: records, then plays by itself."),
        (5, "<b>PLAY</b>: start / stop on the next bar."),
        (6, "<b>PAUSE</b>: silent at once; again = continues at once."),
        (7, "<b>OVERDUB</b>: add a layer (next page)."),
        (8, "<b>CLEAR</b>: erase the loop."),
        (9, "<b>MOVEMENT</b>: how it moves in the room."),
        (10, "Where the loop is."),
    ], 92 * mm), 165 * mm, 97 * mm))
st.append(Spacer(1, 2 * mm))
st.append(steps([
    "REAPER <b>playing</b><br/>(space)",
    "Listen to the synth<br/>on the <b>headphones</b>",
    "<b>REC</b> on a loop<br/>(it blinks: waiting)",
    "Red: <b>recording</b>",
    "Green: <b>playing</b><br/>in the room",
]))
st.append(Spacer(1, 2 * mm))
st.append(side(
    pic(marked(PANEL, (860, 76, 970, 112), [], "recmode"), 40 * mm),
    P("<b>REC: BAR / BEAT / NOW</b> (toolbar) – when REC starts: on the next <b>bar</b>, the next "
      "<b>beat</b>, or <b>at once</b> (you keep time). With length <b>FREE</b> the REC button reads "
      "<b>END</b>: press it to close the loop where you want.", "body"), 40 * mm, 222 * mm))
st.append(PageBreak())

# 4 ------------------------------------------------------------------ overdub, pause, clear
st.append(P("Overdub: layers on top of a loop", "h"))
st.append(pic(marked(PANEL, (0, 152, 880, 196), [], "odub",
                     frames=[(526, 156, 606, 192)]), 267 * mm))
st.append(Spacer(1, 5 * mm))
st.append(steps([
    "The loop is <b>playing</b>",
    "Press <b>OVERDUB</b><br/>(orange)",
    "Play: it is <b>added</b><br/>on top, every pass",
    "Press <b>OVERDUB</b><br/>again to stop",
]))
st.append(Spacer(1, 5 * mm))
st.append(note("Overdub starts and stops <b>at once</b> (not on the bar). Layers add up: watch the level. "
               "There is no undo of one layer: <b>CLEAR</b> erases the whole loop. The new layer moves "
               "with the loop's MOVEMENT."))
st.append(Spacer(1, 6 * mm))
st.append(P("Play / pause", "h"))
st.append(steps([
    "<b>PLAY</b>: the loop starts from its beginning on the next bar (or stops on the next bar)",
    "<b>PAUSE</b>: silent at once",
    "<b>PAUSE</b> again: continues at once from the same point (like tape)",
    "<b>PLAY</b>: back on the bars",
]))
st.append(PageBreak())

# 5 ------------------------------------------------------------------ add sounds
st.append(P("Add sounds", "h"))
st.append(pic(marked(PANEL, (0, 76, 970, 112), [
    (1, 48, 60), (2, 136, 60), (3, 226, 60), (4, 312, 60), (5, 500, 60), (6, 713, 60), (7, 822, 60),
    (8, 914, 60)], "toolbar", pad=(0, 32, 0, 0)), 267 * mm))
st.append(Spacer(1, 3 * mm))
st.append(legend([
    (1, "<b>+ LOOP</b>: one more loop track."),
    (2, "<b>+ AUDIO</b>: a sound file, looped from bar 1 (or <b>drag files from the Finder</b> onto the panel). "
        "Mono, stereo or quad: it spreads over the speakers by itself."),
    (3, "<b>+ INPUT</b>: one more interface input for the loops (IN 2…)."),
    (4, "<b>+ LIVE</b>: an input played live in the room with its own movement (VCV Rack via BlackHole, "
        "another synth). Not looped."),
    (5, "<b>SAVE / LOAD TEMPLATE</b>: keep the set-up of a piece (tracks, files, movements, tempo)."),
    (6, "<b>NEW TEMPLATE</b>: a new live project."),
    (7, "<b>+ SYNC</b>: clock / reset pulses for an analog sequencer (then a menu: on/off, settings, output)."),
    (8, "<b>REC: BAR / BEAT / NOW</b>: when loops start recording."),
], 267 * mm))
st.append(Spacer(1, 4 * mm))
st.append(side(
    pic(marked(PANEL, (0, 312, 880, 436), [(1, 270, 296), (2, 435, 296), (3, 494, 296), (4, 566, 296),
                                            (5, 166, 452), (6, 466, 452)], "audio",
               pad=(0, 32, 0, 32)), 150 * mm),
    legend([
        (1, "Time left in the file (orange near the end: get ready)."),
        (2, "<b>PLAY</b>: from the start on the next bar."),
        (3, "<b>PAUSE</b>: silent; again = goes on from that bar."),
        (4, "<b>DELETE</b>: click twice."),
        (5, "<b>ON AIR</b>: the live input is in the room."),
        (6, "<b>MUTE</b>: out at once."),
    ], 110 * mm), 150 * mm, 112 * mm))
st.append(PageBreak())

# 6 ------------------------------------------------------------------ movement
st.append(P("Move the sound: MOVEMENT", "h"))
st.append(side(
    pic(marked(EDITOR, (0, 76, 1240, 680), [
        (1, 462, 170), (2, 120, 207), (3, 185, 360), (4, 625, 208), (5, 725, 346), (6, 600, 444),
        (7, 950, 135), (8, 676, 137)], "editor"), 175 * mm),
    legend([
        (1, "<b>E4L effect</b>: one point, two points (stereo), four (quad)…"),
        (2, "<b>Position</b>: direction, height, distance."),
        (3, "<b>Automatic rotation</b>: full turn or swing, in seconds or in bars."),
        (4, "<b>Up and down</b> (little effect in quad)."),
        (5, "<b>Random movement</b>: wanders inside the room."),
        (6, "<b>Quick movements</b>: one click."),
        (7, "Drag a dot to place a track."),
        (8, "<b>BACK TO THE LOOPS</b> (or Esc)."),
    ], 87 * mm), 175 * mm, 87 * mm))
st.append(Spacer(1, 3 * mm))
st.append(P("Open it with the <b>MOVEMENT</b> button of a row. Movements freeze on PAUSE and continue; after "
            "STOP they start again from the beginning.", "small"))
st.append(PageBreak())

# 7 ------------------------------------------------------------------ reverb
st.append(P("Reverb", "h"))
st.append(side(
    pic(marked(PANEL, (884, 468, 1236, 676), [
        (1, 984, 452), (2, 1120, 452), (3, 948, 522), (4, 1140, 522), (5, 952, 562), (6, 1122, 562),
        (7, 954, 602), (8, 1120, 602), (9, 1254, 644)], "reverb", pad=(0, 32, 34, 0)), 120 * mm),
    legend([
        (1, "<b>ON / OFF</b> (first time: <b>+ REVERB</b>)."),
        (2, "<b>Room</b>: choose the room."),
        (3, "<b>Size</b>: smaller / bigger room."),
        (4, "<b>Rotation</b>: turns the reflections."),
        (5, "<b>Early</b>: first reflections."),
        (6, "<b>Late</b>: the long tail."),
        (7, "<b>Level</b>: the whole reverb."),
        (8, "<b>Send</b>: how much reverb the chosen track gets (left end = off)."),
        (9, "<b>Reverb of ▾</b>: choose the track (or click a row's name: blue edge)."),
    ], 140 * mm), 120 * mm, 142 * mm))
st.append(Spacer(1, 6 * mm))
st.append(steps([
    "<b>+ REVERB</b><br/>(once per project)",
    "<b>Reverb of ▾</b><br/>choose a track",
    "<b>Send</b>: start near<br/>−10 dB",
    "<b>Room, Size, Late</b><br/>by ear",
]))
st.append(Spacer(1, 4 * mm))
st.append(P("Changing room or size takes a second or two (“building…”). The reverb uses about 20 % of one "
            "CPU core. More rooms: copy 4-channel B-format WAV files to Data/E4L/ir in REAPER's resource folder.",
            "small"))
st.append(PageBreak())

# 7b ----------------------------------------------------------------- reverb and movement
st.append(P("Reverb and movement", "h"))
st.append(legend([
    ("+", "<b>What it does</b>: puts the sounds <b>inside a room</b> (they no longer stick to the speakers), "
          "gives <b>depth</b> (more reverb = farther; with <b>Distance</b> in MOVEMENT the coming and going "
          "is much clearer) and, by contrast, helps to follow a moving sound."),
    ("−", "<b>What it does not do</b>: the reverb does <b>not follow</b> the sound. Each track sends only "
          "its non-directional signal, so the room answers the same whether the sound is in front or "
          "behind. Only the direct sound moves."),
    ("−", "<b>Too much reverb blurs the movement</b>: a loud tail (<b>Late</b>) washes out the position. "
          "Moderate amounts show movement best."),
], 267 * mm))
st.append(Spacer(1, 4 * mm))
st.append(P("Check it by ear (in the middle of the 4 speakers, or on the headphones)", "body"))
st.append(Spacer(1, 2 * mm))
st.append(steps([
    "<b>A/B</b>: a short, percussive loop with <b>Slow turn</b>; switch <b>Send</b> between off and "
    "−12 dB several times. Is the turn easier to follow?",
    "<b>Solo the REVERB track</b>: while the loop turns the reverb stays still; moving "
    "<b>Rotation</b> turns it.",
    "<b>Depth</b>: a still sound, raise <b>Send</b> and <b>Distance</b>: farther. Lower Send, "
    "closer: more present.",
    "<b>Early vs Late</b>: Late −20 dB, Early 0 = room shape, position kept. Then the reverse: "
    "the tail hides the movement.",
]))
st.append(Spacer(1, 5 * mm))
st.append(note("<b>Starting point for clear movement</b>: Send −15 to −10 dB · Late −3 to −6 dB · Early 0 dB."))
st.append(PageBreak())

# 8 ------------------------------------------------------------------ record and export
st.append(P("Record the session and export it", "h"))
st.append(side(
    pic(marked(PANEL, (800, 30, 1236, 70), [(1, 866, 14)], "rec", pad=(0, 32, 0, 0)), 110 * mm),
    P("<b>● REC</b> records what goes to the 4 speakers (two tracks REC 1-2 and REC 3-4). "
      "<b>Save the project first</b> (the files go into its folder). ● REC again, or STOP, ends it.",
      "body"), 110 * mm, 152 * mm))
st.append(Spacer(1, 5 * mm))
st.append(steps([
    "<b>● REC</b><br/>play your set",
    "<b>● REC</b> again<br/>(or STOP)",
    "Run <b>E4L - Binaural mix<br/>of the session</b>",
    "Press <b>Render</b>:<br/>a binaural stereo file",
]))
st.append(Spacer(1, 8 * mm))
st.append(P("Control it with MIDI", "h"))
st.append(steps([
    "Actions › <b>Show action list</b>",
    "Search <b>E4L ctl</b><br/>(e.g. E4L ctl - LOOP 1 REC)",
    "<b>Add…</b>",
    "Press the button<br/>on the controller",
]))
st.append(Spacer(1, 3 * mm))
st.append(P("Every panel button has its action: LOOP 1-12 REC / PLAY / PAUSE / OVERDUB / CLEAR, AUDIO 1-6 "
            "PLAY / PAUSE, LIVE 1-4 ON-OFF, MASTER PLAY-STOP / PAUSE / REC SESSION / STOP ALL LOOPS / "
            "REC START. Knobs and faders: open the plug-in, <b>Param › Learn</b>.", "small"))
st.append(PageBreak())

# 9 ------------------------------------------------------------------ update and good to know
st.append(P("Update", "h"))
st.append(steps([
    "Run <b>E4L - Update from GitHub</b>",
    "It downloads and installs<br/>(REAPER keeps working)",
    "<b>Yes</b> to reopen the project<br/>(new plug-ins)",
    "The panel opens again",
]))
st.append(Spacer(1, 6 * mm))
st.append(P("Good to know", "h"))
st.append(legend([
    ("!", "<b>Recorded loops live in memory</b>: they are not saved with the project and are lost when it "
          "is reopened. Use <b>● REC</b> to keep a performance."),
    ("!", "REAPER must be <b>playing</b> for the loops to record and play."),
    ("!", "The synth comes in hot: keep its level below 0 dB on the IN meter, and watch it when overdubbing."),
    ("!", "Outputs: speakers <b>1-4</b>, sub <b>5</b>, headphones <b>7-8</b> (binaural). "
          "The synth goes to the headphones only, until it is recorded in a loop."),
    ("!", "If a loop sounds early or late, adjust <b>Recording Latency Compensation</b> in its E4L Looper."),
    ("!", "The full guide (every control) is <b>E4L_REAPER_Guide.pdf</b>, next to this one in "
          "REAPER's resource folder › Data › E4L."),
], 267 * mm))


def page(c, doc):
    c.saveState()
    c.setFont("DV", 8.5)
    c.setFillColor(colors.HexColor("#888888"))
    c.drawString(15 * mm, 8 * mm, "E4L for REAPER · quick guide · GPLv2, port of Envelop for Live (envelop.us)")
    c.drawRightString(282 * mm, 8 * mm, str(doc.page))
    c.restoreState()


doc = SimpleDocTemplate(OUT, pagesize=landscape(A4), leftMargin=15 * mm, rightMargin=15 * mm,
                        topMargin=12 * mm, bottomMargin=14 * mm, title="E4L for REAPER - Quick guide",
                        author="Envelop for REAPER")
doc.build(st, onFirstPage=page, onLaterPages=page)
print("wrote", OUT)
