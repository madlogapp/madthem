/* =========================================================================
 * MADTHEM - アプリロジック
 * ========================================================================= */

/* ---------- ユーティリティ ---------- */

// GA4 イベント送信（gtagが無くても安全）
function track(event, params) {
  try {
    if (typeof gtag === "function") gtag("event", event, params || {});
  } catch (e) {}
}

// タイトルから決定的に色を生成（サムネ用グラデーション）
function gradientFor(str) {
  let h = 0;
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) % 360;
  const h2 = (h + 40) % 360;
  return `linear-gradient(135deg, hsl(${h} 65% 32%), hsl(${h2} 70% 18%))`;
}

// YouTubeサムネURL（IDが有効なら表示、ダメならグラデにフォールバック）
function thumbUrl(id) {
  return `https://i.ytimg.com/vi/${id}/hqdefault.jpg`;
}

const typeLabel = (t) =>
  t === "single" ? "単体" : t === "composite" ? "複合" : "名言集";
// 区分の表示名（名言集は「名言集」、他は「単体MAD」「複合MAD」）
const categoryLabel = (t) => (t === "quote" ? "名言集" : typeLabel(t) + "MAD");

/* ---------- カードDOM生成 ---------- */
function createCard(mad) {
  const card = document.createElement("div");
  card.className = "card";
  card.dataset.id = mad.id;

  const grad = gradientFor(mad.title);

  card.innerHTML = `
    <div class="card__thumb-fallback" style="background:${grad}">${mad.title}</div>
    <div class="card__thumb" style="background-image:url('${thumbUrl(mad.youtubeId)}')"></div>
    <div class="card__grad"></div>
    <div class="card__badges">
      ${mad.hot ? '<span class="badge badge--hot">今注目</span>' : ""}
      ${mad.recommended ? '<span class="badge badge--rec">★おすすめ</span>' : ""}
      <span class="badge badge--type">${typeLabel(mad.type)}</span>
    </div>
    <div class="card__duration">${mad.duration}</div>
    <div class="card__info">
      <div class="card__title">${mad.title}</div>
      <div class="card__sub">${mad.author} ・ ${mad.genres.join(" / ")}</div>
    </div>
  `;

  // サムネ画像が読めなかったら非表示にしてグラデを見せる
  const thumb = card.querySelector(".card__thumb");
  const img = new Image();
  img.onload = () => {
    // YouTubeの「動画なし」プレースホルダ(120x90)を弾く
    if (img.naturalWidth <= 120) thumb.style.display = "none";
  };
  img.onerror = () => (thumb.style.display = "none");
  img.src = thumbUrl(mad.youtubeId);

  card.addEventListener("click", () => openModal(mad));
  return card;
}

/* ---------- 行DOM生成 ---------- */
function createRow(title, items, accentTitle = false) {
  if (!items.length) return null;

  const row = document.createElement("section");
  row.className = "row";

  const h = document.createElement("h2");
  h.className = "row__title";
  h.innerHTML = accentTitle ? `<em>${title}</em>` : title;
  row.appendChild(h);

  const viewport = document.createElement("div");
  viewport.className = "row__viewport";

  const track = document.createElement("div");
  track.className = "row__track";
  items.forEach((mad) => track.appendChild(createCard(mad)));

  const left = document.createElement("button");
  left.className = "row__arrow row__arrow--left";
  left.innerHTML = "‹";
  left.addEventListener("click", () =>
    track.scrollBy({ left: -track.clientWidth * 0.8, behavior: "smooth" })
  );

  const right = document.createElement("button");
  right.className = "row__arrow row__arrow--right";
  right.innerHTML = "›";
  right.addEventListener("click", () =>
    track.scrollBy({ left: track.clientWidth * 0.8, behavior: "smooth" })
  );

  viewport.appendChild(left);
  viewport.appendChild(track);
  viewport.appendChild(right);
  row.appendChild(viewport);
  return row;
}

/* ---------- 行構成の定義 ---------- */

// MADが少なく行として表示しないジャンル（検索は引き続き可能）
const HIDDEN_GENRES = ["クラシック", "シティポップ", "ダブステップ", "メタル"];

// 音楽ジャンル一覧（非表示ジャンルを除外・日本語ソート・「その他」は末尾）
function genresOf(items) {
  return [...new Set(items.flatMap((m) => m.genres))]
    .filter((g) => !HIDDEN_GENRES.includes(g))
    .sort((a, b) => {
    if (a === "その他") return 1;
    if (b === "その他") return -1;
    return a.localeCompare(b, "ja");
  });
}

