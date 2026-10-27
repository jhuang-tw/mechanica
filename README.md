# Mechanica

手機打開就能玩的機械教學：選一台機器（或拍一張真的），拆開它、讓它動起來，問 Meta AI 為什麼，
AI 會**自己編排零件動作**示範給你看。有 Quest 的話，同一個網址可以進 VR（選用）。

Meta Global AI Developer Hackathon · Indie track。本 repo 的所有程式、資料與模型都是活動期間（2026-10-26 起）做的。

## 執行

```bash
npm install
cp .env.example .env      # 填 META_API_KEY
npm start                 # build ＋ server → http://localhost:8098
npm run dev               # 開發：Vite 8099（/api 轉給 8098，另外要跑 node server/serve.mjs）
npm test                  # 離線測試，不呼叫模型
```

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
