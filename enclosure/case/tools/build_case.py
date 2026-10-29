# Builds the ChAIpi case in Blender from layout.py: printable parts (STL), rough models of the
# components, a coloured assembly (GLB) and preview renders.
#
#   Blender --background --factory-startup --python enclosure/case/tools/build_case.py -- enclosure/case
#
# Units are millimetres (1 Blender unit = 1 mm). STL files are written in print orientation.
import bpy, bmesh, math, os, sys
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as L  # noqa: E402

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = os.path.abspath(ARGS[0] if ARGS else os.path.join(HERE, '..'))
FONT = os.path.join(HERE, '..', '..', '..', 'device', 'fonts', 'Unbounded-SemiBold.ttf')

bpy.ops.wm.read_factory_settings(use_empty=True)
SCENE = bpy.context.scene
WORK = SCENE.collection

W, D, HB, FZ = L.W, L.D, L.HB, L.FACE_Z
IN = L.IN
LT = L.LID_T
AX_Y, AX_Z = L.HINGE_AXIS_Y, L.HINGE_AXIS_Z      # hinge axis (lid frame z)
R = L.BARREL_R
COLLAR = 2.0          # thickening under the top-plate screw heads
SEG = 48

# ---------------------------------------------------------------------------------------------
# geometry helpers
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


def circle(cx, cy, r, seg=SEG):
    return [(cx + r * math.cos(2 * math.pi * i / seg), cy + r * math.sin(2 * math.pi * i / seg)) for i in range(seg)]


