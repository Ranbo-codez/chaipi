# Builds a one-piece ChAIpi case (portrait or landscape) in Blender from its tools/layout.py:
# printable parts (STL), rough models of the bought parts, a coloured model (GLB) and renders.
#
#   Blender --background --factory-startup --python enclosure/tools/build_slab.py -- enclosure/case-portrait
#   Blender --background --factory-startup --python enclosure/tools/build_slab.py -- enclosure/case-landscape
#
# Units are millimetres. STL files are written in print orientation. The geometry helpers are the
# same as the clamshell's (enclosure/case/tools/build_case.py), and so are the colours and the
# render setup, so the three cases look like one family.
import bpy, bmesh, math, os, sys
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import slab as S  # noqa: E402

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
if not ARGS:
    raise SystemExit('usage: ... build_slab.py -- enclosure/case-portrait')
OUT = os.path.abspath(ARGS[0])
LAY = S._load(os.path.join(OUT, 'tools', 'layout.py'), 'case_layout').LAYOUT
FONT = os.path.join(HERE, '..', '..', 'device', 'fonts', 'Unbounded-SemiBold.ttf')

bpy.ops.wm.read_factory_settings(use_empty=True)
SCENE = bpy.context.scene
WORK = SCENE.collection

W, D, HB, FZ = LAY.W, LAY.D, S.HB, S.FZ
IN = LAY.IN
SEG = 48

# ---------------------------------------------------------------------------------------------
# geometry helpers (as in build_case.py)
# ---------------------------------------------------------------------------------------------

def _obj(name, bm):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    WORK.objects.link(ob)
    return ob


def _map(u, v, a, axis):
    return {'z': (u, v, a), 'x': (a, u, v), 'y': (u, a, v)}[axis]


def loft(lo, hi, a0, a1, axis='z', name='p'):
    """Closed solid between outline `lo` at a0 and outline `hi` at a1 (same point count)."""
    bm = bmesh.new()
    b = [bm.verts.new(_map(u, v, a0, axis)) for u, v in lo]
    t = [bm.verts.new(_map(u, v, a1, axis)) for u, v in hi]
    bm.faces.new(b[::-1])
    bm.faces.new(t)
    n = len(lo)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((b[i], b[j], t[j], t[i]))
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    return _obj(name, bm)


def prism(pts, a0, a1, axis='z', name='p'):
    return loft(pts, pts, a0, a1, axis, name)


def rrect(x0, y0, x1, y1, r, seg=8):
    r = max(0.0, min(r, (x1 - x0) / 2 - 1e-3, (y1 - y0) / 2 - 1e-3))
    if r <= 0:
        return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    pts = []
    for cx, cy, a in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for i in range(seg + 1):
            t = math.radians(a + 90 * i / seg)
            pts.append((cx + r * math.cos(t), cy + r * math.sin(t)))
    return pts


def shape(x0, y0, x1, y1, radii, inset=0.0):
    """Outline of a rectangle with its own corner radii (bl, br, tr, tl), placed at (x0, y0)."""
    return [(x0 + u, y0 + v) for u, v in S.outline(x1 - x0, y1 - y0, radii, inset)]


def circle(cx, cy, r, seg=SEG):
    return [(cx + r * math.cos(2 * math.pi * i / seg), cy + r * math.sin(2 * math.pi * i / seg)) for i in range(seg)]