// ジャンル別の行スペックを生成（suffix 例: "のMAD" / "の複合MAD"）
function genreRowSpecs(items, suffix) {
  return genresOf(items).map((g) => [
    `${g} ${suffix}`,
    items.filter((m) => m.genres.includes(g)),
  ]);
}

/* ---------- 五十音インデックス用ヘルパー ---------- */
// カタカナ→ひらがな
function kataToHira(s) {
  return (s || "").replace(/[ァ-ヶ]/g, (c) =>
    String.fromCharCode(c.charCodeAt(0) - 0x60)
  );
}
// ひらがな → 行（あかさたなはまやらわ）
const GOJUON_ROWS = [
  ["あ", "あいうえおぁぃぅぇぉゔ"],
  ["か", "かきくけこがぎぐげご"],
  ["さ", "さしすせそざじずぜぞ"],
  ["た", "たちつてとだぢづでどっ"],
  ["な", "なにぬねの"],
  ["は", "はひふへほばびぶべぼぱぴぷぺぽ"],
  ["ま", "まみむめも"],
  ["や", "やゆよゃゅょ"],
  ["ら", "らりるれろ"],
  ["わ", "わをんゐゑ"],
];
const HIRA2ROW = {};
GOJUON_ROWS.forEach(([row, chars]) => {
  for (const c of chars) HIRA2ROW[c] = row;
});

// アニメ名 → 並び順情報 {grp, label, sort}（A〜Z → あ〜わ → 他）
function bucketOf(anime, reading) {
  const t = (anime || "").trim();
  if (!t || anime === "その他の単体MAD") return { grp: 3, label: "他", sort: "3" };
  const c0 = t[0];
  if (/[A-Za-z]/.test(c0)) {
    const L = c0.toUpperCase();
    return { grp: 0, label: L, sort: "0" + t.toUpperCase() };
  }
  if (/[0-9]/.test(c0)) return { grp: 2, label: "#", sort: "2" + t };
  const h = reading || kataToHira(t);
  const row = HIRA2ROW[h[0]] || HIRA2ROW[kataToHira(c0)[0]];
  if (row) return { grp: 1, label: row, sort: "1" + (h || t) };
  return { grp: 2, label: "#", sort: "2" + t };
}

// アニメ名 → 読み の対応表（単体MADの reading から）
function buildReadingMap() {
  const m = {};
  MAD_DATA.forEach((x) => {
    if (x.type === "single" && x.anime && x.reading && !m[x.anime]) {
      m[x.anime] = x.reading;
    }
  });
  return m;
}

// フィルタごとに表示する行スペック [title, items, accent?] を返す
function specsFor(filter, pool) {
  if (filter === "single") {
    // 単体MAD: アニメ名ごとの横スクロール（A〜Z → 五十音順 に並べる）
    const singles = pool.filter((m) => m.type === "single");
    const rmap = buildReadingMap();
    const animes = [...new Set(singles.map((m) => m.anime).filter(Boolean))].sort(
      (a, b) => bucketOf(a, rmap[a]).sort.localeCompare(bucketOf(b, rmap[b]).sort, "ja")
    );
    const specs = animes.map((a) => [
      a,
      singles.filter((m) => m.anime === a),
    ]);
    const noAnime = singles.filter((m) => !m.anime);
    if (noAnime.length) specs.push(["その他の単体MAD", noAnime]);
    return specs;
  }

  if (filter === "composite") {
    const comps = pool.filter((m) => m.type === "composite");
    return [["複合MAD", comps, true], ...genreRowSpecs(comps, "の複合MAD")];
  }

  if (filter === "quote") {
    const quotes = pool.filter((m) => m.type === "quote");
    return [["名言集", quotes, true], ...genreRowSpecs(quotes, "の名言集")];
  }

  if (filter === "hot" || filter === "recommended") {
    const sub = pool.filter((m) => (filter === "hot" ? m.hot : m.recommended));
    return [
      ["単体MAD", sub.filter((m) => m.type === "single")],
      ["複合MAD", sub.filter((m) => m.type === "composite")],
      ["名言集", sub.filter((m) => m.type === "quote")],
      ...genreRowSpecs(sub, "のMAD"),
    ];
  }

  // "all"（ホーム）
  return [
    ["今注目のMAD", pool.filter((m) => m.hot), true],
    ["おすすめのMAD", pool.filter((m) => m.recommended), true],
    ["単体MAD", pool.filter((m) => m.type === "single")],
    ["複合MAD", pool.filter((m) => m.type === "composite")],
    ["名言集", pool.filter((m) => m.type === "quote")],
    ...genreRowSpecs(pool, "のMAD"),
  ];
}

