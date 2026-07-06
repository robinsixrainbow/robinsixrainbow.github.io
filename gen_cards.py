#!/usr/bin/env python3
"""planetarian-style meishi — 3 faces (ZH / EN / JP), 91×55mm trim + 3mm bleed.
Canvas units: 0.1mm  →  page 970×610, trim (30,30)-(940,580)."""
import random

W, H = 970, 610
TX0, TY0, TX1, TY1 = 30, 30, 940, 580          # trim box
SAFE = 50                                       # safe inset from trim

CYAN  = "#28efef"
GLOW  = "#22c8ff"
WHITE = "#eaf7f8"

# ---- Summer Triangle: real J2000 geometry lifted from the CV site (viewBox 1000×800)
V  = (247.4,160.3); D = (60.0,457.7); A = (626.0,501.8)
MEMBER_LINES = [((247.4, 160.3), (261.7, 185.9)), ((261.7, 185.9), (267.4, 216.0)), ((267.4, 216.0), (324.8, 240.5)), ((324.8, 240.5), (320.1, 211.9)), ((320.1, 211.9), (261.7, 185.9)), ((60.0, 457.7), (151.7, 439.9)), ((151.7, 439.9), (248.3, 396.7)), ((248.3, 396.7), (368.1, 352.0)), ((118.6, 322.0), (151.7, 439.9)), ((151.7, 439.9), (206.3, 541.3)), ((603.6, 476.7), (626.0, 501.8)), ((626.0, 501.8), (660.9, 531.7)), ((626.0, 501.8), (751.6, 434.8)), ((751.6, 434.8), (769.2, 639.7)), ((751.6, 434.8), (940.0, 373.4))]
MEMBER_STARS = [(261.7, 185.9, 0.9), (267.4, 216.0, 0.8), (324.8, 240.5, 1.2), (320.1, 211.9, 1.1), (151.7, 439.9, 1.6), (118.6, 322.0, 1.3), (206.3, 541.3, 1.4), (368.1, 352.0, 1.3), (248.3, 396.7, 1.0), (603.6, 476.7, 1.4), (660.9, 531.7, 1.0), (769.2, 639.7, 1.2), (751.6, 434.8, 1.1), (940.0, 373.4, 1.1)]

def map_chart():
    pts = [V, D, A] + [(x, y) for x, y, _ in MEMBER_STARS]
    xs = [min(p[0] for p in pts), max(p[0] for p in pts)]
    ys = [min(p[1] for p in pts), max(p[1] for p in pts)]
    pad = 60
    bw, bh = (xs[1]-xs[0])+2*pad, (ys[1]-ys[0])+2*pad
    # chart zone on card (right side)
    zx0, zy0, zx1, zy1 = 565, 55, 945, 575
    s = min((zx1-zx0)/bw, (zy1-zy0)/bh)
    ox = zx0 + ((zx1-zx0) - bw*s)/2 - (xs[0]-pad)*s
    oy = zy0 + ((zy1-zy0) - bh*s)/2 - (ys[0]-pad)*s
    f = lambda p: (p[0]*s+ox, p[1]*s+oy)
    return f, s

def starfield(seed, n=64, avoid=None):
    rnd = random.Random(seed)
    out = []
    for _ in range(n):
        x = rnd.uniform(TX0+8, TX1-8); y = rnd.uniform(TY0+8, TY1-8)
        r = rnd.uniform(1.5, 5.2); a = rnd.uniform(0.18, 0.8)
        halo = rnd.random() < 0.08
        out.append((x, y, r, a, halo))
    return out

def memori(x, flip=False):
    """three-tier ruler ticks along a vertical strip at x (site .memori grammar)"""
    g = []
    y = TY0
    i = 0
    while y <= TY1:
        if i % 100 == 0:   ln, col, w = 14, CYAN, 1.6            # major every 10mm
        elif i % 40 == 0:  ln, col, w = 10, "rgba(255,255,255,0.55)", 1.2
        elif i % 10 == 0:  ln, col, w = 6,  "rgba(255,255,255,0.22)", 1.0
        else: ln = 0
        if ln:
            x2 = x - ln if flip else x + ln
            g.append(f'<line x1="{x}" y1="{y:.0f}" x2="{x2}" y2="{y:.0f}" stroke="{col}" stroke-width="{w}"/>')
        y += 1; i += 1
    return "\n".join(g)