def box(x0, y0, z0, x1, y1, z1, name='box'):
    return prism([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1, 'z', name)


def rbox(x0, y0, z0, x1, y1, z1, r, name='rbox'):
    return prism(rrect(x0, y0, x1, y1, r), z0, z1, 'z', name)


def cyl(cx, cy, z0, z1, r, seg=SEG, name='cyl'):
    return prism(circle(cx, cy, r, seg), z0, z1, 'z', name)


def slot_xy(p0, p1, w, z0, z1, name='slot'):
    """Rounded slot from p0 to p1 (any angle), width w."""
    (x0, y0), (x1, y1) = p0, p1
    a = math.atan2(y1 - y0, x1 - x0)
    pts = []
    for (cx, cy), start in (((x1, y1), a - math.pi / 2), ((x0, y0), a + math.pi / 2)):
        for i in range(13):
            t = start + math.pi * i / 12
            pts.append((cx + w / 2 * math.cos(t), cy + w / 2 * math.sin(t)))
    return prism(pts, z0, z1, 'z', name)


def apply_mods(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    bpy.data.meshes.remove(old)


def boolean(target, tools, op, solver='MANIFOLD'):
    tools = [t for t in tools if t is not None]
    if not tools:
        return target
    coll = bpy.data.collections.new('tools')
    SCENE.collection.children.link(coll)
    for t in tools:
        for c in list(t.users_collection):
            c.objects.unlink(t)
        coll.objects.link(t)
    m = target.modifiers.new('b', 'BOOLEAN')
    m.operation = op
    m.solver = solver
    m.operand_type = 'COLLECTION'
    m.collection = coll
    apply_mods(target)
    for t in tools:
        bpy.data.objects.remove(t)
    bpy.data.collections.remove(coll)
    return target


def union(target, tools):
    return boolean(target, tools, 'UNION')


def diff(target, tools, solver='MANIFOLD'):
    return boolean(target, tools, 'DIFFERENCE', solver)


def intersect(target, tool):
    return boolean(target, [tool], 'INTERSECT')


def text_solid(s, size, cx, cy, z0, z1, name='text', mirror_y=False):
    cu = bpy.data.curves.new(name, 'FONT')
    cu.body = s
    cu.font = bpy.data.fonts.load(FONT)
    cu.size = size
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    cu.extrude = (z1 - z0) / 2
    cu.resolution_u = 6
    ob = bpy.data.objects.new(name + '_c', cu)
    WORK.objects.link(ob)
    ob.location = (cx, cy, (z0 + z1) / 2)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    m = ob.matrix_world.copy()
    bpy.data.objects.remove(ob)
    if mirror_y:      # reads correctly on the back once the case is turned over top-to-bottom
        m = Matrix.Translation((0, cy, 0)) @ Matrix.Scale(-1, 4, (0, 1, 0)) @ Matrix.Translation((0, -cy, 0)) @ m
    me.transform(m)
    mob = bpy.data.objects.new(name, me)
    WORK.objects.link(mob)
    bm = bmesh.new()
    bm.from_mesh(mob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(mob.data)
    bm.free()
    return mob


def joined(name, obs):
    """Join objects into one mesh without booleans (for component models made of touching parts)."""
    obs = [o for o in obs if o is not None]
    bm = bmesh.new()
    for o in obs:
        t = bmesh.new()
        t.from_mesh(o.data)
        t.transform(o.matrix_world)
        me = bpy.data.meshes.new('tmp')
        t.to_mesh(me)
        t.free()
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
        bpy.data.objects.remove(o)
    return _obj(name, bm)


# ---------------------------------------------------------------------------------------------
# positions from the layout
# ---------------------------------------------------------------------------------------------
J, P, T, B = S.J, S.P, S.T, S.B
JX, JY = LAY.JOY_ORG
JC = LAY.JC
BTN = LAY.buttons
SCREWS = LAY.screws()
OUTER = S.outline(W, D, LAY.radii)
INNER = S.outline(W, D, LAY.radii, S.WALL)


def outer_prism(z0, z1):
    return prism(OUTER, z0, z1)


# ---------------------------------------------------------------------------------------------
# printable parts (built in place)
# ---------------------------------------------------------------------------------------------

def make_tub():
    t = prism(OUTER, 0, FZ, 'z', 'tub')
    t = diff(t, [prism(INNER, S.FLOOR, FZ + 1)])
    add = []
    top = FZ - S.COLLAR
    for x, y, zl, webs in SCREWS:                       # face-screw posts, standing on the back, tied into the walls
        full = S.FLOOR - 0.1
        add.append(cyl(x, y, full, top, S.BOSS_R))
        r = S.BOSS_R
        web = {'L': (-1, y - r, x, y + r), 'R': (x, y - r, W + 1, y + r),
               'B': (x - r, -1, x + r, y), 'T': (x - r, y, x + r, D + 1)}
        for wd in webs:
            x0, y0, x1, y1 = web[wd]
            add.append(box(x0, y0, full, x1, y1, top))
    for hx, hy in LAY.joy_holes:                        # joystick pads
        add.append(cyl(hx, hy, S.FLOOR - 0.1, S.JOY_PCB_Z, 3.0))
    for hx, hy in LAY.pi_holes:                         # Pi posts (the Pi lies upside down on them)
        add.append(cyl(hx, hy, S.FLOOR - 0.1, S.PI_B0, 2.6))
    bx0, by0, _, bx1, by1, _ = LAY.batt_box             # battery corners
    g, th, ln, h = 0.3, 1.2, 6.0, S.FLOOR + 4.0
    for cx, sx in ((bx0, -1), (bx1, 1)):
        for cy, sy in ((by0, -1), (by1, 1)):
            xa, ya = cx + sx * g, cy + sy * g
            add.append(box(min(xa, xa + sx * th), min(ya - sy * ln, ya + sy * th), S.FLOOR - 0.1,
                           max(xa, xa + sx * th), max(ya - sy * ln, ya + sy * th), h))
            add.append(box(min(xa - sx * ln, xa + sx * th), min(ya, ya + sy * th), S.FLOOR - 0.1,
                           max(xa - sx * ln, xa + sx * th), max(ya, ya + sy * th), h))
    ub = LAY.usbc_box                                   # backstop behind the USB-C board
    add.append(box(ub[0] + 0.5, ub[4] + 0.4, S.FLOOR - 0.1, ub[3] - 0.5, ub[4] + 1.5, S.FLOOR + 3.0))
    t = union(t, add)
    t = intersect(t, outer_prism(-1, FZ))               # trims boss webs to the rounded outside
    cut = []
    for x, y, zl, _ in SCREWS:
        cut.append(cyl(x, y, top - S.PILOT_DEPTH, FZ + 1, 1.05, 24))
    for hx, hy in LAY.joy_holes:
        cut.append(cyl(hx, hy, 0.4, S.JOY_PCB_Z + 0.1, 1.05, 24))
    for hx, hy in LAY.pi_holes:
        cut.append(cyl(hx, hy, S.PI_B0 - 4.0, S.PI_B0 + 0.1, 1.05, 24))
    ucx = (ub[0] + ub[3]) / 2                           # USB-C opening in the bottom wall
    uz = S.FLOOR + 1.6 + S.PART['usbc']['port_h'] / 2
    cut.append(prism(rrect(ucx - 4.9, uz - 2.0, ucx + 4.9, uz + 2.0, 1.95), -1, IN['y0'] + 0.6, 'y'))
    (cx, cy), (wx, wy) = LAY.cpu, LAY.wifi              # vents in the back, right under the Pi's heatsinks
    vx0, vx1 = cx - 8.0, wx + 6.5
    for i in range(int((vx1 - vx0) // 3.0)):
        x = vx0 + 1.5 + i * 3.0
        cut.append(slot_xy((x, cy - 6.0), (x, cy + 6.0), 1.5, -1, S.FLOOR + 0.1))
    t = diff(t, cut)
    if LAY.back_wordmark:
        s, size, x, y = LAY.back_wordmark
        try:
            t = diff(t, [text_solid(s, size, x, y, -1.0, 0.45, 'backword', mirror_y=True)], 'EXACT')
        except Exception as e:                          # decoration only
            print('back wordmark skipped:', e)
    return t


def window_cutters(z_face, chamfer=True):
    p = LAY.picture
    wx0, wy0, wx1, wy1 = p[0] - 0.5, p[1] - 0.5, p[2] + 0.5, p[3] + 0.5
    out = [rbox(wx0, wy0, FZ - 1, wx1, wy1, z_face + 1, 0.8)]
    if chamfer:
        out.append(loft(rrect(wx0, wy0, wx1, wy1, 0.8), rrect(wx0 - 0.7, wy0 - 0.7, wx1 + 0.7, wy1 + 0.7, 1.5), z_face - 0.7, z_face + 0.01))
    return out


def lens_outline(inset=0.0):
    l = LAY.lens
    r = l['r']
    return shape(l['x0'], l['y0'], l['x1'], l['y1'], (r, l['r_br'], r, r), inset)


def make_top_plate():
    p = prism(OUTER, FZ, HB, 'z', 'top_plate')
    add = [cyl(x, y, FZ - S.COLLAR, FZ + 0.1, 3.2) for x, y, _, _ in SCREWS]
    for c in LAY.carriers:
        for x, y in c['screws']:
            add.append(cyl(x, y, S.BTN_BED_Z + S.BTN_BED_T, FZ + 0.1, 2.6))
    for x, y in LAY.tft_holes:                          # the screen hangs on four posts
        add.append(cyl(x, y, S.SCREEN_PCB_TOP, FZ + 0.1, 2.3))
    p = union(p, add)
    cut = [cyl(JC[0], JC[1], FZ - 1, HB + 1, S.joy_hole_r(), 64)]
    for name, ((x, y), dcap) in BTN.items():
        cut.append(cyl(x, y, FZ - 1, HB + 1, dcap / 2 + 0.2, 40))
    for x, y, _, _ in SCREWS:
        cut.append(cyl(x, y, FZ - S.COLLAR - 1, HB + 1, 1.4, 24))
        cut.append(cyl(x, y, HB - 1.0, HB + 1, 2.7, 32))
    for c in LAY.carriers:
        for x, y in c['screws']:
            cut.append(cyl(x, y, S.BTN_BED_Z, FZ - 0.6, 0.8, 20))
    for x, y in LAY.tft_holes:
        cut.append(cyl(x, y, S.SCREEN_PCB_TOP - 0.1, S.SCREEN_PCB_TOP + 4.2, 1.05, 24))
    if LAY.lens:                                        # pocket for the dark screen surround
        cut.append(prism(lens_outline(-0.15), HB - 0.8, HB + 1))
        cut += window_cutters(HB - 0.8, chamfer=False)
    else:
        cut += window_cutters(HB)
    for p0, p1, w in LAY.grille:
        cut.append(slot_xy(p0, p1, w, FZ - 1, HB + 1))
    p = diff(p, cut)
    if LAY.wordmark:
        s, size, x, y = LAY.wordmark
        try:
            p = diff(p, [text_solid(s, size, x, y, HB - 0.45, HB + 1.0, 'word')], 'EXACT')
        except Exception as e:
            print('wordmark skipped:', e)
    return p


def make_lens():
    z0 = HB - 0.8
    l = prism(lens_outline(), z0, HB - 0.02, 'z', 'lens')
    return diff(l, window_cutters(HB - 0.02))


def make_carrier(c):
    z0, z1 = S.BTN_BED_Z, S.BTN_BED_Z + S.BTN_BED_T
    k = prism(LAY.carrier_outline(c), z0, z1, 'z', 'carrier_' + c['name'])
    k = intersect(k, prism(S.outline(W, D, LAY.radii, S.WALL + 0.3), z0 - 1, z1 + 1))
    cut = []
    for n in c['buttons']:
        (x, y), _ = BTN[n]
        for sx in (-1, 1):
            for sy in (-1, 1):
                cut.append(cyl(x + sx * B['legs'][0] / 2, y + sy * B['legs'][1] / 2, z0 - 1, z1 + 1, 0.7, 16))
    for x, y in c['screws']:
        cut.append(cyl(x, y, z0 - 1, z1 + 1, 1.1, 20))
    return diff(k, cut)


def make_button_caps():
    out = []
    for name, ((x, y), dcap) in BTN.items():
        flange = cyl(x, y, S.BTN_TOP, S.BTN_TOP + 0.8, dcap / 2 + 1.2, 40)
        body = cyl(x, y, S.BTN_TOP + 0.8 - 0.01, HB - 0.05, dcap / 2, 40)
        cap = union(flange, [body])
        cap.name = 'cap_' + name
        out.append(cap)
    return out


def make_joy_cap():
    cx, cy = JC
    tip = S.JOY_PCB_Z + J['t'] + J['tip']
    disc = cyl(cx, cy, HB - S.JOY_CAP_DISC, HB - 0.05, S.JOY_CAP_R, 64, 'joystick_cap')
    boss = cyl(cx, cy, tip - 4.0, HB - S.JOY_CAP_DISC + 0.1, 2.6, 32)
    c = union(disc, [boss])
    cut = [box(cx - 1.05, cy - 2.3, tip - 4.1, cx + 1.05, cy + 2.3, tip + 0.01)]
    for rr in (2.5, 4.5, 6.5):
        ring = diff(cyl(cx, cy, HB - 0.25, HB + 1, rr + 0.35, 64), [cyl(cx, cy, HB - 1, HB + 2, rr - 0.35, 64)])
        cut.append(ring)
    return diff(c, cut)


# ---------------------------------------------------------------------------------------------
# rough models of the bought parts (assembled position)
# ---------------------------------------------------------------------------------------------

def comp_models():
    out = {}
    b0, b1 = S.PI_B0, S.PI_B1
    r = LAY.pi_rect(0, 0, P['w'], P['d'])
    pi = box(r[0], r[1], b0, r[2], r[3], b1)
    out['Pi Zero 2 W'] = [diff(pi, [cyl(x, y, b0 - 1, b1 + 1, 1.375, 20) for x, y in LAY.pi_holes])]
    hs = []
    for (cx, cy), part in ((LAY.cpu, S.PART['hs_cpu']), (LAY.wifi, S.PART['hs_wifi'])):
        w = part['w'] / 2
        hs.append(box(cx - w, cy - w, b0 - part['chip'] - 1.0, cx + w, cy + w, b0))
        for i in range(5):
            fx = cx - w + 0.6 + i * (2 * w - 1.2) / 4
            hs.append(box(fx - 0.5, cy - w, b0 - part['chip'] - part['h'], fx + 0.5, cy + w, b0 - part['chip'] - 0.9))
    out['heatsinks'] = hs
    con = []
    for xc, wc, hc in ((12.4, 11.2, 3.3), (41.4, 8.0, 2.6), (54.0, 8.0, 2.6)):
        q = LAY.pi_rect(xc - wc / 2, -0.5, xc + wc / 2, 5.5)
        con.append(box(q[0], q[1], b0 - hc, q[2], q[3], b0))
    q = LAY.pi_rect(1.5, 10.8, 13.0, 22.9)
    con.append(box(q[0], q[1], b0 - 1.4, q[2], q[3], b0))
    q = LAY.pi_rect(-2.5, 11.5, 2.0, 22.5)
    con.append(box(q[0], q[1], b0 - 1.2, q[2], q[3], b0 - 0.4))
    out['Pi connectors'] = con
    bx, by, _ = LAY.battery
    c = S.C
    out['battery'] = [prism(rrect(bx, by, bx + c['w'], by + c['d'], 1.0), S.FLOOR, S.FLOOR + c['t']),
                      prism(rrect(bx, by, bx + c['w'], by + c['d'], 1.0), S.FLOOR + c['t'] + c['tape'], S.FLOOR + 2 * c['t'] + c['tape'])]
    jz = S.JOY_PCB_Z
    jt = jz + J['t']
    jb = box(JX, JY, jz, JX + J['w'], JY + J['d'], jt)
    out['joystick board'] = [diff(jb, [cyl(x, y, jz - 1, jt + 1, J['hole_d'] / 2, 24) for x, y in LAY.joy_holes])]
    cx, cy = JC
    f = J['frame'] / 2
    out['joystick'] = [box(cx - f, cy - f, jt, cx + f, cy + f, jt + J['frame_h']),
                       box(cx + f, cy - 4.75, jt, cx + 12.8, cy + 4.75, jt + 11.0),
                       box(cx - 4.75, cy + f, jt, cx + 4.75, cy + 8.6, jt + 11.0),
                       box(cx - 3.5, cy - 15.0, jt, cx + 3.5, cy - f, jt + 5.0),
                       cyl(cx, cy, jt + J['frame_h'], jt + J['tip'], 1.6, 20)]
    r = LAY.board_box('rtc')
    rw, rd = r[3] - r[0], r[4] - r[1]
    out['DS3231 clock'] = [box(r[0], r[1], r[2] + 4.3, r[3], r[4], r[2] + 5.9),
                           cyl((r[0] + r[3]) / 2, (r[1] + r[4]) / 2, r[2], r[2] + 4.3, min(rw, rd) / 2 - 0.5),
                           box(r[0] + rw * 0.55, r[1] + rd * 0.25, r[2] + 5.9, r[0] + rw * 0.85, r[1] + rd * 0.7, r[5])]
    bo, pot = LAY.board_box('boost'), LAY.boost_pot()
    out['MT3608 boost'] = [box(bo[0], bo[1], bo[2], bo[3], bo[4], bo[2] + 1.2),
                           box((bo[0] + bo[3]) / 2 - 3.5, (bo[1] + bo[4]) / 2 - 3.5, bo[2] + 1.2,
                               (bo[0] + bo[3]) / 2 + 3.5, (bo[1] + bo[4]) / 2 + 3.5, bo[5]), box(*pot)]
    for key, name, h1 in (('chg', 'TP4056 charger', 1.0), ('adc', 'ADS1115', 1.6)):
        q = LAY.board_box(key)
        mx, my = (q[0] + q[3]) / 2, (q[1] + q[4]) / 2
        out[name] = [box(q[0], q[1], q[2], q[3], q[4], q[2] + h1), box(mx - 3.5, my - 3.5, q[2] + h1, mx + 3.5, my + 3.5, q[5])]
    u = LAY.usbc_box
    out['USB-C breakout'] = [box(u[0], u[1], u[2], u[3], u[4], u[2] + 1.6),
                             box((u[0] + u[3]) / 2 - 4.5, u[1] - 0.3, u[2] + 1.6, (u[0] + u[3]) / 2 + 4.5, u[1] + 7.3, u[2] + 1.6 + 3.3)]
    sw = []
    for (x, y), dcap in BTN.values():
        z0 = S.BTN_BED_Z + S.BTN_BED_T
        sw.append(box(x - 6, y - 6, z0, x + 6, y + 6, z0 + B['body']))
        sw.append(cyl(x, y, z0 + B['body'] - 0.01, S.BTN_TOP, B['act_d'] / 2 - 0.6, 32))
    out['buttons'] = sw
    x0, y0, x1, y1 = LAY.pcb
    g = LAY.tft_rect(T['lcd'][0], 0, T['lcd'][1], T['d'])
    pcb = box(x0, y0, S.SCREEN_PCB_BOT, x1, y1, S.SCREEN_PCB_TOP)
    pcb = diff(pcb, [cyl(x, y, S.SCREEN_PCB_BOT - 1, S.SCREEN_PCB_TOP + 1, T['hole_d'] / 2, 24) for x, y in LAY.tft_holes])
    out['screen'] = [pcb, box(g[0], g[1], S.SCREEN_PCB_TOP, g[2], g[3], FZ - 0.02)]
    p = LAY.picture
    out['screen picture'] = [box(p[0], p[1], FZ - 0.01, p[2], p[3], FZ + 0.15)]   # just above the glass, so they don't flicker
    return out


COLOURS = {
    'tub': (0.40, 0.28, 0.22), 'top_plate': (0.45, 0.32, 0.25), 'lens': (0.16, 0.15, 0.15),
    'cap_Confirm': (0.82, 0.21, 0.40), 'joystick_cap': (0.12, 0.10, 0.10),
    'Pi Zero 2 W': (0.10, 0.45, 0.25), 'heatsinks': (0.65, 0.66, 0.70), 'Pi connectors': (0.75, 0.76, 0.78),
    'battery': (0.30, 0.45, 0.80), 'joystick board': (0.08, 0.08, 0.09), 'joystick': (0.55, 0.56, 0.58),
    'DS3231 clock': (0.10, 0.30, 0.65), 'MT3608 boost': (0.12, 0.35, 0.75), 'TP4056 charger': (0.15, 0.35, 0.70),
    'ADS1115': (0.45, 0.20, 0.55), 'USB-C breakout': (0.08, 0.08, 0.09), 'buttons': (0.10, 0.10, 0.11),
    'screen': (0.75, 0.15, 0.12), 'screen picture': (0.20, 0.45, 0.85),
}
CARRIER_RGB = (0.85, 0.78, 0.68)
CAP_RGB = (0.90, 0.85, 0.78)


def colour_for(k):
    if k in COLOURS:
        return COLOURS[k]
    if k.startswith('carrier_'):
        return CARRIER_RGB
    if k.startswith('cap_'):
        return CAP_RGB
    return (0.45, 0.32, 0.25)


def colour(ob, rgb):
    mat = bpy.data.materials.new(ob.name)
    mat.diffuse_color = (*rgb, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (*rgb, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.6
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    ob.color = (*rgb, 1.0)


def export_stl(obs, path):
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True, ascii_format=False, apply_modifiers=True)


def copy_obj(ob, name, m=None):
    me = ob.data.copy()
    if m is not None:
        me.transform(m)
    c = bpy.data.objects.new(name, me)
    WORK.objects.link(c)
    return c


# ---------------------------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------------------------

def _bvh(ob, m=None, shrink=0.08):
    """Triangle tree of an object, shrunk inward a little so faces that only touch don't count."""
    from mathutils.bvhtree import BVHTree
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.transform((m if m is not None else Matrix.Identity(4)))
    bm.normal_update()
    for v in bm.verts:
        v.co -= v.normal * shrink
    t = BVHTree.FromBMesh(bm)
    bm.free()
    return t


# pairs that are meant to touch or nest (screws, posts, pads, things resting on the floor)
EXPECTED = {frozenset(p) for p in [
    ('tub', 'top_plate'), ('top_plate', 'lens'), ('top_plate', 'screen'), ('top_plate', 'screen picture'),
    ('lens', 'screen picture'), ('tub', 'battery'), ('tub', 'joystick board'), ('tub', 'Pi Zero 2 W'),
    ('joystick', 'joystick_cap'), ('tub', 'DS3231 clock'), ('tub', 'TP4056 charger'), ('tub', 'ADS1115'),
    ('tub', 'MT3608 boost'), ('tub', 'USB-C breakout'), ('Pi Zero 2 W', 'heatsinks'), ('Pi Zero 2 W', 'Pi connectors'),
    ('heatsinks', 'Pi connectors'), ('joystick board', 'joystick'), ('screen', 'screen picture')]}


def verify(objs):
    trees = {k: _bvh(ob) for k, ob in objs.items()}
    names = list(objs)
    problems = []
    control = len(trees['joystick'].overlap(trees['joystick_cap']))   # the model's round stick is wider than the cap's slot
    print('VERIFY control (should be > 0):', control)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            pair = frozenset((a, b))
            if pair in EXPECTED:
                continue
            if any(n.startswith('carrier_') for n in pair) and ('top_plate' in pair or 'buttons' in pair):
                continue                                  # screwed to the plate; the switches sit in it
            if any(n.startswith('cap_') for n in pair) and ('top_plate' in pair or 'buttons' in pair):
                continue
            hits = trees[a].overlap(trees[b])
            if hits:
                problems.append(f'INTERSECT {a} x {b}: {len(hits)} triangle pairs')
    with open(os.path.join(OUT, 'tools', 'fit_report.txt'), 'w') as fh:
        fh.write(f'{LAY.title} fit report (generated by enclosure/tools/build_slab.py)\n')
        fh.write(f'size {W:.1f} x {D:.1f} x {HB:.1f} mm\n')
        fh.write(f'box check (layout.py): {LAY.check(quiet=True)} collisions, {LAY.check(0.25, quiet=True)} spots under 0.5 mm\n')
        fh.write('\n'.join(problems) + ('\n' if problems else 'real-mesh check: no parts cut into each other\n'))
    print('VERIFY', len(problems), 'problems')
    for p_ in problems:
        print('  ', p_)
    return problems


# ---------------------------------------------------------------------------------------------
# exports
# ---------------------------------------------------------------------------------------------

def loose_parts(ob):
    """One object per connected piece of ob's mesh."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.faces.ensure_lookup_table()
    seen, pieces = set(), []
    for f in bm.faces:
        if f.index in seen:
            continue
        comp, stack = [], [f]
        seen.add(f.index)
        while stack:
            g = stack.pop()
            comp.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen:
                        seen.add(h.index)
                        stack.append(h)
        nb, vmap = bmesh.new(), {}
        for g in comp:
            for v in g.verts:
                if v.index not in vmap:
                    vmap[v.index] = nb.verts.new(v.co)
            nb.faces.new([vmap[v.index] for v in g.verts])
        pieces.append(_obj(ob.name + ' piece', nb))
    bm.free()
    return pieces


def export_assembled(objs, files):
    """One STL per part in its finished place. All carry the same two 0.4 mm marker cubes, so they
    share one bounding box and Tinkercad (which places imports by their bounding box) lines them up."""
    d = os.path.join(OUT, 'stl', 'assembled')
    os.makedirs(d, exist_ok=True)
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for ob in objs.values():
        for v in ob.data.vertices:
            w = ob.matrix_world @ v.co
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    lo -= Vector((1, 1, 0))
    hi += Vector((1, 1, 1))
    for fname, keys in files:
        pieces = []
        for k in keys:
            c = copy_obj(objs[k], k, objs[k].matrix_world)
            pieces += loose_parts(c)
            bpy.data.objects.remove(c)
        ob = boolean(pieces[0], pieces[1:], 'UNION', 'EXACT')
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bpy.data.objects.remove(ob)
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4)
        bmesh.ops.dissolve_degenerate(bm, dist=1e-4, edges=bm.edges[:])
        for c in (lo, hi - Vector((0.4, 0.4, 0.4))):
            bmesh.ops.create_cube(bm, size=0.4, matrix=Matrix.Translation(c + Vector((0.2, 0.2, 0.2))))
        ob = _obj(fname, bm)
        export_stl([ob], os.path.join(d, fname + '.stl'))
        bpy.data.objects.remove(ob)
    print('ASSEMBLED', len(files), 'files')


def export_glb(objs, path):
    root = bpy.data.objects.new(f'{LAY.title} (metres)', None)
    WORK.objects.link(root)
    root.scale = (0.001, 0.001, 0.001)
    for ob in objs.values():
        mw = ob.matrix_world.copy()
        ob.parent = root
        ob.matrix_parent_inverse = Matrix.Identity(4)
        ob.matrix_basis = mw
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=False, export_apply=True)
    for ob in objs.values():
        mw = ob.matrix_world.copy()
        ob.parent = None
        ob.matrix_world = Matrix.Scale(1000, 4) @ mw
    bpy.data.objects.remove(root)


def render_views(objs):
    rdir = os.path.join(OUT, 'renders')
    os.makedirs(rdir, exist_ok=True)
    sc = SCENE
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'STUDIO'
    sc.display.shading.color_type = 'MATERIAL'
    sc.display.shading.show_shadows = True
    sc.display.shading.show_cavity = True
    sc.render.resolution_x, sc.render.resolution_y = 1120, 800
    sc.render.image_settings.compression = 100
    for k in ('use_stamp_date', 'use_stamp_time', 'use_stamp_render_time', 'use_stamp_frame', 'use_stamp_frame_range',
              'use_stamp_memory', 'use_stamp_hostname', 'use_stamp_camera', 'use_stamp_lens', 'use_stamp_scene',
              'use_stamp_marker', 'use_stamp_filename', 'use_stamp_sequencer_strip', 'use_stamp_note'):
        if hasattr(sc.render, k):
            setattr(sc.render, k, False)          # no render metadata (date, host name, file path) in the PNGs
    sc.render.film_transparent = False
    sc.world = bpy.data.worlds.new('bg')
    sc.world.color = (0.93, 0.92, 0.90)
    sc.render.image_settings.file_format = 'PNG'
    cam_data = bpy.data.cameras.new('cam')
    cam_data.clip_start, cam_data.clip_end = 5.0, 2000.0     # tight depth range: the screen picture sits just above the glass
    cam = bpy.data.objects.new('cam', cam_data)
    WORK.objects.link(cam)
    sc.camera = cam
    centre = Vector((W / 2, D / 2, HB / 2))
    size = max(W, D)

    def shoot(name, direction, dist, look=centre, lens=50, hide=(), roll_up=(0, 0, 1)):
        for k, ob in objs.items():
            ob.hide_render = k in hide
        d = Vector(direction).normalized()
        cam.location = look + d * dist
        fwd = -d
        up = Vector(roll_up)
        right = fwd.cross(up).normalized()
        up = right.cross(fwd).normalized()
        cam.matrix_world = Matrix((
            (right.x, up.x, -fwd.x, cam.location.x),
            (right.y, up.y, -fwd.y, cam.location.y),
            (right.z, up.z, -fwd.z, cam.location.z),
            (0, 0, 0, 1)))
        cam_data.lens = lens
        sc.render.filepath = os.path.join(rdir, name + '.png')
        bpy.ops.render.render(write_still=True)

    tall = D > W
    lid = {'top_plate', 'lens', 'joystick_cap', 'screen', 'screen picture'} | {k for k in objs if k.startswith(('cap_', 'carrier_'))}
    saved = {k: ob.matrix_world.copy() for k, ob in objs.items()}
    turn = Matrix.Translation(centre) @ Matrix.Rotation(math.pi, 4, 'X') @ Matrix.Translation(-centre)
    if tall:
        shoot('front', (-0.42, -0.62, 0.86), size * 2.25, centre + Vector((0, 4, 4)), 45)
        shoot('inside', (-0.10, -0.42, 1.0), size * 2.05, Vector((W / 2, D / 2, 4)), 45, hide=lid, roll_up=(0, 1, 0))
    else:
        shoot('front', (-0.30, -0.80, 0.80), size * 1.70, centre + Vector((0, 2, 4)), 45)
        shoot('inside', (-0.05, -0.55, 1.0), size * 1.55, Vector((W / 2, D / 2, 4)), 45, hide=lid, roll_up=(0, 1, 0))
    for k, ob in objs.items():
        ob.matrix_world = turn @ saved[k]
    shoot('back', (0.42, -0.62, 0.86) if tall else (0.30, -0.80, 0.80), size * (2.25 if tall else 1.70), centre, 45)
    for k, ob in objs.items():
        ob.matrix_world = saved[k]
    # exploded: lift each layer
    lift = {'Pi Zero 2 W': 22, 'heatsinks': 22, 'Pi connectors': 22, 'buttons': 52, 'joystick_cap': 92,
            'screen': 62, 'screen picture': 62, 'top_plate': 78, 'lens': 92}
    saved = {k: ob.matrix_world.copy() for k, ob in objs.items()}
    for k, ob in objs.items():
        z = lift.get(k, 0)
        if k.startswith('carrier_'):
            z = 52
        elif k.startswith('cap_'):
            z = 92
        ob.matrix_world = Matrix.Translation((0, 0, z)) @ saved[k]
    if tall:
        shoot('exploded', (0.55, -0.80, 0.62), size * 2.35, Vector((W / 2, D / 2, 48)), 45)
    else:
        shoot('exploded', (0.45, -0.85, 0.72), size * 1.95, Vector((W / 2, D / 2, 46)), 45)
    for k, ob in objs.items():
        ob.matrix_world = saved[k]


# ---------------------------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------------------------

def main():
    parts = {}
    for ob in [make_tub(), make_top_plate(), make_joy_cap()] + [make_carrier(c) for c in LAY.carriers]:
        parts[ob.name] = ob
        print('built', ob.name, len(ob.data.polygons), 'faces')
    if LAY.lens:
        parts['lens'] = make_lens()
    caps = make_button_caps()
    for c in caps:
        parts[c.name] = c
    comps = {k: joined(k, v) for k, v in comp_models().items()}

    os.makedirs(os.path.join(OUT, 'stl', 'components'), exist_ok=True)
    flip_x = lambda h: Matrix.Translation((0, 0, h)) @ Matrix.Rotation(math.pi, 4, 'X')     # upside down, about X
    PRINT = {
        'tub': (parts['tub'], Matrix.Identity(4)),
        'top_plate': (parts['top_plate'], Matrix.Translation((0, D, 0)) @ flip_x(HB)),
        'joystick_cap': (parts['joystick_cap'], Matrix.Translation((0, D, 0)) @ flip_x(HB)),
    }
    for c in LAY.carriers:
        PRINT['button_carrier_' + c['name']] = (parts['carrier_' + c['name']], Matrix.Translation((0, D, 0)) @ flip_x(S.BTN_BED_Z + S.BTN_BED_T))
    if LAY.lens:
        PRINT['screen_surround'] = (parts['lens'], Matrix.Translation((0, D, 0)) @ flip_x(HB))
    for fname, (ob, m) in PRINT.items():
        c = copy_obj(ob, fname, m)
        bb = [Vector(v) for v in c.bound_box]
        c.data.transform(Matrix.Translation((-min(v.x for v in bb), -min(v.y for v in bb), -min(v.z for v in bb))))
        export_stl([c], os.path.join(OUT, 'stl', fname + '.stl'))
        bpy.data.objects.remove(c)
    capset = [copy_obj(cap, cap.name, Matrix.Translation((0, 0, -S.BTN_TOP))) for cap in caps]
    export_stl(capset, os.path.join(OUT, 'stl', 'button_caps.stl'))
    for c in capset:
        bpy.data.objects.remove(c)

    asm = [copy_obj(ob, 'asm_' + k) for k, ob in list(parts.items()) + list(comps.items())]
    export_stl(asm, os.path.join(OUT, 'stl', 'assembly.stl'))
    for o in asm:
        bpy.data.objects.remove(o)
    for k, ob in comps.items():
        c = copy_obj(ob, k)
        export_stl([c], os.path.join(OUT, 'stl', 'components', k.replace(' ', '_') + '.stl'))
        bpy.data.objects.remove(c)

    objs = {}
    for k, ob in list(parts.items()) + list(comps.items()):
        colour(ob, colour_for(k))
        objs[k] = ob
    verify(objs)
    files = [('01 tub', ['tub']), ('02 top plate', ['top_plate'])]
    if LAY.lens:
        files.append(('03 screen surround', ['lens']))
    files += [(f'04 button carrier {c["name"].replace("_", " ")}', ['carrier_' + c['name']]) for c in LAY.carriers]
    files += [('05 button caps', [f'cap_{n}' for n in BTN]), ('06 joystick cap', ['joystick_cap']),
              ('20 screen', ['screen']), ('21 Pi Zero 2 W', ['Pi Zero 2 W', 'heatsinks', 'Pi connectors']),
              ('22 battery', ['battery']), ('23 joystick', ['joystick board', 'joystick']),
              ('24 DS3231 clock', ['DS3231 clock']), ('25 MT3608 boost', ['MT3608 boost']),
              ('26 TP4056 charger', ['TP4056 charger']), ('27 ADS1115', ['ADS1115']),
              ('28 USB-C breakout', ['USB-C breakout']), ('29 buttons', ['buttons'])]
    export_assembled(objs, files)
    export_glb(objs, os.path.join(OUT, f'chaipi-{LAY.name}.glb'))
    render_views(objs)
    print('BUILD OK')


main()