function buildRows(specs) {
  const rowsEl = document.getElementById("rows");
  rowsEl.innerHTML = "";

  const rendered = specs
    .map(([title, items, accent]) => createRow(title, items, accent))
    .filter(Boolean);

  if (!rendered.length) {
    rowsEl.innerHTML = '<p class="empty">該当するMADが見つかりませんでした。</p>';
    return;
  }
  rendered.forEach((r) => rowsEl.appendChild(r));
}

/* ---------- ヒーロー ---------- */
function setHero(mad) {
  document.getElementById("heroTitle").textContent = mad.title;
  document.getElementById("heroMeta").textContent =
    `${mad.year} ・ ${categoryLabel(mad.type)} ・ ${mad.genres.join(" / ")} ・ ${mad.duration} ・ ${mad.author}`;
  document.getElementById("heroDesc").textContent = mad.description;

  const bd = document.getElementById("heroBackdrop");
  // サムネを背景に敷き（動画読み込み前のフォールバック）
  bd.style.backgroundImage =
    `url('${thumbUrl(mad.youtubeId)}'), ${gradientFor(mad.title)}`;
  bd.style.backgroundSize = "cover";
  bd.style.backgroundPosition = "center";
  // ミュート・ループの自動再生動画を被せる
  const v = mad.youtubeId;
  bd.innerHTML =
    `<iframe class="hero__video" allow="autoplay; encrypted-media"
       src="https://www.youtube-nocookie.com/embed/${v}?autoplay=1&mute=1&loop=1&playlist=${v}&controls=0&showinfo=0&modestbranding=1&playsinline=1&rel=0&iv_load_policy=3&disablekb=1"></iframe>`;

  document.getElementById("heroPlay").onclick = () => openModal(mad);
  document.getElementById("heroInfo").onclick = () => openModal(mad);
}

/* ---------- 関連MAD（モーダル下部） ---------- */

// 同じジャンルを共有するMADを近い順に。足りなければ同タイプで補完。
function relatedTo(mad) {
  const sameGenre = MAD_DATA.filter(
    (m) => m.id !== mad.id && m.genres.some((g) => mad.genres.includes(g))
  ).sort(
    (a, b) =>
      b.genres.filter((g) => mad.genres.includes(g)).length -
      a.genres.filter((g) => mad.genres.includes(g)).length
  );
  const ids = new Set([mad.id, ...sameGenre.map((m) => m.id)]);
  const sameType = MAD_DATA.filter((m) => !ids.has(m.id) && m.type === mad.type);
  return [...sameGenre, ...sameType].slice(0, 12);
}

// モーダル内用の小さめ関連カード
function createRelatedCard(mad) {
  const card = document.createElement("div");
  card.className = "rcard";
  const grad = gradientFor(mad.title);
  card.innerHTML = `
    <div class="rcard__thumb-fallback" style="background:${grad}">${mad.title}</div>
    <div class="rcard__thumb" style="background-image:url('${thumbUrl(mad.youtubeId)}')"></div>
    <div class="rcard__grad"></div>
    <span class="rcard__duration">${mad.duration}</span>
    <div class="rcard__info">
      <div class="rcard__title">${mad.title}</div>
      <div class="rcard__sub">${mad.genres.join(" / ")}</div>
    </div>
  `;
  const thumb = card.querySelector(".rcard__thumb");
  const img = new Image();
  img.onload = () => { if (img.naturalWidth <= 120) thumb.style.display = "none"; };
  img.onerror = () => (thumb.style.display = "none");
  img.src = thumbUrl(mad.youtubeId);

  // クリックでそのMADにモーダルを切り替え
  card.addEventListener("click", () => openModal(mad));
  return card;
}

function renderRelated(mad) {
  const wrap = document.getElementById("modalRelated");
  const track = document.getElementById("modalRelatedTrack");
  const items = relatedTo(mad);
  track.innerHTML = "";
  if (!items.length) {
    wrap.hidden = true;
    return;
  }
  items.forEach((m) => track.appendChild(createRelatedCard(m)));
  wrap.hidden = false;
}

/* ---------- モーダル ---------- */
const modal = document.getElementById("modal");

