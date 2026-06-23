#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MADTHEM 静的SEOページ生成
===============================================================================
全MAD（手動 js/data.js + 自動 js/data-auto.js.json）を読み、
アニメごとの実HTMLページ /anime/<slug>.html を生成する。
各ページは独自の title / description / 自己canonical / OGP / 構造化データ(ItemList)
を持ち、SPA本体と違ってクローラーが個別にインデックスできる。

併せて以下も生成:
  - /anime/index.html         アニメ一覧ハブ（五十音）
  - /anime/pages.css          ページ共通CSS
  - sitemap.xml / robots.txt  （実HTMLページを列挙）

依存: json5, pykakasi
===============================================================================
"""
import html
import json
import os
import re

import json5

try:
    import pykakasi
    _KKS = pykakasi.kakasi()
except Exception:
    _KKS = None

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA_JS = os.path.join(ROOT, "js", "data.js")
DATA_AUTO = os.path.join(ROOT, "js", "data-auto.js.json")
ANIME_DIR = os.path.join(ROOT, "anime")
GENRE_DIR = os.path.join(ROOT, "genre")
BASE = "https://madlogapp.github.io/madthem/"

# 音楽ジャンル → URLスラッグ（英語）
GENRE_SLUG = {
    "ロック": "rock", "J-POP": "jpop", "アニソン": "anison", "バラード": "ballad",
    "ボカロ": "vocaloid", "ヒップホップ": "hiphop", "K-POP": "kpop", "EDM": "edm",
    "シティポップ": "citypop", "メタル": "metal", "クラシック": "classic",
    "ダブステップ": "dubstep", "フューチャーファンク": "futurefunk", "その他": "others",
}

GOJUON = [
    ("あ", "あいうえおぁぃぅぇぉゔ"), ("か", "かきくけこがぎぐげご"),
    ("さ", "さしすせそざじずぜぞ"), ("た", "たちつてとだぢづでどっ"),
    ("な", "なにぬねの"), ("は", "はひふへほばびぶべぼぱぴぷぺぽ"),
    ("ま", "まみむめも"), ("や", "やゆよゃゅょ"), ("ら", "らりるれろ"),
    ("わ", "わをんゐゑ"),
]
HIRA2ROW = {c: row for row, chars in GOJUON for c in chars}


def load_catalog():
    items = []
    # 自動分(JSON)
    try:
        with open(DATA_AUTO, encoding="utf-8") as f:
            items += json.load(f)
    except Exception:
        pass
    # 手動分(data.js の const MAD_DATA = [...])
    try:
        src = open(DATA_JS, encoding="utf-8").read()
        s = src.index("[", src.index("const MAD_DATA"))
        e = src.index("];", s)
        items = json5.loads(src[s:e + 1]) + items
    except Exception as ex:
        print(f"[warn] data.js parse skip: {ex}")
    # youtubeId で重複排除（先勝ち＝手動優先）
    seen, uniq = set(), []
    for m in items:
        vid = m.get("youtubeId")
        if vid and vid not in seen:
            seen.add(vid)
            uniq.append(m)
    return uniq


def slugify(name):
    if _KKS:
        romaji = "".join(it["hepburn"] for it in _KKS.convert(name))
    else:
        romaji = name
    slug = re.sub(r"[^a-z0-9]+", "-", romaji.lower()).strip("-")
    return slug or "anime"


def reading_of(name, fallback):
    return fallback or ("".join(it["hira"] for it in _KKS.convert(name)) if _KKS else name)


def row_of(anime, reading):
    c = (reading or anime)[:1]
    if re.match(r"[A-Za-z]", anime[:1]):
        return ("0", anime[0].upper())
    # カタカナ→ひらがな
    h = chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c
    return ("1", HIRA2ROW.get(h, "#"))


def esc(s):
    return html.escape(str(s or ""), quote=True)


def thumb(vid):
    return f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"


PAGE_CSS = """
:root{--bg:#141414;--text:#fff;--dim:#b3b3b3;--accent:#e50914}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:"Helvetica Neue","Hiragino Kaku Gothic ProN","Yu Gothic","Meiryo",sans-serif;line-height:1.6}
a{color:inherit;text-decoration:none}
.wrap{max-width:1200px;margin:0 auto;padding:0 5%}
.top{display:flex;align-items:center;gap:16px;padding:18px 0;border-bottom:1px solid #222;position:sticky;top:0;background:rgba(20,20,20,.95);backdrop-filter:blur(6px);z-index:10}
.logo{font-size:24px;font-weight:900;font-style:italic;background:linear-gradient(92deg,#ff1f3d,#ff5e1a 40%,#ffb800 75%,#ffe14d);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}
.top nav{font-size:14px;color:var(--dim);display:flex;gap:18px}
.top nav a:hover{color:#fff}
h1{font-size:30px;margin:28px 0 6px}
.lead{color:var(--dim);margin-bottom:8px}
.count{color:var(--accent);font-weight:700}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:16px;margin:24px 0 40px}
.card{display:block;background:#181818;border-radius:8px;overflow:hidden;transition:transform .15s,box-shadow .15s}
.card:hover{transform:translateY(-4px);box-shadow:0 8px 22px rgba(0,0,0,.6)}
.card img{width:100%;aspect-ratio:16/9;object-fit:cover;display:block;background:#222}
.card .body{padding:10px 12px}
.card .t{font-weight:700;font-size:14px;line-height:1.35;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.card .s{font-size:12px;color:var(--dim);margin-top:4px}
.badge{display:inline-block;font-size:10px;font-weight:700;padding:1px 7px;border-radius:3px;background:#2a2a2a;color:#ddd;margin-right:4px}
.actions{margin-top:8px;font-size:12px}
.actions a{color:#7ab8ff}
.alpha{display:flex;flex-wrap:wrap;gap:6px;margin:18px 0}
.alpha a{padding:4px 10px;background:#1f1f1f;border-radius:6px;font-weight:700;font-size:13px}
.alpha a:hover{background:var(--accent)}
.sec{font-size:20px;margin:26px 0 10px;border-left:4px solid var(--accent);padding-left:10px}
.animelist{display:flex;flex-wrap:wrap;gap:8px}
.animelist a{padding:7px 12px;background:#1f1f1f;border-radius:8px;font-size:14px}
.animelist a:hover{background:#2a2a2a;color:#fff}
.foot{border-top:1px solid #222;margin-top:30px;padding:24px 0 50px;color:#777;font-size:13px}
.related{margin:10px 0 30px}
.cta{display:inline-block;margin:6px 0 20px;padding:10px 20px;background:#fff;color:#000;border-radius:6px;font-weight:700}
"""


def head(title, desc, canonical, og_image, jsonld):
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script async src="https://www.googletagmanager.com/gtag/js?id=G-5D80J1V5PS"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-5D80J1V5PS');</script>
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="MADTHEM">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{og_image}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{BASE}icons/favicon-64.png">
<link rel="stylesheet" href="{BASE}anime/pages.css">
<script type="application/ld+json">{jsonld}</script>
</head>
<body>
<header class="top"><div class="wrap" style="display:flex;align-items:center;gap:20px;width:100%">
<a class="logo" href="{BASE}">MADTHEM</a>
<nav><a href="{BASE}">ホーム</a><a href="{BASE}anime/">アニメ一覧</a><a href="{BASE}genre/">ジャンル一覧</a></nav>
</div></header>
<main class="wrap">"""


FOOT = f"""</main>
<footer class="foot"><div class="wrap">
<p>MADTHEM — アニメMAD/AMVをジャンル・アニメ別にまとめる非公式まとめサイト</p>
<p>動画の権利は各制作者・権利者に帰属します。</p>
</div></footer>
</body></html>"""


def card_html(m):
    vid = m["youtubeId"]
    genres = " ".join(f'<span class="badge">{esc(g)}</span>' for g in m.get("genres", []))
    return f"""<a class="card" href="{BASE}?mad={vid}">
<img loading="lazy" src="{thumb(vid)}" alt="{esc(m.get('title'))} のMAD">
<div class="body"><div class="t">{esc(m.get('title'))}</div>
<div class="s">{esc(m.get('author',''))}</div>
<div class="s">{genres}</div>
<div class="actions"><span>▶ サイトで見る</span> ・ <a href="https://youtu.be/{vid}" target="_blank" rel="noopener">YouTube</a></div>
</div></a>"""


def build_anime_page(anime, mads, slug, all_anime_slugs):
    n = len(mads)
    creators = "、".join(sorted({m.get("author", "") for m in mads if m.get("author")})[:5])
    title = f"{anime}のMAD・AMVまとめ（{n}本） | MADTHEM"
    desc = (f"アニメ『{anime}』のMAD/AMVを{n}本まとめました。"
            f"{creators} などによる高品質な単体MADをまとめて視聴できます。"
            "MADTHEMはアニメMADをジャンル・アニメ別に毎日更新。")
    canonical = f"{BASE}anime/{slug}.html"
    og_image = thumb(mads[0]["youtubeId"])
    # JSON-LD: ItemList(VideoObject) + BreadcrumbList
    elements = []
    for i, m in enumerate(mads, 1):
        vid = m["youtubeId"]
        elements.append({
            "@type": "ListItem", "position": i,
            "item": {
                "@type": "VideoObject",
                "name": m.get("title"),
                "description": m.get("description") or f"{anime} のMAD/AMV",
                "thumbnailUrl": thumb(vid),
                "uploadDate": f"{m.get('year', 2024)}-01-01",
                "contentUrl": f"https://www.youtube.com/watch?v={vid}",
                "embedUrl": f"https://www.youtube.com/embed/{vid}",
                "url": f"{BASE}?mad={vid}",
            },
        })
    jsonld = json.dumps({
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "ItemList", "name": f"{anime} の MAD/AMV", "numberOfItems": n,
             "itemListElement": elements},
            {"@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "MADTHEM", "item": BASE},
                {"@type": "ListItem", "position": 2, "name": "アニメ一覧",
                 "item": f"{BASE}anime/"},
                {"@type": "ListItem", "position": 3, "name": anime, "item": canonical},
            ]},
        ],
    }, ensure_ascii=False)

    # 関連アニメ（ランダム近傍8件）
    import random
    rel = [(a, s) for a, s in all_anime_slugs if a != anime]
    random.shuffle(rel)
    related = "".join(f'<a href="{s}.html">{esc(a)}</a>' for a, s in rel[:8])

    cards = "\n".join(card_html(m) for m in mads)
    return f"""{head(title, desc, canonical, og_image, jsonld)}
<h1>『{esc(anime)}』のMAD・AMV <span class="count">{n}本</span></h1>
<p class="lead">アニメ『{esc(anime)}』のMAD/AMVをまとめました。サムネイルをクリックすると MADTHEM 上で再生できます。</p>
<a class="cta" href="{BASE}?q={esc(anime)}">MADTHEMで『{esc(anime)}』を検索 →</a>
<div class="grid">
{cards}
</div>
<h2 class="sec">他のアニメのMAD</h2>
<div class="animelist related">{related}</div>
<p><a href="index.html" style="color:#7ab8ff">▶ アニメ一覧をすべて見る</a></p>
{FOOT}"""


def build_index(anime_slugs, total_mads):
    # 五十音/A-Z でグルーピング
    rmap = {}  # anime -> (grp,row)
    groups = {}
    for anime, slug, reading in anime_slugs:
        grp, row = row_of(anime, reading)
        groups.setdefault((grp, row), []).append((anime, slug))
    order = sorted(groups.keys())
    nav = "".join(f'<a href="#g{esc(r)}">{esc(r)}</a>' for _, r in order)
    sections = []
    for key in order:
        _, row = key
        links = "".join(f'<a href="{s}.html">{esc(a)}</a>'
                        for a, s in sorted(groups[key], key=lambda x: x[0]))
        sections.append(f'<h2 class="sec" id="g{esc(row)}">{esc(row)}</h2>'
                        f'<div class="animelist">{links}</div>')
    title = "アニメ一覧（MAD/AMVまとめ） | MADTHEM"
    desc = (f"MADTHEMに収録されたアニメ{len(anime_slugs)}作品のMAD/AMVまとめ一覧。"
            f"全{total_mads}本のアニメMADをアニメ別に探せます。")
    canonical = f"{BASE}anime/"
    jsonld = json.dumps({
        "@context": "https://schema.org", "@type": "CollectionPage",
        "name": title, "url": canonical,
    }, ensure_ascii=False)
    return f"""{head(title, desc, canonical, BASE + 'og.png', jsonld)}
<h1>アニメ一覧 <span class="count">{len(anime_slugs)}作品</span></h1>
<p class="lead">収録アニメをすべて掲載。頭文字から探せます（全{total_mads}本のMAD）。</p>
<div class="alpha">{nav}</div>
{''.join(sections)}
{FOOT}"""


def genre_slug(g):
    return GENRE_SLUG.get(g, slugify(g))


def build_genre_page(genre, mads, all_genre_links):
    n = len(mads)
    slug = genre_slug(genre)
    title = f"{genre}のアニメMAD・AMVまとめ（{n}本） | MADTHEM"
    desc = (f"音楽ジャンル「{genre}」のアニメMAD/AMVを{n}本まとめました。"
            f"{genre}の楽曲に乗せた高品質なMADをまとめて視聴できます。MADTHEMは毎日更新。")
    canonical = f"{BASE}genre/{slug}.html"
    og_image = thumb(mads[0]["youtubeId"])
    elements = []
    for i, m in enumerate(mads[:100], 1):  # 構造化データは上限100件
        vid = m["youtubeId"]
        elements.append({
            "@type": "ListItem", "position": i,
            "item": {"@type": "VideoObject", "name": m.get("title"),
                     "description": m.get("description") or f"{genre} のMAD/AMV",
                     "thumbnailUrl": thumb(vid), "uploadDate": f"{m.get('year',2024)}-01-01",
                     "contentUrl": f"https://www.youtube.com/watch?v={vid}",
                     "embedUrl": f"https://www.youtube.com/embed/{vid}",
                     "url": f"{BASE}?mad={vid}"},
        })
    jsonld = json.dumps({"@context": "https://schema.org", "@graph": [
        {"@type": "ItemList", "name": f"{genre} の アニメMAD/AMV",
         "numberOfItems": n, "itemListElement": elements},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "MADTHEM", "item": BASE},
            {"@type": "ListItem", "position": 2, "name": "ジャンル一覧", "item": f"{BASE}genre/"},
            {"@type": "ListItem", "position": 3, "name": genre, "item": canonical}]},
    ]}, ensure_ascii=False)
    others = "".join(f'<a href="{s}.html">{esc(g)}</a>' for g, s in all_genre_links if g != genre)
    cards = "\n".join(card_html(m) for m in mads)
    return f"""{head(title, desc, canonical, og_image, jsonld)}
<h1>{esc(genre)} のアニメMAD・AMV <span class="count">{n}本</span></h1>
<p class="lead">音楽ジャンル「{esc(genre)}」の楽曲を使ったアニメMAD/AMVをまとめました。サムネイルをクリックすると MADTHEM 上で再生できます。</p>
<div class="grid">
{cards}
</div>
<h2 class="sec">他のジャンル</h2>
<div class="animelist related">{others}</div>
<p><a href="{BASE}anime/" style="color:#7ab8ff">▶ アニメ別の一覧を見る</a></p>
{FOOT}"""


def build_genre_index(genre_links, counts):
    title = "音楽ジャンル一覧（アニメMAD/AMV） | MADTHEM"
    desc = "ロック・J-POP・アニソン・ボカロ・バラードなど、音楽ジャンル別にアニメMAD/AMVを探せます。"
    canonical = f"{BASE}genre/"
    jsonld = json.dumps({"@context": "https://schema.org", "@type": "CollectionPage",
                         "name": title, "url": canonical}, ensure_ascii=False)
    links = "".join(
        f'<a href="{s}.html">{esc(g)} <span class="count">{counts[g]}</span></a>'
        for g, s in genre_links)
    return f"""{head(title, desc, canonical, BASE + 'og.png', jsonld)}
<h1>音楽ジャンル一覧</h1>
<p class="lead">ジャンル別にアニメMAD/AMVを探せます。</p>
<div class="animelist" style="margin-top:20px">{links}</div>
<p style="margin-top:20px"><a href="{BASE}anime/" style="color:#7ab8ff">▶ アニメ別の一覧はこちら</a></p>
{FOOT}"""


def write_sitemap(anime_slugs, genre_slugs=None):
    import time
    today = time.strftime("%Y-%m-%d")
    urls = [(BASE, "1.0", "daily"),
            (f"{BASE}anime/", "0.9", "daily"),
            (f"{BASE}genre/", "0.9", "daily")]
    for _, slug, _ in anime_slugs:
        urls.append((f"{BASE}anime/{slug}.html", "0.8", "weekly"))
    for slug in (genre_slugs or []):
        urls.append((f"{BASE}genre/{slug}.html", "0.8", "weekly"))
    body = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u, pr, ch in urls:
        body.append(f"  <url><loc>{u}</loc><lastmod>{today}</lastmod>"
                    f"<changefreq>{ch}</changefreq><priority>{pr}</priority></url>")
    body.append("</urlset>")
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(body) + "\n")
    with open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {BASE}sitemap.xml\n")


def main():
    catalog = load_catalog()
    singles = [m for m in catalog if m.get("type") == "single" and m.get("anime")]
    by_anime = {}
    for m in singles:
        by_anime.setdefault(m["anime"], []).append(m)

    os.makedirs(ANIME_DIR, exist_ok=True)
    # slug 割当（衝突回避）
    slug_used, anime_slugs = {}, []
    for anime in sorted(by_anime.keys()):
        slug = slugify(anime)
        if slug in slug_used:
            slug_used[slug] += 1
            slug = f"{slug}-{slug_used[slug]}"
        else:
            slug_used[slug] = 0
        reading = reading_of(anime, next((m.get("reading") for m in by_anime[anime] if m.get("reading")), ""))
        anime_slugs.append((anime, slug, reading))

    slug_pairs = [(a, s) for a, s, _ in anime_slugs]
    for anime, slug, _ in anime_slugs:
        page = build_anime_page(anime, by_anime[anime], slug, slug_pairs)
        with open(os.path.join(ANIME_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
            f.write(page)

    with open(os.path.join(ANIME_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(build_index(anime_slugs, len(singles)))
    with open(os.path.join(ANIME_DIR, "pages.css"), "w", encoding="utf-8") as f:
        f.write(PAGE_CSS)

    # --- ジャンル別ページ（全タイプのMADを対象） ---
    os.makedirs(GENRE_DIR, exist_ok=True)
    by_genre = {}
    for m in catalog:
        for g in m.get("genres", []):
            by_genre.setdefault(g, []).append(m)
    # 表示順: 件数の多い順
    genres_sorted = sorted(by_genre.keys(), key=lambda g: -len(by_genre[g]))
    genre_links = [(g, genre_slug(g)) for g in genres_sorted]
    counts = {g: len(by_genre[g]) for g in by_genre}
    for g in genres_sorted:
        page = build_genre_page(g, by_genre[g], genre_links)
        with open(os.path.join(GENRE_DIR, f"{genre_slug(g)}.html"), "w", encoding="utf-8") as f:
            f.write(page)
    with open(os.path.join(GENRE_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(build_genre_index(genre_links, counts))

    write_sitemap(anime_slugs, [genre_slug(g) for g in genres_sorted])

    print(f"生成完了: アニメ {len(anime_slugs)} + ジャンル {len(genres_sorted)} ページ + 各一覧 + sitemap "
          f"(総MAD {len(catalog)} / 単体 {len(singles)})")


if __name__ == "__main__":
    main()
