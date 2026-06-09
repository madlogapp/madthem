# MADTHEM

YouTube の **MAD / AMV** をジャンルごとにまとめる、Netflix 風まとめサイト。

- **MAD/AMV の定義**: ジャンル不問の楽曲1曲を、高度にカット編集されたアニメ映像に乗せた数分の動画。
- **区分**: 単体MAD / 複合MAD / 名言集（音楽ジャンル別にも分類）。
- 静的な単一構成（HTML/CSS/JS のみ・ビルド不要）。

## 構成

```
madthem/
├─ index.html              トップページ
├─ css/style.css           Netflix 風ダークテーマ
├─ js/
│  ├─ data.js              手動キュレーションのMADデータ（MAD_DATA）
│  ├─ data-auto.js         ★自動生成（1日3回 update_mads.py が再生成）
│  └─ app.js               行生成・モーダル・関連MAD・検索・フィルタ
├─ tools/
│  ├─ update_mads.py       日次自動更新スクリプト
│  ├─ seen_ids.json        採用済み動画ID（重複防止の永続記録）
│  └─ anime_cache.json     AniList 確認結果キャッシュ
└─ .github/workflows/
   └─ update.yml           1日3回（06/14/22時 JST）自動実行する GitHub Actions
```

## ローカルで見る

`index.html` をブラウザで直接開くだけ（サーバー不要）。

## 自動更新の仕組み（1日3回）

`tools/update_mads.py` が以下を行う:

1. `yt-dlp` で YouTube からアニメ MAD/AMV を検索（**API キー不要**）。
2. **厳格フィルタ**で配信者 / YouTuber / 芸能人 / 人物MADを排除:
   - NG ワード（実況・切り抜き・Vtuber・淫夢・ゲーム名 等）を除外。
   - **単体MAD** … タイトルのアニメ名を抽出し **AniList で実在確認**できたものだけ採用。
   - **複合MAD / 名言集** … 単一アニメ名が無いことが多いため、YouTube カテゴリ
     「Film & Animation」で人物/ゲームを排除。
3. 分類ルール:
   - タイトルに「名言集」→ **名言集**（最優先・単体/複合には絶対しない）
   - 「複合」「神作画」「合作」「年末」等 or 複数アニメ → **複合MAD**
   - 単一アニメ名 → **単体MAD**（`anime` に正式名を格納）
4. `seen_ids.json` で **重複を排除**し、最大 50 件を `js/data-auto.js` に書き出し。
5. `data-auto.js` が読み込み時に `MAD_DATA` へマージ → 全行へ自動反映。

### 手動実行

```bash
pip install yt-dlp
python3 tools/update_mads.py
```

## デプロイ（GitHub Pages + Actions・無料）

1. この `madthem/` の中身を GitHub リポジトリの**ルート**として push（`index.html` が直下）。
2. **Settings → Pages** → "Deploy from a branch" → `main` / `(root)`。
3. **Settings → Actions → General → Workflow permissions** → "Read and write permissions"。
4. **Actions** タブで `Daily MAD auto-update` を一度手動実行して確認。

以降、1日3回 自動で YouTube を取得 → `data-auto.js` を更新 → コミット → Pages 再デプロイ。

> ⚠️ GitHub runner の IP が YouTube に時々ブロックされる場合があります。その際は
> self-hosted runner か Cloudflare への移行で回避できます。

## データを手で足す

`js/data.js` の `MAD_DATA` に1件追加すれば該当ジャンル/区分の行へ自動で並びます
（書式は既存エントリ参照）。手動分は自動更新で上書きされません（自動分は `data-auto.js`）。
