"""Draws docs/wiring/circuit.svg: the complete ChAIpi circuit (revision 3), every part and every wire.

    python3 docs/wiring/tools/make_circuit.py docs/wiring

The Pi is drawn as a schematic symbol: its pins are grouped by job, and each shows its header pin
number. docs/wiring/header-map.svg shows where those pins physically are.
"""
import os
import sys
from xml.sax.saxutils import escape as esc

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..')
os.makedirs(OUT, exist_ok=True)

# same palette as make_diagrams.py, plus the power-side nets
C = {'5v': '#d7263d', '3v3': '#ee7d1a', 'gnd': '#222222', 'spi': '#2f6fe0', 'i2c': '#13a06f', 'btn': '#c79400',
     'pwm': '#d6337a', 'uart': '#6b7785', 'free': '#b9bec6', 'vbat': '#8c1d18', 'vbus': '#a0522d',
     'ana': '#0f8b8d', 'usb': '#5b4fc8', 'box': '#3a2a22', 'ink': '#1b1b1b', 'muted': '#5d5d5d'}
FONT = "font-family:'Atkinson Hyperlegible','Segoe UI',Helvetica,Arial,sans-serif"
MONO = "font-family:'JetBrains Mono',Menlo,Consolas,monospace"
W, H = 1800, 1440
S = []


def text(x, y, s, size=13, anchor='start', weight=400, fill=C['ink'], mono=False, italic=False):
    st = f"{MONO if mono else FONT};font-size:{size}px;font-weight:{weight}" + (';font-style:italic' if italic else '')
    S.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" style="{st}" fill="{fill}">{esc(s)}</text>')


def line(pts, color, width=3.0, dashed=False):
    d = 'M' + ' L'.join(f'{x} {y}' for x, y in pts)
    dash = ' stroke-dasharray="7 6"' if dashed else ''
    S.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"{dash}/>')


def hline_hop(x0, x1, y, hops, color, width=3.0):
    """Horizontal wire from x0 to x1 that hops over vertical wires at the given x positions."""
    xs = sorted(h for h in hops if min(x0, x1) < h < max(x0, x1))
    if x0 > x1:
        xs = xs[::-1]
    r = 7
    d = f'M{x0} {y}'
    step = 1 if x1 > x0 else -1
    for h in xs:
        d += f' L{h - step * r} {y} A{r} {r} 0 0 {1 if step > 0 else 0} {h + step * r} {y}'
    d += f' L{x1} {y}'
    S.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"/>')


def dot(x, y, color):
    S.append(f'<circle cx="{x}" cy="{y}" r="5" fill="{color}"/>')


def gnd(x, y, stem=14):
    """Ground symbol hanging below (x, y)."""
    line([(x, y), (x, y + stem)], C['gnd'])
    yy = y + stem
    for i, w in enumerate((18, 12, 6)):
        S.append(f'<line x1="{x - w / 2}" y1="{yy + i * 5}" x2="{x + w / 2}" y2="{yy + i * 5}" stroke="{C["gnd"]}" stroke-width="2.6" stroke-linecap="round"/>')


def flag(x, y, label, color, left=False):
    """Power flag: a short stub ending in a labelled bar (means: connect to that supply)."""
    dx = -26 if left else 26
    line([(x, y), (x + dx, y)], color)
    S.append(f'<line x1="{x + dx}" y1="{y - 9}" x2="{x + dx}" y2="{y + 9}" stroke="{color}" stroke-width="3.4" stroke-linecap="round"/>')
    text(x + dx + (-7 if left else 7), y + 4.5, label, 12.5, 'end' if left else 'start', 700, color)


def nc(x, y, dx=18):
    line([(x, y), (x + dx, y)], C['free'], 2)
    xx = x + dx
    for a, b in (((-5, -5), (5, 5)), ((-5, 5), (5, -5))):
        S.append(f'<line x1="{xx + a[0]}" y1="{y + a[1]}" x2="{xx + b[0]}" y2="{y + b[1]}" stroke="{C["muted"]}" stroke-width="2"/>')


