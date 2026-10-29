"""ChAIpi case: every dimension and every part position, in one place.

Pure Python (no Blender needed), so the fit can be checked anywhere:
    python3 enclosure/case/tools/layout.py          # prints collisions and clearances

build_case.py (run inside Blender) imports this file to build the printable parts and the
rough component models.

Coordinates, in mm. The BASE frame: origin at the base's outer front-left-bottom corner.
X runs left to right, Y front to back (the hinge is at the back), Z bottom to top.
The LID frame: origin at the lid's front-left corner on its screen face. z runs from the
screen face (z = 0, which touches the base when closed) to the lid's back (z = LID_T).
"""

# ---------------------------------------------------------------------------------------------
# Sizes of the bought parts. "src" says where each number comes from; "CHECK" marks numbers to
# measure on your own part before printing (cheap modules vary by a millimetre or two).
# ---------------------------------------------------------------------------------------------
PART = {
    # Raspberry Pi Zero 2 W: official mechanical drawing (65 x 30, holes 3.5 mm in, M2.5)
    'pi': dict(w=65.0, d=30.0, t=1.4, hole=2.75, hole_in=3.5, under=0.8, sd_out=2.5),
    # Heatsinks you measured: main processor 14.7 x 14.7 x 7, Wi-Fi module 11 x 11 x 5
    'hs_cpu': dict(w=14.7, h=7.0, chip=1.2),
    'hs_wifi': dict(w=11.0, h=5.0, chip=1.5),
    # 2.8" ILI9341 MSP2807: LCDwiki drawing. PCB 86 x 50 x 1.6; 5.6 mm thick without the header;
    # active area 57.6 x 43.2 (x 9.30..66.90, y 3.40..46.60 from the non-header end); holes 3.2 mm,
    # centres 3.0 mm from the edges and 76.08 mm apart along the length; SMD parts on the back <= 2.2
    'tft': dict(w=86.0, d=50.0, pcb=1.6, total=5.6, back_smd=2.2,
                aa=(9.30, 3.40, 66.90, 46.60), holes=((3.0, 3.0), (3.0, 47.0), (79.08, 3.0), (79.08, 47.0)),
                hole_d=3.2, lcd=(6.40, 75.60), header_x=84.0),
    # Your two cells: 51.4 x 34.5 x 4.7 each, stacked with tape between
    'cell': dict(w=51.4, d=34.5, t=4.7, tape=0.2),
    # KY-023 joystick board: 34 x 26 (your photo). Joystick part (Sunrom 4398 drawing): frame
    # 16 x 16 x 12.2, stick tip 19.3 above the board, tilts 25 degrees each way.
    # CHECK: stick centre ~16.9 mm from the pin edge and ~8.5 mm from the long edge nearest the
    # frame; mounting holes ~3.2 mm in from each corner.
    'joy': dict(w=34.0, d=26.0, t=1.6, lever=(16.9, 17.5), frame=16.0, frame_h=12.2, tip=19.3,
                env=(-9.0, -15.0, 12.8, 8.6), env_h=12.4, tilt=25.0, pivot=7.0,
                holes_in=3.2, hole_d=3.2, joints=1.0),
    # DS3231 clock board ZS-042 with the CR2032 holder underneath. CHECK
    'rtc': dict(w=38.0, d=22.0, h=8.6),
    # TP4056 USB-C charger with protection. Its own USB-C port stays unused (the breakout charges)
    'chg': dict(w=28.0, d=17.5, h=4.6),
    # MT3608 boost board; the 3296 trimmer stands up at one end. CHECK
    'boost': dict(w=36.0, d=17.0, h=5.2, pot=(9.6, 5.0, 11.2), pot_in=1.0),
    # ADS1115 board. CHECK
    'adc': dict(w=28.0, d=17.5, h=3.4),
    # 16-pin USB-C breakout. CHECK
    'usbc': dict(w=12.6, d=21.0, h=5.0, port_w=9.0, port_h=3.3),
    # Your tactile switches: 12 x 12 x 2.5 body, round actuator 1.5 above it
    'btn': dict(w=12.0, body=2.5, act=1.5, act_d=11.0, legs=(12.5, 5.0)),
    # 470-1000 uF capacitor, lying down
    'cap': dict(d=8.2, l=13.0),
}

