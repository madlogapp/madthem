/* =========================================================================
 * MADTHEM - 手動キュレーションMADデータ（MAD_DATA）
 * -------------------------------------------------------------------------
 * 各MADの定義:
 *   id          : 一意ID
 *   title       : 作品タイトル
 *   author      : 制作者（MAD職人）
 *   type        : "single"（単体MAD） | "composite"（複合MAD） | "quote"（名言集）
 *                 分類ルール:
 *                   - タイトルに「名言集」→ "quote"（最優先。単体/複合には絶対しない）
 *                   - タイトルに「複合MAD」 or 複数アニメを含む → "composite"
 *                   - 単一アニメ名を含む → "single"（anime に実在確認済みのアニメ名）
 *   anime       : 単体MADの題材アニメ名（実在確認済みのもののみ。検索対象）
 *   genres      : 音楽ジャンルの配列
 *   youtubeId   : YouTube動画ID（モーダル再生・サムネに使用）
 *   duration    : 尺
 *   year        : 投稿年
 *   hot         : 今注目フラグ
 *   recommended : 管理人おすすめフラグ
 *   description : 説明文
 *   tags        : 使用アニメ・楽曲などのタグ
 *
 * ※ ここは手動キュレーション分。日次の自動取得分は js/data-auto.js に入り、
 *   読み込み時に MAD_DATA へマージされる。
 * ========================================================================= */