def module(x, y, w, h, title, sub=None, dashed=False, fill='#fbfaf8', title_y=None, below=False, sub_y=None):
    """A part. Its name sits at the top (or at title_y); notes go under the name, or under the box."""
    dash = ' stroke-dasharray="8 6"' if dashed else ''
    S.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" stroke="{C["box"]}" stroke-width="2.4"{dash}/>')
    ty = title_y if title_y is not None else y + 24
    text(x + w / 2, ty, title, 15.5, 'middle', 700)
    if sub:
        sub = sub if isinstance(sub, (list, tuple)) else [sub]
        y0 = sub_y if sub_y is not None else ((y + h + 18) if below else ty + 18)
        for i, s in enumerate(sub):
            text(x + w / 2, y0 + i * 16, s, 12, 'middle', 400, C['muted'])


def pin(x, y, side, label, num=None, color=C['ink']):
    """A labelled pin stub on a module edge; returns the wire end point."""
    L = 16
    if side == 'l':
        line([(x - L, y), (x, y)], C['box'], 2.4)
        text(x + 8, y + 4.5, label, 13, 'start', 600, color)
        if num:
            text(x - L - 4, y - 6, num, 11, 'end', 700, C['muted'], True)
        return (x - L, y)
    if side == 'r':
        line([(x, y), (x + L, y)], C['box'], 2.4)
        text(x - 8, y + 4.5, label, 13, 'end', 600, color)
        if num:
            text(x + L + 4, y - 6, num, 11, 'start', 700, C['muted'], True)
        return (x + L, y)
    if side == 't':
        line([(x, y - L), (x, y)], C['box'], 2.4)
        text(x, y + 17, label, 12.5, 'middle', 600, color)
        return (x, y - L)
    line([(x, y), (x, y + L)], C['box'], 2.4)
    text(x, y - 7, label, 12.5, 'middle', 600, color)
    return (x, y + L)


def switch(x, y, label, color=C['btn'], label_above=True):
    """Push button between (x, y) and (x + 70, y)."""
    line([(x, y), (x + 20, y)], color)
    line([(x + 50, y), (x + 70, y)], color)
    for xx in (x + 20, x + 50):
        S.append(f'<circle cx="{xx}" cy="{y}" r="3.4" fill="#fff" stroke="{C["ink"]}" stroke-width="2"/>')
    S.append(f'<line x1="{x + 17}" y1="{y - 10}" x2="{x + 53}" y2="{y - 10}" stroke="{C["ink"]}" stroke-width="2.4"/>')
    S.append(f'<line x1="{x + 35}" y1="{y - 10}" x2="{x + 35}" y2="{y - 17}" stroke="{C["ink"]}" stroke-width="2.4"/>')
    text(x + 35, y - 22 if label_above else y + 22, label, 12.5, 'middle', 700, C['ink'])


def resistor(x, y0, y1, label, color, left=False):
    """Vertical resistor from (x, y0) to (x, y1)."""
    mid0, mid1 = y0 + (y1 - y0) * 0.22, y1 - (y1 - y0) * 0.22
    line([(x, y0), (x, mid0)], color)
    line([(x, mid1), (x, y1)], color)
    S.append(f'<rect x="{x - 7}" y="{mid0}" width="14" height="{mid1 - mid0}" rx="2" fill="#fff" stroke="{C["ink"]}" stroke-width="2"/>')
    text(x - 12 if left else x + 12, (y0 + y1) / 2 + 4, label, 12, 'end' if left else 'start', 600, C['muted'])


