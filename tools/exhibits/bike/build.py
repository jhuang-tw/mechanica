# Road bicycle exhibit, built from scratch for Mechanica: one GLB node per semantic part, plus thumb.jpg.
#   "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup -t 4 -P tools/exhibits/bike/build.py -- public/exhibits/bike
# Model frame (Blender): metres, ground z = 0, front = +x, drive (chain) side = -y. glTF export turns that into
# front +x, up +y, drive side +z. Every node's origin is its pivot, so the app turns a part with node.rotateOnAxis(extras.axis).
# Node ids = the `parts[].id` of public/exhibits/bike/manifest.json (checked at export). All nodes sit flat under the scene
# except pedal_l / pedal_r, which are children of crank; spin axes are glTF -z (Blender +y) so positive turns forward.
# Run tools/exhibits/bike/cad.py first: chainring, cassette, cranks, hubs and jockey wheels come from its STLs.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import *   # Mesh, part, run, V, Matrix, Y, TAU, maths
import common

# CAD parts are modelled in mm about +z; these put CAD z on the bike's axle (+90 deg about x: z -> -y = drive side)
TO_DRIVE = Matrix.Rotation(pi / 2, 4, 'X') @ Matrix.Scale(0.001, 4)
TO_LEFT = Matrix.Rotation(-pi / 2, 4, 'X') @ Matrix.Scale(0.001, 4)

# ---------------------------------------------------------------- geometry (metres)
WR = 0.311                      # rim bead seat radius (700c)
TR = 0.0135                     # tyre section radius (~25 mm)
WHEEL = WR + 2 * TR - 0.002     # wheel radius on the ground
RA = V((-0.41, 0, WHEEL))       # rear axle
FA = V((0.575, 0, WHEEL))       # front axle
BB = V((0, 0, 0.27))            # bottom bracket
HA, SA = radians(73), radians(73.5)
U = V((-cos(HA), 0, sin(HA)))   # steering axis, pointing up
PERP = V((sin(HA), 0, cos(HA))) # forward, perpendicular to the steering axis
AXP = FA - PERP * 0.045         # fork offset (rake)
HB = AXP + U * 0.37             # head tube bottom (= fork crown)
HT = HB + U * 0.15              # head tube top
SD = V((-cos(SA), 0, sin(SA)))
STT = BB + SD * 0.52            # seat tube top
RING, COGS = 50, [11, 12, 13, 14, 15, 17, 19, 21, 23, 25, 28]
COG = 5                         # the chain sits on the 17T at rest
PITCH = 0.0127
rT = lambda n: PITCH / (2 * sin(pi / n))
CHAIN_Y = -0.044                # chain line
CRANK = 0.1725

common.MATS.update({   # base colour (linear), metallic, roughness
    'paint':  ((0.50, 0.03, 0.02), 0.3, 0.28),
    'black':  ((0.012, 0.012, 0.013), 0.0, 0.6),
    'rubber': ((0.015, 0.015, 0.015), 0.0, 0.85),
    'alu':    ((0.78, 0.79, 0.80), 1.0, 0.32),
    'steel':  ((0.45, 0.46, 0.47), 1.0, 0.4),
    'gum':    ((0.33, 0.19, 0.08), 0.0, 0.7),
    'dark':   ((0.05, 0.05, 0.055), 1.0, 0.45),
    'reflector': ((0.9, 0.25, 0.02), 0.0, 0.25),   # inner chain plates, so the links alternate bright/dark at a distance
})


def at(y):   # a point d metres across the bike (y), for the side s parts below
    return V((0, y, 0))

