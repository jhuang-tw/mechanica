# Mechanical parts of the helicopter exhibit as real CAD (build123d), exported as STL (mm) for build.py.
#   C:\AI\cad-venv\Scripts\python.exe tools/exhibits/heli/cad.py      -> tools/exhibits/heli/cad/out/<name>.stl (gitignored)
# Generic light single-turbine helicopter with a two-blade teetering main rotor. Every rotating part is modelled about +z
# with its rotation centre at the origin. Bevel gears have their pitch cone apex on +z.
import os
from math import sin, cos, pi, radians
from build123d import (BuildPart, BuildSketch, BuildLine, Polyline, Circle, Rectangle, Locations, PolarLocations, make_face, RegularPolygon, add,
                       extrude, revolve, Mode, Cylinder, Box, Sphere, Plane, Axis, Pos, Rot, export_stl)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cad', 'out')
TAU = 2 * pi

def gear_outline(n, m, seg=2):
    rp = m * n / 2; ra, rf = rp + m, rp - 1.25 * m; pts = []
    for k in range(n):
        a = TAU * k / n; da = TAU / n
        for i in range(seg + 1): t = a - 0.25 * da + 0.25 * da * i / seg; pts.append((rf * cos(t), rf * sin(t)))
        for t, r in ((a + 0.05 * da, rp - 0.2 * m), (a + 0.17 * da, ra), (a + 0.33 * da, ra), (a + 0.45 * da, rp - 0.2 * m)): pts.append((r * cos(t), r * sin(t)))
        t = a + 0.5 * da; pts.append((rf * cos(t), rf * sin(t)))
    return pts

def bevel(n, m, width, cone_deg, bore, steps=4):
    """Straight bevel gear approximated by stacked tooth rings, each smaller towards +z along the pitch cone."""
    rp = m * n / 2; shrink = width * cos(radians(cone_deg)) / rp
    with BuildPart() as p:
        for i in range(steps):
            k = 1 - shrink * (i + 0.5) / steps
            with BuildSketch(Plane.XY.offset(width * i / steps)):
                with BuildLine(): Polyline(*[(x * k, y * k) for x, y in gear_outline(n, m)], close=True)
                make_face()
                Circle(bore, mode=Mode.SUBTRACT)
            extrude(amount=width / steps)
        with Locations(Pos(0, 0, -15)): Cylinder(bore + 18, 30)
        with Locations(Pos(0, 0, -15)): Cylinder(bore, 32, mode=Mode.SUBTRACT)
    return p.part

def spur(n, m, width, bore):
    with BuildPart() as p:
        with BuildSketch():
            with BuildLine(): Polyline(*gear_outline(n, m), close=True)
            make_face()
            Circle(bore, mode=Mode.SUBTRACT)
        extrude(amount=width / 2, both=True)
    return p.part

def planetary():
    """Main-gearbox planetary stage around the mast (z): sun, 4 planets on a carrier, fixed ring gear (cut open)."""
    sun = spur(24, 4, 50, 30)
    planets = None
    for k in range(4):
        a = TAU * k / 4 + pi / 4
        pl = spur(24, 4, 50, 12).moved(Pos(96 * cos(a), 96 * sin(a), 0))
        planets = pl if planets is None else planets + pl
    with BuildPart() as ring:
        Cylinder(220, 50)
        with BuildSketch(Plane.XY.offset(-30)):
            with BuildLine(): Polyline(*gear_outline(72, 4), close=True)
            make_face()
        extrude(amount=60, mode=Mode.SUBTRACT)
        with Locations(Pos(150, 150, 0)): Box(300, 300, 60, mode=Mode.SUBTRACT)    # quarter cut away
    with BuildPart() as carrier:
        with Locations(Pos(0, 0, 40)): Cylinder(125, 14)
        with Locations(Pos(0, 0, 40)): Cylinder(40, 16, mode=Mode.SUBTRACT)
    return sun, planets, ring.part, carrier.part

def swash_lower():
    """Stationary swashplate: ring on a spherical bearing, three servo lugs at 0/120/240 deg plus the anti-rotation arm."""
    with BuildPart() as p:
        Cylinder(190, 40)
        Cylinder(120, 42, mode=Mode.SUBTRACT)
        with PolarLocations(215, 3): Box(70, 50, 40)
        with Locations(Pos(-230, 0, 0)): Box(60, 30, 40)
        with Locations(Pos(0, 0, -10)): Sphere(110)
        Cylinder(75, 300, mode=Mode.SUBTRACT)
    return p.part

def swash_upper():
    """Rotating swashplate above it, with two pitch-link lugs (blade 1 at +x, lugs lead by 90 deg)."""
    with BuildPart() as p:
        with Locations(Pos(0, 0, 45)):
            Cylinder(175, 34)
            Cylinder(125, 36, mode=Mode.SUBTRACT)
            with PolarLocations(200, 2, start_angle=24): Box(60, 40, 34)   # under the pitch horns
            with PolarLocations(150, 2, start_angle=0): Box(40, 30, 34)           # scissor lugs
    return p.part

NUTS = {k: extrude(RegularPolygon(k[0] / 3 ** 0.5, 6), k[1]) for k in ((46, 18), (120, 50), (56, 26))}   # built outside any builder

