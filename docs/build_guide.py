#!/usr/bin/env python3
"""Genera docs/Guia_E4L_REAPER_Cuadrafonia.pdf (guía de usuario en español)."""
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
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer,
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
    names = [("Pista 1", ["Stereo Panner", "16 canales"]), ("Pista 2", ["Mono Panner", "16 canales"]),
             ("Pista 3 …", ["Panner + LFO", "16 canales"])]
    for y, (t, s) in zip(ys, names):
        node(0, y, tw, th, t, s, colors.HexColor("#f4f8fa"))
    mx, mw, mh = 172, 122, 62
    my = H / 2 - mh / 2
    node(mx, my, mw, mh, "Pista «E4L Master»", ["E4L Master Bus", "Decoder = Quad", "16 canales"],
         ACCENT_LIGHT)
    for y in ys:
        arrow(tw, y + th / 2, mx, my + mh / 2, None)
    d.add(String((tw + mx) / 2 + 4, H / 2 + 6, "envíos 1-16", fontName="DV", fontSize=7,
                 textAnchor="middle", fillColor=ACCENT))
    ox, ow, oh = 352, 128, 62
    node(ox, my, ow, oh, "Master de REAPER", ["4 canales", "Salidas 1-2 y 3-4", "de la interfaz"],
         colors.HexColor("#f4f8fa"))
    arrow(mx + mw, my + mh / 2, ox, my + mh / 2, "canales 1-4")
    return d