def pedal(p, pos, s):
    """Flat platform pedal, 100 x 95 x 17 mm: a spindle from the crank eye through a round barrel, a hollow alloy
    cage (front and back bars joined by the inner and outer side plates and two webs) with six grip pins top and
    bottom on each bar, and an orange reflector on each bar's face."""
    y0, y1 = 0.014, 0.108; yc = (y0 + y1) / 2
    p.disc(pos + at(s * 0.006), Y, 0.0085, 0.012, 'steel', 6)                      # spindle flats (15 mm spanner)
    p.disc(pos + at(s * 0.03), Y, 0.0062, 0.04, 'steel', 12)                       # spindle
    p.disc(pos + at(s * yc), Y, 0.0115, y1 - y0 - 0.006, 'black', 20)              # barrel round the bearings
    p.disc(pos + at(s * (y1 - 0.001)), Y, 0.009, 0.004, 'alu', 20)                # end cap
    for x in (-0.045, 0.045):
        rbox(p, pos + V((x, s * yc, 0)), (0.009, y1 - y0, 0.017), 0.003, 'black')  # front / back bar
        rbox(p, pos + V((x + (0.0048 if x > 0 else -0.0048), s * yc, 0)), (0.0015, 0.05, 0.007), 0.0006, 'reflector')
        for k in range(3):
            for z in (-1, 1):
                py = s * (y0 + 0.016 + k * 0.031)
                p.tube(pos + V((x, py, z * 0.0085)), pos + V((x, py, z * 0.0125)), 0.0017, 'steel', 6)   # grip pin
    for y in (y0 + 0.003, y1 - 0.003):
        rbox(p, pos + V((0, s * y, 0)), (0.099, 0.006, 0.013), 0.0025, 'black')    # inner / outer side plate
    for y in (y0 + 0.03, y1 - 0.03):
        rbox(p, pos + V((0, s * y, 0)), (0.09, 0.005, 0.006), 0.002, 'black')      # webs to the barrel

def hood(m, c, s):
    """Brake / shift lever on the drop bar: a rubber hood over the lever body, clamped on the bar's forward curve and
    rising to a rounded horn, the alloy brake blade curving down in front of the drop, the shift paddle behind it."""
    def P(x, z): return c + V((x, 0, z))
    body = smooth([P(-0.008, 0.002), P(0.012, 0.011), P(0.032, 0.015), P(0.048, 0.019), P(0.058, 0.03)], 4)
    m.sweep(body, [0.0115, 0.012, 0.0125, 0.013, 0.013, 0.013, 0.0125, 0.012, 0.0115, 0.011, 0.0105, 0.01, 0.0095, 0.009, 0.0082, 0.0075, 0.0065], 'rubber', 14)
    m.disc(P(0.061, 0.034), V((0.6, 0, 0.8)), 0.006, 0.005, 'rubber', 12)        # horn tip
    blade = smooth([P(0.046, 0.004), P(0.054, -0.028), P(0.05, -0.064), P(0.036, -0.094), P(0.016, -0.114)], 4)
    m.sweep(blade, [0.0055] * 6 + [0.005] * 6 + [0.0045] * 5, 'alu', 8)          # brake blade, in front of the drop
    m.sweep(smooth([P(0.04, 0.0), P(0.042, -0.03), P(0.034, -0.058)], 3), 0.003, 'black', 6)   # shift paddle behind it
    m.tube(c + V((-0.008, s * 0.012, 0)), c + V((-0.008, -s * 0.012, 0)), 0.0128, 'black', 12)   # clamp band on the bar