def capacitor(x, y0, y1, label):
    """Vertical polarised capacitor from (x, y0) [+] to (x, y1) [-]."""
    m = (y0 + y1) / 2
    line([(x, y0), (x, m - 5)], C['5v'])
    line([(x, m + 5), (x, y1)], C['gnd'])
    S.append(f'<line x1="{x - 13}" y1="{m - 5}" x2="{x + 13}" y2="{m - 5}" stroke="{C["ink"]}" stroke-width="2.6"/>')
    S.append(f'<path d="M{x - 13} {m + 8} Q{x} {m + 1} {x + 13} {m + 8}" fill="none" stroke="{C["ink"]}" stroke-width="2.6"/>')
    text(x - 16, m - 10, '+', 13, 'end', 700)
    text(x + 18, m + 4, label, 12, 'start', 600, C['muted'])


def cell(x, y, label):
    """A battery cell drawn vertically, + at the top, centred on x between y and y + 40."""
    S.append(f'<line x1="{x - 16}" y1="{y + 14}" x2="{x + 16}" y2="{y + 14}" stroke="{C["ink"]}" stroke-width="2.8"/>')
    S.append(f'<line x1="{x - 9}" y1="{y + 24}" x2="{x + 9}" y2="{y + 24}" stroke="{C["ink"]}" stroke-width="5"/>')
    line([(x, y), (x, y + 14)], C['vbat'])
    line([(x, y + 24), (x, y + 40)], C['gnd'])
    text(x + 21, y + 12, '+', 13, 'start', 700)
    text(x, y + 58, label, 12, 'middle', 600, C['muted'])


# ---------------------------------------------------------------------------------------------
S.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" style="{FONT}">')
S.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
text(40, 46, 'ChAIpi: the complete circuit', 28, 'start', 700)
text(40, 74, 'Every part and every wire. Coloured lines are wires; a dot is a join; lines that cross without a dot (or hop over) are not joined.', 15, 'start', 400, C['muted'])
text(40, 94, '⏚ means "to GND". A bar labelled 3.3 V or 5 V means "to that supply". Small grey numbers are Pi header pin numbers (see header-map.svg). Dashed = optional or later.', 15, 'start', 400, C['muted'])

# --- power -----------------------------------------------------------------------------------
module(40, 130, 180, 160, 'USB-C breakout', ['charging + data;', 'CC resistors on board'], below=True)
vb = pin(220, 180, 'r', 'VBUS', None, C['vbus'])
ug = pin(220, 212, 'r', 'GND')
udp = pin(220, 246, 'r', 'D+', None, C['usb'])
udm = pin(220, 272, 'r', 'D−', None, C['usb'])
for (x, y), lab in ((udp, 'USB D+'), (udm, 'USB D−')):
    line([(x, y), (x + 14, y)], C['usb'])
    S.append(f'<rect x="{x + 14}" y="{y - 9}" width="62" height="18" rx="9" fill="#fff" stroke="{C["usb"]}" stroke-width="2"/>')
    text(x + 45, y + 4.5, lab, 11.5, 'middle', 700, C['usb'])
line([ug, (252, 212), (252, 220)], C['gnd'])
gnd(252, 220, 2)

module(380, 130, 180, 160, 'TP4056 charger', ['with protection;', 'its own USB-C stays empty'], sub_y=242)
ip = pin(380, 180, 'l', 'IN+', None, C['vbus'])
im = pin(380, 212, 'l', 'IN−')
op = pin(560, 180, 'r', 'OUT+', None, C['vbat'])
om = pin(560, 212, 'r', 'OUT−')
bp = pin(430, 290, 'b', 'B+', None, C['vbat'])
bm = pin(510, 290, 'b', 'B−')
line([vb, ip], C['vbus'])
line([im, (348, 212), (348, 220)], C['gnd'])
gnd(348, 220, 2)
line([om, (592, 212), (592, 220)], C['gnd'])
gnd(592, 220, 2)
# USB sense divider on VBUS
dot(320, 180, C['vbus'])
resistor(320, 180, 250, '100 k', C['vbus'], left=True)
line([(320, 250), (320, 262)], C['ana'])
dot(320, 262, C['ana'])
resistor(320, 262, 326, '100 k', C['gnd'], left=True)
gnd(320, 326, 6)