def boxline(cx, y, w):
    """site hero boxline: faded hairline + end ticks + double center dot"""
    x0, x1 = cx - w/2, cx + w/2
    return f'''<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="url(#bl)" stroke-width="1.4" filter="url(#soft)"/>
<line x1="{x0+2}" y1="{y-5}" x2="{x0+2}" y2="{y+5}" stroke="rgba(255,255,255,0.5)" stroke-width="1"/>
<line x1="{x1-2}" y1="{y-5}" x2="{x1-2}" y2="{y+5}" stroke="rgba(255,255,255,0.5)" stroke-width="1"/>
<circle cx="{cx}" cy="{y}" r="7" fill="rgba(40,239,239,0.3)"/>
<circle cx="{cx}" cy="{y}" r="3" fill="{CYAN}"/>'''

def chart_svg(labels, label_font):
    f, s = map_chart()
    out = ['<g>']
    # member lines
    for a, b in MEMBER_LINES:
        (x1,y1),(x2,y2) = f(a), f(b)
        out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="rgba(40,239,239,0.20)" stroke-width="1.2" stroke-linecap="round"/>')
    # dashed triangle
    for a, b in [(D,V),(V,A),(A,D)]:
        (x1,y1),(x2,y2) = f(a), f(b)
        out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="rgba(40,239,239,0.42)" stroke-width="1.2" stroke-dasharray="4 13" stroke-linecap="round"/>')
    # member stars
    for x, y, r in MEMBER_STARS:
        X, Y = f((x,y))
        out.append(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="{r*1.35:.1f}" fill="rgba(40,239,239,0.5)"/>')
    # the three: crosshairs + bright core + glow
    tri = [(V, labels[0]), (D, labels[1]), (A, labels[2])]
    for (p, (name, dx, dy, anch)) in tri:
        X, Y = f(p); arm = 46*s
        out.append(f'<g stroke="rgba(140,230,240,0.35)" stroke-width="1">'
                   f'<line x1="{X-arm:.1f}" y1="{Y:.1f}" x2="{X+arm:.1f}" y2="{Y:.1f}"/>'
                   f'<line x1="{X:.1f}" y1="{Y-arm:.1f}" x2="{X:.1f}" y2="{Y+arm:.1f}"/></g>')
        out.append(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="8" fill="rgba(34,200,255,0.35)" filter="url(#soft)"/>')
        out.append(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="4.2" fill="rgba(234,247,248,0.95)"/>')
        out.append(f'<text x="{X+dx:.1f}" y="{Y+dy:.1f}" text-anchor="{anch}" font-family="{label_font}" '
                   f'font-size="15" fill="rgba(234,247,248,0.85)">{name}</text>')
    out.append('</g>')
    return "\n".join(out)

import qrcode as _qr
def qr_block(x, y, size, url="https://robinsixrainbow.github.io/"):
    q = _qr.QRCode(error_correction=_qr.constants.ERROR_CORRECT_H, border=0)
    q.add_data(url); q.make(fit=True)
    m = q.get_matrix(); n = len(m)
    mod = size / n
    quiet = 4 * mod
    px, py, pw = x - quiet, y - quiet, size + 2*quiet
    out = [f'<rect x="{px:.1f}" y="{py:.1f}" width="{pw:.1f}" height="{pw:.1f}" rx="6" '
           f'fill="rgba(3,8,16,0.94)" stroke="rgba(255,255,255,0.18)" stroke-width="1"/>']
    for r in range(n):
        run = None
        for c in range(n + 1):
            filled = c < n and m[r][c]
            if filled and run is None: run = c
            elif not filled and run is not None:
                out.append(f'<rect x="{x+run*mod:.2f}" y="{y+r*mod:.2f}" '
                           f'width="{(c-run)*mod+0.15:.2f}" height="{mod+0.15:.2f}" fill="#f2fbfc"/>')
                run = None
    return "\n".join(out)

def face(seed, cfg):
    stars = "\n".join(
        (f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r*3.2:.1f}" fill="rgba(140,230,240,{a*0.25:.2f})"/>' if halo else '') +
        f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.1f}" fill="rgba(234,247,248,{a:.2f})"/>'
        for x, y, r, a, halo in starfield(seed))

    name_block = cfg["name_block"]
    roles = "\n".join(
        f'<text x="{SAFE+TX0}" y="{y}" font-family="{cfg["cjk"]}" font-size="{cfg["role_size"]}" fill="rgba(255,255,255,0.86)">{t}</text>'
        for y, t in cfg["roles"])
    contacts = []
    cy0 = 458
    for i, (lab, val) in enumerate(cfg["contacts"]):
        y = cy0 + i*34
        contacts.append(f'<text x="{SAFE+TX0}" y="{y}" font-family="{cfg["label_font"]}" font-size="13" fill="rgba(255,255,255,0.55)">{lab}</text>')
        contacts.append(f'<text x="{SAFE+TX0+92}" y="{y}" font-family="{cfg["latin"]}" font-size="17" fill="{WHITE}">{val}</text>')
    contacts = "\n".join(contacts)

    field_line = (f'<line x1="{SAFE+TX0}" y1="{SAFE+TY0+2}" x2="{SAFE+TX0+16}" y2="{SAFE+TY0+2}" stroke="{CYAN}" stroke-width="1.6"/>'
                  f'<text x="{SAFE+TX0+26}" y="{SAFE+TY0+7}" font-family="{cfg["label_font"]}" font-size="14" '
                  f'fill="rgba(255,255,255,0.7)">{cfg["field"]}</text>')

    rotated = (f'<text x="898" y="506" font-family="Amiri" font-size="15" fill="rgba(255,255,255,0.5)" '
               f'text-anchor="end">Summer Triangle · Epoch J2034.514</text>'
               f'<text x="898" y="524" font-family="Amiri" font-size="12" fill="rgba(255,255,255,0.38)" '
               f'text-anchor="end">2034·07·07 23:24 JST · Vega culmination · 34°42′N 137°44′E</text>')

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="97mm" height="61mm" viewBox="0 0 {W} {H}">
<defs>
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#050b16"/><stop offset="0.45" stop-color="#0a1424"/>
    <stop offset="0.75" stop-color="#0b1730"/><stop offset="1" stop-color="#050b16"/>
  </linearGradient>
  <radialGradient id="haze" cx="0.72" cy="0.42" r="0.75">
    <stop offset="0" stop-color="rgba(34,200,255,0.10)"/><stop offset="1" stop-color="rgba(34,200,255,0)"/>
  </radialGradient>
  <linearGradient id="bl" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{CYAN}" stop-opacity="0"/><stop offset="0.15" stop-color="{CYAN}" stop-opacity="0.55"/>
    <stop offset="0.5" stop-color="{CYAN}" stop-opacity="1"/><stop offset="0.85" stop-color="{CYAN}" stop-opacity="0.55"/>
    <stop offset="1" stop-color="{CYAN}" stop-opacity="0"/>
  </linearGradient>
  <filter id="soft" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="1.6"/></filter>
  <filter id="glow" x="-40%" y="-80%" width="180%" height="260%">
    <feGaussianBlur stdDeviation="5.2" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>
<rect width="{W}" height="{H}" fill="url(#sky)"/>
<rect width="{W}" height="{H}" fill="url(#haze)"/>
{stars}
{chart_svg(cfg["star_labels"], cfg["cjk"])}
{memori(TX0+12)}
{memori(TX1-12, flip=True)}
{field_line}
{name_block}
{boxline(SAFE+TX0+170, 300, 340)}
{qr_block(558, 400, 112)}
{roles}
{contacts}
{rotated}
</svg>'''

# ------------------------------------------------------------------ face configs
TC  = "Noto Sans CJK TC Light"
JPF = "Noto Sans CJK JP Light"
TCr = "Noto Sans CJK TC"

def glow_text(x, y, txt, font, size, spacing=""):
    ls = f' letter-spacing="{spacing}"' if spacing else ""
    return (f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}"{ls} fill="rgba(34,200,255,0.9)" filter="url(#glow)">{txt}</text>'
            f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}"{ls} fill="#ffffff">{txt}</text>')

X0 = SAFE + TX0

FACES = {
 "zh": dict(seed=71,
   field="醫療人工智慧 × 生醫工程",
   cjk=TC, latin="Amiri", label_font=TC, role_size=20,
   name_block=(glow_text(X0, 252, "吳 國 禎", TC, 78)
     + f'<text x="{X0+318}" y="252" font-family="{TC}" font-size="24" fill="{CYAN}">博士</text>'
     + f'<text x="{X0}" y="286" font-family="Amiri" font-size="19" fill="rgba(255,255,255,0.6)">Kuo-Chen Wu, Ph.D.</text>'),
   roles=[(346,"智富生醫科技股份有限公司　技術長"),
          (382,"國立臺灣師範大學　博士後研究員"),
          (418,"國立勤益科技大學　教授")],
   contacts=[("電 話","+886 925-595-900"),("信 箱","d09945002@ntu.edu.tw"),("網 站","robinsixrainbow.github.io")],
   star_labels=[("織女一", 0, -26, "middle"), ("天津四", 0, 34, "middle"), ("河鼓二", 18, 6, "start")]),

 "en": dict(seed=72,
   field="MEDICAL AI × BIOMEDICAL ENGINEERING",
   cjk=TC, latin="Amiri", label_font="Amiri", role_size=16,
   name_block=(glow_text(X0, 246, "Kuo-Chen Wu", "Amiri", 66)
     + f'<text x="{X0}" y="284" font-family="Amiri" font-size="20" fill="{CYAN}">Ph.D. in Biomedical Electronics &amp; Bioinformatics</text>'),
   roles=[(346,"Chief Technology Officer — Zhifu Biomedical Technology"),
          (382,"Postdoctoral Researcher — National Taiwan Normal University"),
          (418,"Professor — National Chin-Yi University of Technology")],
   contacts=[("TEL","+886 925-595-900"),("MAIL","d09945002@ntu.edu.tw"),("WEB","robinsixrainbow.github.io")],
   star_labels=[("VEGA", 0, -26, "middle"), ("DENEB", 0, 34, "middle"), ("ALTAIR", 18, 6, "start")]),

 "jp": dict(seed=73,
   field="医療人工知能 × 生体医工学",
   cjk=JPF, latin="Amiri", label_font=JPF, role_size=19,
   name_block=(glow_text(X0, 248, "呉　国禎", JPF, 76)
     + f'<text x="{X0+330}" y="248" font-family="{JPF}" font-size="23" fill="{CYAN}">博士</text>'
     + f'<text x="{X0+2}" y="285" font-family="{JPF}" font-size="19" fill="rgba(255,255,255,0.6)">ウー・クオチェン ／ Kuo-Chen Wu, Ph.D.</text>'),
   roles=[(346,"智富生醫科技股份有限公司　最高技術責任者（CTO）"),
          (382,"国立台湾師範大学　博士研究員"),
          (418,"国立勤益科技大学　教授")],
   contacts=[("TEL","+886 925-595-900"),("MAIL","d09945002@ntu.edu.tw"),("WEB","robinsixrainbow.github.io")],
   star_labels=[("ベガ", 0, -26, "middle"), ("デネブ", 0, 34, "middle"), ("アルタイル", 18, 6, "start")]),
}

import cairosvg, os
os.makedirs("/home/claude/meishi", exist_ok=True)
for key, cfg in FACES.items():
    svg = face(cfg.pop("seed"), cfg)
    open(f"/home/claude/meishi/{key}.svg", "w").write(svg)
    cairosvg.svg2pdf(bytestring=svg.encode(), write_to=f"/home/claude/meishi/{key}.pdf")
    cairosvg.svg2png(bytestring=svg.encode(), write_to=f"/home/claude/meishi/{key}.png",
                     output_width=1600)
    print(key, "done")