def caliper(m, c, axle):
    """Dual-pivot rim brake: the centre bolt through the fork crown or the brake bridge, two alloy arms reaching round
    the tyre to the rim's braking track, a pad in a holder on each side, the cable barrel adjuster and the
    quick-release lever on top."""
    d = (c - axle).normalized(); t = d.cross(Y).normalized()          # d: axle -> mount; t: along the rim at the pads
    pad = axle + d * (WR - 0.011); rot = Matrix.Rotation(-atan2(t.z, t.x), 3, 'Y')
    m.disc(c, t, 0.0045, 0.05, 'steel', 10)                                       # centre bolt
    rbox(m, c - d * 0.004, (0.016, 0.03, 0.018), 0.004, 'alu', Matrix.Rotation(-atan2(d.x, d.z), 3, 'Y'))   # pivot body
    for side, off in ((1, 0.0), (-1, 0.006)):
        reach = c - d * 0.006 + t * off
        path = smooth([reach + V((0, side * 0.008, 0)), reach + V((0, side * 0.024, 0)) - d * 0.008,
                       pad + d * 0.012 + V((0, side * 0.026, 0)), pad + V((0, side * 0.019, 0))], 4)
        m.sweep(path, [0.0068] * 4 + [0.006] * 4 + [0.005] * 5, 'alu', 10)        # arm
        rbox(m, pad + V((0, side * 0.0165, 0)), (0.036, 0.005, 0.011), 0.0018, 'alu', rot)   # pad holder
        rbox(m, pad + V((0, side * 0.0125, 0)), (0.032, 0.004, 0.009), 0.0015, 'black', rot)  # pad
    top = c + d * 0.006 + V((0, 0.018, 0))
    m.tube(top, top + d * 0.024, 0.0042, 'alu', 10)                              # barrel adjuster
    m.sweep(smooth([c + V((0, -0.022, 0)), c + V((0, -0.03, 0)) + d * 0.012, c + V((0, -0.026, 0)) + d * 0.028], 3), 0.0028, 'alu', 6)   # QR lever

def frame():
    m = part('frame', explode=(0, 0, 0))
    ht0, ht1 = HB - U * 0.005, HT + U * 0.005
    m.tube(ht0, ht1, 0.019, 'paint', 16)                                          # head tube
    m.tube(BB + SD * 0.03, STT, 0.0145, 'paint', 14)                              # seat tube
    m.tube(BB + SD * 0.035 + PERP * 0.02, HB + U * 0.025, 0.0175, 'paint', 14)    # down tube
    m.tube(STT - SD * 0.035, HT - U * 0.03, 0.0135, 'paint', 14)                  # top tube
    m.disc(BB, Y, 0.022, 0.072, 'paint', 20)                                      # BB shell
    for s in (-1, 1):
        drop = RA + V((0, s * 0.066, 0))
        m.sweep([BB + V((0, s * 0.03, -0.005)), BB.lerp(drop, 0.45) + V((0, s * 0.048, 0)), drop], [0.011, 0.01, 0.0075], 'paint', 10)   # chainstay
        m.sweep([drop, drop.lerp(STT - SD * 0.06, 0.5) + V((0, -s * 0.012, 0)), STT - SD * 0.06 + V((0, s * 0.016, 0))], [0.0075, 0.0085, 0.009], 'paint', 10)   # seatstay
        m.box(drop + V((0.004, 0, -0.004)), (0.03, 0.005, 0.032), 'paint')       # dropout
    m.tube(STT - SD * 0.13 + V((0, -0.03, 0)), STT - SD * 0.13 + V((0, 0.03, 0)), 0.005, 'paint', 8)   # brake bridge
    m.tube(STT - SD * 0.01, STT + SD * 0.012, 0.0165, 'black', 14)                # seat clamp

def fork():
    m = part('fork', pivot=HB, axis=U, explode=(0.25, 0, 0.05))
    m.tube(HB - U * 0.01, HT + U * 0.035, 0.0145, 'black', 12)                   # steerer
    rbox(m, HB - U * 0.018, (0.03, 0.1, 0.03), 0.011, 'black', Matrix.Rotation(-(pi / 2 - HA), 3, 'Y'))   # crown, rounded into the blades
    for s in (-1, 1):
        top = HB - U * 0.03 + V((0, s * 0.045, 0)); tip = FA + V((0, s * 0.052, 0))
        mid = top.lerp(tip, 0.6) + PERP * 0.012
        m.sweep([top, mid, tip + V((0, 0, 0.012)), tip], [0.0125, 0.0105, 0.008, 0.007], 'black', 10)
    m.tube(HT + U * 0.006, HT + U * 0.03, 0.0175, 'alu', 14)                      # headset spacers + top cap

