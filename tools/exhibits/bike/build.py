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
    'dark':   ((0.05, 0.05, 0.055), 1.0, 0.45),   # inner chain plates, so the links alternate bright/dark at a distance
})

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
    m.box(HB - U * 0.015, (0.035, 0.105, 0.035), 'black', Matrix.Rotation(-(pi / 2 - HA), 3, 'Y'))   # crown
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
    m.sweep(pts[0][::-1] + pts[1], 0.012, 'black', 10)                            # drop bar (taped)
    for hood in (p[3] for p in pts):                                              # brake/shift levers on the hoods
        m.box(hood + V((0.02, 0, 0.015)), (0.05, 0.026, 0.032), 'black', Matrix.Rotation(radians(-15), 3, 'Y'))   # hood body
        m.sweep([hood + V((0.04, 0, 0.012)), hood + V((0.05, 0, -0.03)), hood + V((0.035, 0, -0.085))], [0.006, 0.006, 0.005], 'alu', 8)   # blade

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
        p.disc(pos + V((0, s * 0.03, 0)), Y, 0.006, 0.06, 'steel', 8)            # axle
        p.box(pos + V((0, s * 0.06, 0)), (0.11, 0.07, 0.014), 'black')           # platform
        p.box(pos + V((0.04, s * 0.06, 0.012)), (0.012, 0.07, 0.01), 'black')    # cleat edge

    c = part('cassette', pivot=RA, axis=V((0, 1, 0)), explode=(-0.15, -0.2, 0))
    c.stl('cassette', 'steel', Matrix.Translation(RA + V((0, -0.064, 0))) @ TO_DRIVE)   # 11T outermost

    # rear derailleur: hanger on the drop-out, parallelogram, cage with two jockey wheels under the 17T
    cogR = rT(COGS[COG]); cy = -0.064 + COG * 0.0039
    j1 = RA + V((0.0, cy, -cogR - 0.025)); j2 = j1 + V((0.012, 0, -0.07))
    d = part('rear_derailleur', pivot=j1, axis=V((0, 1, 0)), explode=(-0.1, -0.25, -0.1))
    bk = RA + V((-0.016, -0.072, -0.03)); pk = j1 + V((-0.012, -0.014, 0.014))   # B-knuckle on the hanger, P-knuckle over the cage
    d.box(RA + V((-0.006, -0.07, -0.014)), (0.022, 0.004, 0.034), 'black', Matrix.Rotation(0.5, 3, 'Y'))   # hanger
    d.disc(bk, Y, 0.010, 0.016, 'black', 16)
    for dz in (-0.006, 0.008): d.sweep([bk + V((0, 0, dz)), pk + V((0, 0, dz))], 0.0035, 'alu', 8)   # parallelogram links
    d.disc(pk, Y, 0.009, 0.016, 'black', 16)
    for j in (j1, j2): d.stl('jockey', 'black', Matrix.Translation(j) @ TO_DRIVE)
    for s in (-1, 1): d.box(j1.lerp(j2, 0.5) + V((0, s * 0.006, 0)), (0.03, 0.002, 0.1), 'alu', Matrix.Rotation(-0.17, 3, 'Y'))

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
    for pid, parent, c, s, ex in (('brake_front', None, HB - U * 0.03 + PERP * 0.012, 1, (0.2, 0, 0.15)),
                                  ('brake_rear', None, STT - SD * 0.13 + V((-0.012, 0, 0)), -1, (-0.2, 0, 0.15))):
        m = part(pid, pivot=c, parent=parent, axis=V((1, 0, 0)), explode=ex)
        m.disc(c, V((1, 0, 0)), 0.005, 0.03, 'steel', 8)
        axle = FA if pid == 'brake_front' else RA
        for side in (-1, 1):    # caliper arms down to the rim, pads at the braking track
            pad = axle + (c - axle).normalized() * (WR - 0.012) + V((0, side * 0.013, 0))
            m.sweep([c + V((0, side * 0.01, 0)), c.lerp(pad, 0.5) + V((0, side * 0.03, 0)), pad + V((0, side * 0.006, 0))], [0.006, 0.005, 0.005], 'alu', 8)
            m.box(pad, (0.03, 0.006, 0.01), 'black', Matrix.Rotation(0, 3, 'Y'))

def saddle():
    top = STT + SD * 0.2
    p = part('seatpost', pivot=STT, axis=SD, explode=(0, 0, 0.25))
    p.tube(STT - SD * 0.08, top, 0.0136, 'black', 12)
    p.box(top + V((0, 0, 0.008)), (0.05, 0.03, 0.014), 'alu')
    s = part('saddle', pivot=top, axis=V((0, 1, 0)), explode=(0, 0, 0.4))
    prof = [(-0.12, 0.072), (-0.09, 0.07), (-0.04, 0.05), (0.02, 0.03), (0.08, 0.02), (0.14, 0.014)]
    rings = []
    for x, w in prof:
        c = top + V((x, 0, 0.04 + 0.006 * (x < -0.06)))
        rings.append([s.bm.verts.new(c + V((0, w * cos(a), 0.018 * sin(a) * (0.5 if sin(a) < 0 else 1)))) for a in (TAU * i / 12 for i in range(12))])
    for a, b in zip(rings, rings[1:]): s.bridge(a, b, 'black')
    s.cap(rings[0], 'black', True); s.cap(rings[-1], 'black')
    for sd in (-1, 1): s.sweep([top + V((-0.09, sd * 0.03, 0.03)), top + V((0, sd * 0.02, 0.012)), top + V((0.1, sd * 0.012, 0.025))], 0.0035, 'steel', 6)   # rails

def build():
    frame(); fork(); handlebar()
    wheel('front_wheel', FA, (0.45, 0, 0)); wheel('rear_wheel', RA, (-0.45, 0, 0))
    drivetrain(); brakes(); saddle()

# look pass before export: whole bike from both sides and front, plus a close-up of the drivetrain
VIEWS = {'drive_side': ((0.55, -2.6, 0.75), (0.07, 0, 0.5), 50), 'left_side': ((-0.3, 2.6, 0.9), (0.07, 0, 0.5), 50),
         'front': ((2.4, -0.9, 1.1), (0.07, 0, 0.5), 50), 'drivetrain': ((-0.05, -0.85, 0.45), (-0.2, -0.04, 0.3), 50)}

if __name__ == '__main__':
    run(__file__, build, VIEWS, VIEWS['drive_side'])
