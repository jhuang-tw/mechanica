# 約定

## 展品

`public/exhibits/index.json`：`{"exhibits": ["bike"]}`，順序就是首頁的順序。
每個展品一個資料夾 `public/exhibits/<id>/`：`manifest.json`、`model.glb`、`thumb.jpg`（正方形約 512 px）。

### manifest.json

| 欄位 | 說明 |
|---|---|
| `id`, `name`, `title` | 代號、短名、完整名稱 |
| `model`, `thumb` | 同資料夾內的檔名 |
| `view` | 選用：一開始從哪個方向看（`[x,y,z]`，例如切開的那一面） |
| `ride` | 選用：「坐上去」第一人稱。`eye`／`look`（模型座標，公尺）、`wheel: {part, r}` 驅動輪和半徑、`gears` 每檔一個 drive id、`idle`／`redline` 引擎轉速範圍（儀表用真實數字）、`see` 按「透視」時顯示的零件、`hide` 坐上去時拿掉的外殼、`lane` 道路中線的 z、`hint` 開場說明 |
| `look` | 選用：打光微調 `{exposure, env, key}`（曝光、環境反射強度、主光與輪廓光強度，預設都是 1），見 `src/look.js` |
| `intro` | 打開展品時的一句話 |
| `suggest[]` | 建議問題（畫面上的按鈕，送給 AI） |
| `looksLike` | 真實世界裡像什麼（拍照比對用） |
| `parts[]` | `{id, name, en, info, aliases[], axis?}`。`id` 就是模型的節點名稱；`en` 是給 SAM 的完整英文描述（"bicycle chain"）；`axis` 是零件自己的轉軸（零件本身座標），有 axis 的零件可以自由旋轉；`fixed: true` 的零件（車架、車身這類底座）不能拖，拖它就是轉視角 |
| `drives[]` | 真實機構 `{id, name, rpm, moves:[{part, ratio}]}`：速度 1 時第一個零件轉 rpm，其他乘 ratio |
| `drives[].swing` | 有 `swing`（度）就是來回擺動（方向盤），`period` 秒一個來回；ratio 乘在角度上；move 有 `slide:[x,y,z]`（公尺）就改成沿這個向量來回滑動；`oneWay: true` 只往一邊擺（0 → swing → 0，像門、引擎蓋）；move 也可以有自己的 `period`（擒縱叉擺得比擺輪快一倍） |
| `linkages[]` | 曲柄滑塊（引擎）`{type:"slider_crank", crank, r, L, up, cylinders:[{piston, rod, phase, slides?, follow?, valve?, valveAmp?, valveLead?}]}`：活塞（和 `slides`，如十字頭）沿 `up` 滑動、連桿從曲柄銷擺到活塞銷、`follow`（聯結桿）跟著曲柄銷平移不轉、`valve` 領先 `valveLead` 弧度滑動 `valveAmp` 公尺，跟著 `crank` 的角度。<br>斜盤（直升機）`{type:"swashplate", mast, plates[], hub, blades[], collective:{part,max}, cyclic:{part,max}, rise, tilt, pitch, cyclicPitch, flap}`：總距桿角度（÷max）讓斜盤上升 `rise` 公尺、槳葉一起變距 `pitch` 度；週期桿讓斜盤前傾 `tilt` 度、每片槳葉變距 `cyclicPitch`·sin(方位角)、蹺蹺板旋翼頭傾 `flap` 度 |
| `lessons[]` | 因果連動 `{id, title, steps:[{say, parts[], drive?, speed?, quiz?}]}`（`drive` 可以是 id 或 id 陣列，一起跑）；`quiz` = `{q, options:[[文字, 是否正確, 為什麼]]}`，只有一個正確 |

| `faults[]` | 修理挑戰 `{id, title, short, symptom, drive, speed?, broken[], stops[], look?, see?, hint, suspects[], cause, why, answer, lesson}`：`drive` 照常運轉，但 `stops` 裡的零件（都要在這個 drive 的 moves 裡）不動；`broken` 是壞掉的零件（答案）；`look.detach {parts?, dir?, amount}` 讓壞的零件歪掉、`look.hide[]` 拿掉擋住的外殼；`see[]` 一開始只看這些（其他變透明）；`short` 首頁的一句症狀；`symptom` 開場題目；`hint` 提示；`suspects` 卡住時給的 3 個猜測（含對的）；`cause` 找到後的說明；`why` 修好後追問；`answer` 正確解釋（評分用）；`lesson` 對應的原理課 |

用手拖零件（`Rig.grab/drag`）：在 drive 裡的零件（或曲柄上的活塞、連桿，主軸上的槳葉，掛在曲柄上的踏板）帶動整個機構；`oneWay` 的門、蓋各自沿鉸鏈開關；swing 的桿在範圍內；只有 axis 的零件自己轉；其他零件沿爆炸方向拉出來。

`test/rig.test.mjs` 會檢查 manifest 裡提到的每個零件都在模型裡。

### model.glb

- 每個零件一個節點，名稱 = `parts[].id`，節點原點放在它的旋轉中心。
- 公尺；+x 往前、+y 往上；自行車的輪軸沿 z，驅動側在 +z。
- 節點 extras 可帶 `axis`（轉軸）和 `explode`（爆炸圖位移，公尺）；manifest 有寫的話以 manifest 為準。
- 子零件跟著父零件動（自行車：`pedal_l`、`pedal_r` 是 `crank` 的子節點）。爆炸圖只移動最上層的零件。
- 參考：`tools/placeholder-bike.mjs`（用幾何體做的暫用模型，完全照這份約定）。

## API（server/）

金鑰只在伺服器。每個 IP 每天有呼叫上限，超過回 429。

| 路徑 | 輸入 | 輸出 |
|---|---|---|
| `GET /api/status` | – | `{meta}` 是否可用 |
| `POST /api/ask` | `{exhibit, text, pointed?, history?}` | `{say, steps[]}` |
| `POST /api/explain` | `{exhibit, lesson, text}` | `{covered[] (one per lesson step), wrong, say}` |
| `POST /api/tutor` | `{exhibit, answer?, history?, known?[{concept, verdict}], focus?}` | `{say, grade?{verdict, concept, gap}, question?{q, choices[]}, steps[]}` |
| `POST /api/fix` | `{exhibit, fault, stage: diagnose\|explain, text, pointed?, history?, solved?[fault keys]}` | diagnose：`{say, result: found\|close\|not_it, suspect[], steps[]}`；explain：`{say, grade?{verdict, gap}, next? ("<exhibit>/<fault>"), steps[]}` |
| `POST /api/identify` | 圖片（不儲存） | `{match, exhibit, confidence, machine, parts[≤4], say}` |
| `POST /api/segment?exhibit=&part=` | 圖片 | `{exhibit, results:[{part, masks:[{bounds, width, height, path}]}]}` |
| `POST /api/stt?exhibit=` | 16 kHz 單聲道 WAV | `{text}` |

### steps（AI 編排的示範）

`{do, at, parts?, drive?, speed?, duration?, degrees?, rpm?, dir?, amount?}`，依 `at`（秒）播放。
`do`：`highlight`、`isolate`（只看這些，其他變透明）、`hide`、`show`、`detach`（拉出來，`dir` = up/down/front/back/left/right，`amount` 0–1）、
`rotate`（`degrees` 或 `rpm`）、`drive`（`drive` = 機構 id，`speed` −1–1）、`reset`。`translate` 視同 `detach`。
前端 `src/choreo.js` 的 `cleanSteps()` 會再檢查一次：未知零件或動作丟掉、數字夾在範圍內（最多 16 步、30 秒）。