def handlebar():
    stem0 = HT + U * 0.02; dirS = (PERP * 0.92 + U * 0.25).normalized(); stem1 = stem0 + dirS * 0.10
    st = part('stem', pivot=stem0, axis=U, explode=(0.1, 0, 0.2))
    st.tube(stem0 - dirS * 0.02, stem1, 0.016, 'alu', 12)
    st.tube(stem1 + V((0, -0.02, 0)), stem1 + V((0, 0.02, 0)), 0.0185, 'alu', 12)   # bar clamp
    m = part('handlebar', pivot=stem1, axis=V((0, 1, 0)), explode=(0.15, 0, 0.3))
    pts = []
    for s in (-1, 1):
        side = [stem1 + V((0.0, s * 0.07, 0)), stem1 + V((0.0, s * 0.19, 0)), stem1 + V((0.04, s * 0.205, -0.01)),
                stem1 + V((0.075, s * 0.21, -0.05)), stem1 + V((0.07, s * 0.21, -0.11)), stem1 + V((0.035, s * 0.21, -0.135)), stem1 + V((-0.04, s * 0.21, -0.13))]
        pts.append(side)
    m.sweep(smooth(pts[0][::-1] + pts[1], 4), 0.012, 'black', 12)                 # drop bar (taped), bends rounded
    for s in (-1, 1): hood(m, stem1 + V((0.036, s * 0.206, -0.008)), s)           # brake/shift levers on the hoods

