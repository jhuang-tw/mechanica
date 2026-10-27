# Steam locomotive exhibit (generic 0-6-0 tank engine), built from scratch for Mechanica: one GLB node per semantic part.
#   "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup -t 4 -P tools/exhibits/steam/build.py -- public/exhibits/steam [--preview]
# Run tools/exhibits/steam/cad.py first (wheels, cylinders, pistons, valves and crossheads come from its STLs).
# Model frame (Blender): metres, rail top z = 0, smokebox = +x, engine's left = +y. glTF: front +x, up +y, right = +z.
# Wheelsets spin about glTF -z (Blender +y): a positive turn drives forward. Right cranks lead the left by 90 deg; at rest the
# right crankpins are on top and the left ones at the front. Everything else in the motion sits where that crank angle puts it;
# the app moves pistons, crossheads, rods and valve gear as linkages (see the node list sent with the model).
# The boiler shell, cab, side tanks and smokebox come from Tripo (tools/tripo-ref) and are added when that GLB exists.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import *   # Mesh, part, run, V, Matrix, Y, TAU, maths
import common

S = Matrix.Scale(0.001, 4)
NY = Matrix.Rotation(pi / 2, 4, 'X') @ S      # CAD z -> Blender -y, CAD y -> +z
PY = Matrix.Rotation(-pi / 2, 4, 'X') @ S     # CAD z -> Blender +y, CAD y -> -z
def at(p, M=S, rz=0): return Matrix.Translation(p) @ M @ Matrix.Rotation(rz, 4, 'Z')

# ---------------------------------------------------------------- layout (metres)
AZ = 0.60                                     # axle height = tread radius
AXLES = [1.45, 0.0, -1.45]
WY = 0.75                                     # wheel tread centre, |y|
CRANK, ROD = 0.30, 1.90
PHI = {1: 0.0, -1: pi / 2}                    # crank angle in the xz plane (from +x towards +z): left at front, right on top
CYL0, CY = 2.35, 1.00                         # cylinder back cover x, cylinder axis |y|
VZ = AZ + 0.34                                # valve axis height
GY = 1.06                                     # valve gear plane |y|
LINK = V((1.00, 0, 0.95))                     # expansion link trunnion (x, -, z)
BOILER_Z, BOILER_R = 1.85, 0.62

def pin(axle_x, side, r=CRANK, extra=0.0):
    a = PHI[side] + extra
    return V((axle_x + r * cos(a), 0, AZ + r * sin(a)))
def crosshead_x(side):
    p = pin(0, side); return p.x + (ROD ** 2 - (p.z - AZ) ** 2) ** 0.5
def Yv(v, y): return V((v.x, y, v.z))

common.MATS.update({   # base colour (linear), metallic, roughness
    'paint':  ((0.02, 0.02, 0.022), 0.2, 0.45),   # black loco paint
    'red':    ((0.35, 0.03, 0.02), 0.2, 0.40),
    'steel':  ((0.55, 0.56, 0.58), 1.0, 0.28),
    'iron':   ((0.10, 0.10, 0.11), 0.8, 0.55),
    'copper': ((0.80, 0.36, 0.20), 1.0, 0.35),
    'brass':  ((0.70, 0.50, 0.18), 1.0, 0.30),
    'wood':   ((0.18, 0.10, 0.05), 0.0, 0.80),
    'glow':   ((1.00, 0.35, 0.05), 0.0, 0.60),
})

def rod(m, a, b, w0, w1, t, mat, bosses=()):
    """Flat rod in the xz plane at a.y: tapered web from a to b (heights w0 -> w1), thickness t along y, round bosses (pos, r)."""
    d = (b - a); L = d.length; d.normalize(); n = V((-d.z, 0, d.x))
    pts = [a + n * w0 / 2, b + n * w1 / 2, b - n * w1 / 2, a - n * w0 / 2]
    vs = [[m.bm.verts.new(p + V((0, dy, 0))) for p in pts] for dy in (-t / 2, t / 2)]
    m.face(vs[0][::-1], mat); m.face(vs[1], mat)
    for i in range(4): m.face([vs[0][i], vs[0][(i + 1) % 4], vs[1][(i + 1) % 4], vs[1][i]], mat)
    for c, r in bosses: m.disc(c, Y, r, t * 1.3, mat, 20)

