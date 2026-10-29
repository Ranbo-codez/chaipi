"""Layout maths shared by the one-piece ChAIpi cases (portrait and landscape).

The clamshell (enclosure/case) keeps the screen in a lid. These two are single slabs: the screen
sits under the same top plate as the joystick and the buttons, like a handheld game console.

Same bought parts, and the same height stack as the clamshell's base. Part sizes come from
enclosure/case/tools/layout.py, so a size you correct there reaches all three cases.

Coordinates in mm. Origin at the case's outer bottom-left corner on its back:
X runs left to right, Y from the bottom edge (nearest you) to the top edge, Z from the back (0)
up to the face (HB).

Each case's tools/layout.py builds a Layout from positions, and `python3 <case>/tools/layout.py`
prints its collision check. build_slab.py (run inside Blender) turns a Layout into parts.
"""
import importlib.util
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


clam = _load(os.path.join(HERE, '..', 'case', 'tools', 'layout.py'), 'clamshell_layout')
PART = clam.PART
T, J, P, C, B = PART['tft'], PART['joy'], PART['pi'], PART['cell'], PART['btn']

# ---------------------------------------------------------------------------------------------
# Height stack (Z). The joystick sets it, exactly as in the clamshell's base.
# ---------------------------------------------------------------------------------------------
WALL = 1.6                                   # side walls
FLOOR = clam.FLOOR                           # 1.6, the back
FACE = clam.FACE                             # 1.6, the top plate
JOY_PCB_Z = clam.JOY_PCB_Z                   # 4.0: joystick board on 2.4 mm pads
HB = clam.HB                                 # 25.9: whole thickness (the stick's cap ends flush with the face)
FZ = clam.FACE_Z                             # 24.3: underside of the top plate
SCREEN_PCB_TOP = FZ - (T['total'] - T['pcb'])  # 20.3: the screen's glass touches the plate, its board hangs below
SCREEN_PCB_BOT = FZ - T['total']               # 18.7
SCREEN_FLOOR = SCREEN_PCB_BOT - clam.SCREEN_BACK_GAP   # 16.3: below this is free (SMD parts + wires above it)
BTN_TOP = FZ - clam.BTN_CAP_FLANGE           # 23.5: switch actuator top
BTN_BED_T = clam.BTN_BED_T
BTN_BED_Z = BTN_TOP - B['act'] - B['body'] - BTN_BED_T   # 18.5: button carrier underside
BTN_LEGS = clam.BTN_LEGS
BATT_T = 2 * C['t'] + C['tape']              # 9.6
# The Pi lies upside down: heatsinks toward the back, over vent slots in it. Its board rests on
# four posts, and the screws go in from the side that faces you.
PI_AIR = 0.6                                 # heatsink fins to the floor
PI_B0 = FLOOR + PI_AIR + PART['hs_cpu']['chip'] + PART['hs_cpu']['h']   # 10.4: the Pi's component side (facing down)
PI_B1 = PI_B0 + P['t']                       # 11.8
COLLAR = 2.0                                 # thickening under each face screw head
BOSS_R = 3.2                                 # radius of the screw bosses in the tub
PILOT_DEPTH = 6.0                            # M2.5 x 8 face screws: plate + collar, then 6 mm into the post
JOY_CAP_R, JOY_CAP_DISC = clam.JOY_CAP_R, clam.JOY_CAP_DISC
joy_hole_r = clam.joy_hole_r
cap_low_point = clam.cap_low_point
JOY_STOP_DEG = clam.JOY_STOP_DEG
BOARD_SIZES = {'rtc': PART['rtc'], 'chg': PART['chg'], 'boost': PART['boost'], 'adc': PART['adc']}
BOARD_NAMES = {'rtc': 'DS3231 clock', 'chg': 'TP4056 charger', 'boost': 'MT3608 boost', 'adc': 'ADS1115'}


# ---------------------------------------------------------------------------------------------
# 2D helpers
# ---------------------------------------------------------------------------------------------
def outline(W, D, radii, inset=0.0, seg=10):
    """Rounded rectangle with its own radius at each corner (bl, br, tr, tl), inset inward."""
    bl, br, tr, tl = (max(0.0, r - inset) for r in radii)
    x0, y0, x1, y1 = inset, inset, W - inset, D - inset
    pts = []
    for cx, cy, r, a in ((x0 + bl, y0 + bl, bl, 180), (x1 - br, y0 + br, br, 270),
                         (x1 - tr, y1 - tr, tr, 0), (x0 + tl, y1 - tl, tl, 90)):
        if r <= 0:
            pts.append((cx, cy))
            continue
        k = max(2, int(seg * (1 + r / 8)))           # more segments on bigger corners
        for i in range(k + 1):
            t = math.radians(a + 90 * i / k)
            pts.append((cx + r * math.cos(t), cy + r * math.sin(t)))
    return pts


