# Casings and rotor drums of the turbofan exhibit as real CAD (build123d), exported as STL (mm) for build.py.
#   C:\AI\cad-venv\Scripts\python.exe tools/exhibits/jet/cad.py      -> tools/exhibits/jet/cad/out/<name>.stl (gitignored)
# Generic two-spool high-bypass turbofan (CFM56 class, no brand). Everything is a revolve about +z (= engine front, Blender +x),
# z = 0 at the fan blade root trailing edge. Casings lose the quadrant x < 0, y > 0 (Blender: upper left) so the core shows.
import os, sys
from build123d import (BuildPart, BuildSketch, BuildLine, Polyline, make_face, revolve, Mode, Cylinder, Box, Locations, Plane, Axis, Pos,
                       export_stl)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from heli.cad import bevel

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cad', 'out')

def lathe(prof, cut=False):
    """Revolve a closed (r, z) profile; cut = remove the cutaway quadrant."""
    with BuildPart() as p:
        with BuildSketch(Plane.XZ):
            with BuildLine(): Polyline(*prof, close=True)
            make_face()
        revolve(axis=Axis.Z)
        if cut:
            with Locations(Pos(-600, 600, 0)): Box(1200, 1200, 6000, mode=Mode.SUBTRACT)
    return p.part

def shell(zs, rin, rout, cut=True):
    """Thick wall between two radius curves along z."""
    return lathe([(r, z) for r, z in zip(rout, zs)] + [(r, z) for r, z in zip(rin[::-1], zs[::-1])], cut)

def half(part, s):
    """Keep the y > 0 (s = 1) or y < 0 (s = -1) half: left and right fan-cowl doors."""
    return part - Pos(0, -s * 1100, 0) * Box(2200, 2200, 6000)

def drum(zs, r, t, cut=False): return shell(zs, [x - t for x in r], r, cut)

JOBS = {
    # nacelle: inlet lip, fan cowl (split left / right in build.py), translating thrust-reverser sleeve
    'inlet':     lambda: shell([560, 540, 470, 330, 150, 50], [868, 845, 818, 806, 805, 805], [880, 912, 955, 980, 988, 990]),
    'fan_cowl_l': lambda: half(shell([50, -300, -700], [945, 938, 912], [990, 980, 955]), 1),
    'fan_cowl_r': lambda: half(shell([50, -300, -700], [945, 938, 912], [990, 980, 955]), -1),
    'reverser':  lambda: (shell([-700, -1000, -1100], [940, 905, 888], [955, 918, 898]) +            # outer skin
                          shell([-700, -1000, -1100], [795, 783, 777], [810, 798, 792]) +            # inner skin (bypass duct wall)
                          shell([-1100, -1250], [777, 765], [898, 868])),                            # solid trailing edge
    'fan_case':  lambda: shell([60, -20, -700], [806, 806, 796], [862, 862, 852]),
    # core: inner bypass wall (splitter to core nozzle), compressor / combustor / turbine case
    'core_cowl': lambda: shell([-240, -260, -400, -700, -1100, -1450, -1700], [420, 422, 445, 475, 475, 455, 440], [432, 445, 470, 500, 500, 480, 462]),
    'core_case': lambda: shell([-560, -1150, -1190, -1450, -1490, -1580, -1960, -2060], [350, 310, 395, 395, 350, 362, 432, 420],
                               [368, 328, 418, 418, 368, 380, 450, 436]),
    'liner':     lambda: lathe([(255, -1180), (335, -1180), (350, -1250), (350, -1440), (330, -1440), (330, -1260), (310, -1205),
                                (280, -1205), (270, -1260), (270, -1440), (250, -1440), (240, -1250)]),
    'plug':      lambda: lathe([(0, -1880), (225, -1900), (230, -2000), (170, -2250), (60, -2450), (0, -2500)]),
    # rotors (no cut: they spin)
    'spinner':   lambda: lathe([(262 * (1 - u / 20) ** 0.8, 200 + 21 * u) for u in range(20)] + [(0, 620), (0, 200)]),   # r = R (1 - u)^0.8
    'fan_disk':  lambda: drum([210, -90], [262, 255], 40),
    'booster':   lambda: drum([-260, -540], [282, 278], 18),
    'hpc_drum':  lambda: drum([-590, -1160], [222, 270], 14),
    'hpt_disk':  lambda: lathe([(90, -1470), (250, -1475), (250, -1530), (90, -1535)]),
    'lpt_drum':  lambda: drum([-1580, -1970], [228, 282], 14),
    'lp_shaft':  lambda: lathe([(0, 230), (45, 230), (45, -2000), (0, -2000)]),
    'hp_shaft':  lambda: drum([-560, -1520], [95, 95], 14),
    'bevel_hp':  lambda: bevel(48, 4, 28, 56, 70),
    'bevel_tower': lambda: bevel(32, 4, 28, 34, 14),
    'bevel_agb': lambda: bevel(24, 4, 28, 45, 14),
}

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for name, make in JOBS.items():
        part = make()
        assert part.is_valid, name
        export_stl(part, os.path.join(OUT, name + '.stl'), tolerance=0.3, angular_tolerance=0.25)
        print(name, 'ok')