# ---------------------------------------------------------------------------------------------
# Case sizes
# ---------------------------------------------------------------------------------------------
FIT = 0.3            # gap around boards in pockets
WALL = 1.4           # lid side walls (thin bezels)
WALL_B = 1.4         # base side and front walls
WALL_BACK = 1.2      # base back wall (the hinge block stiffens it)
FLOOR = 1.6          # base bottom plate
FACE = 1.6           # base top plate
BEZEL = 1.2          # lid front (over the screen)
LID_BACK = 1.2       # lid back cover
R_OUT = 3.0          # outside corner radius

T = PART['tft']
LID_W = T['w'] + 2 * 0.2 + 2 * WALL           # 89.2: the screen, 0.2 mm each side, 1.4 mm walls
LID_D = T['d'] + 2 * 0.2 + 2 * WALL           # 53.2
SCREEN_BACK_GAP = 2.4                         # behind the screen board: SMD parts and the wires
LID_T = BEZEL + T['total'] + SCREEN_BACK_GAP + LID_BACK   # 10.4
TFT_ORG = (WALL + 0.2, WALL + 0.2, BEZEL)     # screen board corner in the lid frame (its front face at z = BEZEL)

HINGE_GAP = 0.3
BARREL_R = 3.5
HINGE_AXIS_Y = LID_D + HINGE_GAP + BARREL_R    # 57.0 (both frames)
HINGE_AXIS_Z = LID_T - BARREL_R                # 6.9 in the lid frame: the barrel's top is flush with the lid back

W = LID_W                                     # the base is exactly as wide as the lid
D = LID_D + HINGE_GAP + 2 * BARREL_R          # 60.5: and as deep as the lid plus its hinge

# The joystick sets the base height: its printed cap ends flush with the top plate.
J = PART['joy']
CAP_ABOVE_TIP = 1.0                           # cap material above the stick tip
JOY_RISER = 2.4                               # the joystick board rests on pads this high (sets the base height)
JOY_PCB_Z = FLOOR + JOY_RISER
HB = JOY_PCB_Z + J['t'] + J['tip'] + CAP_ABOVE_TIP   # base height: the cap top = the face top
FACE_Z = HB - FACE                            # underside of the top plate
CLOSED_T = HB + LID_T

# ---------------------------------------------------------------------------------------------
# Where things go (base frame)
# ---------------------------------------------------------------------------------------------
IN = dict(x0=WALL_B, x1=W - WALL_B, y0=WALL_B, y1=D - WALL_BACK, z0=FLOOR, z1=FACE_Z)

JOY_ORG = (IN['x0'] + 0.2, IN['y0'] + 0.35)                   # board corner (front-left); its 5-pin header is removed
JOY_C = (JOY_ORG[0] + J['lever'][0], JOY_ORG[1] + J['lever'][1])  # stick centre

C = PART['cell']
BATT_T = 2 * C['t'] + C['tape']
BATT_ORG = (IN['x1'] - C['w'] - 0.3, IN['y1'] - C['d'] - 0.3)   # back-right, on the floor

SHEET_Z = FLOOR + BATT_T + 0.4               # middle sheet bottom (your "sheet on top of the battery")
SHEET_T = 1.2

P = PART['pi']
PI_STAND = 1.6                               # Pi board on 1.6 mm pucks (blind screw holes, so no screw tip points at the battery)
PI_Z = SHEET_Z + SHEET_T + PI_STAND          # Pi board underside
PI_ORG = (IN['x0'] + 4.2, IN['y1'] - P['d'] - 0.3)   # GPIO edge at the back; room for a corner screw at the left

B = PART['btn']
BTN_CAP_FLANGE = 0.8
BTN_TOP = FACE_Z - BTN_CAP_FLANGE            # top of the actuator
BTN_BED_T = 1.0                              # printed carrier the switches sit in
BTN_BED_Z = BTN_TOP - B['act'] - B['body'] - BTN_BED_T
BTN_LEGS = 1.0                               # legs (trimmed) and solder under the carrier