def box(x0, y0, z0, x1, y1, z1, name='box'):
    return prism([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1, 'z', name)


def rbox(x0, y0, z0, x1, y1, z1, r, name='rbox'):
    return prism(rrect(x0, y0, x1, y1, r), z0, z1, 'z', name)


def cyl(cx, cy, z0, z1, r, seg=SEG, name='cyl'):
    return prism(circle(cx, cy, r, seg), z0, z1, 'z', name)


def cyl_x(x0, x1, cy, cz, r, seg=SEG, name='cylx'):
    return prism(circle(cy, cz, r, seg), x0, x1, 'x', name)


def slot(x0, y0, x1, y1, z0, z1, name='slot'):
    """Rounded slot (stadium) between two centres, width = y1 - y0 if horizontal."""
    w = min(x1 - x0, y1 - y0)
    return rbox(x0, y0, z0, x1, y1, z1, w / 2 - 1e-3, name)


def corner_wedge(xc, yc, sx, sy, z_top, depth, name='wedge'):
    """Pyramid under a corner boss: point at the wall corner, square (sx, sy) at z_top (45 degrees)."""
    bm = bmesh.new()
    pts = [(xc, yc, z_top - depth), (xc + sx, yc, z_top), (xc, yc + sy, z_top), (xc + sx, yc + sy, z_top), (xc, yc, z_top)]
    for p in pts:
        bm.verts.new(p)
    bmesh.ops.convex_hull(bm, input=bm.verts[:])
    return _obj(name, bm)


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


def text_solid(s, size, cx, cy, z0, z1, name='text'):
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
    mob = bpy.data.objects.new(name, me)
    mob.matrix_world = ob.matrix_world.copy()
    WORK.objects.link(mob)
    bpy.data.objects.remove(ob)
    bm = bmesh.new()
    bm.from_mesh(mob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bm.to_mesh(mob.data)
    bm.free()
    return mob


def transform(ob, m):
    ob.data.transform(m)
    ob.data.update()


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
J = L.J
JX, JY = L.JOY_ORG
JC = L.JOY_C
JOY_HOLES = [(JX + J['holes_in'], JY + J['holes_in']), (JX + J['w'] - J['holes_in'], JY + J['holes_in']),
             (JX + J['holes_in'], JY + J['d'] - J['holes_in']), (JX + J['w'] - J['holes_in'], JY + J['d'] - J['holes_in'])]
PX, PY = L.PI_ORG
PI_HOLES = [(PX + 3.5, PY + 3.5), (PX + 61.5, PY + 3.5), (PX + 3.5, PY + 26.5), (PX + 61.5, PY + 26.5)]
SHEET_POSTS = [(33.0, 31.0), (33.0, 55.0), (12.0, 52.0)]
CORNER_SCREWS = [((b[0] + b[2]) / 2, (b[1] + b[3]) / 2) for b in L.CORNER_BOSSES]
BTN = L.BUTTONS
CARRIER_SCREWS = [(34.2, 4.2), (L.FREE_SLOTS[1][0], L.FREE_SLOTS[1][1])]
# hinge segments along x: base posts and lid knuckles
SEGS = dict(B_L=(0.0, 5.6), L_main=(5.9, 53.7), B_W=(54.0, 70.3), L_R=(70.6, 83.3), B_R=(83.6, W))
WIRE_CH = (58.0, 61.8)            # x range of the wire channel down through B_W and the top plate
WIRE_SLOT = (71.5, 78.0)          # x range where the screen wires leave the lid into L_R
TFT_POSTS = [(L.TFT_ORG[0] + hx, L.TFT_ORG[1] + hy) for hx, hy in L.T['holes']]
CPU = (PX + 27.3, PY + L.P['d'] - 16.05)
WIFI = (PX + 44.15, PY + L.P['d'] - 16.4)


# ---------------------------------------------------------------------------------------------
# printable parts (built in place, base frame; lid parts in the lid frame)
# ---------------------------------------------------------------------------------------------

def make_tub():
    t = rbox(0, 0, 0, W, D, FZ, L.R_OUT, 'tub')
    t = diff(t, [rbox(IN['x0'], IN['y0'], L.FLOOR, IN['x1'], IN['y1'], FZ + 1, 1.6)])
    add = []
    for i, (x0, y0, x1, y1, zl) in enumerate(L.CORNER_BOSSES):
        top = FZ - COLLAR
        add.append(box(x0 - 0.5 if x0 <= IN['x0'] else x0, y0 - 0.5 if y0 <= IN['y0'] else y0, zl,
                       x1 + 0.5 if x1 >= IN['x1'] else x1, y1 + 0.5 if y1 >= IN['y1'] else y1, top))   # hangs from the walls
    for k, (hx, hy) in enumerate(JOY_HOLES):                        # joystick pads
        add.append(cyl(hx, hy, L.FLOOR - 0.1, L.JOY_PCB_Z, 3.0))
        if k == 0:
            add.append(cyl(hx, hy, L.JOY_PCB_Z - 0.1, L.JOY_PCB_Z + 1.3, 1.4, 24))   # locating pin (no screw room)
    for x, y in SHEET_POSTS:                                         # middle-sheet posts
        add.append(cyl(x, y, L.FLOOR - 0.1, L.SHEET_Z, 2.75))
    ub = L.USBC_BOX                                                  # backstop behind the USB-C board
    add.append(box(ub[0] + 0.5, ub[4] + 0.4, L.FLOOR - 0.1, ub[3], ub[4] + 1.5, L.FLOOR + 3.0))
    t = union(t, add)
    cut = []
    for x, y in CORNER_SCREWS:
        cut.append(cyl(x, y, FZ - COLLAR - 6.0, FZ + 1, 1.05, 24))
    for k, (hx, hy) in enumerate(JOY_HOLES):
        if k:
            cut.append(cyl(hx, hy, L.FLOOR - 1.4 + 0.2, L.JOY_PCB_Z + 0.1, 1.05, 24))
    for x, y in SHEET_POSTS:
        cut.append(cyl(x, y, L.SHEET_Z - 4.6, L.SHEET_Z + 0.1, 1.05, 24))
    ucx = (ub[0] + ub[3]) / 2                                       # USB-C opening in the front wall
    uz = L.FLOOR + 1.6 + L.PART['usbc']['port_h'] / 2
    cut.append(prism(rrect(ucx - 4.9, uz - 2.0, ucx + 4.9, uz + 2.0, 1.95), -1, IN['y0'] + 0.6, 'y'))
    return diff(t, cut)


def make_top_plate():
    p = rbox(0, 0, FZ, W, D, HB, L.R_OUT, 'top_plate')
    add = []
    for x, y in CORNER_SCREWS:
        add.append(cyl(x, y, FZ - COLLAR, FZ + 0.1, 3.2))
    for x, y in CARRIER_SCREWS:
        add.append(cyl(x, y, L.BTN_BED_Z + L.BTN_BED_T, FZ + 0.1, 2.6))
    p = union(p, add)
    cut = [cyl(JC[0], JC[1], FZ - 1, HB + 1, L.joy_hole_r(), 64)]
    for name, ((x, y), dcap) in BTN.items():
        cut.append(cyl(x, y, FZ - 1, HB + 1, dcap / 2 + 0.2, 40))
    for x, y in CORNER_SCREWS:
        cut.append(cyl(x, y, FZ - COLLAR - 1, HB + 1, 1.4, 24))
        cut.append(cyl(x, y, HB - 1.0, HB + 1, 2.7, 32))
    for x, y in CARRIER_SCREWS:
        cut.append(cyl(x, y, L.BTN_BED_Z, FZ - 0.6, 0.8, 20))
    # vent slots over the two heatsinks (the lid covers them when closed)
    vx0, vx1 = CPU[0] - 9.0, WIFI[0] + 7.5
    n = int((vx1 - vx0) // 3.0)
    for i in range(n):
        x = vx0 + 1.5 + i * 3.0
        cut.append(slot(x - 0.75, CPU[1] - 6.0, x + 0.75, CPU[1] + 6.0, FZ - 1, HB + 1))
    # screw holes for the hinge block (from below) and the screen-wire passage
    for x in HINGE_SCREWS_X:
        cut.append(cyl(x, AX_Y, FZ - 1, HB + 1, 1.4, 24))
    cut.append(box(WIRE_CH[0], AX_Y - 1.9, FZ - 1, WIRE_CH[1], AX_Y + 1.9, HB + 1))
    return diff(p, cut)


HINGE_SCREWS_X = (3.8, 56.0, 67.6, W - 3.8)


def post_profile(x0, x1, z_base):
    """A hinge post: block from the shelf up to the axis, plus the barrel."""
    a = box(x0, L.LID_D + L.HINGE_GAP, z_base, x1, D, HB + AX_Z)
    return union(a, [cyl_x(x0, x1, AX_Y, HB + AX_Z, R)])


def make_hinge_block():
    shelf_top = HB + 3.0
    y0 = L.LID_D + L.HINGE_GAP
    h = box(0, y0, HB, W, D, shelf_top, 'hinge_block')
    h = union(h, [post_profile(*SEGS['B_L'], HB), post_profile(*SEGS['B_W'], HB), post_profile(*SEGS['B_R'], HB)])
    outline = prism(rrect(0, 0, W, D, L.R_OUT), HB - 1, HB + LT + 1)           # follow the base's rounded back corners
    h = boolean(h, [outline], 'INTERSECT')
    cut = [
        cyl_x(-1, SEGS['B_L'][1] + 0.1, AX_Y, HB + AX_Z, 1.4, 24),                 # pivot screw clearance, left
        cyl_x(-1, 1.5, AX_Y, HB + AX_Z, 2.7, 32),                                  # head counterbore
        cyl_x(SEGS['B_R'][0] - 0.1, W + 1, AX_Y, HB + AX_Z, 1.4, 24),               # right
        cyl_x(W - 1.5, W + 1, AX_Y, HB + AX_Z, 2.7, 32),
        cyl_x(SEGS['B_W'][0] - 0.1, SEGS['B_W'][1] + 0.1, AX_Y, HB + AX_Z, 1.9, 32),   # wire bore
        box(WIRE_CH[0], AX_Y - 1.9, HB - 1, WIRE_CH[1], AX_Y + 1.9, HB + AX_Z),     # wire channel down
    ]
    for x in HINGE_SCREWS_X:
        depth = 4.0 if SEGS['B_W'][0] <= x <= SEGS['B_W'][1] else 5.0
        cut.append(cyl(x, AX_Y, HB - 1, HB + depth, 1.05, 24))
    return diff(h, cut)


def knuckle(x0, x1):
    a = box(x0, L.LID_D - 0.2, 3.4, x1, AX_Y, LT)
    return union(a, [cyl_x(x0, x1, AX_Y, AX_Z, R)])


def make_lid_frame():
    f = rbox(0, 0, 0, W, L.LID_D, LT - L.LID_BACK, L.R_OUT, 'lid_frame')
    f = union(f, [knuckle(*SEGS['L_main']), knuckle(*SEGS['L_R'])])
    ox, oy, _ = L.TFT_ORG
    aa = L.T['aa']
    wx0, wy0, wx1, wy1 = ox + aa[0] - 0.5, oy + aa[1] - 0.5, ox + aa[2] + 0.5, oy + aa[3] + 0.5
    cut = [rbox(L.WALL, L.WALL, L.BEZEL, W - L.WALL, L.LID_D - L.WALL, LT, 1.0),
           loft(rrect(wx0 - 0.7, wy0 - 0.7, wx1 + 0.7, wy1 + 0.7, 1.5), rrect(wx0, wy0, wx1, wy1, 0.8), -0.01, 0.7),
           rbox(wx0, wy0, 0.5, wx1, wy1, L.BEZEL + 0.1, 0.8)]
    f = diff(f, cut)
    posts = [cyl(x, y, L.BEZEL - 0.1, L.BEZEL + L.T['total'] - L.T['pcb'], 2.3) for x, y in TFT_POSTS]
    f = union(f, posts)
    cut = [cyl(x, y, L.BEZEL + 0.2, L.BEZEL + 4.2, 1.05, 24) for x, y in TFT_POSTS]
    zb = L.BEZEL + L.T['total']
    cut += [box(WIRE_SLOT[0], L.LID_D - L.WALL - 0.6, zb + 0.1, WIRE_SLOT[1], AX_Y, LT - L.LID_BACK + 0.01),
            cyl_x(SEGS['L_R'][0] - 0.1, WIRE_SLOT[1] + 0.4, AX_Y, AX_Z, 1.9, 32),
            cyl_x(SEGS['L_main'][0] - 0.1, SEGS['L_main'][0] + 4.2, AX_Y, AX_Z, 1.05, 24),
            cyl_x(SEGS['L_R'][1] - 4.2, SEGS['L_R'][1] + 0.1, AX_Y, AX_Z, 1.05, 24)]
    return diff(f, cut)


def make_lid_back():
    z0 = LT - L.LID_BACK
    c = rbox(0, 0, z0, W, L.LID_D, LT, L.R_OUT, 'lid_back')
    zb = L.BEZEL + L.T['total']
    c = union(c, [cyl(x, y, zb, z0 + 0.1, 3.0) for x, y in TFT_POSTS])
    cut = []
    for x, y in TFT_POSTS:
        cut.append(cyl(x, y, zb - 0.1, LT + 1, 1.4, 24))
        cut.append(cyl(x, y, LT - 1.0, LT + 1, 2.7, 32))
    c = diff(c, cut)
    try:
        word = text_solid('ChAIpi', 9.0, W / 2, L.LID_D / 2, LT - 0.45, LT + 1.0, 'word')
        c = diff(c, [word], 'EXACT')
    except Exception as e:                               # the wordmark is decoration only
        print('wordmark skipped:', e)
    return c


def make_sheet():
    y0 = JY + J['d'] + 0.4
    s = prism(rrect(IN['x0'] + 0.3, y0, IN['x1'] - 0.3, IN['y1'] - 0.3, 1.8), L.SHEET_Z, L.SHEET_Z + L.SHEET_T, 'z', 'mid_sheet')
    top = L.SHEET_Z + L.SHEET_T
    # flat underneath so it prints flat; a strip of foam tape on the battery supports its right half
    s = union(s, [cyl(x, y, top - 0.1, L.PI_Z, 3.0) for x, y in PI_HOLES])
    cut = [cyl(x, y, L.PI_Z - 2.6, L.PI_Z + 0.1, 1.05, 24) for x, y in PI_HOLES]       # blind: stops 0.2 above the battery side
    cut += [cyl(x, y, L.SHEET_Z - 1, top + 1, 1.4, 24) for x, y in SHEET_POSTS]
    cut.append(slot(30.4, 38.0, 35.6, 50.0, L.SHEET_Z - 1, top + 1))                   # wire pass beside the battery
    cut.append(slot(IN['x0'] + 1.2, y0 - 1, IN['x0'] + 9.0, y0 + 3.2, L.SHEET_Z - 1, top + 1))   # joystick + SW wires
    cut.append(slot(15.0, 46.8, 26.0, 50.2, L.SHEET_Z - 1, top + 1))                   # ADC + I2C wires up to the GPIO
    return diff(s, cut)


def make_carrier():
    z0, z1 = L.BTN_BED_Z, L.BTN_BED_Z + L.BTN_BED_T
    xs = [x for (x, y), d in BTN.values()]
    ys = [y for (x, y), d in BTN.values()]
    lx = L.B['legs'][0] / 2 + 0.5
    c = prism(rrect(min(xs) - lx, min(L.GY) - 6.3, max(xs) + lx, max(L.GY) + 6.0, 1.5), z0, z1, 'z', 'button_carrier')
    add = []                                                                             # the switch legs locate each switch
    bo = L.BOOST_BOX                                                                     # pads holding the boost board down
    for x0 in (bo[0] + 10.5, bo[3] - 9.0):
        for y0, y1 in ((bo[1] + 0.2, bo[1] + 1.4), (bo[4] - 1.7, bo[4] - 0.5)):
            add.append(box(x0, y0, bo[5] + 0.3, x0 + 3.0, y1, z0 + 0.1))
    c = union(c, add)
    cut = []
    for (x, y), dcap in BTN.values():
        for sx in (-1, 1):
            for sy in (-1, 1):
                cut.append(cyl(x + sx * L.B['legs'][0] / 2, y + sy * L.B['legs'][1] / 2, z0 - 1, z1 + 1, 0.7, 16))
    fx, fy = L.FREE_SLOTS[0]                                                             # window for the boost trimmer
    pot = L.BOOST_POT
    cut.append(rbox(pot[0] - 1.0, pot[1] - 1.5, z0 - 1, pot[3] + 1.0, pot[4] + 1.5, z1 + 2, 1.0))
    b = L.CORNER_BOSSES[1]                                                                # notch for the front-right corner screw
    cut.append(box(b[0] - 0.6, b[1] - 1, z0 - 1, b[2] + 1, b[3] + 0.6, z1 + 2))
    for x, y in CARRIER_SCREWS:
        cut.append(cyl(x, y, z0 - 1, z1 + 1, 1.1, 20))
    return diff(c, cut)


def make_button_caps():
    out = []
    for name, ((x, y), dcap) in BTN.items():
        flange = cyl(x, y, L.BTN_TOP, L.BTN_TOP + L.BTN_CAP_FLANGE, dcap / 2 + 1.2, 40)
        body = cyl(x, y, L.BTN_TOP + L.BTN_CAP_FLANGE - 0.01, HB - 0.05, dcap / 2, 40)
        cap = union(flange, [body])
        cap.name = 'cap_' + name
        out.append(cap)
    return out


def make_fit_test():
    """30 x 22 x 4 coupon: M2.5 and M2 pilot holes in three sizes, clearance holes with counterbores,
    and a cap hole, so screw grip and fits can be checked on your printer before the big parts."""
    c = rbox(0, 0, 0, 34, 22, 4.0, 2.0, 'fit_test')
    cut = []
    for i, r in enumerate((1.00, 1.05, 1.10)):                     # M2.5 pilots 2.0 / 2.1 / 2.2
        cut.append(cyl(5 + i * 6, 6, 0.4, 5, r, 24))
    for i, r in enumerate((0.75, 0.80, 0.85)):                     # M2 pilots 1.5 / 1.6 / 1.7
        cut.append(cyl(5 + i * 6, 16, 0.4, 5, r, 24))
    cut.append(cyl(24, 6, -1, 5, 1.4, 24)); cut.append(cyl(24, 6, 3.0, 5, 2.7, 32))   # M2.5 clearance + counterbore
    cut.append(cyl(24, 16, -1, 5, 1.1, 24))                        # M2 clearance
    cut.append(cyl(30.0, 11, -1, 5, 8.5 / 2 + 0.2, 40))             # small cap hole (the 8.5 mm cap should drop in)
    return diff(c, cut)


def make_joy_cap():
    import math as m
    cx, cy = JC
    tip = L.JOY_PCB_Z + J['t'] + J['tip']
    disc = cyl(cx, cy, HB - L.JOY_CAP_DISC, HB - 0.05, L.JOY_CAP_R, 64, 'joystick_cap')
    boss = cyl(cx, cy, tip - 4.0, HB - L.JOY_CAP_DISC + 0.1, 2.6, 32)
    c = union(disc, [boss])
    cut = [box(cx - 1.05, cy - 2.3, tip - 4.1, cx + 1.05, cy + 2.3, tip + 0.01)]          # slot for the stick's flat tip
    for rr in (2.5, 4.5, 6.5):                                                          # grip grooves
        ring = diff(cyl(cx, cy, HB - 0.25, HB + 1, rr + 0.35, 64), [cyl(cx, cy, HB - 1, HB + 2, rr - 0.35, 64)])
        cut.append(ring)
    return diff(c, cut)


# ---------------------------------------------------------------------------------------------
# rough models of the bought parts (assembled position)
# ---------------------------------------------------------------------------------------------

def comp_models():
    out = {}
    b = L.boxes()
    # Pi: board, microSD card, heatsinks, connectors
    pz = L.PI_Z
    pi = [box(PX, PY, pz, PX + 65, PY + 30, pz + 1.4)]
    pi = [diff(pi[0], [cyl(x, y, pz - 1, pz + 3, 1.375, 20) for x, y in PI_HOLES])]
    out['Pi Zero 2 W'] = pi
    hs = []
    for (cx, cy), part in ((CPU, L.PART['hs_cpu']), (WIFI, L.PART['hs_wifi'])):
        w = part['w'] / 2
        hs.append(box(cx - w, cy - w, pz + 1.4, cx + w, cy + w, pz + 1.4 + part['chip'] + 1.0))
        for i in range(5):
            fx = cx - w + 0.6 + i * (2 * w - 1.2) / 4
            hs.append(box(fx - 0.5, cy - w, pz + 1.4 + part['chip'] + 0.9, fx + 0.5, cy + w, pz + 1.4 + part['chip'] + part['h']))
    out['heatsinks'] = hs
    con = []
    for xc, wc, hc in ((12.4, 11.2, 3.3), (41.4, 8.0, 2.6), (54.0, 8.0, 2.6)):
        con.append(box(PX + xc - wc / 2, PY - 0.5, pz + 1.4, PX + xc + wc / 2, PY + 5.5, pz + 1.4 + hc))
    con.append(box(PX + 1.5, PY + 10.8, pz + 1.4, PX + 13.0, PY + 22.9, pz + 2.8))
    con.append(box(PX - 2.5, PY + 11.5, pz + 1.6, PX + 2.0, PY + 22.5, pz + 2.4))
    out['Pi connectors'] = con
    # battery: two cells
    bx, by = L.BATT_ORG
    c = L.C
    out['battery'] = [rbox(bx, by, L.FLOOR, bx + c['w'], by + c['d'], L.FLOOR + c['t'], 1.0),
                      rbox(bx, by, L.FLOOR + c['t'] + c['tape'], bx + c['w'], by + c['d'], L.FLOOR + 2 * c['t'] + c['tape'], 1.0)]
    # joystick
    jz = L.JOY_PCB_Z
    jt = jz + J['t']
    jb = box(JX, JY, jz, JX + J['w'], JY + J['d'], jt)
    jb = diff(jb, [cyl(x, y, jz - 1, jt + 1, J['hole_d'] / 2, 24) for x, y in JOY_HOLES])
    out['joystick board'] = [jb]
    cx, cy = JC
    f = J['frame'] / 2
    out['joystick'] = [box(cx - f, cy - f, jt, cx + f, cy + f, jt + J['frame_h']),
                       box(cx + f, cy - 4.75, jt, cx + 12.8, cy + 4.75, jt + 11.0),
                       box(cx - 4.75, cy + f, jt, cx + 4.75, cy + 8.6, jt + 11.0),
                       box(cx - 3.5, cy - 15.0, jt, cx + 3.5, cy - f, jt + 5.0),
                       cyl(cx, cy, jt + J['frame_h'], jt + J['tip'], 1.6, 20)]
    # other boards
    r = L.RTC_BOX
    out['DS3231 clock'] = [box(r[0], r[1], r[2] + 4.3, r[3], r[4], r[2] + 5.9), cyl(r[0] + 14, (r[1] + r[4]) / 2, r[2], r[2] + 4.3, 10.5),
                           box(r[0] + 22, r[1] + 5, r[2] + 5.9, r[0] + 32, r[1] + 15, r[5])]
    bo, pot = L.BOOST_BOX, L.BOOST_POT
    out['MT3608 boost'] = [box(bo[0], bo[1], bo[2], bo[3], bo[4], bo[2] + 1.2), box(bo[0] + 16, bo[1] + 3, bo[2] + 1.2, bo[0] + 23, bo[1] + 10, bo[5]),
                           box(*pot)]
    ch = L.CHG_BOX
    out['TP4056 charger'] = [box(ch[0], ch[1], ch[2], ch[3], ch[4], ch[2] + 1.0), box(ch[0], ch[1] + 4, ch[2] + 1.0, ch[0] + 7.4, ch[1] + 13, ch[5])]
    a = L.ADC_BOX
    out['ADS1115'] = [box(a[0], a[1], a[2], a[3], a[4], a[2] + 1.6), box(a[0] + 9, a[1] + 5, a[2] + 1.6, a[0] + 15, a[1] + 11, a[5])]
    u = L.USBC_BOX
    out['USB-C breakout'] = [box(u[0], u[1], u[2], u[3], u[4], u[2] + 1.6),
                             box((u[0] + u[3]) / 2 - 4.5, u[1] - 0.3, u[2] + 1.6, (u[0] + u[3]) / 2 + 4.5, u[1] + 7.3, u[2] + 1.6 + 3.3)]
    sw = []
    for (x, y), dcap in BTN.values():
        z0 = L.BTN_BED_Z + L.BTN_BED_T
        sw.append(box(x - 6, y - 6, z0, x + 6, y + 6, z0 + L.B['body']))
        sw.append(cyl(x, y, z0 + L.B['body'] - 0.01, L.BTN_TOP, L.B['act_d'] / 2 - 0.6, 32))
    out['buttons'] = sw
    # screen (lid frame)
    ox, oy, oz = L.TFT_ORG
    T = L.T
    out['screen'] = [box(ox, oy, oz + T['total'] - T['pcb'], ox + T['w'], oy + T['d'], oz + T['total']),
                     box(ox + T['lcd'][0], oy, oz, ox + T['lcd'][1], oy + T['d'], oz + T['total'] - T['pcb'])]
    out['screen picture'] = [box(ox + T['aa'][0], oy + T['aa'][1], oz - 0.05, ox + T['aa'][2], oy + T['aa'][3], oz + 0.05)]
    return out


COLOURS = {
    'tub': (0.40, 0.28, 0.22), 'top_plate': (0.45, 0.32, 0.25), 'hinge_block': (0.40, 0.28, 0.22),
    'lid_frame': (0.45, 0.32, 0.25), 'lid_back': (0.40, 0.28, 0.22), 'mid_sheet': (0.85, 0.78, 0.68),
    'button_carrier': (0.85, 0.78, 0.68), 'cap_Confirm': (0.82, 0.21, 0.40), 'joystick_cap': (0.12, 0.10, 0.10),
    'Pi Zero 2 W': (0.10, 0.45, 0.25), 'heatsinks': (0.65, 0.66, 0.70), 'Pi connectors': (0.75, 0.76, 0.78),
    'battery': (0.30, 0.45, 0.80), 'joystick board': (0.08, 0.08, 0.09), 'joystick': (0.55, 0.56, 0.58),
    'DS3231 clock': (0.10, 0.30, 0.65), 'MT3608 boost': (0.12, 0.35, 0.75), 'TP4056 charger': (0.15, 0.35, 0.70),
    'ADS1115': (0.45, 0.20, 0.55), 'USB-C breakout': (0.08, 0.08, 0.09), 'buttons': (0.10, 0.10, 0.11),
    'screen': (0.75, 0.15, 0.12), 'screen picture': (0.20, 0.45, 0.85),
}


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
# build
# ---------------------------------------------------------------------------------------------

def main():
    parts = {}
    for fn in (make_tub, make_top_plate, make_hinge_block, make_sheet, make_carrier, make_joy_cap, make_fit_test):
        ob = fn()
        parts[ob.name] = ob
        print('built', ob.name, len(ob.data.polygons), 'faces')
    caps = make_button_caps()
    for c in caps:
        parts[c.name] = c
    lid = {'lid_frame': make_lid_frame(), 'lid_back': make_lid_back()}
    print('built lid parts')
    comps = {k: joined(k, v) for k, v in comp_models().items()}
    lid_comps = {k: comps.pop(k) for k in ('screen', 'screen picture')}

    os.makedirs(os.path.join(OUT, 'stl'), exist_ok=True)
    os.makedirs(os.path.join(OUT, 'stl', 'components'), exist_ok=True)

    # --- print-orientation STLs ---
    flip_x = lambda h: Matrix.Translation((0, 0, h)) @ Matrix.Rotation(math.pi, 4, 'X')     # upside down, about X
    PRINT = {
        'base_tub': (parts['tub'], Matrix.Identity(4)),
        'base_top_plate': (parts['top_plate'], Matrix.Translation((0, D, 0)) @ flip_x(HB)),
        'hinge_block': (parts['hinge_block'], Matrix.Translation((0, 0, -HB))),
        'middle_sheet': (parts['mid_sheet'], Matrix.Translation((0, 0, -L.SHEET_Z))),
        'button_carrier': (parts['button_carrier'], Matrix.Translation((0, D, 0)) @ flip_x(L.BTN_BED_Z + L.BTN_BED_T)),
        'joystick_cap': (parts['joystick_cap'], Matrix.Translation((0, D, 0)) @ flip_x(HB)),
        'lid_frame': (lid['lid_frame'], Matrix.Identity(4)),
        'lid_back_cover': (lid['lid_back'], Matrix.Translation((0, L.LID_D, 0)) @ flip_x(LT)),
        'fit_test': (parts['fit_test'], Matrix.Identity(4)),
    }
    for fname, (ob, m) in PRINT.items():
        c = copy_obj(ob, fname, m)
        bb = [c.matrix_world @ Vector(v) for v in c.bound_box]
        dz = -min(v.z for v in bb)
        c.data.transform(Matrix.Translation((0, 0, dz)))
        export_stl([c], os.path.join(OUT, 'stl', fname + '.stl'))
        bpy.data.objects.remove(c)
    capset = []
    for i, cap in enumerate(caps):
        c = copy_obj(cap, cap.name, Matrix.Translation((0, 0, -L.BTN_TOP)))
        capset.append(c)
    export_stl(capset, os.path.join(OUT, 'stl', 'button_caps.stl'))
    for c in capset:
        bpy.data.objects.remove(c)

    # --- assembled models: printed parts + components, lid closed ---
    lid_closed = Matrix.Translation((0, 0, HB))
    asm = []
    for k, ob in parts.items():
        if k == 'fit_test':
            continue
        asm.append(copy_obj(ob, 'asm_' + k))
    for k, ob in lid.items():
        asm.append(copy_obj(ob, 'asm_' + k, lid_closed))
    for k, ob in comps.items():
        asm.append(copy_obj(ob, 'asm_' + k))
    for k, ob in lid_comps.items():
        asm.append(copy_obj(ob, 'asm_' + k, lid_closed))
    export_stl(asm, os.path.join(OUT, 'stl', 'assembly_closed.stl'))
    for o in asm:
        bpy.data.objects.remove(o)
    for k, ob in list(comps.items()) + list(lid_comps.items()):
        m = lid_closed if k in lid_comps else Matrix.Identity(4)
        c = copy_obj(ob, k, m)
        export_stl([c], os.path.join(OUT, 'stl', 'components', k.replace(' ', '_') + '.stl'))
        bpy.data.objects.remove(c)

    # --- scene for renders and the GLB: lid open at 115 degrees ---
    ang = math.radians(115)
    axis_pt = Vector((0, AX_Y, HB + AX_Z))
    lid_open = Matrix.Translation(axis_pt) @ Matrix.Rotation(-ang, 4, 'X') @ Matrix.Translation(-axis_pt) @ lid_closed
    scene_objs = {}
    for k, ob in parts.items():
        if k == 'fit_test':
            ob.hide_render = True
            continue
        colour(ob, COLOURS.get(k, (0.45, 0.32, 0.25) if not k.startswith('cap_') else (0.90, 0.85, 0.78)))
        scene_objs[k] = ob
    for k, ob in comps.items():
        colour(ob, COLOURS[k])
        scene_objs[k] = ob
    for k, ob in list(lid.items()) + list(lid_comps.items()):
        colour(ob, COLOURS[k])
        ob.matrix_world = lid_open
        scene_objs[k] = ob
    verify(parts, lid, comps, lid_comps, lid_closed)
    export_assembled(scene_objs)
    export_glb(scene_objs, os.path.join(OUT, 'chaipi-case.glb'))
    render_views(scene_objs, lid, lid_comps, lid_closed, lid_open)
    print('BUILD OK')


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


# pairs that are meant to touch or nest (screws, posts, pads), checked separately or by design
EXPECTED = {frozenset(p) for p in [
    ('tub', 'top_plate'), ('top_plate', 'hinge_block'), ('top_plate', 'button_carrier'), ('tub', 'mid_sheet'),
    ('lid_frame', 'lid_back'), ('tub', 'battery'), ('tub', 'joystick board'), ('mid_sheet', 'Pi Zero 2 W'),
    ('joystick', 'joystick_cap'), ('button_carrier', 'buttons'), ('tub', 'DS3231 clock'), ('tub', 'TP4056 charger'),
    ('tub', 'USB-C breakout'), ('lid_frame', 'screen'), ('lid_back', 'screen'), ('Pi Zero 2 W', 'heatsinks'),
    ('Pi Zero 2 W', 'Pi connectors'), ('heatsinks', 'Pi connectors'), ('joystick board', 'joystick'),
    ('screen', 'screen picture'), ('lid_frame', 'screen picture'), ('DS3231 clock', 'MT3608 boost'),
    ('TP4056 charger', 'ADS1115'), ('mid_sheet', 'ADS1115'), ('button_carrier', 'MT3608 boost'),
    ('mid_sheet', 'battery')]}


def verify(parts, lid, comps, lid_comps, lid_closed):
    """Real-mesh checks: parts that cut into each other when closed, and the lid's full swing."""
    objs = {}
    for k, ob in parts.items():
        if k != 'fit_test':
            objs[k] = (ob, None)
    for k, ob in comps.items():
        objs[k] = (ob, None)
    for k, ob in list(lid.items()) + list(lid_comps.items()):
        objs[k] = (ob, lid_closed)
    trees = {k: _bvh(ob, m) for k, (ob, m) in objs.items()}
    names = list(objs)
    problems = []
    # positive control: the model's round stick is wider than the cap's flat slot, so these must intersect
    control = len(trees['joystick'].overlap(trees['joystick_cap']))
    print('VERIFY control (should be > 0):', control)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if frozenset((a, b)) in EXPECTED:
                continue
            if a.startswith('cap_') and b in ('top_plate', 'buttons') or b.startswith('cap_') and a in ('top_plate', 'buttons'):
                continue
            hits = trees[a].overlap(trees[b])
            if hits:
                problems.append(f'INTERSECT {a} x {b}: {len(hits)} triangle pairs')
    # lid swing: 0..180 degrees about the hinge axis
    axis_pt = Vector((0, AX_Y, HB + AX_Z))
    moving = list(lid) + list(lid_comps)
    fixed = [k for k in ('tub', 'top_plate', 'hinge_block', 'joystick_cap') if k in objs] + [k for k in objs if k.startswith('cap_')]
    first = None
    for deg in range(2, 182, 2):
        rot = Matrix.Translation(axis_pt) @ Matrix.Rotation(-math.radians(deg), 4, 'X') @ Matrix.Translation(-axis_pt) @ lid_closed
        for k in moving:
            t = _bvh(objs[k][0], rot, 0.15)
            for f in fixed:
                if t.overlap(trees[f]):
                    first = first or (deg, k, f)
        if first:
            break
    with open(os.path.join(OUT, 'tools', 'fit_report.txt'), 'w') as fh:
        fh.write(f'ChAIpi case fit report (generated by build_case.py)\n')
        fh.write(f'closed thickness {L.CLOSED_T:.1f} mm; base {W:.1f} x {D:.1f} x {HB:.1f}; lid {L.LID_W:.1f} x {L.LID_D:.1f} x {LT:.1f}\n')
        fh.write('\n'.join(problems) + ('\n' if problems else 'no parts cut into each other when closed\n'))
        fh.write(f'lid swing: first contact at {first[0]} deg ({first[1]} x {first[2]})\n' if first else 'lid swing: free from 0 to 180 degrees\n')
    print('VERIFY', len(problems), 'problems;', 'swing stop', first)
    for p_ in problems:
        print('  ', p_)


# Tinkercad drops every imported file in the middle of its workplane. These files all carry the same two
# tiny marker cubes at the same far corners, so they share one bounding box and land assembled. Each file is
# also unioned into one clean solid: Tinkercad garbled a file whose pieces touched or overlapped.
ASSEMBLED = [  # file name -> objects in it
    ('01 base tub', ['tub']), ('02 middle sheet', ['mid_sheet']), ('03 button carrier', ['button_carrier']),
    ('04 top plate', ['top_plate']), ('05 button caps', [f'cap_{n}' for n in L.BUTTONS]), ('06 joystick cap', ['joystick_cap']),
    ('07 hinge block', ['hinge_block']), ('08 lid frame', ['lid_frame']), ('09 lid back cover', ['lid_back']),
    ('20 screen', ['screen']), ('21 Pi Zero 2 W', ['Pi Zero 2 W', 'heatsinks', 'Pi connectors']),
    ('22 battery', ['battery']), ('23 joystick', ['joystick board', 'joystick']), ('24 DS3231 clock', ['DS3231 clock']),
    ('25 MT3608 boost', ['MT3608 boost']), ('26 TP4056 charger', ['TP4056 charger']), ('27 ADS1115', ['ADS1115']),
    ('28 USB-C breakout', ['USB-C breakout']), ('29 buttons', ['buttons']),
]


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


def export_assembled(objs):
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
    for fname, keys in ASSEMBLED:
        pieces = []
        for k in keys:
            c = copy_obj(objs[k], k, objs[k].matrix_world)
            pieces += loose_parts(c)
            bpy.data.objects.remove(c)
        ob = boolean(pieces[0], pieces[1:], 'UNION', 'EXACT')      # EXACT merges pieces that only touch
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bpy.data.objects.remove(ob)
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4)       # the union can leave near-twin vertices
        bmesh.ops.dissolve_degenerate(bm, dist=1e-4, edges=bm.edges[:])
        for c in (lo, hi - Vector((0.4, 0.4, 0.4))):                     # the two 0.4 mm marker cubes
            bmesh.ops.create_cube(bm, size=0.4, matrix=Matrix.Translation(c + Vector((0.2, 0.2, 0.2))))
        ob = _obj(fname, bm)
        export_stl([ob], os.path.join(d, fname + '.stl'))
        bpy.data.objects.remove(ob)
    print('ASSEMBLED', len(ASSEMBLED), 'files, frame', [round(v, 1) for v in lo], [round(v, 1) for v in hi])


def export_glb(objs, path):
    root = bpy.data.objects.new('ChAIpi case (metres)', None)
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


def render_views(objs, lid, lid_comps, lid_closed, lid_open):
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
    cam = bpy.data.objects.new('cam', cam_data)
    WORK.objects.link(cam)
    sc.camera = cam
    centre = Vector((W / 2, D / 2, HB / 2))

    def shoot(name, loc, look=centre, lens=50, show=None, hide=()):
        for k, ob in objs.items():
            vis = (show is None or k in show) and k not in hide
            ob.hide_render = not vis
        cam.location = loc
        d = (look - Vector(loc))
        cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        cam_data.lens = lens
        sc.render.filepath = os.path.join(rdir, name + '.png')
        bpy.ops.render.render(write_still=True)

    lid_keys = list(lid) + list(lid_comps)
    axis_pt = Vector((0, AX_Y, HB + AX_Z))
    for k in lid_keys:
        objs[k].matrix_world = lid_open
    shoot('open', (-95, -150, 150), Vector((W / 2, D / 2 + 4, HB + 12)), 42)
    at90 = Matrix.Translation(axis_pt) @ Matrix.Rotation(-math.radians(90), 4, 'X') @ Matrix.Translation(-axis_pt) @ lid_closed
    for k in lid_keys:
        objs[k].matrix_world = at90
    shoot('hinge', (-70, D + 95, HB + 35), Vector((W * 0.35, D - 2, HB + 6)), 40)
    for k in lid_keys:
        objs[k].matrix_world = lid_open
    for k in lid_keys:
        objs[k].matrix_world = lid_closed
    shoot('closed', (200, -150, 130), Vector((W / 2, D / 2, HB / 2 + 4)), 50)
    inside_hide = set(lid_keys) | {'top_plate', 'button_carrier', 'joystick_cap', 'hinge_block'} | {k for k in objs if k.startswith('cap_')}
    shoot('inside', (W / 2 - 10, -95, 190), Vector((W / 2, D / 2 + 2, 6)), 45, hide=inside_hide)
    under_hide = inside_hide | {'Pi Zero 2 W', 'heatsinks', 'Pi connectors', 'mid_sheet', 'buttons'}
    shoot('inside_lower', (W / 2 - 10, -95, 190), Vector((W / 2, D / 2 + 2, 6)), 45, hide=under_hide)
    # exploded: lift each layer
    lift = {'tub': 0, 'battery': 0, 'joystick board': 0, 'joystick': 0, 'DS3231 clock': 0, 'TP4056 charger': 0,
            'ADS1115': 0, 'USB-C breakout': 0, 'MT3608 boost': 18, 'mid_sheet': 30, 'Pi Zero 2 W': 45, 'heatsinks': 45,
            'Pi connectors': 45, 'buttons': 62, 'button_carrier': 62, 'joystick_cap': 92, 'top_plate': 80, 'hinge_block': 100}
    saved = {k: ob.matrix_world.copy() for k, ob in objs.items()}
    for k, ob in objs.items():
        if k in lid_keys:
            ob.matrix_world = Matrix.Translation((0, 0, 125)) @ lid_closed
        elif k.startswith('cap_'):
            ob.matrix_world = Matrix.Translation((0, 0, 92)) @ saved[k]
        else:
            ob.matrix_world = Matrix.Translation((0, 0, lift.get(k, 0))) @ saved[k]
    shoot('exploded', (230, -260, 190), Vector((W / 2, D / 2, 70)), 45)
    for k, ob in objs.items():
        ob.matrix_world = saved[k]
    for k in lid_keys:
        objs[k].matrix_world = lid_open


main()