# two cells in parallel, each with its own BMS
S.append(f'<rect x="400" y="360" width="160" height="104" rx="8" fill="none" stroke="{C["muted"]}" stroke-width="1.6" stroke-dasharray="4 4"/>')
cell(446, 374, '')
cell(514, 374, '')
text(480, 458, '2 × 3.7 V cells, each with BMS', 11.5, 'middle', 700, C['muted'])
line([bp, (430, 340), (446, 340), (446, 374)], C['vbat'])
line([(446, 352), (514, 352), (514, 374)], C['vbat'])
dot(446, 352, C['vbat'])
line([bm, (510, 322), (576, 322), (576, 426), (514, 426), (514, 414)], C['gnd'])
line([(446, 414), (446, 426), (514, 426)], C['gnd'])
dot(514, 426, C['gnd'])
text(590, 344, 'add a 2 A resettable', 11, 'start', 400, C['muted'], italic=True)
text(590, 358, 'fuse in B+ (recommended)', 11, 'start', 400, C['muted'], italic=True)

# rocker switch (later), battery sense divider after it, then the boost
line([op, (620, 180)], C['vbat'])
S.append(f'<rect x="616" y="154" width="76" height="40" rx="6" fill="none" stroke="{C["muted"]}" stroke-width="1.4" stroke-dasharray="4 4"/>')
S.append(f'<circle cx="626" cy="180" r="3.4" fill="#fff" stroke="{C["ink"]}" stroke-width="2"/>')
S.append(f'<circle cx="682" cy="180" r="3.4" fill="#fff" stroke="{C["ink"]}" stroke-width="2"/>')
S.append(f'<line x1="628" y1="178" x2="674" y2="164" stroke="{C["ink"]}" stroke-width="2.6"/>')
text(654, 146, 'rocker switch (later)', 12, 'middle', 700, C['muted'])
text(650, 212, 'until fitted, join these', 11, 'middle', 400, C['muted'], italic=True)
line([(685, 180), (784, 180)], C['vbat'])
dot(750, 180, C['vbat'])
resistor(750, 180, 250, '100 k', C['vbat'], left=True)
line([(750, 250), (750, 262)], C['ana'])
dot(750, 262, C['ana'])
resistor(750, 262, 326, '100 k', C['gnd'], left=True)
gnd(750, 326, 6)

module(800, 130, 180, 120, 'MT3608 boost', ['set to 5.1 V first', 'with a multimeter'], below=True)
pin(800, 180, 'l', 'VIN+', None, C['vbat'])
vim = pin(800, 212, 'l', 'VIN−')
line([vim, (772, 212), (772, 220)], C['gnd'])
gnd(772, 220, 2)
vo = pin(980, 180, 'r', 'VOUT+', None, C['5v'])
vom = pin(980, 212, 'r', 'VOUT−')
line([vom, (1012, 212), (1012, 220)], C['gnd'])
gnd(1012, 220, 2)
line([vo, (1060, 180), (1060, 464)], C['5v'])
text(1068, 206, '5 V', 13, 'start', 700, C['5v'])
dot(1060, 330, C['5v'])
line([(1060, 330), (1120, 330), (1120, 346)], C['5v'])
capacitor(1120, 346, 398, '470–1000 µF, stripe to GND')
gnd(1120, 398, 6)

# sense lines down to the ADS1115
line([(320, 262), (340, 262), (340, 470), (520, 470), (520, 484)], C['ana'])
line([(750, 262), (772, 262), (772, 440), (600, 440), (600, 484)], C['ana'])
text(348, 484, 'USB SENSE', 11, 'start', 700, C['ana'])
text(606, 458, 'BATTERY SENSE', 11, 'start', 700, C['ana'])