def hex_nut(af, h, z, x=0):
    """Hex nut across flats `af`, height h, sitting on z at (x, 0), axis z."""
    add(Pos(x, 0, z) * NUTS[(af, h)])

def hub():
    """Teetering hub like a light turbine single's: forged yoke across a trunnion on the mast, teeter pin in two pillow blocks (y),
    blade grips on feathering bearings along +-x, forked at the tip round the blade bolt, pitch horns leading by 90 deg;
    retaining nut, cotter cap and flapping-stop ring on top."""
    with BuildPart() as p:
        Box(210, 170, 120)                                                         # trunnion on the mast splines
        for y in (-105, 105):
            with Locations(Pos(0, y, 0)): Box(90, 40, 150)                         # pillow blocks
        Cylinder(36, 290, rotation=(90, 0, 0))                                     # teeter pin
        Box(560, 150, 36)                                                          # yoke plate
        for s in (-1, 1):
            with Locations(Pos(s * 280, 0, 0)): Cylinder(75, 36)                  # yoke ends round the grip bearings
            with Locations(Pos(s * 330, 0, 0)): Cylinder(78, 170, rotation=(0, 90, 0))      # feathering bearing housing
            with Locations(Pos(s * 330, 0, 0)): Cylinder(84, 18, rotation=(0, 90, 0))       # housing flange
            for z in (-37, 37):
                with Locations(Pos(s * 505, 0, z)): Box(190, 130, 20)              # grip fork straps
            with Locations(Pos(s * 545, 0, 0)): Cylinder(26, 120)                 # blade bolt
            hex_nut(46, 18, 47, s * 545)
            with Locations(Pos(s * 330, s * 95, -40)): Box(70, 110, 32)            # pitch horn arm
            with Locations(Pos(s * 330, s * 150, -50)): Cylinder(30, 44)           # horn clevis lug
        Cylinder(48, 400, mode=Mode.SUBTRACT)                                      # mast bore
        with Locations(Pos(0, 0, -78)): Cylinder(118, 16)                          # flapping-stop ring
        hex_nut(120, 50, 60)                                                       # mast retaining nut
        with Locations(Pos(0, 0, 122)): Cylinder(30, 24)                           # cotter cap
    return p.part

def tail_hub():
    """Two-blade tail rotor hub (axis z): delta-hinged yoke, grips with pitch horns toward the crosshead, retaining nut."""
    with BuildPart() as p:
        Cylinder(42, 70)
        Box(200, 64, 34)                                                           # yoke
        Cylinder(18, 120, rotation=(0, 90, 0), mode=Mode.ADD)
        with Locations(Pos(0, 0, 0)): Cylinder(14, 150, rotation=(90, 0, 0))       # flapping hinge pin
        for s in (-1, 1):
            with Locations(Pos(s * 125, 0, 0)): Cylinder(32, 90, rotation=(0, 90, 0))        # grip
            with Locations(Pos(s * 160, 0, 0)): Cylinder(36, 14, rotation=(0, 90, 0))        # grip flange
            with Locations(Pos(s * 120, s * 40, -30)): Box(26, 56, 18)             # pitch horn
            with Locations(Pos(s * 120, s * 62, -45)): Cylinder(10, 26)            # horn lug
        hex_nut(56, 26, 30)
        with Locations(Pos(0, 0, -60)): Cylinder(25, 70)
    return p.part

def turboshaft():
    """Turboshaft casing, axis z: intake bell at +z (front), compressor, combustor bulge, turbine, exhaust collector at -z."""
    prof = [(0, 400), (60, 400), (95, 360), (150, 290), (175, 200), (172, 110), (192, 60), (192, -20), (160, -80), (150, -220),
            (172, -290), (150, -380), (0, -380)]
    with BuildPart() as p:
        with BuildSketch(Plane.XZ):
            with BuildLine(): Polyline(*prof, close=True)
            make_face()
        revolve(axis=Axis.Z)
        for z in (300, 200, 120):                                                  # compressor stage rings
            with Locations(Pos(0, 0, z)): Cylinder(178 if z < 300 else 160, 10)
        with Locations(Pos(0, 0, -130)): Box(400, 120, 140, mode=Mode.SUBTRACT)  # window onto the power turbine (cut both sides)
        with Locations(Pos(0, 0, -130)): Cylinder(60, 140)                        # turbine shaft visible in the window
    return p.part

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    sun, planets, ring, carrier = planetary()
    jobs = [('bevel_input', lambda: bevel(19, 6, 45, 25, 20), 0.1), ('bevel_output', lambda: bevel(71, 6, 45, 65, 60), 0.15),
            ('sun', lambda: sun, 0.1), ('planets', lambda: planets, 0.1), ('ring_gear', lambda: ring, 0.15), ('carrier', lambda: carrier, 0.15),
            ('swash_lower', swash_lower, 0.15), ('swash_upper', swash_upper, 0.15), ('hub', hub, 0.2), ('tail_hub', tail_hub, 0.1),
            ('turboshaft', turboshaft, 0.2), ('tail_bevel_a', lambda: bevel(20, 3, 25, 45, 10), 0.08), ('tail_bevel_b', lambda: bevel(20, 3, 25, 45, 10), 0.08)]
    for name, make, tol in jobs:
        part = make()
        assert part.is_valid, name
        export_stl(part, os.path.join(OUT, name + '.stl'), tolerance=tol, angular_tolerance=0.3)
        print(name, 'ok')
