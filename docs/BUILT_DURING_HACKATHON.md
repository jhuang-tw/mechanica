# Built during the hackathon (Oct 26 – Nov 4, 2026)

Every line of code and every asset in this repository was created during the Meta Global AI Developer Hackathon (Indie track).
The GitHub repository was created on 2026-10-27 (19:03 UTC, 2026-10-28 03:03 Taiwan time). Its first commit is `9577cd8` (2026-10-27 20:34 +08:00). The git history is the record.

The history has three root commits because the work started in three folders on 2026-10-27 and was joined by merges that night: `9577cd8` (server and Meta AI calls), `14c8ce8` (steam locomotive CAD) and `4da19c8` (the app, the other exhibits' CAD and Blender builds, and the VR mode, committed as one snapshot at 23:58 +08:00). Features below that list `4da19c8` or `9577cd8` were built on 2026-10-27 inside those snapshots; their earlier local commit ids are not in this repository.

An earlier personal prototype (a private VR mechanics explorer, started 2026-10-20) was used only as a design reference.
None of its code, models or media are in this repository; everything here was rewritten from scratch.

## Features → commits
| Feature | Meta model / tool | Commits | Date |
|---|---|---|---|
| Mobile-first app: landing, exhibit view, tap a part, explode, reset, optional WebXR VR (three.js) | — | `4da19c8` | 2026-10-27 |
| Manifest-driven part rig: isolate, detach, rotate, real drives (gear ratios), explode | — | `4da19c8` | 2026-10-27 |
| Car exhibit app side: manifest (62 parts, 4 lessons with quiz), slider-crank engine, steering, camera glides to the parts in a lesson | — | `4da19c8` | 2026-10-27 |
| Steam exhibit app side: manifest (33 parts, 3 lessons with quiz), slider-crank generalised to any crank axis and slide direction (crossheads, coupling rods, valves 90° ahead) | — | `4da19c8` | 2026-10-27 |
| Helicopter exhibit app side: manifest (27 parts, 3 lessons with quiz), swashplate linkage (collective lifts plates and pitches both blades; cyclic tilts plates, per-blade sin(azimuth) pitch, teetering disc tilts toward the stick), lesson steps can run several drives | — | `4da19c8` | 2026-10-27 |
| VR headset exhibit app side: manifest (28 parts, 3 lessons with quiz), sliding drives (IPD wheel turns while both eye modules slide), camera focus scaled to small models | — | `4da19c8` | 2026-10-27 |
| VR mode: wrist-gear menu (exhibits, lessons, quiz, explode, reset, ask by voice, exit), joint-node hands with grip/pinch colours, two-fist explode/turn/move, poke and ray panels, fading one-line subtitle, lesson and quiz panel; IWER emulator for dev (`?xr`) | — | `4da19c8` | 2026-10-27 |
| Car body app side: 11 shell, door, seat and dashboard parts, one-way swing drives (doors, hood and trunk open and close), Node tests load textured models | — | `68901e8` | 2026-10-28 |
| Jet exhibit app side: manifest (19 parts, 3 lessons with quiz), LP/HP spools at 1:3 with the radial drive, cowls and thrust reverser (one-way swings and slide), manifest `view` opens on the cutaway | — | `3a899f9` | 2026-10-28 |
| Watch exhibit app side: manifest (24 parts, 3 lessons with quiz), going train at the real ratios (seconds 60×, hour 1/12), balance ±270° with the pallet fork flicking ±10° at twice its rate (new per-move swing `period`), rotor, crown and bezel drives | — | `deeb1fe` | 2026-10-28 |
| Steam shell app side: 8 shell parts with explanations, one-way open drive (smokebox door swings out, cab roof lifts), a smokebox-door step in the blastpipe lesson | — | `321cff6` | 2026-10-28 |
| Moto exhibit app side: manifest (39 parts, 4 lessons with quiz), 270-degree parallel twin on the slider-crank linkage along the 15-degree bore, cams at half crank, primary 32/58, 1st and 6th gear through the 15/43 chain to both wheels, steering about the raked axis, swingarm | — | `823404b` | 2026-10-28 |
| Heli shell app side: 10 shell parts with explanations, one-way open drive (four cabin doors swing out 70 degrees), intro points to explode | — | `160d3b1` | 2026-10-28 |
| Server fix: a missing static file returns 404 instead of crashing the server (headers were written before the read) | — | `00f72fd` | 2026-10-28 |
| Landing reframed as a teaching platform: lesson count per exhibit, lessons first in the how-to, photo search moved below as a secondary button | — | `1b17555` | 2026-10-28 |
| Hands-on parts (touch and VR): drag a pedal, wheel or piston and the whole drive follows at its ratios through the linkages; doors, hood and cowls swing on their own hinges within range; levers stay in their swing; loose parts pull out along their explode direction; `fixed` bases orbit instead. VR: hold the trigger or pinch on a part and move the ray | — | `9374549` | 2026-10-28 |
| Studio look and PBR pass on all 8 exhibits: softbox reflections, neutral tone mapping, key/fill/rim lights with soft shadow, faded floor and contact shadow, metal roughness grain, per-exhibit `look`; models get rounded edges, baked AO in vertex colours and clear-coat paint | — | `7db46ac` | 2026-10-28 |
| Highlights keep the real material (rim glow, no colour override) on all exhibits; moto engine sealed like a real parallel twin with a right-side cover | — | `fd8d7af` | 2026-10-28 |
| Moto right mirror stalk restored | — | `5a17edc` | 2026-10-28 |
| ⛓ Cause-and-effect lessons and ❓ guess-first quiz (from the manifest) | — | `4da19c8` | 2026-10-27 |
| Voice and text questions in the app, spoken answers, AI demo playback | Muse Spark, Muse Voice Transcribe (via server) | `4da19c8` | 2026-10-27 |
| Bicycle exhibit: manifest (18 parts, 2 drives, 2 lessons with quiz), placeholder model script | — | `4da19c8` | 2026-10-27 |
| Photo → machine recognition | Muse Spark vision | `9577cd8` (server) | 2026-10-27 |
| Photo → part masks linked to 3D parts | SAM 3.1 | `9577cd8` (server); 3D link `4da19c8` | 2026-10-27 |
| Q&A agent that drives the exhibit | Muse Spark tool calling | `9577cd8` (server) | 2026-10-27 |
| AI-choreographed part demos (server checks every step against the manifest) | Muse Spark tool calling | `9577cd8` (server) | 2026-10-27 |
| Voice questions (+ one Muse Spark pass: simplified → traditional, part-name fixes) | Muse Voice Transcribe, Muse Spark | `9577cd8` (server) | 2026-10-27 |
| AI tutor (AI 家教): Socratic questions, grading of free-form spoken or typed answers (right / partial / misconception), a demo on the 3D model aimed at the gap, adaptive next question (choices after repeated misses), learner record per exhibit so a return visit starts from weak spots, photo of a real machine starts the tutor at that part, VR menu entry. One Muse call per turn | Muse Spark tool calling, Muse Voice Transcribe | `899702d` | 2026-10-28 |
| Explain it back (講一遍給我聽): after the last lesson step the learner retells the mechanism by voice or text; Muse marks each cause → effect link covered or missed and names any misconception; the model replays only the missed links; the result feeds the AI tutor's learner record. Picked by a Jevnu score (0.73, highest of six options) | Muse Spark (JSON grading), Muse Voice Transcribe | `2597b92` | 2026-10-28 |
| Daily spend caps for the public demo | — | `9577cd8` (server) | 2026-10-27 |
| Bicycle model from scratch: CAD drivetrain (build123d), Blender build with one node per manifest part, phone GLB optimizer | — | `4da19c8` | 2026-10-27 |
| Car exhibit mechanisms from scratch: CAD inline-four engine, 5-speed gearbox, differential, wheels and brakes; Blender chassis, steering, suspension | — | `4da19c8` | 2026-10-27 |
| Steam locomotive mechanisms from scratch: CAD spoked wheelsets, cutaway cylinders, pistons, valves, crossheads; Walschaerts valve gear, boiler tubes, firebox, steam pipes | — | `14c8ce8` | 2026-10-27 |
| Helicopter mechanisms from scratch: CAD main gearbox (bevel + planetary), swashplate, teetering hub, turboshaft casing, tail gears; lofted blades, servos, controls, skids | — | `09ad2dd` | 2026-10-27 |
| Mixed-reality headset from scratch: lofted front cover with sensor windows, mainboard with SoC, heatsink and heat pipe, blower fan with spinning rotor, cameras and depth sensor, battery, pancake lenses and displays on sliding IPD carriages with a thumb wheel, face cushion, speakers, strap | — | `56efaf2` | 2026-10-27 |
| Car body from a Tripo3D shell: aligned to the CAD axles, Tripo wheels cut away, decimated to ~18k triangles, split into hood, four doors, trunk and body with hinge pivots; metallic-roughness map derived from the colour texture; seats and dashboard modelled in Blender | — | `2367db0` | 2026-10-28 |
| Turbofan from scratch: CAD-revolved nacelle (inlet, hinged fan-cowl doors, thrust-reverser sleeve), fan case and core casings cut away over one quadrant, spinner, rotor drums, exhaust plug and a bevel pair to the radial drive shaft; lofted wide-chord fan, booster, 9-stage HP compressor, HP and 4-stage LP turbine blade rows with stators, annular combustor with 20 fuel nozzles, accessory gearbox, display stand | — | `335d000` | 2026-10-28 |
| Dive watch from scratch: CAD-revolved 42 mm case, coin-edge bezel and display case back, crown and stem; going train with real tooth counts (84T barrel, 75/80/84T wheels, 20-tooth club escape wheel, 60:1 seconds, 12:1 motion works), pallet fork, balance with hairspring, bridges with jewels and blued screws, half-moon rotor; lume dial and hands, rubber strap with buckle | — | `a598bec` | 2026-10-28 |
| Steam locomotive shell from a Tripo3D mesh: aligned to the CAD axles and narrowed to the CAD gauge, Tripo wheels, motion, frames and buffer beams cut away, unbaked cab texture and stray faces repaired, decimated to ~22k triangles with a 2048 texture, split into footplate, boiler cladding, smokebox, hinged smokebox door, side tanks, cab and hinged cab roof; buffer beams and boiler internals moved to fit it; Cycles previews pinned to the discrete GPU | — | `f237245` | 2026-10-28 |
| Motorcycle from scratch: CAD 700 cc parallel twin (270-degree crank, pistons, rods, camshafts, cutaway block and crankcase), wet clutch, 6-speed gearbox, 520 chain and sprockets, 17-inch rims, floating discs; Tripo3D bodywork fitted to the CAD axles and split into tank, seat, side covers, tail, headlight cowl, handlebar, fork, swingarm and frame; shared Tripo shell pipeline in `common.py` | — | `62f9977` | 2026-10-28 |
| Helicopter shell from a Tripo3D mesh (Tripo paid plan): stretched onto the CAD rotor hub and tail rotor, Tripo rotors, skids and cyclic sticks cut away, decimated to ~24k triangles with a 2048 texture, split along its own pieces into fuselage (with Tripo seats and panel), canopy, hinged front and rear doors, transmission and engine cowlings, tail boom and tail fins; pilot controls and fuel tank moved to fit it | — | `ddfc3af` | 2026-10-28 |
| UI redesign: landing hero that starts the first lesson in one tap, lesson-led exhibit cards, own line-icon set (no emoji), glass panels and lesson progress bar in the exhibit view; photo kept as a secondary entry | — | `d156fbc` | 2026-10-28 |
| Continuous lessons and free camera: a 連貫 toggle shows every step's parts and drives together while the captions walk through the cause-and-effect chain on a loop; dragging the camera during a lesson stops the steps from re-aiming it | — | `83efd34` | 2026-10-28 |
| First-person ride (坐上去) on the motorbike and car: eye-point camera with drag look-around, a road rolling at the driven wheel's speed, throttle and per-gear drives (moto 6, car 5) with real rpm and km/h from the gear ratios, x-ray to the drivetrain, car shell lifted like a convertible | — | `ee5a780` | 2026-10-28 |
| Own hand-gesture formulation for VR (finger bend angles, metacarpal palm normal, spread/twist/shift hold) | — | `4da19c8` | 2026-10-27 |
| Mobile pass: 44 px touch targets, landscape phones get the sheet on the side | — | `5248aa3` | 2026-10-28 |
| Mic: tap to start, tap again to send; AI questions get their own row | — | `8832687` | 2026-10-28 |
| Tutor and explain-back in one compact card, choices as pills | — | `41f5ead` | 2026-10-28 |
| Desktop: chips wrap for mouse users, panel uses the full right column | — | `b9ea3a6` | 2026-10-28 |
| Repair challenge (修理挑戰): the app opens on a broken machine; the learner guesses the fault, Muse checks the guess on the model, the learner repairs it and hears why; three guesses from the start, wrong picks explained | Muse Spark | `75e93c3`, `54086d4` | 2026-10-28 |
| Close-up detail pass on all 8 models (bike, headset, car, jet, heli, steam, watch, moto) | — | `3aff675`, `dcea7c9`, `0b63c1a`, `f6817ae`, `8678b8c`, `7cbe41e`, `fb7d73a`, `5ed2417` | 2026-10-28 |
| English site: the whole app in English or 繁體中文 (browser, switch or `?lang=`), English by default | — | `6da3806`, `8e7a311` | 2026-10-28 |
| Car engine: cast shapes instead of boxes; GLB optimizer recomputes normals | — | `3a4db92` | 2026-10-28 |
| Bike: pedals stay level while the crank turns | — | `d95934a` | 2026-10-29 |
| Every question offers tappable options as well as voice and typing | — | `2aba12f` | 2026-10-29 |
| Natural voice: `/api/tts` with Inworld TTS-2 Flash (Xinyi zh-TW, Ashley en), Azure neural TTS next, the browser's voice last | — | `99f0a2b`, `456ac4b`, `16ef004` | 2026-10-28 – 2026-10-29 |
| Phone: two fingers pan as well as pinch, even when the first lands on a movable part | — | `5c095cf` | 2026-10-30 |
| Voice plays each line as a whole clip, the lesson waits for it, the next line is fetched ahead | — | `3a0996c` | 2026-10-30 |
| Guess-first quiz keeps the explanation playing instead of replaying the old step | — | `2985f6e` | 2026-10-31 |
| Content tools: export all teaching text to Markdown and import it back by key | — | `2c8e43d`, `b59b25f` | 2026-10-31 |
| Teaching text rewrite: shorter, plainer part info, lesson lines, quizzes and repair hints (edited with Gemini, imported with the content tools) | — | `31c7b23` | 2026-10-31 |
| Steam repair challenge hides the coupling rods while they are off | — | `e1f985d` | 2026-10-31 |
| Repair challenge: Muse makes every model check in one reply, then a second call says what the model showed and ends on a clue; a failed call falls back to the exhibit's clue | Muse Spark tool calling | `34fc6c7` | 2026-11-01 |
| 90-second demo video: screen capture of the running app, English voice-over from the app's own `/api/tts` (Inworld TTS-2, voice Ashley), no music | Muse Spark, Muse Voice Transcribe (real calls in the repair shots) | — | 2026-11-01 |

## Third-party (unmodified dependencies, used under their licenses)
| Package | License |
|---|---|
| three | MIT |
| Vite | MIT |
| @meta-sam/parser (official SAM 3.1 mask parser) | SAM License (see its LICENSE) |
| build123d (CAD for the drivetrain parts, build tool only) | Apache-2.0 |
| glTF Transform, meshoptimizer (GLB optimization, dev only) | MIT |
| iwer (Meta's WebXR emulator, dev only) | MIT |

## Assets
| Asset | Made with | Rights |
|---|---|---|
| Bicycle model | `tools/exhibits/bike/cad.py` (build123d) + `build.py` (Blender) + `tools/optimize-glb.mjs` | Ours |
| Car body shell (in `public/exhibits/car/model.glb`) | Tripo3D Multiview to 3D from Codex-generated reference views (`tools/exhibits/car/tripo-ref`), generated 2026-10-27, then processed by `tools/exhibits/car/build.py` | Generated on Jim's paid Tripo3D plan (confirmed 2026-10-28), which covers publishing |
| Steam locomotive shell (in `public/exhibits/steam/model.glb`) | Tripo3D Multiview to 3D from Codex-generated reference views (`tools/exhibits/steam/tripo-ref`), generated 2026-10-27, then processed by `tools/exhibits/steam/build.py` | Generated on Jim's paid Tripo3D plan (confirmed 2026-10-28), which covers publishing |
| Motorcycle bodywork (in `public/exhibits/moto/model.glb`) | Tripo3D Multiview to 3D from Codex-generated reference views (`tools/exhibits/moto/tripo-ref`), generated 2026-10-27, then processed by `tools/exhibits/moto/build.py` | Generated on Jim's paid Tripo3D plan (confirmed 2026-10-28), which covers publishing |
| Helicopter shell (in `public/exhibits/heli/model.glb`) | Tripo3D mesh, generated 2026-10-27, then processed by `tools/exhibits/heli/build.py` | Generated on Jim's paid Tripo3D plan (confirmed 2026-10-28), which covers publishing |
| Spoken lesson lines and answers | Generated at run time by Inworld TTS-2 Flash (voices Xinyi, Ashley) on Jim's Inworld account; Azure neural TTS or the browser's own voice as fallbacks. No audio files are stored in the repository | Under the Inworld and Azure terms of service |
| Music | None in the app or the repository | — |