# --- the Pi ------------------------------------------------------------------------------------
PX0, PX1, PY0, PY1 = 820, 1080, 480, 1240
S.append(f'<rect x="{PX0}" y="{PY0}" width="{PX1 - PX0}" height="{PY1 - PY0}" rx="14" fill="#eaf4ee" stroke="#1f7a4d" stroke-width="3"/>')
text((PX0 + PX1) / 2, 896, 'Raspberry Pi', 20, 'middle', 700, '#145234')
text((PX0 + PX1) / 2, 921, 'Zero 2 W', 20, 'middle', 700, '#145234')
text((PX0 + PX1) / 2, 944, 'no header pins: solder wires', 12, 'middle', 400, C['muted'])
text((PX0 + PX1) / 2, 960, 'into the holes', 12, 'middle', 400, C['muted'])
pin(1060, PY0, 't', '5V', None, C['5v'])
text(1068, PY0 - 24, 'pins 2, 4', 11, 'start', 700, C['muted'], italic=True)
pl = {}
for name, y, num, col in (('3V3', 520, '1', C['3v3']), ('GPIO2 SDA', 600, '3', C['i2c']), ('GPIO3 SCL', 640, '5', C['i2c']),
                          ('GPIO27', 1000, '13', C['btn']), ('GPIO5', 1050, '29', C['btn']), ('GPIO6', 1100, '31', C['btn']),
                          ('GPIO26', 1150, '37', C['btn']), ('GPIO17', 1200, '11', C['btn'])):
    pl[name] = pin(PX0, y, 'l', name, num, col)
pr = {}
for name, y, num, col in (('3V3', 520, '17', C['3v3']), ('GPIO8 CE0', 600, '24', C['spi']), ('GPIO24', 640, '18', C['spi']),
                          ('GPIO25', 680, '22', C['spi']), ('GPIO10 MOSI', 720, '19', C['spi']), ('GPIO11 SCLK', 760, '23', C['spi']),
                          ('GPIO13 PWM', 800, '33', C['pwm']), ('GPIO12', 1000, '32', C['pwm']), ('GPIO23', 1100, '16', C['btn']),
                          ('GPIO16', 1150, '36', C['btn'])):
    pr[name] = pin(PX1, y, 'r', name, num, col)
pin(860, PY1, 'b', 'GND', None)
gnd(860, PY1 + 16, 6)
text(840, PY1 + 34, 'pins 6 9 14 20 25 30 34 39', 11, 'end', 700, C['muted'], italic=True)
dp = pin(950, PY1, 'b', 'D+', None, C['usb'])
dm = pin(990, PY1, 'b', 'D−', None, C['usb'])
text(970, PY1 - 26, 'USB data', 12, 'middle', 700, C['usb'])
for (x, y), lab, dx in ((dp, 'USB D+', -40), (dm, 'USB D−', 40)):
    line([(x, y), (x, y + 18), (x + dx, y + 18), (x + dx, y + 30)], C['usb'])
    S.append(f'<rect x="{x + dx - 31}" y="{y + 30}" width="62" height="18" rx="9" fill="#fff" stroke="{C["usb"]}" stroke-width="2"/>')
    text(x + dx, y + 43.5, lab, 11.5, 'middle', 700, C['usb'])
text(970, PY1 + 92, "to the Pi's USB_DP / USB_DM test pads (underneath, by the USB socket)", 11, 'middle', 400, C['muted'], italic=True)
for x, lab in ((1036, 'TX'), (1062, 'RX')):
    S.append(f'<line x1="{x}" y1="{PY1}" x2="{x}" y2="{PY1 + 10}" stroke="{C["box"]}" stroke-width="2.4"/>')
    text(x, PY1 - 7, lab, 11.5, 'middle', 600, C['uart'])
text(1050, PY1 + 26, 'pins 8, 10:', 11, 'start', 700, C['uart'], italic=True)
text(1050, PY1 + 40, 'keep free (serial console)', 11, 'start', 700, C['uart'], italic=True)