# Buttons sit on one shared printed carrier, on a 13 mm grid right of the joystick.
# The two empty front-row spots leave room for the boost board's tall trimmer underneath.
GX = (39.2, 52.8, 66.4, 80.0)
GY = (9.0, 22.0)
BUTTONS = {                                   # name -> ((x, y) centre, cap diameter)
    'Tab':     ((GX[0], GY[1]), 8.5),
    'Menu':    ((GX[1], GY[1]), 8.5),
    'Esc':     ((GX[2], GY[1]), 8.5),
    'Confirm': ((GX[3], GY[1]), 10.5),
    'Fn':      ((GX[1], GY[0]), 8.5),
    'Undo':    ((GX[2], GY[0]), 10.5),
}
FREE_SLOTS = ((GX[0], GY[0]), (GX[3], GY[0]))   # boost trimmer underneath; corner screw beside


RTC_BOX = (IN['x1'] - PART['usbc']['w'] - 0.6 - PART['rtc']['w'] - 0.4, IN['y0'] + 0.4, FLOOR, 0, 0, 0)
RTC_BOX = (RTC_BOX[0], RTC_BOX[1], FLOOR, RTC_BOX[0] + PART['rtc']['w'], RTC_BOX[1] + PART['rtc']['d'], FLOOR + PART['rtc']['h'])
USBC_BOX = (IN['x1'] - PART['usbc']['w'] - 0.3, IN['y0'] + 0.4, FLOOR,
            IN['x1'] - 0.3, IN['y0'] + 0.4 + PART['usbc']['d'], FLOOR + PART['usbc']['h'])
SHELF_T = 0.8                                # printed shelves that carry a board over another
_bo = PART['boost']
_bz = RTC_BOX[5] + 0.3 + SHELF_T
BOOST_BOX = (RTC_BOX[0] - 1.5, IN['y0'] + 0.9, _bz, RTC_BOX[0] - 1.5 + _bo['w'], IN['y0'] + 0.9 + _bo['d'], _bz + _bo['h'])
BOOST_POT = (BOOST_BOX[0] + _bo['pot_in'], BOOST_BOX[1] + (_bo['d'] - _bo['pot'][1]) / 2, _bz,
             BOOST_BOX[0] + _bo['pot_in'] + _bo['pot'][0], BOOST_BOX[1] + (_bo['d'] + _bo['pot'][1]) / 2, _bz + _bo['pot'][2])
_ch = PART['chg']
CHG_BOX = (IN['x0'] + 0.4, JOY_ORG[1] + J['d'] + 0.8, FLOOR, IN['x0'] + 0.4 + _ch['w'], JOY_ORG[1] + J['d'] + 0.8 + _ch['d'], FLOOR + _ch['h'])
_a = PART['adc']
_az = CHG_BOX[5] + 0.3 + SHELF_T
ADC_BOX = (CHG_BOX[0], CHG_BOX[1], _az, CHG_BOX[0] + _a['w'], CHG_BOX[1] + _a['d'], _az + _a['h'])


