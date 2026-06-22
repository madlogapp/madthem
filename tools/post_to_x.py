#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MADTHEM X(Twitter) 自動投稿スクリプト
===============================================================================
未投稿のMADを1本選び、YouTubeサムネ画像付きでXに投稿する。
GitHub Actions から 1日3回 実行する想定。

必要な環境変数（GitHub Secrets に設定）:
  X_API_KEY            (API Key / Consumer Key)
  X_API_SECRET         (API Key Secret / Consumer Secret)
  X_ACCESS_TOKEN       (Access Token)
  X_ACCESS_SECRET      (Access Token Secret)

依存: tweepy （pip install tweepy）

動作確認用: POST_DRYRUN=1 を付けると投稿せず内容だけ表示。
===============================================================================
"""
import json
import os
import random
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CATALOG = os.path.join(ROOT, "js", "data-auto.js.json")  # 自動取得分（1000件）
POSTED_PATH = os.path.join(HERE, "posted_ids.json")
SITE_URL = "https://madlogapp.github.io/madthem/"
POSTS_PER_RUN = int(os.environ.get("POSTS_PER_RUN", "1"))


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def thumb_path(video_id):
    """YouTubeサムネをダウンロードして一時ファイルパスを返す。"""
    for q in ("maxresdefault", "hqdefault"):
        url = f"https://i.ytimg.com/vi/{video_id}/{q}.jpg"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            data = urllib.request.urlopen(req, timeout=20).read()
            if len(data) > 2000:  # プレースホルダ画像を除外
                p = f"/tmp/madthem_{video_id}.jpg"
                with open(p, "wb") as f:
                    f.write(data)
                return p
        except Exception:
            continue
    return None


def hashtagify(name):
    """アニメ名を簡易ハッシュタグ化（記号除去）。"""
    if not name:
        return ""
    tag = "".join(ch for ch in name if ch.isalnum())
    return f" #{tag}" if 1 < len(tag) <= 20 else ""


def compose(mad):
    title = mad.get("title", "")
    anime = mad.get("anime", "")
    url = f"{SITE_URL}?mad={mad['youtubeId']}"
    head = f"🎬 {title}"
    if anime:
        head += f"\n📺 {anime}"
    body = (
        f"{head}\n\n"
        f"アニメMADまとめ「MADTHEM」で見る👇\n{url}\n\n"
        f"#MAD #AMV #アニメMAD{hashtagify(anime)}"
    )
    return body


def pick(catalog, posted):
    pool = [m for m in catalog if m.get("youtubeId") and m["youtubeId"] not in posted]
    if not pool:                       # 全部投稿し終えたら一周してリセット
        pool = [m for m in catalog if m.get("youtubeId")]
        posted.clear()
    random.shuffle(pool)
    return pool


def main():
    catalog = load_json(CATALOG, [])
    if not catalog:
        print("カタログが空です。終了。")
        return
    posted = set(load_json(POSTED_PATH, []))
    dry = os.environ.get("POST_DRYRUN") == "1"

    client = api_v1 = None
    if not dry:
        ck = os.environ.get("X_API_KEY", "")
        cs = os.environ.get("X_API_SECRET", "")
        at = os.environ.get("X_ACCESS_TOKEN", "")
        ats = os.environ.get("X_ACCESS_SECRET", "")
        if not all([ck, cs, at, ats]):
            print("X APIキー(Secrets)が未設定のためスキップします。"
                  "（X_API_KEY/X_API_SECRET/X_ACCESS_TOKEN/X_ACCESS_SECRET）")
            return
        import tweepy
        client = tweepy.Client(
            consumer_key=ck, consumer_secret=cs,
            access_token=at, access_token_secret=ats,
        )
        auth = tweepy.OAuth1UserHandler(ck, cs, at, ats)
        api_v1 = tweepy.API(auth)  # メディアアップロード用(v1.1)

    candidates = pick(catalog, posted)
    done = 0
    for mad in candidates:
        if done >= POSTS_PER_RUN:
            break
        text = compose(mad)
        print(f"--- 投稿候補 ---\n{text}\n")
        if dry:
            done += 1
            posted.add(mad["youtubeId"])
            continue
        try:
            media_ids = None
            # 画像アップロードは有料枠が必要(無料枠は402)。POST_WITH_MEDIA=1で有効化。
            if os.environ.get("POST_WITH_MEDIA") == "1":
                tp = thumb_path(mad["youtubeId"])
                if tp:
                    media = api_v1.media_upload(tp)
                    media_ids = [media.media_id]
            client.create_tweet(text=text, media_ids=media_ids)
            posted.add(mad["youtubeId"])
            done += 1
            print("→ 投稿成功")
        except Exception as e:
            msg = str(e)
            print(f"→ 投稿失敗: {msg}", file=sys.stderr)
            # 恒久的エラー（権限/課金/レート）は即打ち切り（無駄打ち防止）
            if any(c in msg for c in ("401", "402", "403", "429")):
                break

    with open(POSTED_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted(posted), f, ensure_ascii=False, indent=2)
    print(f"\n完了: {done} 件投稿 / 投稿済み累計 {len(posted)} 件")


if __name__ == "__main__":
    main()