# --- left: ADS1115, joystick, DS3231, buttons --------------------------------------------------
module(420, 484, 200, 276, 'ADS1115', ['analog in · I2C 0x48'], title_y=566)
text(520, 780, 'board pins: VDD GND SCL SDA ADDR ALRT A0 A1 A2 A3', 11, 'middle', 400, C['muted'], italic=True)
a_vdd = pin(620, 520, 'r', 'VDD', None, C['3v3'])
a_gnd = pin(620, 556, 'r', 'GND')
a_sda = pin(620, 600, 'r', 'SDA', None, C['i2c'])
a_scl = pin(620, 640, 'r', 'SCL', None, C['i2c'])
a_adr = pin(620, 680, 'r', 'ADDR')
a_al = pin(620, 716, 'r', 'ALRT', None, C['muted'])
a0 = pin(420, 620, 'l', 'A0', None, C['ana'])
a1 = pin(420, 650, 'l', 'A1', None, C['ana'])
pin(520, 484, 't', 'A3', None, C['ana'])
pin(600, 484, 't', 'A2', None, C['ana'])
line([a_vdd, pl['3V3']], C['3v3'])
line([a_gnd, (660, 556), (660, 562)], C['gnd'])
gnd(660, 562, 2)
line([a_adr, (660, 680), (660, 686)], C['gnd'])
gnd(660, 686, 2)
text(520, 796, 'ADDR to GND sets the address to 0x48', 11, 'middle', 400, C['muted'], italic=True)
nc(a_al[0], a_al[1], 14)
line([a_sda, pl['GPIO2 SDA']], C['i2c'])
line([a_scl, (740, 640)], C['i2c'])
S.append(f'<path d="M740 640 A 12 12 0 0 1 764 640" fill="none" stroke="{C["i2c"]}" stroke-width="3"/>')
line([(764, 640), pl['GPIO3 SCL']], C['i2c'])
dot(752, 600, C['i2c'])
dot(790, 640, C['i2c'])

module(110, 486, 190, 230, 'Joystick', ['PS2 module (KY-023)', 'header removed;', 'its +5V pin goes to 3.3 V!'])
j_g = pin(300, 576, 'r', 'GND')
j_v = pin(300, 600, 'r', '+5V', None, C['3v3'])
j_x = pin(300, 620, 'r', 'VRx', None, C['ana'])
j_y = pin(300, 650, 'r', 'VRy', None, C['ana'])
j_s = pin(300, 690, 'r', 'SW', None, C['btn'])
line([j_g, (332, 576), (332, 582)], C['gnd'])
gnd(332, 582, 2)
flag(j_v[0], j_v[1], '3.3 V', C['3v3'])
line([j_x, a0], C['ana'])
line([j_y, a1], C['ana'])
line([j_s, (340, 690), (340, 1000), pl['GPIO27']], C['btn'])
text(520, 992, 'joystick press', 12, 'middle', 700, C['btn'])

module(420, 822, 200, 150, 'DS3231 clock', ['ZS-042 + CR2032 (+ up);', 'remove its charging resistor'])
d_scl = pin(620, 920, 'r', 'SCL', None, C['i2c'])
d_sda = pin(620, 890, 'r', 'SDA', None, C['i2c'])
d_v = pin(620, 948, 'r', 'VCC', None, C['3v3'])
d_32 = pin(420, 890, 'l', '32K', None, C['muted'])
d_sq = pin(420, 920, 'l', 'SQW', None, C['muted'])
d_g = pin(420, 950, 'l', 'GND')
nc(d_32[0], d_32[1], -14)
nc(d_sq[0], d_sq[1], -14)
line([d_g, (380, 950), (380, 956)], C['gnd'])
gnd(380, 956, 2)
line([(752, 600), (752, 890), d_sda], C['i2c'])
line([(790, 640), (790, 920), d_scl], C['i2c'])
flag(d_v[0], d_v[1], '3.3 V', C['3v3'])