def wheel(pid, axle, explode):
    m = part(pid, pivot=axle, axis=V((0, 1, 0)), explode=explode)
    front = pid == 'front_wheel'
    m.stl('hub_front' if front else 'hub_rear', 'alu', Matrix.Translation(axle) @ TO_DRIVE)
    # flange planes and spoke-hole radius as in cad.py (rear: drive-side flange closer in, room for the cassette)
    fy = {1: 0.027, -1: -0.027} if front else {1: 0.027, -1: -0.020}; fr = 0.018 if front else 0.020
    m.disc(axle, Y, WR + 0.002, 0.02, 'black', 72, r_in=WR - 0.024)               # rim
    for k in range(24):                                                           # 12 spokes per flange, one per hole
        s = 1 if k % 2 else -1; h = radians(30 * (k // 2)); a = h + radians(30 if s < 0 else -15)
        hub = axle + V((cos(h) * fr, fy[s], sin(h) * fr)); rim = axle + V((cos(a) * (WR - 0.02), s * 0.003, sin(a) * (WR - 0.02)))
        m.tube(hub, rim, 0.0011, 'steel', 4, caps=False)
    for sy in (-1, 1): m.disc(axle + V((0, sy * 0.0101, 0)), Y, WR + 0.0015, 0.0006, 'alu', 72, r_in=WR - 0.011)   # machined braking track
    va = radians(100); vr = V((cos(va), 0, sin(va)))
    m.tube(axle + vr * (WR - 0.045), axle + vr * (WR - 0.018), 0.003, 'steel', 8)  # Presta valve
    m.tube(axle + vr * (WR - 0.05), axle + vr * (WR - 0.045), 0.0018, 'steel', 6)
    m.disc(axle + V((0, 0.055, 0)), Y, 0.009, 0.012, 'alu', 16)                  # quick-release cam
    m.sweep(smooth([axle + V((0, 0.06, 0)), axle + V((0.02, 0.064, 0.004)), axle + V((0.055, 0.062, 0.012))], 3), [0.0045, 0.004, 0.0035, 0.003, 0.003, 0.0028, 0.0025], 'alu', 8)   # QR lever
    m.torus(axle, Y, WR + TR - 0.001, TR, 'rubber', 72, 10)
    m.torus(axle, Y, WR + 0.004, 0.0105, 'gum', 72, 6)                            # tan sidewalls peeking out
    return m

def drivetrain():
    m = part('crank', pivot=BB, axis=V((0, 1, 0)), explode=(0, -0.25, -0.1))
    m.disc(BB, Y, 0.012, 0.14, 'steel', 12)                                       # spindle
    # CAD arms: drive arm down with its spider in the ring plane (arm face 24 mm outboard of the chain line), left arm up
    m.stl('crank_right', 'alu', Matrix.Translation(BB + V((0, CHAIN_Y - 0.024, 0))) @ TO_DRIVE)
    m.stl('crank_left', 'alu', Matrix.Translation(BB + V((0, -CHAIN_Y + 0.024, 0))) @ TO_LEFT)
    pedals = [BB + V((0, CHAIN_Y - 0.024, -CRANK)), BB + V((0, -CHAIN_Y + 0.024, CRANK))]

    r = part('chainring', pivot=BB, axis=V((0, 1, 0)), explode=(0, -0.18, 0.05))
    r.stl('chainring', 'steel', Matrix.Translation(BB + V((0, CHAIN_Y, 0))) @ TO_DRIVE)

    for (pos, pid, s) in ((pedals[0], 'pedal_r', -1), (pedals[1], 'pedal_l', 1)):
        p = part(pid, pivot=pos, parent='crank', axis=V((0, 1, 0)), explode=(0, s * 0.3, 0))
        pedal(p, pos, s)

    c = part('cassette', pivot=RA, axis=V((0, 1, 0)), explode=(-0.15, -0.2, 0))
    c.stl('cassette', 'steel', Matrix.Translation(RA + V((0, -0.064, 0))) @ TO_DRIVE)   # 11T outermost

    # rear derailleur: hanger on the drop-out, parallelogram, cage with two jockey wheels under the 17T
    cogR = rT(COGS[COG]); cy = -0.064 + COG * 0.0039
    j1 = RA + V((0.0, cy, -cogR - 0.025)); j2 = j1 + V((0.012, 0, -0.07))
    d = part('rear_derailleur', pivot=j1, axis=V((0, 1, 0)), explode=(-0.1, -0.25, -0.1))
    bk = RA + V((-0.016, -0.072, -0.03)); pk = j1 + V((-0.012, -0.014, 0.014))   # B-knuckle on the hanger, P-knuckle over the cage
    d.box(RA + V((-0.006, -0.07, -0.014)), (0.022, 0.004, 0.034), 'black', Matrix.Rotation(0.5, 3, 'Y'))   # hanger
    rbox(d, bk, (0.024, 0.018, 0.03), 0.005, 'black')                             # B-knuckle (spring and limit screws)
    d.tube(bk + V((0.006, -0.009, 0.01)), bk + V((0.006, -0.016, 0.01)), 0.0022, 'steel', 6)   # limit screws
    d.tube(bk + V((0.006, -0.009, 0.0)), bk + V((0.006, -0.016, 0.0)), 0.0022, 'steel', 6)
    link = pk - bk; rot = Matrix.Rotation(-atan2(link.z, link.x), 3, 'Y')
    for dy, mat in ((-0.008, 'black'), (0.006, 'alu')):                            # parallelogram: outer cover plate, inner link
        rbox(d, bk.lerp(pk, 0.5) + V((0, dy, 0.002)), (link.length + 0.012, 0.004, 0.02), 0.0016, mat, rot)
    rbox(d, pk, (0.02, 0.02, 0.022), 0.005, 'black')                              # P-knuckle
    for j in (j1, j2): d.stl('jockey', 'black', Matrix.Translation(j) @ TO_DRIVE)
    # cage: two stadium-shaped plates round the jockey axles, the outer one with a bolt head at each axle
    cage = j2 - j1; crot = Matrix.Rotation(-atan2(cage.z, cage.x), 3, 'Y')
    for s, mat in ((-1, 'alu'), (1, 'black')):
        o = V((0, s * 0.0055, 0))
        for j in (j1, j2): d.disc(j + o, Y, 0.0105, 0.0016, mat, 24)
        d.box(j1.lerp(j2, 0.5) + o, (cage.length, 0.0016, 0.021), mat, crot)
    for j in (j1, j2): d.disc(j + V((0, -0.008, 0)), Y, 0.004, 0.003, 'steel', 6)
    d.sweep(smooth([bk + V((0.01, 0, 0.012)), bk + V((0.04, 0.004, 0.05)), RA + V((0.12, 0.01, 0.02))], 4), 0.0025, 'black', 8)   # cable housing to the chainstay

    f = part('front_derailleur', pivot=BB + SD * 0.2, axis=SD, explode=(0.05, -0.25, 0.1))
    fc = BB + V((0, CHAIN_Y, 0)) + V((-cos(radians(60)), 0, sin(radians(60)))) * (rT(RING) + 0.012)
    f.tube(BB + SD * 0.19 + V((0, -0.016, 0)), BB + SD * 0.19 + V((0, 0.016, 0)), 0.018, 'black', 14, caps=False)   # band clamp
    f.box(fc + V((0, -0.008, 0.01)), (0.07, 0.002, 0.025), 'alu', Matrix.Rotation(-0.25, 3, 'Y'))
    f.box(fc + V((0, 0.008, 0.01)), (0.07, 0.002, 0.02), 'alu', Matrix.Rotation(-0.25, 3, 'Y'))
    f.tube(fc + V((0, 0, 0.02)), BB + SD * 0.19 + V((0, -0.01, 0)), 0.004, 'black', 6)

    # chain: links along ring top -> cog top, cog bottom -> jockeys -> ring bottom
    ch = part('chain', explode=(0, -0.35, 0))
    ringC, cogC = BB + V((0, CHAIN_Y, 0)), RA + V((0, cy, 0))
    rr, cr = rT(RING), cogR
    def arc(c, r, a0, a1, n): return [c + V((cos(a0 + (a1 - a0) * i / n) * r, 0, sin(a0 + (a1 - a0) * i / n) * r)) for i in range(n + 1)]
    path = [ringC + V((0, 0, rr))] + [cogC + V((0, 0, cr))] + arc(cogC, cr, pi / 2, pi * 1.25, 5)[1:] + [j1 + V((-0.006, 0, 0)), j2 + V((0.006, 0, -0.005)), ringC + V((0.04, 0, -rr))] \
        + arc(ringC, rr, -pi / 2, pi / 2, 16)[1:]
    pts = []
    for a, b in zip(path, path[1:]):
        n = max(1, round((b - a).length / PITCH))
        pts += [a.lerp(b, i / n) for i in range(n)]
    for i, p in enumerate(pts):   # one pitch: roller + pin at p, then a waisted plate pair to q, outer (bright) / inner (dark) alternating
        q = pts[(i + 1) % len(pts)]; t = (q - p)
        if t.length < 1e-6: continue
        rot = Matrix.Rotation(-atan2(t.z, t.x), 3, 'Y')
        ch.disc(p, Y, 0.0039, 0.0058, 'dark', 8)                                    # roller
        ch.disc(p, Y, 0.0018, 0.0112, 'steel', 6)                                   # pin
        outer = i % 2 == 0; w, mat = (0.0048, 'steel') if outer else (0.0037, 'dark')
        for sy in (-1, 1):
            o = V((0, sy * w, 0))
            for e in (p, q): ch.disc(e + o, Y, 0.0042, 0.0009, mat, 8)             # round plate ends
            ch.box(p.lerp(q, 0.5) + o, (PITCH * 0.9, 0.0009, 0.0052), mat, rot)    # waist

def brakes():
    for pid, c, axle, ex in (('brake_front', HB - U * 0.03 + PERP * 0.03, FA, (0.2, 0, 0.15)),
                             ('brake_rear', STT - SD * 0.13 + V((-0.012, 0, 0)), RA, (-0.2, 0, 0.15))):
        m = part(pid, pivot=c, axis=V((1, 0, 0)), explode=ex)
        caliper(m, c, axle)

def saddle():
    top = STT + SD * 0.2
    p = part('seatpost', pivot=STT, axis=SD, explode=(0, 0, 0.25))
    p.tube(STT - SD * 0.08, top, 0.0136, 'black', 12)
    p.box(top + V((0, 0, 0.008)), (0.05, 0.03, 0.014), 'alu')
    s = part('saddle', pivot=top, axis=V((0, 1, 0)), explode=(0, 0, 0.4))
    # road saddle, 275 x 140 mm: (x, half width, crown height) from the tail to the nose; a gently domed top whose sides
    # roll down to a thin shell edge, the tail kicked up a little
    prof = [(-0.128, 0.035, 0.006), (-0.124, 0.058, 0.010), (-0.115, 0.068, 0.012), (-0.095, 0.07, 0.013), (-0.07, 0.065, 0.013),
            (-0.045, 0.052, 0.012), (-0.015, 0.037, 0.011), (0.02, 0.026, 0.010), (0.06, 0.02, 0.010), (0.1, 0.017, 0.010),
            (0.13, 0.014, 0.009), (0.145, 0.008, 0.006)]
    rings = []
    for x, w, h in prof:
        c = top + V((x, 0, 0.045 + 0.008 * max(0, -x - 0.07) / 0.06))
        ring = []
        for i in range(24):
            a = TAU * i / 24; ca, sa = cos(a), sin(a)
            y = w * (abs(ca) ** 0.7) * (1 if ca >= 0 else -1)
            z = h * sa if sa > 0 else 0.004 * sa - 0.002 * (1 - abs(ca))
            ring.append(s.bm.verts.new(c + V((0, y, z))))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]): s.bridge(a, b, 'black')
    s.cap(rings[0], 'black', True); s.cap(rings[-1], 'black')
    for sd in (-1, 1): s.sweep(smooth([top + V((-0.1, sd * 0.034, 0.04)), top + V((-0.06, sd * 0.024, 0.012)), top + V((0.04, sd * 0.02, 0.012)), top + V((0.115, sd * 0.01, 0.038))], 4), 0.0035, 'steel', 6)   # rails
    p.box(top + V((0, 0, 0.012)), (0.03, 0.05, 0.006), 'alu')                    # rail clamp