function openModal(mad) {
  document.getElementById("modalPlayer").innerHTML =
    `<iframe src="https://www.youtube.com/embed/${mad.youtubeId}?autoplay=1&rel=0"
       allow="autoplay; encrypted-media; fullscreen" allowfullscreen></iframe>`;
  document.getElementById("modalTitle").textContent = mad.title;

  const meta = [
    mad.year,
    categoryLabel(mad.type),
    mad.anime ? `アニメ: ${mad.anime}` : null,
    mad.genres.join(" / "),
    mad.duration,
    `制作: ${mad.author}`,
  ].filter(Boolean);
  document.getElementById("modalMeta").innerHTML = meta
    .map((m) => `<span>${m}</span>`)
    .join('<span class="dot">●</span>');

  document.getElementById("modalDesc").textContent = mad.description;
  document.getElementById("modalTags").innerHTML = mad.tags
    .map((t) => `<span class="chip">#${t}</span>`)
    .join("");

  renderRelated(mad);
  setupShare(mad);
  setVideoLD(mad);
  track("play_mad", {
    mad_title: mad.title,
    anime: mad.anime || "(複合/名言集)",
    mad_type: mad.type,
    video_id: mad.youtubeId,
    genre: (mad.genres || []).join("/"),
  });

  // 共有用にURLを ?mad=<youtubeId> に更新（リロード/共有でこのMADが開く）
  try {
    const u = new URL(location.href);
    u.searchParams.set("mad", mad.youtubeId);
    history.replaceState(null, "", u);
  } catch (e) {}

  modal.classList.add("is-open");
  modal.setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";
  modal.scrollTop = 0; // 関連カードから切替えた時に先頭へ
}

// モーダルで開いたMADの構造化データ（VideoObject + BreadcrumbList）を埋め込み
function setVideoLD(mad) {
  document.getElementById("madJsonLd")?.remove();
  const url = `${location.origin}${location.pathname}?mad=${mad.youtubeId}`;
  const ld = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "VideoObject",
        name: mad.title,
        description: mad.description || `${mad.anime || ""} のMAD/AMV`,
        thumbnailUrl: `https://i.ytimg.com/vi/${mad.youtubeId}/hqdefault.jpg`,
        uploadDate: `${mad.year || new Date().getFullYear()}-01-01`,
        contentUrl: `https://www.youtube.com/watch?v=${mad.youtubeId}`,
        embedUrl: `https://www.youtube.com/embed/${mad.youtubeId}`,
        url: url,
        inLanguage: "ja",
        keywords: ["MAD", "AMV", "アニメMAD", ...(mad.tags || [])].join(", "),
      },
      {
        "@type": "BreadcrumbList",
        itemListElement: [
          { "@type": "ListItem", position: 1, name: "MADTHEM",
            item: "https://madlogapp.github.io/madthem/" },
          ...(mad.anime
            ? [{ "@type": "ListItem", position: 2, name: mad.anime, item: url }]
            : []),
          { "@type": "ListItem",
            position: mad.anime ? 3 : 2,
            name: mad.title, item: url },
        ],
      },
    ],
  };
  const s = document.createElement("script");
  s.type = "application/ld+json";
  s.id = "madJsonLd";
  s.textContent = JSON.stringify(ld);
  document.head.appendChild(s);
}
function clearVideoLD() {
  document.getElementById("madJsonLd")?.remove();
}

