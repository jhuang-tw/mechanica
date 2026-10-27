# Movement layout (mm) shared by cad.py and build.py: wheel centres and the gear modules that make each pair mesh.
def module(d, n1, n2): return 2 * d / (n1 + n2)      # the module that makes an n1 / n2 pair mesh at centre distance d

BARREL = (1.15, 6.5)          # 84T barrel drives the 12T centre pinion
THIRD = (4.85, -2.8)          # 10T pinion on the 75T centre wheel; 80T third wheel drives the 10T fourth pinion
ESCAPE = (-3.25, -5.63)       # 7T escape pinion on the 84T fourth wheel
PALLET = (-5.75, -4.25)
BALANCE = (-8.0, -1.5)
MINUTE_WHEEL = (-2.44, -0.89) # motion works under the dial: 12T cannon pinion -> 36T / 10T minute wheel -> 40T hour wheel
def dist(a, b=(0, 0)): return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
M_B, M_3, M_4, M_E = module(dist(BARREL), 84, 12), module(dist(THIRD), 75, 10), module(dist(THIRD), 80, 10), module(dist(ESCAPE), 84, 7)
M_MW, M_HW = module(dist(MINUTE_WHEEL), 12, 36), module(dist(MINUTE_WHEEL), 10, 40)