for name, lab in (('GPIO5', 'Confirm'), ('GPIO6', 'Undo (Backspace)'), ('GPIO26', 'Tab'), ('GPIO17', 'Fn')):
    x, y = pl[name]
    switch(700, y, lab)
    line([(770, y), (x, y)], C['btn'])
    line([(640, y), (700, y)], C['gnd'])
line([(640, 1050), (640, 1214)], C['gnd'])
for y in (1100, 1150, 1200):
    dot(640, y, C['gnd'])
gnd(640, 1214, 6)
text(626, 1120, 'other leg of', 11.5, 'end', 700, C['muted'], italic=True)
text(626, 1136, 'every button', 11.5, 'end', 700, C['muted'], italic=True)

# --- right: screen, buttons, vibration -----------------------------------------------------------
module(1200, 484, 250, 400, '2.8" ILI9341 screen', ['320 × 240 · SPI', 'header and SD slot removed'])
sp = {}
for name, y, col in (('VCC', 520, C['3v3']), ('GND', 560, C['gnd']), ('CS', 600, C['spi']), ('RESET', 640, C['spi']),
                     ('DC', 680, C['spi']), ('SDI (MOSI)', 720, C['spi']), ('SCK', 760, C['spi']), ('LED', 800, C['pwm']),
                     ('SDO (MISO)', 840, C['muted'])):
    sp[name] = pin(1200, y, 'l', name, None, col)
S.append(f'<rect x="1310" y="560" width="120" height="290" rx="4" fill="#dfe7f5" stroke="#9aa9c2" stroke-width="1.6"/>')
text(1370, 690, 'touch pins', 11.5, 'middle', 700, C['muted'])
text(1370, 705, 'T_CLK … T_IRQ', 11.5, 'middle', 400, C['muted'])
text(1370, 720, 'not used', 11.5, 'middle', 400, C['muted'])
line([pr['3V3'], sp['VCC']], C['3v3'])
line([sp['GND'], (1150, 560), (1150, 566)], C['gnd'])
gnd(1150, 566, 2)
for a, b in (('GPIO8 CE0', 'CS'), ('GPIO24', 'RESET'), ('GPIO25', 'DC'), ('GPIO10 MOSI', 'SDI (MOSI)'), ('GPIO11 SCLK', 'SCK')):
    line([pr[a], sp[b]], C['spi'])
line([pr['GPIO13 PWM'], sp['LED']], C['pwm'])
nc(sp['SDO (MISO)'][0], sp['SDO (MISO)'][1], -18)
text(1176, 822, 'backlight', 11, 'end', 700, C['pwm'], italic=True)

for name, lab in (('GPIO23', 'Menu'), ('GPIO16', 'Esc')):
    x, y = pr[name]
    line([(x, y), (1124, y)], C['btn'])
    switch(1124, y, lab)
    line([(1194, y), (1236, y)], C['gnd'])
line([(1236, 1100), (1236, 1170)], C['gnd'])
dot(1236, 1150, C['gnd'])
gnd(1236, 1170, 6)

module(1240, 950, 200, 104, 'Vibration motor', ['5 V module (later)'], dashed=True)
v_in = pin(1240, 1020, 'l', 'IN', None, C['pwm'])
v_vcc = pin(1440, 1000, 'r', 'VCC', None, C['5v'])
v_g = pin(1440, 1034, 'r', 'GND')
line([pr['GPIO12'], (1150, 1000), (1150, 1020), v_in], C['pwm'], dashed=True)
flag(v_vcc[0], v_vcc[1], '5 V', C['5v'])
line([v_g, (1474, 1034), (1474, 1040)], C['gnd'])
gnd(1474, 1040, 2)