def wheelsets():
    for i, x in enumerate(AXLES, 1):
        m = part(f'wheelset_{i}', pivot=V((x, 0, AZ)), axis=Y, explode=(0, 0, -0.9))
        m.tube(V((x, -WY + 0.1, AZ)), V((x, WY - 0.1, AZ)), 0.09, 'steel', 16)                       # axle
        for side in (1, -1):
            c = V((x, side * WY, AZ))
            m.stl('wheel', 'red', at(c, PY if side > 0 else NY, -PHI[side] if side > 0 else PHI[side]))
            p = Yv(pin(x, side), side * WY)
            reach = 0.20 if x == 0 else 0.15
            m.tube(p + V((0, side * 0.05, 0)), p + V((0, side * reach, 0)), 0.05, 'steel', 14)           # crankpin
            if x == 0:                                                                                   # return crank on the main pin
                e = Yv(pin(0, side, 0.13, -pi / 2 * side), side * (GY - 0.02))
                rod(m, Yv(p, side * (GY - 0.02)), e, 0.12, 0.08, 0.04, 'steel', [(e, 0.045)])
                m.tube(e, e + V((0, side * 0.06, 0)), 0.025, 'steel', 8)

def motion(side):
    s = 'l' if side > 0 else 'r'; y = side * CY
    xc = crosshead_x(side); X = V((xc, y, AZ))
    part(f'cylinder_{s}', explode=(0.35, side * 0.6, 0)).stl(f'cylinder_{s}', 'iron', at(V((CYL0, y, AZ))))
    part(f'piston_{s}', pivot=X, explode=(0.9, side * 0.9, 0)).stl('piston', 'steel', at(X + V((0.85, 0, 0))))
    part(f'crosshead_{s}', pivot=X, explode=(0.4, side * 0.9, -0.2)).stl('crosshead', 'steel', at(X))
    vc = V((CYL0 + 0.375, y, VZ))
    v = part(f'valve_{s}', pivot=vc, explode=(0.6, side * 0.9, 0.3)); v.stl('valve', 'brass', at(vc))

    mp = Yv(pin(0, side), side * 0.95)
    m = part(f'connecting_rod_{s}', pivot=mp, axis=Y, explode=(0.2, side * 0.6, -0.15))
    rod(m, mp, Yv(X, side * 0.95), 0.16, 0.11, 0.05, 'steel', [(mp, 0.11), (Yv(X, side * 0.95), 0.075)])
    a, b = Yv(pin(AXLES[0], side), side * 0.875), Yv(pin(AXLES[2], side), side * 0.875)
    m = part(f'coupling_rod_{s}', pivot=Yv(pin(0, side), side * 0.875), explode=(0, side * 0.45, -0.1))
    rod(m, a, b, 0.11, 0.11, 0.045, 'steel', [(a, 0.09), (Yv(pin(0, side), side * 0.875), 0.1), (b, 0.09)])

    # Walschaerts gear, in the plane |y| = GY
    e = Yv(pin(0, side, 0.13, -pi / 2 * side), side * GY)
    lk = Yv(LINK, side * GY); tail = lk + V((0, 0, -0.26))
    m = part(f'eccentric_rod_{s}', pivot=e, axis=Y, explode=(0, side * 0.7, -0.3))
    rod(m, e, tail, 0.07, 0.06, 0.035, 'steel', [(e, 0.06), (tail, 0.045)])
    m = part(f'expansion_link_{s}', pivot=lk, axis=Y, explode=(0, side * 0.7, 0.3))
    R = 1.0; cen = lk + V((R, 0, 0))                                       # slot arc centred on the radius rod's far end
    arc = [cen + V((-R * cos(t), 0, R * sin(t))) for t in [(-0.27 + 0.54 * i / 8) for i in range(9)]]
    for off in (-0.035, 0.035): m.sweep([p + V((off, 0, 0)) for p in arc], 0.018, 'steel', 8)
    m.disc(lk, Y, 0.05, 0.12, 'steel', 16); m.disc(arc[0] + V((0, 0, 0)), Y, 0.04, 0.06, 'steel', 12)
    die = lk + V((0, 0, 0.12)); top = V((xc - 0.30, side * GY, VZ + 0.06))
    m = part(f'radius_rod_{s}', pivot=die, axis=Y, explode=(0, side * 0.8, 0.45))
    rod(m, die, top, 0.06, 0.06, 0.03, 'steel', [(die, 0.05), (top, 0.04)])
    low = V((top.x, side * GY, AZ - 0.25))
    m = part(f'combination_lever_{s}', pivot=V((top.x, side * GY, VZ)), axis=Y, explode=(0.1, side * 0.85, 0.2))
    rod(m, top, low, 0.07, 0.05, 0.03, 'steel', [(top, 0.04), (V((top.x, side * GY, VZ)), 0.035), (low, 0.035)])
    m.tube(V((top.x, side * GY, VZ)), V((CYL0 + 0.375 - 0.75, side * CY, VZ)), 0.02, 'steel', 8)     # valve spindle crosshead link
    drop = V((xc, side * GY, AZ - 0.25))
    m = part(f'union_link_{s}', pivot=drop, axis=Y, explode=(0.1, side * 0.85, -0.35))
    rod(m, drop, low, 0.05, 0.05, 0.03, 'steel', [(drop, 0.035), (low, 0.035)])
    m.box(V((xc, side * (CY + GY) / 2, AZ - 0.13)), (0.06, 0.08, 0.26), 'steel')                       # crosshead drop arm

