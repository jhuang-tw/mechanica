# Built during the hackathon (Oct 26 – Nov 4, 2026)

Every line of code and every asset in this repository was created during the Meta Global AI Developer Hackathon (Indie track).
The repository was created on `<date>`; its first commit is `<hash>`. The git history is the record.

An earlier personal prototype (a private VR mechanics explorer, started 2026-10-20) was used only as a design reference.
None of its code, models or media are in this repository; everything here was rewritten from scratch.

<!-- Team notes (中文，提交前刪掉)：
- 新 repo 是從零重寫，舊專案只當參考。現在 C:\AI\mechanica 的「舊快照」基底（舊 c87ab01）不能進新 repo。
- 每做完一個功能就在下表加一列：功能 → commit 範圍 → 日期。
- 舊專案 10-26 之後的 commit（CAD 傳動、Meta providers、SAM 遮罩、AI 編排）雖然在活動期間，但在舊 repo 裡，為了乾淨一律在新 repo 重寫，不搬。
-->

## Features → commits
| Feature | Meta model / tool | Commits | Date |
|---|---|---|---|
| Mobile-first app: landing, exhibit view, tap a part, explode, reset, optional WebXR VR (three.js) | — | `7dcf6c0`, `44fe640` | 2026-10-27 |
| Manifest-driven part rig: isolate, detach, rotate, real drives (gear ratios), explode | — | `7dcf6c0` | 2026-10-27 |
| Car exhibit app side: manifest (62 parts, 4 lessons with quiz), slider-crank engine, steering, camera glides to the parts in a lesson | — | `1121b07` | 2026-10-27 |
| Steam exhibit app side: manifest (33 parts, 3 lessons with quiz), slider-crank generalised to any crank axis and slide direction (crossheads, coupling rods, valves 90° ahead) | — | `3027350` | 2026-10-27 |
| Helicopter exhibit app side: manifest (27 parts, 3 lessons with quiz), swashplate linkage (collective lifts plates and pitches both blades; cyclic tilts plates, per-blade sin(azimuth) pitch, teetering disc tilts toward the stick), lesson steps can run several drives | — | `9ac7238` | 2026-10-27 |
| VR headset exhibit app side: manifest (28 parts, 3 lessons with quiz), sliding drives (IPD wheel turns while both eye modules slide), camera focus scaled to small models | — | `46d6965` | 2026-10-27 |
| VR mode: wrist-gear menu (exhibits, lessons, quiz, explode, reset, ask by voice, exit), joint-node hands with grip/pinch colours, two-fist explode/turn/move, poke and ray panels, fading one-line subtitle, lesson and quiz panel; IWER emulator for dev (`?xr`) | — | `282a078` | 2026-10-27 |
| Car body app side: 11 shell, door, seat and dashboard parts, one-way swing drives (doors, hood and trunk open and close), Node tests load textured models | — | `68901e8` | 2026-10-28 |
| Jet exhibit app side: manifest (19 parts, 3 lessons with quiz), LP/HP spools at 1:3 with the radial drive, cowls and thrust reverser (one-way swings and slide), manifest `view` opens on the cutaway | — | `3a899f9` | 2026-10-28 |
| Watch exhibit app side: manifest (24 parts, 3 lessons with quiz), going train at the real ratios (seconds 60×, hour 1/12), balance ±270° with the pallet fork flicking ±10° at twice its rate (new per-move swing `period`), rotor, crown and bezel drives | — | `deeb1fe` | 2026-10-28 |
| Steam shell app side: 8 shell parts with explanations, one-way open drive (smokebox door swings out, cab roof lifts), a smokebox-door step in the blastpipe lesson | — | `321cff6` | 2026-10-28 |
| Moto exhibit app side: manifest (39 parts, 4 lessons with quiz), 270-degree parallel twin on the slider-crank linkage along the 15-degree bore, cams at half crank, primary 32/58, 1st and 6th gear through the 15/43 chain to both wheels, steering about the raked axis, swingarm | — | `823404b` | 2026-10-28 |
| Heli shell app side: 10 shell parts with explanations, one-way open drive (four cabin doors swing out 70 degrees), intro points to explode | — | `160d3b1` | 2026-10-28 |
| Server fix: a missing static file returns 404 instead of crashing the server (headers were written before the read) | — | `00f72fd` | 2026-10-28 |
| Landing reframed as a teaching platform: lesson count per exhibit, lessons first in the how-to, photo search moved below as a secondary button | — | `1b17555` | 2026-10-28 |
| ⛓ Cause-and-effect lessons and ❓ guess-first quiz (from the manifest) | — | `44fe640` | 2026-10-27 |
| Voice and text questions in the app, spoken answers, AI demo playback | Muse Spark, Muse Voice Transcribe (via server) | `44fe640` | 2026-10-27 |
| Bicycle exhibit: manifest (18 parts, 2 drives, 2 lessons with quiz), placeholder model script | — | `7dcf6c0` | 2026-10-27 |
| Photo → machine recognition | Muse Spark vision | `468ce33` (server) | 2026-10-27 |
| Photo → part masks linked to 3D parts | SAM 3.1 | `468ce33` (server); 3D link `<range>` | 2026-10-27 |
| Q&A agent that drives the exhibit | Muse Spark tool calling | `468ce33` (server) | 2026-10-27 |
| AI-choreographed part demos (server checks every step against the manifest) | Muse Spark tool calling | `468ce33` (server) | 2026-10-27 |
| Voice questions (+ one Muse Spark pass: simplified → traditional, part-name fixes) | Muse Voice Transcribe, Muse Spark | `468ce33` (server) | 2026-10-27 |
| Daily spend caps for the public demo | — | `468ce33` (server) | 2026-10-27 |
| Bicycle model from scratch: CAD drivetrain (build123d), Blender build with one node per manifest part, phone GLB optimizer | — | `1b8f2dd` | 2026-10-27 |
| Car exhibit mechanisms from scratch: CAD inline-four engine, 5-speed gearbox, differential, wheels and brakes; Blender chassis, steering, suspension | — | `ba0aa36` | 2026-10-27 |
| Steam locomotive mechanisms from scratch: CAD spoked wheelsets, cutaway cylinders, pistons, valves, crossheads; Walschaerts valve gear, boiler tubes, firebox, steam pipes | — | `14c8ce8` | 2026-10-27 |
| Helicopter mechanisms from scratch: CAD main gearbox (bevel + planetary), swashplate, teetering hub, turboshaft casing, tail gears; lofted blades, servos, controls, skids | — | `09ad2dd` | 2026-10-27 |
| Mixed-reality headset from scratch: lofted front cover with sensor windows, mainboard with SoC, heatsink and heat pipe, blower fan with spinning rotor, cameras and depth sensor, battery, pancake lenses and displays on sliding IPD carriages with a thumb wheel, face cushion, speakers, strap | — | `56efaf2` | 2026-10-27 |
| Car body from a Tripo3D shell: aligned to the CAD axles, Tripo wheels cut away, decimated to ~18k triangles, split into hood, four doors, trunk and body with hinge pivots; metallic-roughness map derived from the colour texture; seats and dashboard modelled in Blender | — | `2367db0` | 2026-10-28 |
| Turbofan from scratch: CAD-revolved nacelle (inlet, hinged fan-cowl doors, thrust-reverser sleeve), fan case and core casings cut away over one quadrant, spinner, rotor drums, exhaust plug and a bevel pair to the radial drive shaft; lofted wide-chord fan, booster, 9-stage HP compressor, HP and 4-stage LP turbine blade rows with stators, annular combustor with 20 fuel nozzles, accessory gearbox, display stand | — | `335d000` | 2026-10-28 |
| Dive watch from scratch: CAD-revolved 42 mm case, coin-edge bezel and display case back, crown and stem; going train with real tooth counts (84T barrel, 75/80/84T wheels, 20-tooth club escape wheel, 60:1 seconds, 12:1 motion works), pallet fork, balance with hairspring, bridges with jewels and blued screws, half-moon rotor; lume dial and hands, rubber strap with buckle | — | `a598bec` | 2026-10-28 |
| Steam locomotive shell from a Tripo3D mesh: aligned to the CAD axles and narrowed to the CAD gauge, Tripo wheels, motion, frames and buffer beams cut away, unbaked cab texture and stray faces repaired, decimated to ~22k triangles with a 2048 texture, split into footplate, boiler cladding, smokebox, hinged smokebox door, side tanks, cab and hinged cab roof; buffer beams and boiler internals moved to fit it; Cycles previews pinned to the discrete GPU | — | `f237245` | 2026-10-28 |
| Motorcycle from scratch: CAD 700 cc parallel twin (270-degree crank, pistons, rods, camshafts, cutaway block and crankcase), wet clutch, 6-speed gearbox, 520 chain and sprockets, 17-inch rims, floating discs; Tripo3D bodywork fitted to the CAD axles and split into tank, seat, side covers, tail, headlight cowl, handlebar, fork, swingarm and frame; shared Tripo shell pipeline in `common.py` | — | `62f9977` | 2026-10-28 |
| Helicopter shell from a Tripo3D mesh (Tripo rights: paid plan still to be confirmed): stretched onto the CAD rotor hub and tail rotor, Tripo rotors, skids and cyclic sticks cut away, decimated to ~24k triangles with a 2048 texture, split along its own pieces into fuselage (with Tripo seats and panel), canopy, hinged front and rear doors, transmission and engine cowlings, tail boom and tail fins; pilot controls and fuel tank moved to fit it | — | `ddfc3af` | 2026-10-28 |

