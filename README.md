# Mechanica

手機打開就能玩的機械教學，兩種模式：

- **修理**（一打開就是）：一台壞掉的機器在你面前運轉。看症狀、說出你的猜測，Meta AI 在 3D 模型上檢查你懷疑的零件給你看；
  找到後修好它，再用你自己的話說說看為什麼，AI 評你的解釋、挑下一台。
- **原理**：一步一步的 3D 課程、先猜再看、AI 家教，問任何問題 AI 會**自己編排零件動作**示範給你看。有 Quest 的話，同一個網址可以進 VR（選用）。

Meta Global AI Developer Hackathon · Indie track。本 repo 的所有程式、資料與模型都是活動期間（2026-10-26 起）做的。

## 執行

```bash
npm install
cp .env.example .env      # 填 META_API_KEY
npm start                 # build ＋ server → http://localhost:8098
npm run dev               # 開發：Vite 8099（/api 轉給 8098，另外要跑 node server/serve.mjs）
npm test                  # 離線測試，不呼叫模型
```

## VR（選用）

頭戴裝置的瀏覽器打開同一個網址，按右上角 **VR**：

- 展品放在面前：大機器在地上照實際大小，小東西放大到桌子高度。
- **選單**：左手張開、手掌朝向自己，手腕內側會出現 ⚙，用右手食指點一下（手把：Y 或 B）。選單裡可以換展品、選課程、先猜再看、拆開／合起、重設、🎤 問 AI、離開 VR。
- **點零件**：手把扳機，或手指捏一下（沿著射線）。零件會亮起，說明用語音念出來。
- **雙手握拳**（手把：兩邊都按握把）：拉開＝拆開，轉動＝旋轉，一起推或抬＝移動。每次握拳只做一種動作。
- **字幕**：視線下方一行，幾秒後淡出；完整內容用語音念。課程和測驗的按鈕在手邊的面板上，用手指點或扳機選。
- 開發時沒有頭戴裝置：`npm run dev` 後開 `http://localhost:8099/?xr`，會用 Meta 的 IWER 模擬一台 Quest 3。

## 資料夾

```
src/                  前端（Vite＋three.js）：首頁、看展品、零件動作引擎、AI 示範播放、VR
public/exhibits/      展品：index.json 列表；<id>/manifest.json、model.glb、thumb.jpg
server/               Node 伺服器：靜態檔＋/api（Meta LLM、工具呼叫、看圖、SAM、語音）
tools/                產模腳本（Blender／程式）
docs/interfaces.md    展品 manifest、模型節點、API 的約定
docs/demo/            比賽影片與提交資料
test/                 node --test
```

要加或改約定，先改 `docs/interfaces.md`，再讓 `npm test` 過。不放品牌標誌；只用有權利的素材。