def frames():
    m = part('frames', explode=(0, 0, 0))
    for side in (1, -1):
        m.box(V((0.1, side * 0.60, 0.72)), (6.5, 0.03, 0.62), 'paint')
        for x in AXLES:                                                                                  # axleboxes
            m.box(V((x, side * 0.63, AZ)), (0.30, 0.06, 0.34), 'iron')
        m.box(V((LINK.x, side * (GY - 0.08), LINK.z)), (0.12, 0.08, 0.5), 'paint')                     # motion bracket
        for z in (AZ - 0.12, AZ + 0.12): m.tube(V((CYL0 - 1.04, side * CY, z)), V((CYL0 - 1.04, side * 0.62, z)), 0.02, 'paint', 8)   # slide bar hangers
    for x, w in ((3.32, 0.12), (-3.12, 0.12)):                                                          # buffer beams and buffers
        m.box(V((x, 0, 0.95)), (w, 2.4, 0.35), 'red')
        for side in (1, -1):
            sx = 1 if x > 0 else -1
            m.tube(V((x, side * 0.87, 1.0)), V((x + sx * 0.32, side * 0.87, 1.0)), 0.06, 'iron', 14)
            m.disc(V((x + sx * 0.33, side * 0.87, 1.0)), V((1, 0, 0)), 0.19, 0.03, 'steel', 20)
    m.tube(V((-0.2, -0.55, 1.08)), V((-0.2, 0.55, 1.08)), 0.03, 'paint', 8)