## Third-party (unmodified dependencies, used under their licenses)
| Package | License |
|---|---|
| three | MIT |
| Vite | MIT |
| @meta-sam/parser (official SAM 3.1 mask parser) | SAM License (see its LICENSE) |
| build123d (CAD for the drivetrain parts, build tool only) | Apache-2.0 |
| glTF Transform, meshoptimizer (GLB optimization, dev only) | MIT |
| `<others>` | |

## Assets
| Asset | Made with | Rights |
|---|---|---|
| Bicycle model | `tools/exhibits/bike/cad.py` (build123d) + `build.py` (Blender) + `tools/optimize-glb.mjs` | Ours |
| Car body shell (in `public/exhibits/car/model.glb`) | Tripo3D Multiview to 3D from Codex-generated reference views (`tools/exhibits/car/tripo-ref`), generated 2026-10-27, then processed by `tools/exhibits/car/build.py` | Generated on Jim's Tripo3D account; open-source use needs a paid plan, to be confirmed |
| Steam locomotive shell (in `public/exhibits/steam/model.glb`) | Tripo3D Multiview to 3D from Codex-generated reference views (`tools/exhibits/steam/tripo-ref`), generated 2026-10-27, then processed by `tools/exhibits/steam/build.py` | Generated on Jim's Tripo3D account; open-source use needs a paid plan, to be confirmed |
| Motorcycle bodywork (in `public/exhibits/moto/model.glb`) | Tripo3D Multiview to 3D from Codex-generated reference views (`tools/exhibits/moto/tripo-ref`), generated 2026-10-27, then processed by `tools/exhibits/moto/build.py` | Generated on Jim's Tripo3D account; open-source use needs a paid plan, to be confirmed |
| Voice-over | `<Jim / TTS service>` | `<terms>` |
| Music | `<source>` | Royalty-free |