// シェアボタン（X / リンクコピー）の設定
function setupShare(mad) {
  const url = `${location.origin}${location.pathname}?mad=${mad.youtubeId}`;
  const text = `「${mad.title}」${mad.anime ? " / " + mad.anime : ""} #MAD #AMV #アニメMAD`;
  document.getElementById("shareX").onclick = () => {
    track("share", { method: "x", mad_title: mad.title, video_id: mad.youtubeId });
    const x = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`;
    window.open(x, "_blank", "noopener,width=600,height=500");
  };
  const copyBtn = document.getElementById("shareCopy");
  copyBtn.onclick = async () => {
    try {
      await navigator.clipboard.writeText(url);
      track("share", { method: "copy", mad_title: mad.title, video_id: mad.youtubeId });
      const orig = copyBtn.textContent;
      copyBtn.textContent = "✓ コピーしました";
      setTimeout(() => (copyBtn.textContent = orig), 1600);
    } catch (e) {
      prompt("このリンクをコピーしてください", url);
    }
  };
}

function closeModal() {
  modal.classList.remove("is-open");
  modal.setAttribute("aria-hidden", "true");
  document.getElementById("modalPlayer").innerHTML = ""; // 再生停止
  document.body.style.overflow = "";
  clearVideoLD();
  // URLから ?mad= を除去
  try {
    const u = new URL(location.href);
    u.searchParams.delete("mad");
    history.replaceState(null, "", u.pathname + u.search);
  } catch (e) {}
}

document.getElementById("modalClose").addEventListener("click", closeModal);
document.getElementById("modalOverlay").addEventListener("click", closeModal);
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeModal();
});

/* ---------- フィルタ & 検索 ---------- */
let currentFilter = "all";
let currentQuery = "";

// 検索: タイトル・職人・ジャンル・タグ・アニメ名を対象
function searchMatch(m, q) {
  return [m.title, m.author, m.anime || "", ...m.genres, ...m.tags]
    .join(" ")
    .toLowerCase()
    .includes(q);
}

function applyView() {
  let pool = MAD_DATA;
  if (currentQuery) {
    const q = currentQuery.toLowerCase();
    pool = pool.filter((m) => searchMatch(m, q));
  }
  buildRows(specsFor(currentFilter, pool));
  renderAnimeIndex(currentFilter);
}

/* ---------- 五十音インデックス（単体MADビューのみ） ---------- */
function renderAnimeIndex(filter) {
  const idx = document.getElementById("azIndex");
  if (!idx) return;
  if (filter !== "single") {
    idx.hidden = true;
    idx.innerHTML = "";
    return;
  }
  const rmap = buildReadingMap();
  const seen = new Set();
  const items = [];
  document.querySelectorAll("#rows .row").forEach((r) => {
    const anime = r.querySelector(".row__title").textContent;
    const b = bucketOf(anime, rmap[anime]);
    if (!seen.has(b.label)) {
      seen.add(b.label);
      const id = "bk-" + encodeURIComponent(b.label);
      r.id = id;
      items.push({ label: b.label, id });
    }
  });
  idx.innerHTML = items
    .map((it) => `<a class="az-index__item" data-target="${it.id}">${it.label}</a>`)
    .join("");
  idx.hidden = false;
  idx.querySelectorAll(".az-index__item").forEach((a) => {
    a.addEventListener("click", (e) => {
      e.preventDefault();
      const el = document.getElementById(a.dataset.target);
      if (el) {
        const y = el.getBoundingClientRect().top + window.scrollY - 84;
        window.scrollTo({ top: y, behavior: "smooth" });
      }
    });
  });
}

// ナビ
const navEl = document.getElementById("nav");
const navToggle = document.getElementById("navToggle");
const navToggleLabel = document.getElementById("navToggleLabel");

function closeNav() {
  navEl.classList.remove("is-open");
  navToggle.setAttribute("aria-expanded", "false");
}

document.querySelectorAll(".nav__link").forEach((link) => {
  link.addEventListener("click", (e) => {
    e.preventDefault();
    document.querySelectorAll(".nav__link").forEach((l) => l.classList.remove("is-active"));
    link.classList.add("is-active");
    currentFilter = link.dataset.filter;
    navToggleLabel.textContent = link.textContent; // ボタン表示を現在地に更新
    closeNav();
    applyView();
    window.scrollTo({ top: window.innerHeight * 0.55, behavior: "smooth" });
  });
});

// モバイル: カテゴリボタンでドロップダウン開閉
navToggle.addEventListener("click", (e) => {
  e.stopPropagation();
  const open = navEl.classList.toggle("is-open");
  navToggle.setAttribute("aria-expanded", open ? "true" : "false");
});
// 外側クリックで閉じる
document.addEventListener("click", (e) => {
  if (!navEl.contains(e.target) && e.target !== navToggle && !navToggle.contains(e.target)) {
    closeNav();
  }
});

// 検索
document.getElementById("searchInput").addEventListener("input", (e) => {
  currentQuery = e.target.value.trim();
  applyView();
});

/* ---------- ヘッダーのスクロール変化 ---------- */
window.addEventListener("scroll", () => {
  document.getElementById("header").classList.toggle("is-scrolled", window.scrollY > 40);
});

/* ---------- 初期化 ---------- */
function init() {
  // ヒーローはおすすめ&注目の中からランダムに1つ
  const featured = MAD_DATA.filter((m) => m.recommended && m.hot);
  const pick = (featured.length ? featured : MAD_DATA)[
    Math.floor(Math.random() * (featured.length ? featured.length : MAD_DATA.length))
  ];
  setHero(pick);
  buildRows(specsFor("all", MAD_DATA));

  // ディープリンク: ?mad=<youtubeId> があれば該当MADを開く
  try {
    const id = new URLSearchParams(location.search).get("mad");
    if (id) {
      const target = MAD_DATA.find((m) => m.youtubeId === id);
      if (target) openModal(target);
    }
  } catch (e) {}
}

init();