def build():
    frame(); fork(); handlebar()
    wheel('front_wheel', FA, (0.45, 0, 0)); wheel('rear_wheel', RA, (-0.45, 0, 0))
    drivetrain(); brakes(); saddle()

# look pass before export: whole bike from both sides and front, plus a close-up of the drivetrain
VIEWS = {'drive_side': ((0.55, -2.6, 0.75), (0.07, 0, 0.5), 50), 'left_side': ((-0.3, 2.6, 0.9), (0.07, 0, 0.5), 50),
         'front': ((2.4, -0.9, 1.1), (0.07, 0, 0.5), 50), 'drivetrain': ((-0.05, -0.85, 0.45), (-0.2, -0.04, 0.3), 50),
         # close-ups: pedal, lever on the hood, front caliper, rear derailleur, saddle
         'pedal': ((0.22, -0.42, 0.24), (0.0, -0.11, 0.1), 50), 'hood': ((0.74, -0.52, 0.96), (0.56, -0.2, 0.84), 50),
         'caliper': ((0.74, -0.3, 0.72), (0.47, 0, 0.62), 50), 'derailleur': ((-0.28, -0.42, 0.2), (-0.41, -0.06, 0.21), 50),
         'saddle': ((0.1, -0.6, 1.15), (-0.17, 0, 0.93), 50)}

if __name__ == '__main__':
    run(__file__, build, VIEWS, VIEWS['drive_side'])