def boiler():
    m = part('firebox', explode=(-0.6, 0, 0.6))
    fb = V((-1.85, 0, 1.55))
    m.box(fb + V((0, 0, 0.25)), (1.2, 1.0, 0.04), 'copper')                                                # crown sheet
    for side in (1, -1): m.box(fb + V((0, side * 0.5, -0.1)), (1.2, 0.04, 0.70), 'copper')
    m.box(fb + V((-0.6, 0, -0.1)), (0.04, 1.0, 0.70), 'copper'); m.box(fb + V((0.6, 0, -0.1)), (0.04, 1.0, 0.70), 'copper')  # door plate, tube plate
    m.box(fb + V((0, 0, -0.44)), (1.15, 0.95, 0.03), 'iron')                                              # grate
    m.box(fb + V((0, 0, -0.38)), (1.0, 0.8, 0.08), 'glow')                                                # fire bed
    m.disc(fb + V((-0.62, 0, 0.0)), V((1, 0, 0)), 0.17, 0.03, 'iron', 16)                                 # fire door
    m = part('boiler_tubes', explode=(0, 0, 1.0))
    for k in range(-3, 4):
        for j in range(-2, 3):
            if k * k + j * j * 2.2 > 11: continue
            y, z = k * 0.085, BOILER_Z + j * 0.11 - 0.05
            m.tube(V((-1.23, y, z)), V((2.55, y, z)), 0.026, 'steel', 8, caps=False)
    for k in (-1, 1): m.tube(V((-1.23, k * 0.17, BOILER_Z + 0.27)), V((2.55, k * 0.17, BOILER_Z + 0.27)), 0.06, 'steel', 12, caps=False)   # superheater flues
    for x in (-1.25, 2.57): m.disc(V((x, 0, BOILER_Z)), V((1, 0, 0)), BOILER_R - 0.03, 0.025, 'copper' if x < 0 else 'iron', 32)   # tube plates
    m = part('steam_pipes', explode=(0.2, 0, 1.4))
    dome = V((0.45, 0, BOILER_Z + 0.48))
    m.tube(dome, dome + V((0, 0, -0.25)), 0.06, 'brass', 12)                                              # regulator head
    m.sweep([dome + V((0, 0, -0.25)), V((0.6, 0, BOILER_Z + 0.42)), V((2.65, 0, BOILER_Z + 0.42))], 0.05, 'steel', 12)   # main steam pipe
    hdr = V((2.85, 0, BOILER_Z + 0.2))
    m.sweep([V((2.65, 0, BOILER_Z + 0.42)), hdr], 0.05, 'steel', 12)
    for side in (1, -1):                                                                                   # outside steam pipes to the valve chests
        m.sweep([hdr, V((2.95, side * 0.45, BOILER_Z - 0.2)), V((2.95, side * 0.80, 1.25)), V((CYL0 + 0.375, side * CY, VZ + 0.16))], 0.055, 'steel', 12)
    m = part('blastpipe', explode=(0.6, 0, 1.6))
    bp = V((2.95, 0, BOILER_Z - 0.45))
    m.sweep([bp, bp + V((0, 0, 0.55))], [0.10, 0.06], 'iron', 16)
    for side in (1, -1): m.sweep([V((CYL0 + 0.375, side * CY, VZ - 0.05)), V((2.95, side * 0.55, 1.0)), bp], 0.06, 'iron', 10)   # exhaust from the cylinders
    m.sweep([bp + V((0, 0, 0.75)), bp + V((0, 0, 1.25))], [0.12, 0.17], 'iron', 20, caps=False)           # petticoat / chimney liner

def cab_controls():
    m = part('reverser', explode=(-0.6, 0.4, 0.4))
    lever = V((-2.35, 0.55, 1.15))
    m.sweep([lever, lever + V((0.08, 0, 0.75))], [0.025, 0.015], 'steel', 8)
    m.box(lever + V((0, 0.05, 0.3)), (0.35, 0.02, 0.05), 'steel')                                           # notched quadrant
    m.sweep([lever + V((0.04, 0.02, 0.4)), V((LINK.x + 0.25, GY, LINK.z + 0.55))], 0.015, 'steel', 6)      # reach rod to the lifting arm
    m.tube(V((LINK.x + 0.25, -GY, LINK.z + 0.55)), V((LINK.x + 0.25, GY, LINK.z + 0.55)), 0.025, 'steel', 10)   # weigh shaft
    m = part('regulator', explode=(-0.6, -0.3, 0.6))
    rg = V((-2.45, 0, BOILER_Z + 0.1))
    m.tube(rg, rg + V((0.2, 0, 0)), 0.03, 'brass', 10); m.box(rg + V((-0.02, 0.18, 0.05)), (0.03, 0.36, 0.05), 'brass')

def rails():
    m = part('track', explode=(0, 0, 0))
    for side in (1, -1):
        y = side * (0.7175 + 0.036)
        m.box(V((0, y, -0.08)), (9.0, 0.07, 0.16), 'steel')
    for k in range(13): m.box(V((-4.2 + k * 0.7, 0, -0.24)), (0.25, 2.6, 0.16), 'wood')

def build():
    wheelsets(); frames(); boiler(); cab_controls(); rails()
    for side in (1, -1): motion(side)

VIEWS = {'left_34': ((5.4, 5.6, 2.6), (0.4, 0, 1.0), 35), 'right_side': ((0.4, -8.5, 1.3), (0.4, 0, 1.0), 35),
         'motion_r': ((1.3, -3.2, 1.0), (1.2, -1.0, 0.75), 35), 'front': ((7.5, 1.5, 2.0), (2.5, 0, 1.2), 40)}

if __name__ == '__main__':
    run(__file__, build, VIEWS, VIEWS['left_34'])