const MAD_DATA = [
  /* ===== 実在MAD（提供分・タイトルから区分とジャンルを判定） ===== */
  {
    id: "m022",
    title: "シルエット",
    author: "にわか侍",
    type: "composite",
    genres: ["ロック"],
    youtubeId: "BqrpXCQbS2Y",
    duration: "2:43",
    year: 2023,
    hot: true,
    recommended: true,
    description:
      "KANA-BOON「シルエット」に乗せた大型複合MAD。疾走感あるロックに多数の名場面を畳み掛ける王道構成。",
    tags: ["複合MAD", "シルエット", "KANA-BOON"],
  },
  {
    id: "m023",
    title: "かくれんぼ",
    author: "CO-KEY",
    type: "composite",
    genres: ["ロック"],
    youtubeId: "bV9zkEav4-g",
    duration: "5:16",
    year: 2022,
    hot: false,
    recommended: true,
    description:
      "ヨルシカ「かくれんぼ」を用いた複合MAD。エモーショナルなオルタナロックに切ない場面を重ねた構成が秀逸。",
    tags: ["複合MAD", "かくれんぼ", "ヨルシカ"],
  },
  {
    id: "m024",
    title: "一騎当千",
    author: "ねむねこ",
    type: "single",
    anime: "呪術廻戦",
    genres: ["ロック", "アニソン"],
    youtubeId: "Ze5p7u1hZZo",
    duration: "3:28",
    year: 2024,
    hot: true,
    recommended: true,
    description:
      "Aimer「一騎当千」に乗せた『呪術廻戦』単体MAD。激しいロックサウンドとバトル作画のシンクロが圧巻。",
    tags: ["呪術廻戦", "一騎当千", "Aimer", "バトル"],
  },
  {
    id: "m025",
    title: "lulu.",
    author: "ねむねこ",
    type: "single",
    anime: "葬送のフリーレン",
    genres: ["J-POP", "アニソン"],
    youtubeId: "sAJuN0AIvO8",
    duration: "4:36",
    year: 2026,
    hot: true,
    recommended: true,
    description:
      "Mrs. GREEN APPLE「lulu.」（フリーレン第2期OP）に乗せた『葬送のフリーレン』単体MAD。壮大なメロに旅の温度が滲む。",
    tags: ["葬送のフリーレン", "lulu.", "Mrs. GREEN APPLE"],
  },
  {
    id: "m026",
    title: "DAYBREAK FRONTLINE",
    author: "にわか侍",
    type: "composite",
    genres: ["ボカロ"],
    youtubeId: "owBAOfX8_9g",
    duration: "3:33",
    year: 2023,
    hot: true,
    recommended: false,
    description:
      "Orangestar「DAYBREAK FRONTLINE」を用いた複合MAD。疾走するボカロロックに多彩な作品を乗せた爽快な一本。",
    tags: ["複合MAD", "DAYBREAK FRONTLINE", "Orangestar"],
  },
  {
    id: "m027",
    title: "NENMATSU MAD 2025",
    author: "にわか侍",
    type: "composite",
    genres: ["その他"],
    youtubeId: "JfOCDFXfkhg",
    duration: "9:16",
    year: 2025,
    hot: true,
    recommended: true,
    description:
      "2025年のアニメを総ざらいした年末大型MAD。複数アニメを一本に編んだお祭り構成のため複合MADに分類。",
    tags: ["複合MAD", "年末MAD", "2025", "複数アニメ"],
  },
  {
    id: "m028",
    title: "Blue Archive - AIZO",
    author: "青フェネック",
    type: "single",
    anime: "ブルーアーカイブ",
    genres: ["ロック", "アニソン"],
    youtubeId: "QuqOMH1UQH8",
    duration: "3:35",
    year: 2026,
    hot: false,
    recommended: true,
    description:
      "『ブルーアーカイブ』映像に King Gnu「AIZO」（呪術廻戦 第3期OP）を乗せた単体MAD。和楽器とドラムンベースを織り込んだミクスチャーロックが映像を引き締める。",
    tags: ["ブルーアーカイブ", "ブルアカ", "AIZO", "King Gnu"],
  },

  /* ===== 提供分（第2弾・RADWIMPS / Hump Back 系の単体MAD） ===== */
  {
    id: "m031",
    title: "棒人間",
    author: "'M'ADWIMPS",
    type: "single",
    anime: "ぼっち・ざ・ろっく！",
    genres: ["ロック"],
    youtubeId: "zCdmxEOL9Ak",
    duration: "4:43",
    year: 2024,
    hot: true,
    recommended: true,
    description:
      "RADWIMPS「棒人間」に乗せた『ぼっち・ざ・ろっく！』単体MAD。歌詞と映像が寄り添う4K歌詞付き構成。",
    tags: ["ぼっち・ざ・ろっく！", "ぼっちざろっく", "棒人間", "RADWIMPS"],
  },
  {
    id: "m032",
    title: "ハイパーベンチレイション",
    author: "だいすけゲームズ",
    type: "single",
    anime: "チェンソーマン",
    genres: ["ロック"],
    youtubeId: "R1eDI-XRl_Y",
    duration: "3:39",
    year: 2023,
    hot: true,
    recommended: true,
    description:
      "RADWIMPS「ハイパーベンチレイション」に乗せた『チェンソーマン』単体MAD。疾走するロックと過激な作画が噛み合う。",
    tags: ["チェンソーマン", "ハイパーベンチレイション", "RADWIMPS"],
  },
  {
    id: "m033",
    title: "僕は人間じゃないんです。",
    author: "とある人",
    type: "single",
    anime: "聲の形",
    genres: ["ロック"],
    youtubeId: "jUT9ijxBAm0",
    duration: "4:45",
    year: 2023,
    hot: false,
    recommended: true,
    description:
      "RADWIMPS「棒人間」（歌い出し『僕は人間じゃないんです』）に乗せた『聲の形』単体MAD。贖罪と再生の物語が沁みる。",
    tags: ["聲の形", "棒人間", "RADWIMPS", "感動"],
  },
  {
    id: "m034",
    title: "拝啓、少年よ",
    author: "シノギチャンネル",
    type: "single",
    anime: "ぼっち・ざ・ろっく！",
    genres: ["ロック"],
    youtubeId: "FUPwLCj-o6I",
    duration: "3:14",
    year: 2024,
    hot: false,
    recommended: true,
    description:
      "Hump Back「拝啓、少年よ」に乗せた『ぼっち・ざ・ろっく!』単体MAD。セリフ入りで青春の熱量がそのまま伝わる。",
    tags: ["ぼっち・ざ・ろっく！", "ぼっちざろっく", "拝啓少年よ", "Hump Back"],
  },
];