module(1480, 1090, 290, 240, 'Backlight option', ['only if docs/03 step 2 reads ≥ 20 mA'], dashed=True, fill='#fffdf8')
text(1625, 1160, 'S8550 PNP + 1 kΩ', 13, 'middle', 700)
bx, by = 1610, 1236
S.append(f'<circle cx="{bx}" cy="{by}" r="22" fill="#fff" stroke="{C["ink"]}" stroke-width="2.2"/>')
S.append(f'<line x1="{bx - 8}" y1="{by - 14}" x2="{bx - 8}" y2="{by + 14}" stroke="{C["ink"]}" stroke-width="3"/>')
line([(bx - 8, by - 6), (bx + 12, by - 18)], C['ink'], 2.2)
line([(bx - 8, by + 6), (bx + 12, by + 18)], C['ink'], 2.2)
line([(bx + 12, by - 18), (bx + 12, by - 44)], C['3v3'])
text(bx + 20, by - 30, 'emitter → 3.3 V', 12, 'start', 600, C['3v3'])
line([(bx + 12, by + 18), (bx + 12, by + 44)], C['pwm'])
text(bx + 20, by + 40, 'collector → screen LED', 12, 'start', 600, C['pwm'])
line([(bx - 8, by), (bx - 40, by)], C['pwm'])
S.append(f'<rect x="{bx - 74}" y="{by - 7}" width="34" height="14" rx="2" fill="#fff" stroke="{C["ink"]}" stroke-width="2"/>')
line([(bx - 74, by), (bx - 100, by)], C['pwm'])
text(bx - 57, by - 13, '1 kΩ', 11.5, 'middle', 600, C['muted'])
text(bx - 104, by + 22, 'GPIO13', 12, 'start', 700, C['pwm'])
text(1625, 1314, 'then set invert = true under [backlight]', 11.5, 'middle', 400, C['muted'], italic=True)

# --- legend --------------------------------------------------------------------------------------
lx, ly = 1500, 132
S.append(f'<rect x="{lx - 20}" y="{ly - 24}" width="290" height="338" rx="12" fill="#fafafa" stroke="#e3e3e3"/>')
text(lx, ly, 'Wire colours', 15, 'start', 700)
for i, (k, lab) in enumerate((('vbat', 'Battery + (before the boost)'), ('5v', '5 V'), ('3v3', '3.3 V'), ('gnd', 'GND'),
                              ('vbus', 'USB 5 V (VBUS)'), ('spi', 'Screen (SPI)'), ('i2c', 'I2C'), ('ana', 'Analog'),
                              ('btn', 'Buttons'), ('pwm', 'Backlight / vibration (PWM)'), ('usb', 'USB data'),
                              ('uart', 'Serial (keep free)'))):
    y = ly + 26 + i * 23
    line([(lx, y), (lx + 34, y)], C[k], 3.4)
    text(lx + 46, y + 4.5, lab, 13)
y = ly + 26 + 12 * 23
nc(lx, y, 22)
text(lx + 46, y + 4.5, 'Not connected', 13)

# --- notes -----------------------------------------------------------------------------------------
notes = ['Power: USB-C → TP4056 (charges the cells) → OUT+ → (switch) → MT3608 boost at 5.1 V → Pi pins 2/4. OUT− is the ground for everything.',
         'Everything else runs from the Pi\'s 3.3 V (pins 1 and 17). Never feed the joystick or the ADS1115 from 5 V.',
         'Each sense line is two 100 kΩ resistors in series; the middle point goes to the ADS1115 (A2 battery, A3 USB).',
         'Buttons: use two diagonally opposite legs of each 4-leg switch; the Pi\'s built-in pull-ups do the rest. Joystick SW is a button too.']
for i, n in enumerate(notes):
    text(40, 1356 + i * 22, n, 13.5, 'start', 400, C['ink'])

S.append('</svg>')
path = os.path.join(OUT, 'circuit.svg')
with open(path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(S))
print(path)