def inside_outline(W, D, radii, x, y, inset):
    """Is the point inside the rounded rectangle inset by `inset`?"""
    if not (inset - 1e-6 <= x <= W - inset + 1e-6 and inset - 1e-6 <= y <= D - inset + 1e-6):
        return False
    bl, br, tr, tl = radii
    for cx, cy, r, sx, sy in ((bl, bl, bl, -1, -1), (W - br, br, br, 1, -1), (W - tr, D - tr, tr, 1, 1), (tl, D - tl, tl, -1, 1)):
        if r <= inset:
            continue
        if (x - cx) * sx > 0 and (y - cy) * sy > 0 and math.hypot(x - cx, y - cy) > r - inset + 1e-6:
            return False
    return True


def hull(points):
    """Convex hull, counter-clockwise (monotone chain)."""
    pts = sorted(set(points))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def _circle_pts(cx, cy, r, n=16):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


# ---------------------------------------------------------------------------------------------
# One case
# ---------------------------------------------------------------------------------------------
class Layout:
    def __init__(self, *, name, title, W, D, radii, picture_c, joy_c, buttons, carriers, battery, pi,
                 boards, usbc_x, screws, wordmark=None, back_wordmark=None, lens=None, grille=()):
        self.name, self.title = name, title
        self.W, self.D, self.radii = W, D, radii
        self.IN = dict(x0=WALL, x1=W - WALL, y0=WALL, y1=D - WALL, z0=FLOOR, z1=FZ)
        aa = T['aa']
        # body position of the screen board: its x = 0 end at X0, its y = 0 edge (the top of the picture) at Y0
        self.X0 = picture_c[0] - (aa[0] + aa[2]) / 2
        self.Y0 = picture_c[1] + (aa[1] + aa[3]) / 2
        self.JC = joy_c
        self.JOY_ORG = (joy_c[0] - J['lever'][0], joy_c[1] - J['lever'][1])
        self.buttons = buttons                    # name -> ((x, y), cap diameter)
        self.carriers = carriers                  # list of dict(name, buttons, screws)
        self.battery = battery                    # (x0, y0, side the wires leave: 'L' or 'R')
        self.pi = pi                              # (x0, y0): board corner; GPIO edge along y0
        self.boards = boards                      # key -> (x0, y0, rotated 90?, extra) ; boost extra = trimmer end
        self.usbc_x = usbc_x                      # left edge of the USB-C breakout; its port is in the bottom wall
        self.screw_xy = screws                    # face screws: list of (x, y, webs) webs = walls to tie into
        self.wordmark = wordmark                  # (text, size, x, y) engraved in the face
        self.back_wordmark = back_wordmark        # (text, size, x, y) engraved in the back
        self.lens = lens                          # dict(x0, y0, x1, y1, r, r_br): dark screen surround
        self.grille = grille                      # slots in the face: ((x0, y0), (x1, y1), width)

    # --- screen -------------------------------------------------------------------------
    def tft(self, hx, hy):
        return (self.X0 + hx, self.Y0 - hy)

    def tft_rect(self, x0, y0, x1, y1):
        return (self.X0 + x0, self.Y0 - y1, self.X0 + x1, self.Y0 - y0)

    @property
    def picture(self):
        return self.tft_rect(*T['aa'])

    @property
    def pcb(self):
        return self.tft_rect(0, 0, T['w'], T['d'])

    @property
    def tft_holes(self):
        return [self.tft(*h) for h in T['holes']]

    # --- joystick ------------------------------------------------------------------------
    @property
    def joy_holes(self):
        jx, jy = self.JOY_ORG
        i = J['holes_in']
        return [(jx + i, jy + i), (jx + J['w'] - i, jy + i), (jx + i, jy + J['d'] - i), (jx + J['w'] - i, jy + J['d'] - i)]

    # --- Pi (upside down) ------------------------------------------------------------------
    def pi_xy(self, lx, ly):
        """Pi-board coordinates (its official drawing, top view) to the body. The board is flipped
        about its long axis, so its GPIO edge (ly = 30) lands on the body's y0 side."""
        px, py = self.pi
        return (px + lx, py + P['d'] - ly)

    @property
    def pi_holes(self):
        return [self.pi_xy(x, y) for x, y in ((3.5, 3.5), (61.5, 3.5), (3.5, 26.5), (61.5, 26.5))]

    @property
    def cpu(self):
        return self.pi_xy(27.3, P['d'] - 16.05)

    @property
    def wifi(self):
        return self.pi_xy(44.15, P['d'] - 16.4)

    def pi_rect(self, lx0, ly0, lx1, ly1):
        a, b = self.pi_xy(lx0, ly0), self.pi_xy(lx1, ly1)
        return (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))

    # --- small boards ----------------------------------------------------------------------
    def board_box(self, key):
        x0, y0, rot, *_ = self.boards[key]
        s = BOARD_SIZES[key]
        w, d = (s['d'], s['w']) if rot else (s['w'], s['d'])
        return (x0, y0, FLOOR, x0 + w, y0 + d, FLOOR + s['h'])

    def boost_pot(self):
        x0, y0, rot, end = self.boards['boost']
        b = self.board_box('boost')
        s = PART['boost']
        pl, pw, ph = s['pot']
        if not rot:
            cy = (b[1] + b[4]) / 2
            px0 = b[0] + s['pot_in'] if end == 'L' else b[3] - s['pot_in'] - pl
            return (px0, cy - pw / 2, FLOOR, px0 + pl, cy + pw / 2, FLOOR + ph)
        cx = (b[0] + b[3]) / 2
        py0 = b[1] + s['pot_in'] if end == 'B' else b[4] - s['pot_in'] - pl
        return (cx - pw / 2, py0, FLOOR, cx + pw / 2, py0 + pl, FLOOR + ph)

    @property
    def usbc_box(self):
        u = PART['usbc']
        y0 = self.IN['y0'] + 0.4
        return (self.usbc_x, y0, FLOOR, self.usbc_x + u['w'], y0 + u['d'], FLOOR + u['h'])

    @property
    def batt_box(self):
        bx, by, _ = self.battery
        return (bx, by, FLOOR, bx + C['w'], by + C['d'], FLOOR + BATT_T)

    @property
    def batt_stub(self):
        bx, by, side = self.battery
        x0 = bx - 3.0 if side == 'L' else bx + C['w']
        return (x0, by + 8, FLOOR, x0 + 3.0, by + 26, FLOOR + BATT_T)

    # --- buttons and carriers --------------------------------------------------------------
    def carrier_outline(self, carrier):
        pts = []
        lx = B['legs'][0] / 2 + 0.5 + 0.8
        h = B['w'] / 2 + 0.3
        for n in carrier['buttons']:
            (x, y), _ = self.buttons[n]
            pts += [(x - lx, y - h), (x + lx, y - h), (x + lx, y + h), (x - lx, y + h)]
        for sx, sy in carrier['screws']:
            pts += _circle_pts(sx, sy, 3.0)
        return hull(pts)

    # --- face screws ---------------------------------------------------------------------
    def screws(self):
        """(x, y, lowest z, webs). Every post stands on the back. A post hanging over a part would stop
        that part going in, so check() reports any part under a post as a KEEPOUT problem."""
        return [(x, y, FLOOR, webs) for x, y, webs in self.screw_xy]

    # --- everything as boxes -------------------------------------------------------------
    def boxes(self):
        out = {}

        def add(name, *b):
            out.setdefault(name, []).append(tuple(float(v) for v in b))

        # joystick: board, body (frame, pots, switch), wire stub
        jx, jy = self.JOY_ORG
        add('joystick', jx, jy, JOY_PCB_Z, jx + J['w'], jy + J['d'], JOY_PCB_Z + J['t'])
        cx, cy = self.JC
        e = J['env']
        zt = JOY_PCB_Z + J['t']
        add('joystick', cx + e[0], cy + e[1], zt, cx + e[2], cy + e[3], zt + J['env_h'])
        add('joystick', jx, jy + 7, zt, jx + 3.0, jy + 19, zt + 2.6)
        # battery
        add('battery', *self.batt_box)
        add('battery', *self.batt_stub)
        # Pi, upside down: board, heatsinks and connectors below it, small parts and wires above
        add('pi', *self.pi_rect(0, 0, P['w'], P['d'])[:2], PI_B0, *self.pi_rect(0, 0, P['w'], P['d'])[2:], PI_B1)
        for (hx, hy), part in ((self.cpu, PART['hs_cpu']), (self.wifi, PART['hs_wifi'])):
            w = part['w'] / 2
            add('pi', hx - w, hy - w, PI_B0 - part['chip'] - part['h'], hx + w, hy + w, PI_B0)
        r = self.pi_rect(-P['sd_out'], 10.8, 13.0, 22.9)
        add('pi', r[0], r[1], PI_B0 - 1.4, r[2], r[3], PI_B0)                                  # microSD + card
        for xc, wc, hc in ((12.4, 11.2, 3.3), (41.4, 8.0, 2.6), (54.0, 8.0, 2.6)):            # mini-HDMI, USB, PWR
            r = self.pi_rect(xc - wc / 2, -0.5, xc + wc / 2, 5.5)
            add('pi', r[0], r[1], PI_B0 - hc, r[2], r[3], PI_B0)
        r = self.pi_rect(6.0, P['d'] - 7.0, 59.0, P['d'])
        add('pi', r[0], r[1], PI_B1, r[2], r[3], PI_B1 + 3.0)                                  # GPIO wires (header removed)
        r = self.pi_rect(3.0, 4.0, P['w'] - 3.0, P['d'] - 4.0)
        add('pi', r[0], r[1], PI_B1, r[2], r[3], PI_B1 + P['under'])                           # parts on the far side
        # small boards
        for key in self.boards:
            add(BOARD_NAMES[key], *self.board_box(key))
        add(BOARD_NAMES['boost'], *self.boost_pot())
        add('USB-C breakout', *self.usbc_box)
        # screen: glass, board, and the space its back parts and wires need
        x0, y0, x1, y1 = self.pcb
        g = self.tft_rect(T['lcd'][0], 0, T['lcd'][1], T['d'])
        add('screen', g[0], g[1], SCREEN_PCB_TOP, g[2], g[3], FZ)
        add('screen', x0, y0, SCREEN_FLOOR, x1, y1, SCREEN_PCB_TOP)
        # buttons: switch, carrier strip under it, legs
        for name, ((x, y), _) in self.buttons.items():
            h = B['w'] / 2
            lx, ly = B['legs'][0] / 2 + 0.5, B['legs'][1] / 2 + 0.5
            add('btn_' + name, x - h, y - h, BTN_BED_Z + BTN_BED_T, x + h, y + h, BTN_TOP)
            add('btn_' + name, x - lx, y - h, BTN_BED_Z, x + lx, y + h, BTN_BED_Z + BTN_BED_T)
            add('btn_' + name, x - lx, y - ly, BTN_BED_Z - BTN_LEGS, x + lx, y + ly, BTN_BED_Z)
        return out

    def keepouts(self):
        cx, cy = self.JC
        zl, reach = cap_low_point(JOY_STOP_DEG)
        out = {'stick swing': [(cx - reach, cy - reach, zl, cx + reach, cy + reach, HB)]}
        out['face screws'] = [(x - BOSS_R, y - BOSS_R, zl_, x + BOSS_R, y + BOSS_R, FZ) for x, y, zl_, _ in self.screws()]
        out['Pi posts'] = [(x - 2.6, y - 2.6, FLOOR, x + 2.6, y + 2.6, PI_B0) for x, y in self.pi_holes]
        out['joystick pads'] = [(x - 3.0, y - 3.0, FLOOR, x + 3.0, y + 3.0, JOY_PCB_Z) for x, y in self.joy_holes]
        out['carriers'] = []
        for c in self.carriers:
            xs, ys = zip(*self.carrier_outline(c))
            out['carriers'].append((min(xs), min(ys), BTN_BED_Z, max(xs), max(ys), BTN_BED_Z + BTN_BED_T))
        return out

    def check(self, margin=0.0, quiet=False):
        """Overlaps between parts, parts poking out of the case, and parts in the keep-out volumes."""
        def grow(b):
            return (b[0] - margin, b[1] - margin, b[2] - margin, b[3] + margin, b[4] + margin, b[5] + margin)
        bx = {k: [grow(b) for b in v] for k, v in self.boxes().items()}
        names = list(bx)
        msgs = []

        def ov(p, q):
            return [min(p[k + 3], q[k + 3]) - max(p[k], q[k]) for k in range(3)]
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                if margin and a.startswith('btn_') and b.startswith('btn_'):
                    continue
                for p in bx[a]:
                    for q in bx[b]:
                        o = ov(p, q)
                        if all(v > 1e-6 for v in o):
                            msgs.append(f'OVERLAP {a} x {b} by {o[0]:.1f} x {o[1]:.1f} x {o[2]:.1f} mm')
        for a in names if not margin else ():          # parts poking out (exact sizes only)
            for p in bx[a]:
                if p[2] < FLOOR - 1e-6:
                    msgs.append(f'OUTSIDE {a}: below the floor')
                if p[5] > FZ + 1e-6:
                    msgs.append(f'OUTSIDE {a}: above the top plate')
                for x, y in ((p[0], p[1]), (p[3], p[1]), (p[3], p[4]), (p[0], p[4])):
                    if not inside_outline(self.W, self.D, self.radii, x, y, WALL):
                        msgs.append(f'OUTSIDE {a}: corner ({x:.1f}, {y:.1f}) in a wall')
        skip = {('stick swing', 'joystick'), ('Pi posts', 'pi'), ('joystick pads', 'joystick')}
        for k, vols in self.keepouts().items():
            for v in vols:
                for a in names:
                    if (k, a) in skip or (k == 'carriers' and a.startswith('btn_')):
                        continue
                    for p in bx[a]:
                        if all(x > 1e-6 for x in ov(p, v)):
                            msgs.append(f'KEEPOUT {k} x {a}')
        # things cut through the face must not run into each other
        msgs += self.face_check()
        if not quiet:
            for m in dict.fromkeys(msgs):
                print(m)
        return len(set(msgs))

    def face_holes(self):
        """Circles cut through the top plate: (x, y, r, what)."""
        out = [(self.JC[0], self.JC[1], joy_hole_r(), 'joystick')]
        for n, ((x, y), d) in self.buttons.items():
            out.append((x, y, d / 2 + 0.2 + 1.2, n))       # with the cap's flange underneath
        for x, y, _ in self.screw_xy:
            out.append((x, y, 2.7, 'screw'))               # the counterbore for the head
        for c in self.carriers:
            for x, y in c['screws']:
                out.append((x, y, 2.6, c['name'] + ' screw'))
        for (x0, y0), (x1, y1), w in self.grille:
            n = max(2, int(math.hypot(x1 - x0, y1 - y0) / 1.0))
            for i in range(n + 1):
                out.append((x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n, w / 2, 'grille'))
        return out

    def face_check(self):
        msgs = []
        holes = self.face_holes()
        pic = self.picture
        win = (pic[0] - 1.5, pic[1] - 1.5, pic[2] + 1.5, pic[3] + 1.5)
        pcb = self.pcb
        for i, (x, y, r, a) in enumerate(holes):
            edge = 1.0 if a == 'screw' else WALL + 0.8      # screw heads may sit close to the edge, as on the clamshell
            if not all(inside_outline(self.W, self.D, self.radii, x + dx, y + dy, edge)
                       for dx, dy in ((r, 0), (-r, 0), (0, r), (0, -r))):
                msgs.append(f'FACE {a} too close to the edge')
            if a != 'screw' and pcb[0] - r < x < pcb[2] + r and pcb[1] - r < y < pcb[3] + r:
                msgs.append(f'FACE {a} over the screen board')
            if win[0] - r < x < win[2] + r and win[1] - r < y < win[3] + r:
                msgs.append(f'FACE {a} cuts into the screen window')
            l = self.lens
            if l and l['x0'] - r - 0.8 < x < l['x1'] + r + 0.8 and l['y0'] - r - 0.8 < y < l['y1'] + r + 0.8:
                msgs.append(f'FACE {a} cuts into the screen surround')
            for x2, y2, r2, b in holes[i + 1:]:
                if a == b == 'grille':
                    continue
                if math.hypot(x - x2, y - y2) < r + r2 + 0.8:
                    msgs.append(f'FACE {a} too close to {b}')
        return msgs

    def report(self):
        W, D = self.W, self.D
        print(f'{self.title}: {W:.1f} x {D:.1f} x {HB:.1f} mm')
        print(f'picture {tuple(round(v, 1) for v in self.picture)}; screen board {tuple(round(v, 1) for v in self.pcb)}')
        print(f'stick centre {self.JC}; hole diameter {2 * joy_hole_r():.1f} mm')
        print('face screws at', ', '.join(f'({x:.1f}, {y:.1f})' for x, y, _, _ in self.screws()))
        print('collisions:', self.check())
        print('with 0.5 mm clearance demanded (tight spots):', self.check(0.25, quiet=False))