def boxes():
    """Every solid part as boxes: name -> list of (x0, y0, z0, x1, y1, z1) in the base frame."""
    out = {}

    def add(name, *b):
        out.setdefault(name, []).append(tuple(float(v) for v in b))

    # joystick: board, the joystick body (frame, pots, switch), and the stick + cap swing
    jx, jy = JOY_ORG
    add('joystick', jx, jy, JOY_PCB_Z, jx + J['w'], jy + J['d'], JOY_PCB_Z + J['t'])
    cx, cy = JOY_C
    e = J['env']
    ztop = JOY_PCB_Z + J['t']
    add('joystick', cx + e[0], cy + e[1], ztop, cx + e[2], cy + e[3], ztop + J['env_h'])
    add('joystick', jx, jy + 7, ztop, jx + 3.0, jy + 19, ztop + 2.6)            # pin header stub + wires
    # battery block
    bx, by = BATT_ORG
    add('battery', bx, by, FLOOR, bx + C['w'], by + C['d'], FLOOR + BATT_T)
    add('battery', bx - 3.0, by + 8, FLOOR, bx, by + 26, FLOOR + BATT_T)        # BMS end: wires out to the left
    # Pi with heatsinks and connectors
    px, py = PI_ORG
    pz = PI_Z
    add('pi', px, py, pz, px + P['w'], py + P['d'], pz + P['t'])
    add('pi', px - P['sd_out'], py + 10.8, pz + P['t'], px + 13.0, py + 22.9, pz + P['t'] + 1.4)   # microSD + card
    hs = PART['hs_cpu']
    cxp, cyp = px + 27.3, py + P['d'] - 16.05
    add('pi', cxp - hs['w'] / 2, cyp - hs['w'] / 2, pz + P['t'], cxp + hs['w'] / 2, cyp + hs['w'] / 2, pz + P['t'] + hs['chip'] + hs['h'])
    hw = PART['hs_wifi']
    cxw, cyw = px + 44.15, py + P['d'] - 16.4
    add('pi', cxw - hw['w'] / 2, cyw - hw['w'] / 2, pz + P['t'], cxw + hw['w'] / 2, cyw + hw['w'] / 2, pz + P['t'] + hw['chip'] + hw['h'])
    for xc, wc, hc in ((12.4, 11.2, 3.3), (41.4, 8.0, 2.6), (54.0, 8.0, 2.6)):   # mini-HDMI, USB, PWR (front edge)
        add('pi', px + xc - wc / 2, py - 0.5, pz + P['t'], px + xc + wc / 2, py + 5.5, pz + P['t'] + hc)
    add('pi', px + 6.0, py + P['d'] - 7.0, pz + P['t'], px + 59.0, py + P['d'], pz + P['t'] + 3.5)   # GPIO wires
    add('pi', px + 3.0, py + 4.0, pz - P['under'], px + P['w'] - 3.0, py + P['d'] - 4.0, pz)        # parts underneath
    # front-right floor, in front of the battery and under the buttons: clock, then the USB-C breakout
    r = PART['rtc']
    add('rtc', *RTC_BOX)
    add('usbc', *USBC_BOX)
    # the boost board sits on a shelf over the clock; its trimmer stands up under the empty grid spots
    add('boost', *BOOST_BOX)
    add('boost', *BOOST_POT)
    # back-left, under the middle sheet: charger, and the ADC on a shelf above it
    add('charger', *CHG_BOX)
    add('adc', *ADC_BOX)
    # buttons: switch body + actuator, the carrier under them, legs below
    for name, ((x, y), _) in BUTTONS.items():
        h = B['w'] / 2
        lx, ly = B['legs'][0] / 2 + 0.5, B['legs'][1] / 2 + 0.5
        add('btn_' + name, x - h, y - h, BTN_BED_Z + BTN_BED_T, x + h, y + h, BTN_TOP)                 # switch
        add('btn_' + name, x - lx, y - h, BTN_BED_Z, x + lx, y + h, BTN_BED_Z + BTN_BED_T)               # carrier under it
        add('btn_' + name, x - lx, y - ly, BTN_BED_Z - BTN_LEGS, x + lx, y + ly, BTN_BED_Z)             # legs + solder
    return out


JOY_CAP_R = 8.0          # printed cap: 16 mm disc
JOY_CAP_DISC = 2.0       # disc thickness; a 5 mm boss under it grips the top 4 mm of the stick
JOY_STOP_DEG = 18.0      # the cap's rim meets the hole edge here, a little before the joystick's own 25 degree stop


def joy_hole_r():
    """Radius of the top-plate hole: the cap's top rim touches it at JOY_STOP_DEG of tilt."""
    import math
    t = math.radians(JOY_STOP_DEG)
    return JOY_CAP_R * math.cos(t) + (J['tip'] + CAP_ABOVE_TIP - J['pivot']) * math.sin(t)


def cap_low_point(deg):
    """Lowest z of the cap disc's rim (base frame) and its distance from the stick axis, at a tilt."""
    import math
    t = math.radians(deg)
    pivot = JOY_PCB_Z + J['t'] + J['pivot']
    under = JOY_PCB_Z + J['t'] + J['tip'] + CAP_ABOVE_TIP - JOY_CAP_DISC
    h = under - pivot
    return pivot + h * math.cos(t) - JOY_CAP_R * math.sin(t), h * math.sin(t) + JOY_CAP_R * math.cos(t)


def keepouts():
    """Volumes that must stay empty, as boxes in the base frame: where the tilted cap can reach."""
    cx, cy = JOY_C
    r = joy_hole_r()
    zl, reach = cap_low_point(JOY_STOP_DEG)
    out = {'stick swing': [(cx - reach, cy - reach, zl, cx + reach, cy + reach, HB)]}
    out['corner screws'] = [(x0, y0, z0, x1, y1, FACE_Z) for (x0, y0, x1, y1, z0) in CORNER_BOSSES]
    return out