def speaker_diagram():
    W, H = 170 * mm, 92 * mm
    d = Drawing(W, H)
    cx, cy, R = W / 2, H / 2 - 2, 31 * mm
    d.add(Circle(cx, cy, R, fillColor=None, strokeColor=colors.HexColor("#bbbbbb"), strokeWidth=1,
                 strokeDashArray=[3, 3]))
    # listener
    d.add(Circle(cx, cy, 9, fillColor=colors.HexColor("#dddddd"), strokeColor=GREY))
    d.add(Polygon([cx - 4, cy + 8, cx + 4, cy + 8, cx, cy + 15], fillColor=GREY, strokeColor=GREY))
    d.add(String(cx, cy - 22, "oyente", fontName="DV", fontSize=7.5, textAnchor="middle",
                 fillColor=GREY))
    # angle marks
    for ang, lab in ((0, "0° (frente)"), (90, "+90°"), (180, "±180°"), (-90, "−90°")):
        a = math.radians(ang)
        x, y = cx + (R + 12) * math.sin(a), cy + (R + 12) * math.cos(a)
        d.add(String(x, y - 3, lab, fontName="DV", fontSize=7.5, textAnchor="middle", fillColor=GREY))
    spk = [(-45, "Salida 1", "delantero izq.", "−45°"), (45, "Salida 2", "delantero der.", "+45°"),
           (135, "Salida 3", "trasero der.", "+135°"), (-135, "Salida 4", "trasero izq.", "−135°")]
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
    # rotation arrow (clockwise = positive)
    d.add(String(cx + R + 52, cy + R - 2, "Azimut positivo = sentido horario", fontName="DVI",
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
    node(0, 118, 92, 64, "Sinte analógico", ["entrada de la", "interfaz"], colors.HexColor("#f4f8fa"))
    node(122, 118, 92, 64, "SYNTH IN", ["monitoreo", "(no graba)"], colors.HexColor("#f4f8fa"))
    for k in range(3):
        node(250, 196 - k * 48, 104, 40, ["LOOP 1", "LOOP 2", "LOOP …"][k],
             ["E4L Looper", "+ E4L Panner"], ACCENT_LIGHT)
    node(386, 118, 95, 64, "E4L Master", ["Master Bus = Quad", "salidas 1-4 + sub 5", "(altavoces)"],
         ACCENT_LIGHT)
    node(122, 4, 92, 44, "Auriculares", ["salidas 7-8 →", "toma de auriculares"], colors.HexColor("#f3ecf9"), HP)
    node(250, 4, 104, 44, "CUE (auriculares)", ["Master Bus = Binaural"], colors.HexColor("#f3ecf9"), HP)
    arrow([(92, 150), (122, 150)])
    for k in range(3):
        y = 216 - k * 48
        arrow([(214, 150), (232, 150), (232, y), (250, y)])
        arrow([(354, y), (370, y), (370, 150), (386, 150)])
    arrow([(168, 118), (168, 48)], HP, "sinte en vivo", 172, 80)
    arrow([(250, 26), (214, 26)], HP)
    arrow([(433, 118), (433, 72), (302, 72), (302, 48)], HP, "copia de los loops", 330, 76)
    return d


def lfo_diagram():
    W, H = 170 * mm, 38 * mm
    d = Drawing(W, H)
    panels = [("Cycle: giro completo", "cycle"), ("Sin: vaivén ± Depth", "sin"),
              ("Sync: 1 vuelta cada N compases", "sync")]
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
    st = []
    st += [Spacer(1, 40 * mm), P("Envelop for REAPER", "title"),
           P("Espacialización en cuadrafonía con los plugins E4L", "subtitle"),
           Spacer(1, 6), P("Guía de instalación y uso", "subtitle"), Spacer(1, 22 * mm)]
    st.append(box([
        "Este documento explica, paso a paso, cómo montar en REAPER un proyecto donde "
        "<b>cada pista de audio se mueve por cuatro altavoces</b> con sus propias "
        "automatizaciones de movimiento, y una <b>pista master que decodifica a cuadrafonía</b>.",
        "Repositorio del proyecto: <b>github.com/KinoLab07/enveloppe_live_reaper</b>",
    ], kind="info"))
    st.append(Spacer(1, 10 * mm))
    st.append(P("<b>Contenido</b>", "h2"))
    for t in ["1. Qué se hizo hasta ahora", "2. Cómo funciona (la idea en un dibujo)",
              "3. Instalación en REAPER", "4. Preparar el proyecto para cuadrafonía",
              "5. Agregar pistas de audio y posicionarlas",
              "6. Automatizaciones de movimiento", "7. Escuchar con auriculares y exportar",
              "8. Looper en vivo estilo Ableton (sinte analógico)",
              "9. Solución de problemas", "10. Referencia rápida de parámetros"]:
        st.append(P(t, "toc"))
    st.append(PageBreak())

    # 1
    st.append(P("1. Qué se hizo hasta ahora", "h1"))
    st.append(P("<b>Envelop for Live (E4L)</b> es un conjunto de dispositivos para Ableton Live que "
                "sirve para mezclar en sonido envolvente (ambisonics). Esos dispositivos solo "
                "funcionan dentro de Ableton, así que se <b>reescribieron como plugins nativos de "
                "REAPER</b> (formato JSFX). Funcionan en Windows y Mac, no hay que instalar nada "
                "aparte y todos sus controles se pueden automatizar."))
    st.append(table([
        ["Plugin", "Para qué sirve"],
        ["<b>E4L Master Bus</b>", "Va en la pista master de espacialización. Convierte la mezcla "
         "espacial en las señales de los altavoces. Tiene salida <b>Quad (cuadrafonía)</b>, y "
         "también binaural (auriculares), estéreo, 5.1, 7.1, 7.1.4 y otras."],
        ["<b>E4L Mono Panner</b>", "Mueve una fuente mono por el espacio. Incluye LFO de movimiento."],
        ["<b>E4L Stereo Panner</b>", "Mueve una fuente estéreo (izquierda y derecha separadas). "
         "Incluye LFO de movimiento y de apertura."],
        ["<b>E4L Quad Panner</b>", "Mueve un audio que ya es de 4 canales. Incluye LFO."],
        ["E4L Source Panner", "Posición fija en grados o en coordenadas X/Y/Z (sin LFO)."],
        ["E4L Multi-Panner", "Hasta 16 canales de una misma pista (no necesario para tu proyecto)."],
        ["Script <b>E4L - Setup session</b>", "Arma automáticamente el ruteo: crea la pista master "
         "y configura las pistas que elijas."],
    ], [45, 125]))
    st.append(P("Además se hizo:"))
    st += bullets([
        "Pruebas automáticas que comprueban que el sonido sale por donde debe, que los LFO giran "
        "a la velocidad correcta y que la sincronización con el tempo funciona.",
        "Cambio de la licencia del proyecto a <b>GNU GPL v2 o posterior</b>, la misma de E4L, "
        "porque es una obra derivada. Puedes usarlo, modificarlo y compartirlo, siempre que se "
        "mantenga esa licencia y se dé crédito a Envelop.",
        "Todo está publicado en la rama <b>main</b> del repositorio de GitHub.",
    ])

    # 2
    st.append(P("2. Cómo funciona (la idea en un dibujo)", "h1"))
    st.append(P("Cada pista de audio lleva un <b>paneador E4L</b>. El paneador no manda el sonido "
                "directo a los altavoces, sino a un formato intermedio de <b>16 canales</b> "
                "(ambisonics) que describe <i>desde dónde</i> viene el sonido. Todas las pistas se "
                "envían a la pista <b>«E4L Master»</b>, donde el <b>E4L Master Bus</b> lo convierte "
                "en las 4 señales de los altavoces."))
    st.append(flow_diagram())
    st.append(Spacer(1, 4))
    st.append(box([
        "Gracias a este formato intermedio, el mismo proyecto puede escucharse en cuadrafonía, "
        "en auriculares o en otro sistema cambiando <b>solo una opción</b> del Master Bus. "
        "Las automatizaciones de las pistas no cambian."], kind="info", title="¿Por qué 16 canales?"))
    st.append(P("Disposición de los altavoces", "h2"))
    st.append(P("Coloca los cuatro altavoces en cuadrado, a la misma distancia del oyente, y "
                "conéctalos a las salidas de la interfaz de audio así:"))
    st.append(speaker_diagram())
    st.append(box([
        "El orden de E4L va <b>en círculo, en sentido horario</b>: 1 delantero izquierdo, "
        "2 delantero derecho, <b>3 trasero derecho</b>, <b>4 trasero izquierdo</b>. "
        "Muchos equipos usan otro orden (1 FL, 2 FR, 3 RL, 4 RR): si es tu caso, conecta los "
        "cables siguiendo este dibujo, no el número de la etiqueta del equipo."],
        kind="warn", title="Atención con las salidas 3 y 4"))
    st.append(P("Los ángulos se miden como en E4L: <b>0°</b> es el frente, <b>+90°</b> la "
                "derecha, <b>−90°</b> la izquierda y <b>±180°</b> la parte de atrás."))
    st.append(PageBreak())

    # 3
    st.append(P("3. Instalación en REAPER", "h1"))
    st.append(P("Descargar", "h2"))
    st += steps([
        "Abre <b>github.com/KinoLab07/enveloppe_live_reaper</b> y pulsa el botón verde "
        "<b>Code › Download ZIP</b> (o usa el archivo <b>E4L_para_REAPER.zip</b> que te envié).",
        "Descomprime el archivo. Verás las carpetas <b>Effects</b>, <b>Data</b> y <b>Scripts</b>.",
    ])
    st.append(P("Abrir la carpeta de recursos de REAPER", "h2"))
    st.append(P("Es la carpeta donde REAPER guarda sus plugins y scripts. Hay tres maneras de abrirla:"))
    st += bullets([
        "En REAPER pulsa la tecla <b>?</b> (lista de acciones), escribe <b>resource path</b> y haz "
        "doble clic en <b>Show REAPER resource path in explorer/finder</b>.",
        "<b>Windows:</b> pulsa <b>Win + R</b>, escribe <b>%APPDATA%\\REAPER</b> y pulsa Enter.",
        "<b>Mac:</b> en el Finder pulsa <b>Cmd + Shift + G</b> y escribe "
        "<b>~/Library/Application Support/REAPER</b>.",
    ])
    st.append(P("La carpeta correcta contiene, entre otras, las carpetas <b>Effects</b>, <b>Data</b> "
                "y <b>Scripts</b>, y un archivo <b>reaper.ini</b>."))
    st.append(P("Copiar los archivos", "h2"))
    st += steps([
        "Cierra REAPER.",
        "Copia las carpetas <b>Effects</b>, <b>Data</b> y <b>Scripts</b> del zip dentro de la "
        "carpeta de recursos. Si pregunta por <b>carpetas</b>, elige <b>combinar</b>; si pregunta "
        "por <b>archivos</b>, elige <b>reemplazar</b>. Nunca reemplaces la carpeta entera, o "
        "perderás tus otros plugins.",
        "Abre REAPER, abre el navegador de efectos (botón <b>FX</b> de una pista) y pulsa <b>F5</b>. "
        "Escribe <b>E4L</b> en el buscador: deben aparecer los plugins <b>JS: E4L …</b>",
    ])
    st.append(box([
        "Cuando haya una versión nueva, repite estos mismos pasos. Tus proyectos guardados "
        "siguen funcionando y usan automáticamente la versión nueva."], title="Para actualizar"))
    st.append(P("Cargar el script de configuración (una sola vez)", "h2"))
    st += steps([
        "En REAPER abre <b>Actions › Show action list…</b> (o pulsa <b>?</b>).",
        "Abajo a la derecha pulsa <b>New action…</b> y elige <b>Load ReaScript…</b>",
        "Selecciona <b>Scripts/E4L/E4L - Setup session.lua</b> dentro de la carpeta de recursos y "
        "pulsa <b>Abrir</b>. Quedará en la lista como <b>Script: E4L - Setup session.lua</b>.",
        "Opcional: con el script seleccionado, pulsa <b>Add…</b> (abajo a la izquierda) y presiona "
        "una tecla, por ejemplo <b>Shift + E</b>, para lanzarlo con un atajo.",
    ])
    st.append(PageBreak())

    # 4
    st.append(P("4. Preparar el proyecto para cuadrafonía", "h1"))
    st.append(P("Esto se hace <b>una vez por proyecto</b>."))
    st.append(P("Paso A: la interfaz de audio", "h2"))
    st += steps([
        "Abre <b>Options › Preferences › Audio › Device</b>.",
        "Elige tu interfaz de audio y comprueba que estén activadas al menos las "
        "<b>salidas 1 a 4</b>.",
    ])
    st.append(P("Paso B: el master de REAPER a 4 canales", "h2"))
    st += steps([
        "En la pista <b>MASTER</b> pulsa el botón <b>Route</b> (o clic derecho sobre el master › "
        "<b>Routing</b>).",
        "Arriba, en <b>Track channels</b>, elige <b>4</b> (o <b>6</b> si usas sub en la salida 5).",
        "En <b>Audio Hardware Outputs</b> deja la salida que ya existe: canales <b>1/2 → "
        "salidas 1/2</b>.",
        "Pulsa <b>Add new hardware output</b> y elige las <b>salidas 3/4</b>. En esa nueva salida, "
        "cambia el origen a los canales <b>3/4</b>. Así: canales 1-2 → salidas 1-2 y "
        "canales 3-4 → salidas 3-4.",
    ])
    st.append(P("Paso C: crear la pista «E4L Master» con el script", "h2"))
    st += steps([
        "Selecciona las pistas de audio que quieres espacializar (clic en el nombre; "
        "<b>Ctrl/Cmd + clic</b> para elegir varias).",
        "Lanza el script <b>E4L - Setup session</b> (tecla <b>?</b>, busca «E4L», doble clic).",
        "Escribe el número del paneador y pulsa <b>OK</b>: <b>1</b> Stereo, <b>2</b> Mono, "
        "3 Source, <b>4</b> Quad, 5 Multi. Para audio estéreo usa 1, para audio mono usa 2.",
    ])
    st.append(P("El script crea la pista <b>«E4L Master»</b> con el plugin <b>E4L Master Bus</b> y "
                "deja cada pista seleccionada con <b>16 canales</b>, el paneador, el envío al "
                "master principal <b>desactivado</b> y un envío de 16 canales a «E4L Master». "
                "Si lo ejecutas otra vez con otras pistas, reutiliza la misma «E4L Master»."))
    st.append(P("Paso D: poner el Master Bus en cuadrafonía", "h2"))
    st += steps([
        "En la pista «E4L Master» abre el plugin <b>E4L Master Bus</b> (botón <b>FX</b>).",
        "En <b>Decoder</b> elige <b>Quad</b>.",
        "Deja <b>Order Weighting</b> en <b>In-phase (E4L)</b> y <b>Ambisonics Order</b> en "
        "<b>3rd order</b>.",
    ])
    st.append(box([
        "Se midió el decodificador Quad con las tres opciones de <i>Order Weighting</i>. "
        "<b>In-phase (E4L)</b> es la mejor para cuatro altavoces: cuando un sonido gira, el volumen "
        "se mantiene casi constante y ningún altavoz recibe la señal invertida. "
        "Con <i>Basic</i> o <i>max-rE</i>, el sonido baja mucho de volumen entre altavoces."],
        title="¿Por qué «In-phase»?"))
    st.append(P("Paso E: comprobar", "h2"))
    st += bullets([
        "La pista «E4L Master» debe tener <b>16 canales</b> y el envío al master principal "
        "<b>activado</b> (botón <b>Route › Master send</b>).",
        "Las pistas de audio deben tener <b>16 canales</b>, el <b>Master send desactivado</b> y "
        "un envío a «E4L Master» con <b>Audio: 1-16 → 1-16</b>.",
        "Al reproducir, en el medidor del master deben moverse <b>4 barras</b>.",
    ])
    st.append(P("Hacerlo a mano (sin script)", "h2"))
    st.append(P("Si prefieres no usar el script, el resultado es el mismo:"))
    st += steps([
        "Crea una pista, llámala <b>E4L Master</b>, pulsa <b>Route</b> y pon <b>Track channels: "
        "16</b>. Agrégale el plugin <b>JS: E4L Master Bus</b> con <b>Decoder = Quad</b>.",
        "En cada pista de audio: <b>Route</b> › <b>Track channels: 16</b>, desmarca "
        "<b>Master send</b> y en <b>Add new send</b> elige «E4L Master». En ese envío, en "
        "<b>Audio</b> elige <b>Multichannel source › 16 channels › 1-16</b> hacia los canales "
        "<b>1-16</b>.",
        "Agrega a la pista el plugin <b>JS: E4L Stereo Panner</b> (o Mono/Quad).",
    ])

    # 5
    st.append(P("5. Agregar pistas de audio y posicionarlas", "h1"))
    st.append(P("¿Qué paneador uso?", "h2"))
    st.append(table([
        ["Tipo de audio", "Plugin", "Comentario"],
        ["Mono (una voz, un instrumento)", "<b>E4L Mono Panner</b>", "Un punto que se mueve."],
        ["Estéreo", "<b>E4L Stereo Panner</b>", "Dos puntos (izq./der.) que se mueven juntos. "
         "La distancia entre ellos es la <i>Azimuth Spread</i>."],
        ["Ya en 4 canales (cuadrafónico)", "<b>E4L Quad Panner</b>", "Cuatro puntos que se mueven "
         "juntos: el audio debe estar en los canales 1-4 de la pista."],
    ], [50, 45, 75]))
    st.append(P("Los controles básicos", "h2"))
    st.append(table([
        ["Control", "Qué hace", "Para cuadrafonía"],
        ["<b>Azimuth</b>", "Dirección en grados: 0 frente, +90 derecha, −90 izquierda, ±180 atrás.",
         "−45 = altavoz 1, +45 = altavoz 2, +135 = altavoz 3, −135 = altavoz 4."],
        ["<b>Radius</b> y <b>Range</b>", "Distancia: Radius × Range. Más lejos = más bajo "
         "(−1,5 dB por unidad).", "Pon <b>Radius = 0,1</b> con Range 10 para volumen completo."],
        ["<b>Elevation</b>", "Altura en grados.", "Déjala en <b>0</b>: la cuadrafonía no tiene "
         "altavoces arriba."],
        ["<b>Azimuth Spread</b>", "(Stereo/Quad) Apertura entre los canales.", "Stereo: 30 = "
         "estrecho; 45 = izq. y der. en los altavoces 1 y 2 si Azimuth = 0."],
        ["<b>Azimuth Spread Mode</b>", "(Quad) LR = cuadrado; X = traseros cruzados; "
         "W = abanico.", "Con LR y apertura 90, cada canal va a su altavoz."],
    ], [32, 70, 68]))
    st.append(box([
        "Con los valores de fábrica (Radius 1 y Range 10) el sonido se escucha <b>13,5 dB más "
        "bajo</b>: así funciona E4L, que lo considera «lejos». Para oírlo a volumen normal, baja "
        "<b>Radius a 0,1</b>. Puedes automatizar Radius para acercar y alejar el sonido."],
        kind="warn", title="¿Suena muy bajo?"))
    st.append(P("La ventana del plugin muestra una vista desde arriba: el círculo es la sala, el "
                "centro es el oyente (mirando hacia arriba) y los puntos de color son las "
                "fuentes. Sirve para ver en tiempo real cómo se mueven."))

    # 6
    st.append(P("6. Automatizaciones de movimiento", "h1"))
    st.append(P("Hay dos formas de mover el sonido, y se pueden combinar:"))
    st += bullets([
        "<b>LFO integrados</b> (como en E4L): movimientos repetitivos automáticos, como giros, "
        "vaivenes o movimientos sincronizados al tempo. Solo hay que activarlos.",
        "<b>Envolventes de REAPER</b>: dibujas tú el recorrido en la línea de tiempo, punto "
        "por punto.",
    ])
    st.append(KeepTogether([P("6.1 LFO integrados", "h2"), lfo_diagram()]))
    st.append(table([
        ["Control del LFO de azimut", "Qué hace"],
        ["<b>Azimuth LFO On/Off</b>", "Enciende o apaga el movimiento automático."],
        ["<b>Mode</b>", "<b>Cycle</b>: gira 360° completos, dando vueltas por los 4 altavoces. "
         "<b>Sin</b>: va y vuelve alrededor de <i>Azimuth</i>, ± <i>Depth</i> grados."],
        ["<b>Time Mode</b>", "<b>Freq</b>: velocidad en Hz (vueltas por segundo). "
         "<b>Sync</b>: sincronizado al tempo del proyecto."],
        ["<b>Frequency</b> y <b>Rate</b>", "(Freq) La velocidad es Frequency × Rate. Con un Rate "
         "negativo gira al revés. Ejemplo: 0,1 Hz × 0,5 = una vuelta cada 20 s."],
        ["<b>Sync (bars)</b>", "(Sync) Compases por vuelta: 1/4, 1/2, 1, 2, 3, 4, 6, 8, 16, 32, 64."],
        ["<b>Direction</b>", "(Sync) Clockwise = sentido horario; Counter = antihorario."],
        ["<b>Depth</b>", "(Sin) Amplitud del vaivén en grados."],
        ["<b>Azimuth</b>", "Con el LFO encendido, indica el punto de partida (Cycle) o el "
         "centro del vaivén (Sin)."],
    ], [48, 122]))
    st.append(P("Recetas listas para usar", "h2"))
    st.append(table([
        ["Movimiento deseado", "Ajustes"],
        ["Giro lento por toda la sala", "LFO On · Mode <b>Cycle</b> · Time Mode <b>Freq</b> · "
         "Frequency <b>0,1</b> · Rate <b>1</b> (10 s por vuelta). Para que gire al revés: Rate −1."],
        ["Giro de una vuelta cada 4 compases", "LFO On · Mode <b>Cycle</b> · Time Mode "
         "<b>Sync</b> · Sync <b>4</b> · Direction a elección."],
        ["Vaivén entre los dos altavoces delanteros", "Azimuth <b>0</b> · LFO On · Mode <b>Sin</b> "
         "· Depth <b>45</b> · Frequency 0,25 (4 s ida y vuelta)."],
        ["Vaivén entre delante y atrás por la derecha", "Azimuth <b>90</b> · Mode <b>Sin</b> · "
         "Depth <b>45</b> (va de 45° a 135°, entre los altavoces 2 y 3)."],
        ["Ida y vuelta de lado a lado pasando por delante", "Azimuth <b>0</b> · Mode <b>Sin</b> · "
         "Depth <b>90</b>."],
        ["Una fuente estéreo que «respira»", "Stereo Panner · <b>Azimuth Spread LFO On</b> · "
         "Frequency 0,2 · Depth 30. Los canales se abren y cierran."],
    ], [60, 110]))
    st.append(box([
        "En modo <b>Sync</b>, mientras REAPER reproduce, el giro queda «enganchado» a la posición "
        "de la canción: el sonido está siempre en el mismo lugar en el mismo compás, en cada "
        "reproducción y al exportar."], title="Sincronizado al tempo"))

    st.append(P("6.2 Envolventes de REAPER (dibujar el recorrido)", "h2"))
    st += steps([
        "En la pista, pulsa el botón de <b>envolventes</b> (el icono con una curva, junto a "
        "<b>FX</b>). Se abre la lista de parámetros automatizables.",
        "Busca el plugin <b>E4L Stereo Panner</b> (o Mono/Quad) y marca <b>Azimuth</b>. "
        "Aparece un carril de automatización debajo de la pista.",
        "<b>Clic</b> en el carril para añadir puntos; <b>arrastra</b> los puntos para moverlos. "
        "Arriba del carril es +180°, el centro es 0° (frente) y abajo es −180°.",
        "Clic derecho sobre un punto para cambiar la forma de la curva (lineal, suave, escalón…).",
        "Repite con otros parámetros: <b>Radius</b> para acercar o alejar, o "
        "<b>Azimuth Spread</b> para abrir o cerrar el estéreo.",
    ])
    st.append(P("<b>Grabar el movimiento en tiempo real:</b> en el botón de modo de automatización "
                "de la pista (normalmente dice <b>Trim/Read</b>), elige <b>Latch</b>. Reproduce y "
                "mueve el control <b>Azimuth</b> del plugin con el ratón: REAPER grabará el "
                "movimiento. Al terminar, vuelve a poner el modo en <b>Read</b>."))
    st.append(box([
        "+180° y −180° son el mismo punto (atrás). Si dibujas una línea de +170 a −170, REAPER "
        "pasará por todos los valores intermedios y el sonido <b>dará la vuelta por delante</b>. "
        "Para vueltas completas usa el LFO en modo <b>Cycle</b>, o pon un punto en +180 y el "
        "siguiente en −180 con forma <b>escalón</b> (square)."],
        kind="warn", title="Cuidado al cruzar por detrás"))
    st.append(P("6.3 Combinar LFO y envolventes", "h2"))
    st.append(P("Los propios controles del LFO también se pueden automatizar. Por ejemplo:"))
    st += bullets([
        "Automatiza <b>Azimuth LFO On/Off</b> para que el giro empiece en el compás 9 y pare "
        "en el 17.",
        "Automatiza <b>Azimuth LFO Frequency</b> para que el giro acelere poco a poco.",
        "Automatiza <b>Azimuth</b> con el LFO en <b>Sin</b> para que el centro del vaivén se "
        "desplace por la sala.",
    ])
    st.append(P("Otra opción es la <b>modulación de parámetros</b> de REAPER: en el plugin, pulsa "
                "<b>Param › Parameter modulation</b>. Permite, por ejemplo, que el volumen de otra "
                "pista mueva el Azimuth."))
    st.append(PageBreak())

    # 7
    st.append(P("7. Escuchar con auriculares y exportar", "h1"))
    st.append(P("Previsualizar con auriculares", "h2"))
    st.append(P("Si no tienes los cuatro altavoces a mano, en el <b>E4L Master Bus</b> cambia "
                "<b>Decoder</b> a <b>Binaural (3rd-order)</b>. El sonido saldrá en las salidas 1-2 "
                "con efecto 3D para auriculares (delante, atrás y a los lados). "
                "<b>Vuelve a Quad</b> antes de exportar o de usar los altavoces."))
    st.append(P("Exportar el archivo cuadrafónico", "h2"))
    st += steps([
        "<b>File › Render…</b>",
        "<b>Source:</b> Master mix.",
        "<b>Channels:</b> elige <b>4</b>.",
        "Formato <b>WAV</b> y pulsa <b>Render</b>.",
    ])
    st.append(P("El archivo tendrá 4 canales en el orden de E4L: <b>1</b> delantero izquierdo, "
                "<b>2</b> delantero derecho, <b>3</b> trasero derecho, <b>4</b> trasero izquierdo. "
                "Avísale a quien lo reproduzca, o pídeme una opción para exportar en otro orden."))

    # 8
    st.append(PageBreak())
    st.append(P("8. Looper en vivo estilo Ableton (sinte analógico)", "h1"))
    st.append(P("Esta plantilla sirve para componer en vivo: tocas el sinte analógico y lo "
                "escuchas <b>solo en los auriculares</b>. Cuando un sonido te gusta, lo grabas en "
                "un <b>loop de N compases</b> que entra <b>justo en el siguiente compás</b>, "
                "sincronizado con el «loop general» (el tempo y los compases del proyecto). "
                "Desde ese momento suena en la cuadrafonía, en su propia posición y con sus "
                "movimientos."))
    st.append(live_diagram())
    st.append(Spacer(1, 6))
    st.append(P("Antes de empezar: auriculares y sub (Mbox Pro)", "h2"))
    st.append(P("Los auriculares tienen que recibir una mezcla <b>distinta</b> de la de los altavoces. "
                "La plantilla manda la mezcla de auriculares a las <b>salidas 7-8</b> de la "
                "interfaz, que no van a ningún altavoz. En la <b>Mbox Pro</b>, cada salida de "
                "auriculares (A y B) tiene su propia mezcla, configurable en el panel de control "
                "del driver:"))
    s_ = steps([
        "En REAPER, abre <b>Options › Preferences › Audio › Device</b> y pulsa el botón del panel "
        "de control de la interfaz (<b>ASIO Configuration…</b> en Windows), o abre el "
        "<b>Mbox Pro Control Panel</b>.",
        "En la configuración de salidas, busca <b>Headphones A</b> (y B si la usas) y elige como "
        "origen la señal que llega del ordenador por las <b>salidas 7-8</b>. Los nombres "
        "exactos dependen de la versión del driver.",
        "Comprueba que las salidas <b>1-4</b> (altavoces) y <b>5</b> (sub) reciben lo que llega "
        "del ordenador por esas mismas salidas.",
        "El <b>volumen maestro</b> de la Mbox afecta a todas las salidas. Si quieres que solo "
        "controle los auriculares, desmarca <i>Master Vol.</i> para las demás salidas en "
        "<b>Output Setup</b>.",
    ])
    st += s_
    st.append(P("Si en tu interfaz las salidas 7-8 no existen, indica en el script otro par libre "
                "(campo <i>Headphones output</i>)."))
    st.append(box([
        "El script pone el plugin <b>E4L Sub Out</b> en el <b>master de REAPER</b>: la suma de "
        "<b>todo lo que llega al master</b> sale también por la <b>salida 5</b>. Por eso "
        "<b>cualquier pista que agregues</b> (loops, pistas espacializadas o pistas normales) "
        "alimenta el sub sin hacer nada más.",
        "En el plugin ajustas <b>Sub Level</b> (volumen) y <b>Sub Low-pass</b> (0 = sin filtro, "
        "si tu sub tiene su propio filtro de corte; si no, 80-120 Hz).",
        "Para agregarlo a un proyecto que ya tengas, ejecuta el script "
        "<b>E4L - Add sub to master</b> y escribe la salida del sub (5).",
    ], kind="info", title="El sub (salida 5)"))
    st.append(P("Crear la plantilla", "h2"))
    st += steps([
        "Copia de nuevo las carpetas <b>Effects</b> y <b>Scripts</b> en la carpeta de recursos "
        "de REAPER (sección 3), para tener el <b>E4L Looper</b> y los scripts nuevos.",
        "En un proyecto nuevo, carga y ejecuta el script <b>E4L - Live Looper template</b> "
        "(<b>Actions › New action › Load ReaScript…</b>, como en la sección 3).",
        "Completa la ventana que aparece y pulsa <b>OK</b>:",
    ])
    st.append(table([
        ["Campo", "Qué poner", "Por defecto"],
        ["Loop tracks to add", "Cuántas pistas de loop crear.", "8"],
        ["Synth input (first channel)", "Entrada de la interfaz donde está conectado el sinte.", "1"],
        ["Synth input: 1 mono 2 stereo", "1 si el sinte tiene una salida; 2 si tiene dos.", "1"],
        ["Headphones output (first channel)", "Primera salida para los auriculares.", "7 (salidas 7-8)"],
        ["Loop panner: 1 Mono 2 Stereo", "Paneador de cada loop: Mono para un sinte mono.", "1"],
        ["Sub output (0 = none)", "Salida del subwoofer; recibe la suma de todo.", "5"],
    ], [52, 88, 30]))
    st.append(P("El script crea <b>SYNTH IN</b>, las pistas <b>LOOP 1…8</b>, <b>E4L Master</b> "
                "(Quad, con el sub) y <b>CUE (auriculares)</b>. También prepara el master de REAPER "
                "(salidas 1-2, 3-4 y el sub en la 5) "
                "y calcula la <b>compensación de latencia</b> de grabación de tu interfaz. Cada "
                "loop empieza en una posición distinta de la sala (−45°, 45°, 135°, −135°…). Si "
                "lo vuelves a ejecutar en el mismo proyecto, solo agrega más pistas LOOP."))
    st.append(P("Tocar en vivo, paso a paso", "h2"))
    st += steps([
        "Ajusta el <b>tempo</b> y el <b>compás</b> (ver el recuadro de abajo).",
        "Pulsa <b>PLAY</b> en REAPER (barra espaciadora). El proyecto en marcha es el «loop "
        "general»: todos los loops se sincronizan con sus compases.",
        "Toca el sinte: lo oyes en los auriculares. Por los altavoces todavía no sale nada.",
        "Abre el <b>E4L Looper</b> de <b>LOOP 1</b> (botón FX), elige <b>Length</b> (1, 2, 4, 8, "
        "16 o 32 compases) y pulsa <b>REC</b>.",
        "El looper muestra <b>ARMED - next bar</b>. Al empezar el siguiente compás pasa a "
        "<b>REC</b> (rojo) y graba exactamente los compases elegidos.",
        "Al terminar pasa solo a <b>PLAY</b> (verde): el loop suena en la cuadrafonía y en los "
        "auriculares (por la pista CUE).",
        "Para el siguiente sonido, usa <b>LOOP 2</b>, y así sucesivamente: cada capa en su pista, "
        "con su posición.",
    ])
    st.append(box([
        "<b>En la barra de transporte</b> (abajo de las pistas): a la derecha se ven el tempo "
        "(<b>BPM</b>, por ejemplo 120) y el compás (por ejemplo <b>4/4</b>). <b>Doble clic</b> en "
        "el número de BPM o del compás para escribir el valor nuevo. También puedes arrastrar el "
        "BPM hacia arriba o hacia abajo con el ratón.",
        "<b>En la configuración del proyecto:</b> <b>File › Project settings…</b> (Alt + Enter), "
        "pestaña <b>Project settings</b>: <i>Project BPM</i> y <i>Time signature</i>.",
        "<b>Por pulsaciones:</b> la acción <i>Transport: Tap tempo</i> (en la lista de acciones) "
        "calcula el tempo según tus golpes.",
        "<b>Metrónomo:</b> el botón con forma de metrónomo en la barra de transporte. Para que "
        "suene solo en los auriculares, en <b>Options › Metronome settings</b> envíalo a las "
        "salidas 7-8.",
        "Ajusta el tempo <b>antes</b> de grabar loops. Si lo cambias después, los loops ya "
        "grabados se aceleran o se frenan (y cambia su afinación).",
    ], kind="info", title="Cómo ajustar tempo y compás"))
    st.append(table([
        ["Botón del looper", "Qué hace"],
        ["<b>REC</b>", "Graba en el siguiente compás. Si la pista ya tiene un loop, lo reemplaza; "
         "el anterior sigue sonando hasta que empieza la nueva grabación."],
        ["<b>PLAY</b>", "Para o arranca el loop en el siguiente compás, siempre en fase con el "
         "proyecto."],
        ["<b>OVERDUB</b>", "Mientras está encendido, lo que tocas se suma encima del loop."],
        ["<b>CLEAR</b>", "Borra el loop."],
        ["Loop Volume", "Volumen del loop."],
        ["Input Thru", "Si lo enciendes, el sinte en vivo también sale por los altavoces desde "
         "esa pista. Normalmente apagado."],
        ["Recording Latency Compensation", "La pone el script. Si el loop suena adelantado o "
         "atrasado respecto al tempo, ajústala: más ms si suena tarde."],
    ], [48, 122]))
    st.append(P("El movimiento en el espacio se hace con el paneador que va después del looper, en "
                "la misma pista. Funciona igual que en la sección 6: LFO, envolventes, "
                "o ambos."))
    st.append(P("Controlarlo con teclado o con un controlador MIDI", "h2"))
    st += bullets([
        "<b>Botón por loop (recomendado con un controlador):</b> en el looper de cada pista pulsa "
        "<b>Param › Learn</b>, elige <b>Record</b> (o <b>Play</b>) y pulsa el botón del "
        "controlador. Repite en cada loop.",
        "<b>Con atajos de teclado:</b> carga también los scripts <b>E4L - Loop REC (selected "
        "tracks)</b>, <b>E4L - Loop PLAY-STOP (selected tracks)</b> y <b>E4L - Loops STOP all</b>, "
        "y asígnales una tecla (Actions › Add). REC y PLAY-STOP actúan sobre las pistas "
        "seleccionadas.",
        "<b>Metrónomo solo en auriculares:</b> en <b>Options › Metronome settings</b> envía "
        "el metrónomo a las salidas de los auriculares (por ejemplo 7-8), no a la 1-4.",
    ])
    st.append(box([
        "• REAPER tiene que estar <b>reproduciendo</b>: el looper sigue la posición del proyecto. "
        "No uses la repetición (repeat) de REAPER, salvo que su duración sea múltiplo de la de "
        "los loops.",
        "• Los loops <b>viven en la memoria del plugin</b> mientras REAPER está abierto: "
        "<b>no se guardan al cerrar el proyecto</b>. Para conservar una sesión, expórtala "
        "(sección 7) o graba la salida.",
        "• Duración máxima de cada loop: unos 5 minutos a 48 kHz (de sobra para 32 compases).",
        "• Si prefieres oír el sinte sin la latencia del ordenador, usa el <b>monitoreo directo</b> "
        "de tu interfaz y baja el volumen de la pista SYNTH IN.",
    ], kind="warn", title="A tener en cuenta"))

    # 9
    st.append(PageBreak())
    st.append(P("9. Solución de problemas", "h1"))
    st.append(table([
        ["Problema", "Solución"],
        ["Los plugins E4L no aparecen", "Comprueba que copiaste <b>Effects/E4L</b> dentro de la "
         "carpeta de recursos (no en otra carpeta) y pulsa <b>F5</b> en el navegador de FX."],
        ["No se oye nada", "La pista de audio debe tener <b>16 canales</b> y un envío a «E4L "
         "Master». «E4L Master» debe tener el <b>Master send</b> activado. Revisa que Radius no "
         "esté muy alto."],
        ["Se oye muy bajo", "Baja <b>Radius</b> a 0,1 (ver sección 5)."],
        ["Suena solo por 2 altavoces", "El master de REAPER debe tener <b>4 canales</b> y las "
         "salidas de hardware 1/2 y 3/4 (sección 4, paso B). El Master Bus debe estar en "
         "<b>Quad</b>."],
        ["Los traseros están al revés", "Salida 3 = trasero <b>derecho</b> y salida 4 = trasero "
         "<b>izquierdo</b>. Intercambia esos dos cables."],
        ["Se oye el sonido también sin espacializar", "El <b>Master send</b> de la pista de audio "
         "está activado: desactívalo (Route › Master send)."],
        ["El looper dice «Press play in REAPER»", "Pulsa PLAY: el looper solo graba y "
         "reproduce con el proyecto en marcha."],
        ["El sinte sale por los altavoces", "Revisa que la pista SYNTH IN no tenga el Master send "
         "activado y que el looper tenga <b>Input Thru</b> apagado."],
        ["No oigo el sinte en los auriculares", "La pista SYNTH IN debe estar armada (botón rojo) "
         "con el monitoreo activado. En el panel de la Mbox, los auriculares deben tomar las "
         "salidas 7-8 del ordenador (sección 8)."],
        ["El sub no suena", "El master de REAPER debe tener el plugin <b>E4L Sub Out</b>, "
         "6 canales y una salida de hardware mono hacia la salida 5. El script <b>E4L - Add sub "
         "to master</b> lo configura todo."],
        ["El loop está un poco desfasado", "Ajusta <b>Recording Latency Compensation</b> en el "
         "looper (sección 8)."],
        ["El script da un error", "Copia el texto del error o haz una captura y envíamela."],
        ["El Master Bus dice «HRIR filters not found»", "Solo afecta al modo binaural. Falta la "
         "carpeta <b>Data/E4L/hrtf</b> en la carpeta de recursos."],
    ], [52, 118]))

    # 9
    st.append(PageBreak())
    st.append(KeepTogether([P("10. Referencia rápida de parámetros", "h1"),
                            P("E4L Master Bus", "h2"), table([
        ["Parámetro", "Valores", "Recomendado para tu proyecto"],
        ["Decoder", "Binaural, Stereo, Quad, Octo, 5.1, 7.1, 5.1.2, 7.1.4, AmbiX", "<b>Quad</b>"],
        ["Order Weighting", "In-phase (E4L), max-rE, Basic", "<b>In-phase (E4L)</b>"],
        ["Ambisonics Order", "3rd order (16 ch), 1st order (4 ch)", "<b>3rd order</b>"],
        ["Input Gain / Output Gain", "−70 a +6 dB", "0 dB; ajusta según necesites"],
        ["Sub Output", "Sub propio del decodificador (0 = apagado)", "<b>0</b>: el sub va en el "
         "master (E4L Sub Out)"],
    ], [40, 80, 50])]))
    st.append(P("E4L Mono / Stereo / Quad Panner", "h2"))
    st.append(table([
        ["Grupo", "Parámetros"],
        ["Posición", "Azimuth (−180…180), Elevation (−90…90), Radius (0…1), Range (1…40)"],
        ["Apertura (Stereo/Quad)", "Azimuth Spread, Elevation Spread, Azimuth Spread Mode (Quad)"],
        ["LFO de azimut", "On/Off, Mode (Cycle/Sin), Time Mode (Freq/Sync), Frequency, Rate, "
         "Sync, Direction, Depth"],
        ["LFO de elevación", "On/Off, Polarity (Unipolar/Bipolar), Time Mode, Frequency, Rate, "
         "Sync, Direction, Depth. No se necesita en cuadrafonía."],
        ["LFO de apertura (Stereo/Quad)", "On/Off, Mode (Freq/Sync), Frequency, Sync, Depth"],
    ], [45, 125]))
    st.append(P("E4L Sub Out (en el master de REAPER)", "h2"))
    st.append(table([
        ["Parámetro", "Valores", "Recomendado"],
        ["Sub Output (channel)", "1 a 16", "<b>5</b>"],
        ["Sum of", "Canales 1-4 (quad), 1-2 o 1-6", "<b>1-4</b>"],
        ["Sub Level (dB)", "−40 a +12", "0 dB; ajústalo a oído"],
        ["Sub Low-pass (Hz)", "0 = sin filtro, o 40-250", "0 si el sub tiene filtro propio; si no, 80-120"],
        ["Sub", "On / Muted", "On"],
    ], [45, 70, 55]))
    st.append(P("E4L Looper", "h2"))
    st.append(table([
        ["Parámetro", "Valores"],
        ["Length (bars)", "1, 2, 4, 8, 16, 32 compases"],
        ["Record / Play / Overdub / Clear", "Botones (On/Off), cuantizados al compás"],
        ["Loop Volume (dB)", "−60 a +12"],
        ["Input Thru", "Off / On"],
        ["Recording Latency Compensation (ms)", "0 a 500"],
    ], [60, 110]))
    st.append(Spacer(1, 8))
    st.append(P("Envelop for Live © Envelop (envelop.us), Mark C. Slee y colaboradores. "
                "Port para REAPER bajo licencia GNU GPL v2 o posterior. HRTF: IRCAM Listen. "
                "Si E4L te resulta útil, considera apoyar a Envelop en envelop.us/memberships.",
                "small"))

    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFont("DV", 8)
        canvas.setFillColor(GREY)
        if doc.page > 1:
            canvas.drawString(20 * mm, 287 * mm, "Envelop for REAPER · Guía de cuadrafonía")
            canvas.drawRightString(190 * mm, 10 * mm, "Página %d" % doc.page)
            canvas.setStrokeColor(colors.HexColor("#dddddd"))
            canvas.line(20 * mm, 285 * mm, 190 * mm, 285 * mm)
        canvas.restoreState()

    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=18 * mm, bottomMargin=16 * mm,
                            title="Envelop for REAPER - Guía de cuadrafonía",
                            author="KinoLab07", subject="Instalación y uso de los plugins E4L en REAPER")
    doc.build(st, onFirstPage=on_page, onLaterPages=on_page)


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Guia_E4L_REAPER_Cuadrafonia.pdf")
    build(out)
    print("wrote", out)
