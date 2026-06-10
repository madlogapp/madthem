#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MADTHEM 日次自動更新スクリプト
===============================================================================
YouTube から「アニメMAD/AMV」を取得し、厳格フィルタ（実在アニメ名で確認）を
通したものだけを分類して js/data-auto.js を再生成する。

- API キー不要（yt-dlp によるメタデータ取得のみ）
- 実在アニメ名の確認は AniList GraphQL（無料・キー不要）
- 配信者 / YouTuber / 芸能人 / 人物MAD は採用しない
- 重複なし（youtubeId を tools/seen_ids.json に永続記録）
- 最大 MAX_TOTAL 件まで data-auto.js に保持

使い方:
    python3 -m yt_dlp が利用可能な環境で
    python3 tools/update_mads.py
===============================================================================
"""
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request

# 漢字→読み（五十音インデックス用）。未導入でも動作（reading=None）
try:
    import pykakasi
    _KKS = pykakasi.kakasi()
except Exception:
    _KKS = None


def to_reading(text):
    """日本語タイトルのひらがな読みを返す（索引のバケット判定用）。"""
    if not _KKS or not text:
        return None
    try:
        return "".join(it["hira"] for it in _KKS.convert(text))
    except Exception:
        return None

# ---- 設定 ---------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA_AUTO_JS = os.path.join(ROOT, "js", "data-auto.js")
SEEN_PATH = os.path.join(HERE, "seen_ids.json")
ANIME_CACHE = os.path.join(HERE, "anime_cache.json")

MAX_TOTAL = 500         # data-auto.js に保持する最大件数
PER_QUERY = 80          # 1検索あたりの取得本数
MIN_SEC = 60            # 最短尺（ショート除外）
MAX_SEC = 660          # 最長尺（年末複合などを許容しつつ長尺配信は除外）

# 検索クエリ（単体・複合・名言集 + 人気アニメ別でバランス良く広く拾う）
SEARCH_QUERIES = [
    # 汎用
    "アニメ MAD", "アニメ AMV", "単体MAD アニメ", "複合MAD", "複合MAD アニメ",
    "アニメ 名言集 MAD", "MAD 神作画", "AMV anime", "アニメ MAD 作業用",
    "MAD アニメ 神編集", "アニメ MAD 2024", "アニメ MAD 2025", "AMV 4K アニメ",
    # 人気アニメ別（単体MADを広く確保）
    "呪術廻戦 MAD", "鬼滅の刃 MAD", "チェンソーマン MAD", "葬送のフリーレン MAD",
    "薬屋のひとりごと MAD", "進撃の巨人 MAD", "僕のヒーローアカデミア MAD",
    "ワンピース MAD", "NARUTO MAD", "BLEACH MAD", "ハイキュー MAD",
    "東京リベンジャーズ MAD", "推しの子 MAD", "SPY×FAMILY MAD", "ブルーロック MAD",
    "ぼっち・ざ・ろっく MAD", "暗殺教室 MAD", "Dr.STONE MAD", "炎炎ノ消防隊 MAD",
    "モブサイコ100 MAD", "コードギアス MAD", "Fate MAD", "エヴァンゲリオン MAD",
    "ガンダム MAD", "ポケモン MAD", "ドラゴンボール MAD", "聲の形 MAD",
    "リコリスリコイル MAD", "葬送 MAD", "怪獣8号 MAD", "ダンダダン MAD",
    "薫る花は凛と咲く MAD", "天元突破グレンラガン MAD", "Sakamoto Days MAD",
]

# 非アニメ（人物・配信者・芸能人）系を確実に弾くNGワード
BLOCKLIST = [
    "実況", "切り抜き", "vtuber", "ｖｔｕｂｅｒ", "ホロライブ", "にじさんじ",
    "淫夢", "例のアレ", "真夏の夜の淫夢", "ホモと", "biim", "ゆっくり実況",
    "替え歌", "歌ってみた", "踊ってみた", "弾いてみた", "演奏してみた",
    "プロ野球", "サッカー", "野球", "格闘技", "ボクシング", "競馬",
    "芸能人", "アイドルグループ", "ジャニーズ", "声優MAD",
    "fortnite", "フォートナイト", "apex", "valorant", "マインクラフト",
    "ゲーム実況", "tiktok", "shorts",
    # アダルト/NSFW
    "r18", "r-18", "18禁", "エロ", "hentai", "えっち", "エッチ", "av女優",
    "痴漢", "おっぱい", "巨乳", "下ネタ",
]

# MADタグ等の装飾（アニメ名抽出時に除去する）
DECOR_PATTERNS = [
    r"単体\s*mad", r"複合\s*mad", r"テーマ\s*mad", r"セリフ入り\s*mad",
    r"歌詞付き", r"歌詞和訳入り", r"歌詞", r"高画質", r"作業用",
    r"4k", r"2160p", r"1080p", r"60fps", r"修正版", r"再up", r"再アップ",
    r"mad", r"amv", r"\bmv\b", r"\bpv\b", r"公式", r"フル", r"full",
    r"イヤホン推奨", r"初心者", r"ネタバレ", r"中文字幕", r"ver\.?",
]

# アーティスト/楽曲 → 音楽ジャンル の辞書（増やすほど精度↑）
# ※ ascii キーは単語境界で照合、日本語キーは部分一致で照合する
ARTIST_GENRE = {
    # --- ロック / バンド ---
    "kana-boon": "ロック", "ヨルシカ": "ロック", "yorushika": "ロック",
    "aimer": "ロック", "king gnu": "ロック", "my first story": "ロック",
    "one ok rock": "ロック", "bump of chicken": "ロック", "radwimps": "ロック",
    "uverworld": "ロック", "凛として時雨": "ロック", "ヒトリエ": "ロック",
    "man with a mission": "ロック", "マンウィズ": "ロック", "sim": "ロック",
    "coldrain": "ロック", "crossfaith": "ロック", "sumika": "ロック",
    "アジカン": "ロック", "asian kung-fu generation": "ロック",
    "サカナクション": "ロック", "ストレイテナー": "ロック", "ellegarden": "ロック",
    "ellegarden": "ロック", "10-feet": "ロック", "10feet": "ロック",
    "緑黄色社会": "ロック", "リョクシャカ": "ロック", "[alexandros]": "ロック",
    "フレデリック": "ロック", "go!go!vanillas": "ロック", "ヤバいtシャツ屋さん": "ロック",
    "spyair": "ロック", "flow": "ロック", "the oral cigarettes": "ロック",
    "survive said the prophet": "ロック", "鬼束ちひろ": "ロック",
    "らっぷびと": "ロック",
    # --- J-POP ---
    "mrs. green apple": "J-POP", "mrs.green apple": "J-POP",
    "ミセスグリーンアップル": "J-POP",
    "yoasobi": "J-POP", "ado": "J-POP", "uru": "J-POP", "yama": "J-POP",
    "vaundy": "J-POP", "back number": "J-POP", "official髭男dism": "J-POP",
    "ヒゲダン": "J-POP", "米津玄師": "J-POP", "kenshi yonezu": "J-POP",
    "あいみょん": "J-POP", "saucy dog": "J-POP", "スピッツ": "J-POP",
    "mr.children": "J-POP", "ミスチル": "J-POP", "優里": "J-POP",
    "藤井風": "J-POP", "imase": "J-POP", "tani yuuki": "J-POP",
    "tuki.": "J-POP", "なとり": "J-POP", "natori": "J-POP",
    "lisa": "アニソン", "藍井エイル": "アニソン", "fictionjunction": "アニソン",
    "kalafina": "アニソン", "spira spica": "アニソン", "聖飢魔": "ロック",
    "西川貴教": "アニソン", "t.m.revolution": "アニソン",
    "fripside": "アニソン", "angela": "アニソン", "granrodeo": "アニソン",
    "オーイシマサヨシ": "アニソン", "大石昌良": "アニソン", "宮野真守": "アニソン",
    "halca": "アニソン", "sawano": "アニソン", "澤野弘之": "アニソン",
    "sajou no hana": "アニソン", "majiko": "アニソン",
    # --- ボカロ / ボカロP ---
    "orangestar": "ボカロ", "kanaria": "ボカロ", "deco*27": "ボカロ",
    "eve": "ボカロ", "wowaka": "ボカロ", "n-buna": "ボカロ",
    "ピノキオピー": "ボカロ", "neru": "ボカロ", "須田景凪": "ボカロ",
    "バルーン": "ボカロ", "syudou": "ボカロ", "chinozo": "ボカロ",
    "john": "ボカロ", "カンザキイオリ": "ボカロ", "ナユタン星人": "ボカロ",
    "きくお": "ボカロ", " giga": "ボカロ", "稲葉曇": "ボカロ",
    "ぬゆり": "ボカロ", "柊キライ": "ボカロ", "ツミキ": "ボカロ",
    "みきとp": "ボカロ", "ハチ": "ボカロ", "キタニタツヤ": "ロック",
    # --- EDM ---
    "alan walker": "EDM", "marshmello": "EDM", "skrillex": "EDM",
    "porter robinson": "EDM", "madeon": "EDM", "k-391": "EDM",
    "livetune": "EDM", "kz": "EDM", "teddyloid": "EDM", "yunomi": "EDM",
    "snail's house": "EDM", "camellia": "EDM",
    # --- ヒップホップ ---
    "creepy nuts": "ヒップホップ", "ちゃんみな": "ヒップホップ",
    "awich": "ヒップホップ", "bad hop": "ヒップホップ", "zorn": "ヒップホップ",
    "kohh": "ヒップホップ", "ksuke": "ヒップホップ",
    # --- K-POP ---
    "bts": "K-POP", "blackpink": "K-POP", "twice": "K-POP",
    "newjeans": "K-POP", "seventeen": "K-POP", "stray kids": "K-POP",
    "le sserafim": "K-POP", "ive": "K-POP", "aespa": "K-POP",
}

# タイトルに直接ジャンル語がある場合の検出（アニソンはフォールバック専用）
GENRE_KEYWORDS = {
    "ボカロ": ["ボカロ", "vocaloid", "初音ミク", "ミク", "重音テト", "feat. ia"],
    "EDM": ["edm", "dubstep", "ダブステップ", "electro", "future bass"],
    "ヒップホップ": ["hiphop", "hip hop", "ヒップホップ", "ラップ", " rap "],
    "K-POP": ["k-pop", "kpop", "케이팝"],
    "バラード": ["ballad", "バラード", "感動", "泣ける", "泣きmad"],
    "ロック": ["rock", "ロック", "メタル", "metal", "パンク"],
}


# ---- ユーティリティ -----------------------------------------------------
def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def yt_search(query, n):
    """yt-dlp の flat 検索で候補メタデータを取得"""
    import subprocess
    cmd = [sys.executable, "-m", "yt_dlp", "--flat-playlist",
           "--dump-json", f"ytsearch{n}:{query}"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=180).stdout
    except Exception as e:
        print(f"  [warn] search failed: {query}: {e}", file=sys.stderr)
        return []
    items = []
    for line in out.splitlines():
        try:
            d = json.loads(line)
        except Exception:
            continue
        items.append({
            "id": d.get("id"),
            "title": (d.get("title") or "").strip(),
            "duration": d.get("duration"),
            "channel": d.get("channel") or d.get("uploader") or "",
        })
    return items


def yt_categories(video_id):
    """1本の YouTube カテゴリ一覧を取得（人物/ゲーム除外の最終ゲート）"""
    import subprocess
    cmd = [sys.executable, "-m", "yt_dlp", "--skip-download",
           "--print", "%(categories)j", f"https://youtu.be/{video_id}"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=60).stdout.strip()
        cats = json.loads(out) if out else []
        return cats if isinstance(cats, list) else []
    except Exception:
        return []


# ---- アニメ名抽出 & 実在確認（AniList） ---------------------------------
def _is_decoration(s):
    low = s.lower()
    return any(re.search(p, low) for p in DECOR_PATTERNS)


def extract_anime_for_single(title):
    """単体MADのアニメ名候補を抽出（優先度順）。
    アニメ名は『』内・【】内(装飾語以外)・区切り(×//等)より前 に来やすい。
    「」内や区切り後は曲名なので除外する。"""
    cands = []
    # 1) 『』内（アニメ名であることが多い）
    for m in re.findall(r"『([^』]+)』", title):
        s = m.strip()
        if 2 <= len(s) <= 30:
            cands.append(s)
    # 2) 【】[]（）内で装飾語でないもの（アニメ名を括弧に入れる投稿者が多い）
    for m in re.findall(r"[【\[（(]([^】\]）)]+)[】\]）)]", title):
        s = m.strip()
        if 2 <= len(s) <= 30 and not _is_decoration(s):
            cands.append(s)
    # 3) 角括弧・「」・『』・装飾を除いた本文の「先頭セグメント」
    body = re.sub(r"[【\[\(（][^】\]\)）]*[】\]\)）]", " ", title)
    body = re.sub(r"「[^」]*」", " ", body)
    body = re.sub(r"『[^』]*』", " ", body)
    for p in DECOR_PATTERNS:
        body = re.sub(p, " ", body, flags=re.IGNORECASE)
    first = re.split(r"[×xX/／｜|〜~]+", body)[0].strip(" 　-–—・,、")
    if 2 <= len(first) <= 30:
        cands.append(first)
    # 重複除去（順序維持）
    seen, uniq = set(), []
    for c in cands:
        if c and c not in seen:
            seen.add(c)
            uniq.append(c)
    return uniq[:4]


def _norm(s):
    """比較用に空白・記号を除去して小文字化"""
    return re.sub(r"[\s　・:：!！?？()（）\[\]【】「」『』\-—–~〜.,、。/／｜|]", "", s or "").lower()


def _score_media(name, media):
    """候補語と AniList 結果の一致品質を採点して (正式名, score) を返す。
    score: 3=完全一致 / 2=候補が正式名に内包 / 1=正式名が候補に内包 / 0=不一致。
    完全一致を優先することで、曲名の部分一致(例:英雄⊂「英雄」解体)が
    アニメ名の完全一致(例:NARUTO)に負けるようにする。"""
    if not media or media.get("isAdult"):
        return None  # アダルト作品は除外
    t = media.get("title") or {}
    fields = [t.get("native"), t.get("romaji"), t.get("english")]
    fields += media.get("synonyms") or []
    nc = _norm(name)
    if len(nc) < 2:
        return None
    canonical = t.get("native") or t.get("romaji") or t.get("english")
    best = 0
    for f in fields:
        nf = _norm(f)
        if not nf:
            continue
        if nc == nf:
            best = max(best, 3)
        elif nc in nf:
            best = max(best, 2)
        elif nf in nc:
            best = max(best, 1)
    return (canonical, best) if best > 0 else None


def _anilist_query(name):
    """AniList へ問い合わせて Media を返す（429 は1回リトライ）。"""
    query = """
    query ($s: String) {
      Media(search: $s, type: ANIME) {
        title { romaji english native }
        synonyms
        isAdult
      }
    }"""
    req = urllib.request.Request(
        "https://graphql.anilist.co",
        data=json.dumps({"query": query, "variables": {"s": name}}).encode(),
        headers={"Content-Type": "application/json",
                 "Accept": "application/json",
                 "User-Agent": "MADTHEM-bot/1.0 (+https://github.com)"},
    )
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return (json.load(r).get("data") or {}).get("Media")
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt == 0:
                time.sleep(3)
                continue
            raise
    return None


def anilist_lookup(name, cache):
    """候補語 -> {'n': 正式名, 's': score} or None（キャッシュ付き）。"""
    if name in cache:
        return cache[name]
    try:
        media = _anilist_query(name)
        scored = _score_media(name, media)
        result = {"n": scored[0], "s": scored[1]} if scored else None
        cache[name] = result
        time.sleep(0.8)  # Anilist レート制限に配慮
        return result
    except Exception:
        return None  # キャッシュに残さず次回再試行


def anilist_verify(name, cache):
    """互換用: 実在アニメなら正式名を返す（スコア不問）。"""
    r = anilist_lookup(name, cache)
    return r["n"] if r else None


def best_anime_match(title, cache):
    """タイトルの全候補を照合し、最も一致品質の高いアニメ正式名を返す。
    同点なら候補語が長い方（=より具体的）を優先。"""
    best = None  # (score, candidate_len, name)
    for cand in extract_anime_for_single(title):
        r = anilist_lookup(cand, cache)
        if not r:
            continue
        key = (r["s"], len(cand))
        if best is None or key > best[0]:
            best = (key, r["n"])
    return best[1] if best else None


# ---- 分類 ---------------------------------------------------------------
# 複数アニメ＝複合MADを示す手がかり（単一アニメ名が無くても複合に振る）
COMPOSITE_HINTS = [
    "複合", "神作画", "シーン集", "作画mad", "作画集", "総集", "まとめ",
    "年末", "nenmatsu", "合作", "mix", "オールスター", "all star", "jump",
]


def classify_type(title):
    low = title.lower()
    if "名言集" in title:
        return "quote"  # 名言集は最優先（単体/複合には絶対しない）
    if any(h in low for h in COMPOSITE_HINTS):
        return "composite"
    return "single"


def _artist_genre(title):
    """タイトル中のアーティスト名からジャンルを推定。
    ascii キーは単語境界で、日本語キーは部分一致で照合（誤検出を抑制）。"""
    low = title.lower()
    for key, genre in ARTIST_GENRE.items():
        k = key.strip().lower()
        if re.search(r"[a-z0-9]", k):  # ascii を含むキー
            if re.search(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])", low):
                return genre
        else:  # 日本語キー
            if k in low:
                return genre
    return None


def detect_genres(title):
    low = title.lower()
    genres = []
    a = _artist_genre(title)
    if a:
        genres.append(a)
    for g, kws in GENRE_KEYWORDS.items():
        if g in genres:
            continue
        if any(k.lower() in low for k in kws):
            genres.append(g)
    if not genres:
        genres = ["アニソン"]  # 不明時の既定（曲特定できれば後で手直し可能）
    return genres[:2]


def is_blocked(item):
    text = (item["title"] + " " + item["channel"]).lower()
    return any(ng.lower() in text for ng in BLOCKLIST)


def fmt_duration(sec):
    sec = int(sec or 0)
    return f"{sec // 60}:{sec % 60:02d}"


# ---- 出力（チェックポイント兼用） ---------------------------------------
def write_outputs(accepted, existing, seen, anime_cache):
    """これまでの採用分をマージして data-auto.js / 各状態ファイルを書き出す。
    ループ途中でも呼べるので、停止されても結果が残る。"""
    merged = (accepted + existing)[:MAX_TOTAL]
    save_json(DATA_AUTO_JS + ".json", merged)
    save_json(SEEN_PATH, sorted(seen))
    save_json(ANIME_CACHE, anime_cache)
    body = json.dumps(merged, ensure_ascii=False, indent=2)
    js = (
        "/* 自動生成ファイル — tools/update_mads.py が定期再生成。\n"
        "   手動編集しないこと（次回更新で上書きされます）。 */\n"
        f"const MAD_AUTO = {body};\n\n"
        "// 手動データ(MAD_DATA)へ自動取得分をマージ\n"
        "if (typeof MAD_DATA !== 'undefined' && Array.isArray(MAD_AUTO)) {\n"
        "  const _ids = new Set(MAD_DATA.map((m) => m.youtubeId));\n"
        "  MAD_AUTO.forEach((m) => { if (!_ids.has(m.youtubeId)) MAD_DATA.push(m); });\n"
        "}\n"
    )
    with open(DATA_AUTO_JS, "w", encoding="utf-8") as f:
        f.write(js)
    return len(merged)


# ---- メイン -------------------------------------------------------------
def main():
    seen = set(load_json(SEEN_PATH, []))
    anime_cache = load_json(ANIME_CACHE, {})
    existing = load_json(DATA_AUTO_JS + ".json", [])  # 既存自動分（生データ）
    existing_ids = {e["youtubeId"] for e in existing}

    # 候補収集
    raw = []
    seen_in_run = set()
    for q in SEARCH_QUERIES:
        print(f"[search] {q}")
        for it in yt_search(q, PER_QUERY):
            if not it["id"] or it["id"] in seen_in_run:
                continue
            seen_in_run.add(it["id"])
            raw.append(it)

    # 全クエリ（人気アニメ別含む）から満遍なく集めるためシャッフル
    random.shuffle(raw)

    accepted = []
    for it in raw:
        vid = it["id"]
        if vid in seen or vid in existing_ids:
            continue  # 重複（過去採用済み）
        dur = it.get("duration") or 0
        if not (MIN_SEC <= dur <= MAX_SEC):
            continue
        if is_blocked(it):
            continue

        title = it["title"]
        ctype = classify_type(title)

        # ---- 厳格な採用ゲート ----
        anime = None
        if ctype == "single":
            # 単体MAD: 実在アニメ名で確認できたものだけ採用（一致品質で最良を選択）
            anime = best_anime_match(title, anime_cache)
            if anime is None:
                continue  # アニメ名が確認できない単体は不採用
        else:
            # 複合MAD/名言集: 単一アニメ名が無いことが多いため
            # YouTubeカテゴリ「映画とアニメ」で人物/ゲームMADを排除
            cats = yt_categories(vid)
            if "Film & Animation" not in cats:
                continue

        entry = {
            "id": f"auto_{vid}",
            "title": title,
            "author": it["channel"],
            "type": ctype,
            "genres": detect_genres(title),
            "youtubeId": vid,
            "duration": fmt_duration(dur),
            "year": time.localtime().tm_year,
            "hot": True,             # 自動取得は新着扱い
            "recommended": False,
            "description": f"YouTubeから自動取得したアニメMAD（{it['channel']}）。",
            "tags": (["自動取得"]
                     + ([anime] if anime else [])
                     + (["名言集"] if ctype == "quote" else [])),
            "auto": True,
        }
        # 単体MADのみ anime フィールドと読み（五十音インデックス用）を付与
        if ctype == "single":
            entry["anime"] = anime
            r = to_reading(anime)
            if r:
                entry["reading"] = r

        accepted.append(entry)
        seen.add(vid)
        print(f"  [+] {ctype:9} | {(anime or '-'):12} | {title[:48]}", flush=True)

        # 途中保存（停止されても結果が残るようにチェックポイント）
        if len(accepted) % 25 == 0:
            write_outputs(accepted, existing, seen, anime_cache)

        # 目標件数に達したら打ち切り（処理を短縮して確実に完了させる）
        if len(accepted) + len(existing) >= MAX_TOTAL:
            print(f"  ... 目標 {MAX_TOTAL} 件に到達。打ち切り。")
            break

    n = write_outputs(accepted, existing, seen, anime_cache)
    print(f"\n完了: 新規 {len(accepted)} 件 / 合計 {n} 件を data-auto.js に書き出し")


if __name__ == "__main__":
    main()