S = 3.8                  # corner boss size (square, filleted into the walls)
CORNER_BOSSES = (        # (x0, y0, x1, y1, lowest z): where the face-plate screws go into the tub
    (IN['x0'], IN['y0'], IN['x0'] + S, IN['y0'] + S, JOY_PCB_Z + J['t'] + 0.4),            # front-left, above the joystick board
    (IN['x1'] - S, IN['y0'], IN['x1'], IN['y0'] + S, FLOOR + PART['usbc']['h'] + 0.4),    # front-right, above the USB-C board
    # the back two sit just in front of the hinge block, so nothing covers their screw heads
    (IN['x0'], PI_ORG[1] + 6.5, IN['x0'] + S, PI_ORG[1] + 6.5 + S, SHEET_Z + SHEET_T + 0.2),  # left, in front of the Pi's microSD card
    (IN['x1'] - S, LID_D - 3.7 - S, IN['x1'], LID_D - 3.7, SHEET_Z + SHEET_T + 0.2),       # back-right, above the sheet
)


def check(margin=0.0):
    """Print every overlap between parts, and between parts and the case walls.
    margin: extra gap to demand around every box (0.25 means parts must be 0.5 mm apart)."""
    bx = {k: [(b[0] - margin, b[1] - margin, b[2] - margin, b[3] + margin, b[4] + margin, b[5] + margin) for b in v]
          for k, v in boxes().items()}
    names = list(bx)
    bad = 0
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if margin and a.startswith('btn_') and b.startswith('btn_'):
                continue                      # one shared carrier
            for p in bx[a]:
                for q in bx[b]:
                    ov = [min(p[k + 3], q[k + 3]) - max(p[k], q[k]) for k in range(3)]
                    if all(v > 1e-6 for v in ov):
                        bad += 1
                        print(f'OVERLAP {a:14s} x {b:14s}  by {ov[0]:.1f} x {ov[1]:.1f} x {ov[2]:.1f} mm')
    for a in names:
        for p in bx[a]:
            lim = (IN['x0'], IN['y0'], IN['z0'], IN['x1'], IN['y1'], IN['z1'])
            for k, axis in enumerate('xyz'):
                if margin and k == 2:
                    continue                  # parts may rest on the floor
                if p[k] < lim[k] - 1e-6 and not (a == 'pi' and k == 0):
                    bad += 1; print(f'OUTSIDE {a}: {axis} {p[k]:.1f} < {lim[k]:.1f}')
                if p[k + 3] > lim[k + 3] + 1e-6 and not (a == 'pi' and k == 2):
                    bad += 1; print(f'OUTSIDE {a}: {axis} {p[k+3]:.1f} > {lim[k+3]:.1f}')
    for k, vols in keepouts().items():
        for v in vols:
            for a in names:
                for p in bx[a]:
                    if a == 'joystick' and k == 'stick swing':
                        continue
                    ov = [min(p[i + 3], v[i + 3]) - max(p[i], v[i]) for i in range(3)]
                    if all(x > 1e-6 for x in ov):
                        bad += 1; print(f'KEEPOUT {k} x {a}')
    return bad


if __name__ == '__main__':
    print(f'Lid {LID_W:.1f} x {LID_D:.1f} x {LID_T:.1f} mm; base {W:.1f} x {D:.1f} x {HB:.1f} mm; closed {CLOSED_T:.1f} mm')
    print(f'Inside the base: {IN["x1"]-IN["x0"]:.1f} x {IN["y1"]-IN["y0"]:.1f} x {IN["z1"]-IN["z0"]:.1f} mm')
    print(f'Stick centre ({JOY_C[0]:.1f}, {JOY_C[1]:.1f}); top-plate hole diameter {2*joy_hole_r():.1f} mm')
    print(f'Middle sheet z {SHEET_Z:.1f}..{SHEET_Z+SHEET_T:.1f}; Pi board z {PI_Z:.1f}; button carrier z {BTN_BED_Z:.1f}')
    n = check()
    print('collisions:', n)
    print('with 0.5 mm clearance demanded:')
    print('tight spots:', check(0.25))
