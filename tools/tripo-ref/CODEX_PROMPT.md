# Codex prompt：Tripo 多視角參考圖（外殼和曲面件）

把 `---` 之間的整段貼給 Codex。共 4 組，每組四張：四台載具外殼。只做外殼。Quest 頭顯整台自己在 Blender 建，不走 Tripo。
內裝（座椅、儀表板）、機構、齒輪、輪子和旋轉體（渦扇短艙、錶殼）都由我直接建模，不需要參考圖。

---

You are generating reference images for Tripo3D "Multiview to 3D". Each set of four images becomes the outer shell of one vehicle in a public, open-source educational app about machines. The engines, gears, wheels, rotors and other mechanisms are modelled separately in CAD and placed inside later, so draw only the object named below, alone, as one closed object.

Write files only under `C:\AI\mme-models\tools\exhibits\<exhibit>\tripo-ref\<object>\` (the folder is given with each object below) and do not run any git command.
For each object save exactly four PNGs: `front.png`, `back.png`, `left.png`, `right.png`.

Rules for every image:
- 1024×1024 PNG, plain pure-white background (#FFFFFF), no floor, no ground shadow, no people, no props, no scenery.
- Orthographic-looking side/front camera at the object's mid-height, no perspective tilt, no 3/4 views.
- Consistent scale: within one object all four views use the same scale, and the longest dimension of the object fills about 85 % of the frame in the left/right views. The front/back views use that same scale (so they look narrower), centred.
- Soft, even studio light, identical in all four views. Mostly matte paint, no environment reflections, no motion blur.
- Generic, original design. No logos, brand names, badges, emblems, text, numbers, licence plates, registration codes, flags, stickers or decals anywhere. It must not resemble any specific real model closely enough to be recognised.
- The four views must be the same object: same proportions, same colours, same details.
- View directions: front = looking at the object's front (a vehicle's nose, the headset's visor), back = the opposite side, left / right = the object's own left and right (driver's or wearer's left and right).
- Keep wheels, rotors and propellers simple and present (they are replaced by CAD parts later), and show clean, closed panel lines where the body opens (doors, engine covers, hoods), because the shell will be cut along them.

Objects (folder in brackets):

1. `car/tripo-ref/body` — 2010s-era compact (C-segment) four-door sedan, three-box shape: short hood over a transverse front engine, front-wheel drive, sloped windscreen, short trunk. Length 4.6 m, width 1.78 m, height 1.46 m, wheelbase 2.70 m, front overhang 0.9 m, 16-inch wheels with 205/55 tyres. Metallic silver paint, dark tinted windows, simple five-spoke wheels. Hood, four doors and trunk lid with clear panel gaps.
2. `moto/tripo-ref/body` — modern naked street motorcycle, 700 cc parallel-twin class: upright one-piece handlebar, round headlight, sculpted 14-litre fuel tank, short stepped seat, short tail, engine and frame left open (no fairing), chain on the left side, exhaust tucked under the engine. Length 2.1 m, wheelbase 1.45 m, seat height 0.8 m, 17-inch wheels. Matte dark grey tank, red side panels, no rider. Fuel tank, seat, side covers and headlight cowl drawn as clearly separate pieces.
3. `steam/tripo-ref/body` — early-1900s industrial 0-6-0 side-tank steam locomotive, standard gauge: three pairs of 1.2 m spoked driving wheels (wheelbase 2.9 m), two outside cylinders under the smokebox, round-topped boiler with one dome and a tall single chimney, rectangular side water tanks alongside the boiler, enclosed cab at the rear with round front spectacle windows, small coal bunker behind the cab. Length 8 m over buffers, chimney top about 3.6 m above the rail. Black boiler and tanks, dark red cab sides, red buffer beams. Smokebox door, cab and side tanks clearly separated from the boiler. Draw cylinders and coupling rods simply; they are replaced later.
4. `heli/tripo-ref/body` — modern light single-turbine utility helicopter, five seats (two front, three rear): rounded glazed nose, cabin doors on both sides, turbine engine housed behind the rotor mast on top of the cabin with an exhaust pointing back, slim tail boom with a vertical fin and the tail rotor on the right side, skid landing gear. Two-blade main rotor about 10.7 m across with the hub about 2.95 m above the ground. Fuselage length about 9.5 m, cabin width 1.5 m. White body with a blue lower band. Cabin doors and the engine cowling behind the main rotor mast with clear panel lines.

When finished, print the list of written files.

---

## 交給 Tripo3D 的方式

- 每組用 **Multiview to 3D**，四張依 front／left／back／right 放進對應欄位，**不要貼圖**。顏色和材質我在 Blender 裡用共用材質套，貼圖反而會被換掉，也比較重。
- 輸出 GLB，放到 `C:\AI\mme-models\tools\exhibits\<exhibit>\tripo\<object>.glb`，例如 `car\tripo\body.glb`。
- **授權要先確認**：Tripo 免費方案產出的模型版權歸 Tripo（只能非商業使用），付費方案的使用者才擁有產出、可以修改、散布和商用。這個 repo 要公開開源，所以生成前要在付費方案下產，或至少確認目前帳號是付費方案。

## 外殼怎麼跟 CAD 機構合在一起（每個展品仍可完整拆解）

1. **外殼只是一層皮**：Tripo 的 GLB 匯入 Blender 後先清理（合併重複點、補洞、刪內部面），再減面到手機預算，整個外殼約 1.5–2.5 萬面。
2. **沿面板縫切開**：依參考圖畫的面板線把外殼切成可拆件，每塊都是 manifest 裡有語意 id 的節點，例如：
   - heli：`cowling`（引擎罩）、`door_l/r`、`cabin`、`tail_boom`
   - moto：`tank`、`seat`、`side_cover_l/r`、`headlight_cowl`
   - car：`hood`、`door_fl/fr/rl/rr`、`trunk`、`body`
   - steam：`smokebox_door`、`cab`、`tank_l/r`、`boiler_shell`
   每塊的原點放在鉸鏈或拆卸方向上，帶 `explode` 位移，拆解時能一片一片掀開或拿走。
3. **內部全是 CAD**：引擎、曲軸、活塞、變速箱、輪子、懸吊、旋翼和斜盤、蒸汽缸和閥動連桿，跟單車一樣用 build123d 建、Blender 組，有各自的旋轉軸和 pivot，可以單獨驅動和拆開。外殼裡被機構佔用的空間我會挖空，避免穿模。
4. **對位**：先定 CAD 底盤的基準點（輪軸、引擎座、旋翼軸），再把外殼縮放和平移到這些點上。Tripo 給的比例不準，所以以 CAD 尺寸為準。
5. 輪子、旋翼這類 Tripo 也會長出來的東西，一律刪掉換成 CAD 件，因為要轉動和拆解。

## 八個展品的分工和順序

| 順序 | 展品 | 外觀 | 機構 |
|---|---|---|---|
| 1 | bike | CAD + Blender（已完成） | CAD |
| 2 | car | Tripo 外殼（座椅、儀表板自建） | CAD：引擎、變速箱、差速器、轉向、懸吊 |
| 3 | steam | Tripo 外殼 | CAD：汽缸、Walschaerts 閥動連桿、動輪 |
| 4 | heli | Tripo 外殼 | CAD：主旋翼、斜盤、尾旋翼傳動 |
| 5 | moto | Tripo 外殼 | CAD：雙缸引擎、離合器、鏈條 |
| 6 | jet（渦扇引擎） | CAD 旋轉體短艙 | CAD：風扇、壓縮機、渦輪、反推 |
| 7 | watch | CAD | CAD：擒縱、齒輪系、自動盤 |
| 8 | quest | CAD + Blender（參考舊專案佈局重建） | CAD：鏡片、IPD 調整、電路板、風扇 |

bike、car、steam、heli 優先，示範時先拿得出三到四個完整的展品。每個都在活動期間從零重做，舊專案只當參考。
