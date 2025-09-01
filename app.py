# app.py
import os
import re
import math
import random
import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from googleapiclient.discovery import build
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px

# ========== CONFIG ==========
st.set_page_config(page_title="DASBOARD SENTIMENT ANALYSIS", layout="wide")
st_autorefresh(interval=60 * 60 * 1000, key="auto_reload")  # 60 menit

# ========== THEME TOGGLE (checkbox switch style) ==========
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True

st.sidebar.markdown("<b style='font-size:14px'>Tampilan</b>", unsafe_allow_html=True)
dark = st.sidebar.checkbox("Mode Gelap", value=st.session_state.dark_mode)
st.session_state.dark_mode = dark

# colors based on theme
if st.session_state.dark_mode:
    BG = "#0e1117"
    FG = "#e6eef6"
    CARD = "#11141a"
    ACCENT = "#3dd0e0"
    MUTED = "#aeb8c6"
    METAL1 = "#2f3438"
    METAL2 = "#5b6065"
    SHADOW = "rgba(0,0,0,0.6)"
else:
    BG = "#f5f7fb"
    FG = "#0f172a"
    CARD = "#ffffff"
    ACCENT = "#0ea5e9"
    MUTED = "#555e6b"
    METAL1 = "#e6eef9"
    METAL2 = "#dbeafe"
    SHADOW = "rgba(0,0,0,0.12)"

# ========== CSS STYLES (cards, menu boxes, metallic) ==========
st.markdown(f"""
    <style>
      .stApp {{ background: {BG}; color: {FG}; }}
      .title-center {{ text-align:center; font-size:26px; font-weight:700; color:{FG}; margin-bottom:6px; }}
      .dashboard-card {{ background: {CARD}; border-radius:12px; padding:12px; box-shadow: 8px 8px 24px {SHADOW}; border:1px solid rgba(255,255,255,0.02); }}
      .small-muted {{ color:{MUTED}; font-size:12px; }}
      .stat-small {{ border-radius:10px; padding:10px; background:transparent; }}
      .menu-card {{ border-radius:10px; padding:10px; margin-bottom:8px; cursor:pointer; text-align:left; }}
      .menu-active {{ box-shadow:6px 6px 18px {SHADOW}; transform: translateY(-2px); }}
      .metallic {{ border-radius:10px; padding:10px; color:{FG}; }}
      .video-card {{ border-radius:10px; padding:12px; margin:6px; }}
      .tiny {{ font-size:12px; color:{MUTED}; }}
      .card-title { font-size:14px; font-weight:700; color:{FG}; margin:0; }
      .card-value { font-size:20px; font-weight:800; color:{ACCENT}; margin:0; }
      .gauge-wrap { display:flex; justify-content:center; align-items:center; }
      /* make sidebar menu look like boxes */
      .sidebar .menu-card { width:100%; display:block; }
    </style>
""", unsafe_allow_html=True)

# ========== Sidebar MENU as Boxes ==========
if "menu" not in st.session_state:
    st.session_state.menu = "All"

st.sidebar.markdown("<div style='padding-bottom:6px'><b>MENU</b></div>", unsafe_allow_html=True)

def set_menu(m):
    st.session_state.menu = m

# styled buttons using markdown and real buttons to change menu
for label in ["All", "Postingan", "Sentimen", "Analisis", "WordCloud", "Insight & Rekomendasi"]:
    active = "menu-active" if st.session_state.menu == label else ""
    if st.sidebar.button(label):
        set_menu(label)
    # add a little separation visually (can't style the button directly heavily reliably)

st.sidebar.markdown("---", unsafe_allow_html=True)

# ========== YouTube setup ==========
YOUTUBE_API_KEY = st.secrets.get("YOUTUBE_API_KEY", os.getenv("YOUTUBE_API_KEY", ""))
if not YOUTUBE_API_KEY:
    st.sidebar.error("YOUTUBE_API_KEY belum diset (Streamlit Secrets).")

VIDEO_URLS = [
    "https://youtu.be/Ugfjq0rDz8g?si=vWNO6nEAj9XB2LOB",
    "https://youtu.be/Lr1OHmBpwjw?si=9Mvu8o69V8Zt40yn",
    "https://youtu.be/5BFIAHBBdao?si=LPNB-8ZtJIk3xZVu",
    "https://youtu.be/UzAgIMvb3c0?si=fH01vTOsKuUb8IoF",
    "https://youtu.be/6tAZ-3FSYr0?si=rKhlEpS3oO7BOOtR",
    "https://youtu.be/M-Qsvh18JNM?si=JJZ2-RKikuexaNw5",
    "https://youtu.be/vSbe5C7BTuM?si=2MPkRB08C3P9Vilt",
    "https://youtu.be/Y7hcBMJDNwk?si=rI0-dsunElb5XMVl",
    "https://youtu.be/iySgErYzRR0?si=05mihs5jDRDXYgSZ",
    "https://youtu.be/gwEt2_yxTmc?si=rfBwVGhePy35YA5D",
    "https://youtu.be/9RCbgFi1idc?si=x7ILIEMAow5geJWS",
    "https://youtu.be/ZgkVHrihbXM?si=k8OittX6RL_gcgrd",
    "https://youtu.be/xvHiRY7skIk?si=nzAUYB71fQpLD2lv"
]
VIDEO_ID_RE = re.compile(r"(?:v=|youtu.be/)([A-Za-z0-9_-]{11})")
def extract_video_id(url: str) -> str:
    m = VIDEO_ID_RE.search(url)
    return m.group(1) if m else url.split("/")[-1].split("?")[0]
VIDEO_IDS = [extract_video_id(u) for u in VIDEO_URLS]

# ========== fetch comments (cached) ==========
@st.cache_data(ttl=3600)
def fetch_comments(video_id: str, max_pages=2):
    if not YOUTUBE_API_KEY:
        return pd.DataFrame(columns=["video_id","comment_id","author","text","publishedAt"])
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    comments = []
    page_token = None
    pages = 0
    while True:
        req = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=100,
            pageToken=page_token,
            order="time",
            textFormat="plainText"
        )
        resp = req.execute()
        for item in resp.get("items", []):
            sn = item["snippet"]["topLevelComment"]["snippet"]
            comments.append({
                "video_id": video_id,
                "comment_id": item["snippet"]["topLevelComment"]["id"],
                "author": sn.get("authorDisplayName", ""),
                "text": sn.get("textDisplay", ""),
                "publishedAt": sn.get("publishedAt", "")
            })
        page_token = resp.get("nextPageToken")
        pages += 1
        if (not page_token) or (pages >= max_pages):
            break
    df = pd.DataFrame(comments)
    if not df.empty:
        df["publishedAt"] = pd.to_datetime(df["publishedAt"], errors="coerce")
    return df

@st.cache_data(ttl=3600)
def fetch_all(video_ids):
    frames = []
    for v in video_ids:
        frames.append(fetch_comments(v, max_pages=2))
    if frames:
        df = pd.concat(frames, ignore_index=True)
        return df.drop_duplicates(subset=["comment_id"]).reset_index(drop=True)
    return pd.DataFrame(columns=["video_id","comment_id","author","text","publishedAt"])

# ========== text clean & sentiment ==========
EMOJI_RE = re.compile(r"[\U00010000-\U0010ffff]", flags=re.UNICODE)
URL_RE = re.compile(r"https?://\S+|www\.\S+")
TAG_RE = re.compile(r"<.*?>")
def clean_text(s):
    if not isinstance(s, str):
        return ""
    s = TAG_RE.sub(" ", s)
    s = URL_RE.sub(" ", s)
    s = EMOJI_RE.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

analyzer = SentimentIntensityAnalyzer()
def label_from_score(t):
    sc = analyzer.polarity_scores(clean_text(t))["compound"]
    if sc >= 0.05: return "positif"
    if sc <= -0.05: return "negatif"
    return "netral"

# ========== load data ==========
with st.spinner("Mengambil dan memproses komentar (cache 60 menit)..."):
    raw = fetch_all(VIDEO_IDS)
if raw.empty:
    df = raw.copy()
else:
    df = raw.copy()
    df["text_clean"] = df["text"].astype(str).apply(clean_text)
    df["label"] = df["text_clean"].apply(label_from_score)

by_video = df.groupby("video_id").agg(total_komentar=("comment_id","count"), unik_user=("author","nunique")).reset_index()
by_label = df["label"].value_counts().reindex(["positif","negatif","netral"]).fillna(0).astype(int)
total_komen = int(df.shape[0])
unique_users = int(df["author"].nunique()) if not df.empty else 0
last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ========== helper visuals ==========
def donut_plotly(counts):
    labels = counts.index.tolist()
    values = counts.values.tolist()
    fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.5,
                           marker=dict(line=dict(color='rgba(255,255,255,0.02)', width=1))))
    fig.update_traces(textinfo="percent+label")
    fig.update_layout(margin=dict(l=10,r=10,t=10,b=10), paper_bgcolor="rgba(0,0,0,0)")
    return fig

def gauge_sentiment(positive, neutral, negative):
    # show percent positive as gauge
    total = positive + neutral + negative
    pct = int((positive / total * 100) if total else 0)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=pct,
        gauge={'axis': {'range': [0, 100]},
               'bar': {'color': ACCENT},
               'steps': [{'range':[0,50],'color':"#ff6b6b"},{'range':[50,80],'color':"#f6c85f"},{'range':[80,100],'color':"#4caf50"}]},
        number={'suffix':'%'},
        title={'text':'Positif (%)'}
    ))
    fig.update_layout(margin=dict(l=10,r=10,t=10,b=10), height=260, paper_bgcolor="rgba(0,0,0,0)")
    return fig

def wordcloud_figure(texts):
    big = " ".join(texts)
    wc = WordCloud(width=800, height=400, background_color=("black" if st.session_state.dark_mode else "white")).generate(big)
    fig, ax = plt.subplots(figsize=(8,4))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    return fig

# simulate forex OHLC-like data for candlestick
def simulate_forex(n=100):
    import pandas as pd
    times = pd.date_range(end=datetime.now(), periods=n, freq='T')
    price = 1.10 + np.cumsum(np.random.normal(0,0.0015,size=n))
    openp = price
    closep = price + np.random.normal(0,0.0008,size=n)
    high = np.maximum(openp, closep) + np.abs(np.random.normal(0,0.0006,size=n))
    low = np.minimum(openp, closep) - np.abs(np.random.normal(0,0.0006,size=n))
    dfc = pd.DataFrame({"time":times,"open":openp,"high":high,"low":low,"close":closep})
    return dfc

# ========== RENDER PAGES ==========
st.markdown(f"<div class='title-center'>DASBOARD SENTIMENT ANALYSIS</div>", unsafe_allow_html=True)
menu = st.session_state.menu

# ---------- ALL (single big card, grid) ----------
if menu == "All":
    st.markdown("<div class='dashboard-card'>", unsafe_allow_html=True)
    # Layout: left column stats & table, right column charts (comment bar above donut)
    left, right = st.columns([1.1, 1])

    # left: 4 small stat boxes stacked 2x2 then small table
    with left:
        # 2x2 grid
        r1c1, r1c2 = st.columns(2)
        with r1c1:
            st.markdown("<div class='stat-small'><p class='tiny'>Total Komentar</p><p class='card-value'>{:,}</p></div>".format(total_komen), unsafe_allow_html=True)
        with r1c2:
            st.markdown("<div class='stat-small'><p class='tiny'>Total User</p><p class='card-value'>{:,}</p></div>".format(unique_users), unsafe_allow_html=True)

        r2c1, r2c2 = st.columns(2)
        with r2c1:
            st.markdown("<div class='stat-small'><p class='tiny'>Update Terakhir</p><p class='tiny'>{}</p></div>".format(last_update), unsafe_allow_html=True)
        with r2c2:
            st.markdown("<div class='stat-small'><p class='tiny'>Video Terpantau</p><p class='card-value'>{}</p></div>".format(len(VIDEO_IDS)), unsafe_allow_html=True)

        st.markdown("<hr>", unsafe_allow_html=True)
        # compact table (latest 8) under stats
        if not df.empty:
            preview = df.sort_values("publishedAt", ascending=False).head(8)[["publishedAt","author","text"]]
            preview["publishedAt"] = preview["publishedAt"].astype(str)
            st.markdown("<div style='max-height:240px; overflow:auto;'>", unsafe_allow_html=True)
            st.table(preview.rename(columns={"publishedAt":"Waktu","author":"Author","text":"Komentar"}))
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("Belum ada komentar.")

    # right: comment bar (top) then donut + gauge stacked
    with right:
        # small bar: komentar per video (compact)
        st.markdown("<div style='margin-bottom:8px'>", unsafe_allow_html=True)
        st.markdown("<div style='background:transparent;border-radius:8px;padding:6px'>", unsafe_allow_html=True)
        if not by_video.empty:
            fig_bar = px.bar(by_video.sort_values("total_komentar", ascending=True), x="total_komentar", y="video_id", orientation='h', text="total_komentar", height=220)
            fig_bar.update_layout(margin=dict(l=10,r=10,t=10,b=10), paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Belum ada data komentar.")
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # donut and gauge side by side
        d1, d2 = st.columns([1,1])
        with d1:
            if not df.empty:
                st.plotly_chart(donut_plotly(by_label), use_container_width=True)
            else:
                st.info("No data")
        with d2:
            st.markdown("<div class='gauge-wrap'>", unsafe_allow_html=True)
            st.plotly_chart(gauge_sentiment(int(by_label.get("positif",0)), int(by_label.get("netral",0)), int(by_label.get("negatif",0))), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ---------- POSTINGAN (summary + 3 rows of video cards) ----------
elif menu == "Postingan":
    st.markdown("<div class='dashboard-card'>", unsafe_allow_html=True)
    st.subheader("📌 Postingan")

    # top center: Total komentar & Total user (side by side, centered)
    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        st.markdown(f"<div style='text-align:center'><p class='tiny'>Total Komentar</p><p class='card-value'>{total_komen:,}</p></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div style='text-align:center'><p class='tiny'>Total User</p><p class='card-value'>{unique_users:,}</p></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div style='text-align:center'><p class='tiny'>Update</p><p class='tiny'>{last_update}</p></div>", unsafe_allow_html=True)

    st.markdown("<hr/>", unsafe_allow_html=True)

    # grid of video cards: we want 3 rows (and distribute cards across rows)
    total_cards = len(VIDEO_IDS)
    # divide into 3 rows as equally as possible
    rows = 3
    per_row = math.ceil(total_cards / rows)
    idx = 0
    for r in range(rows):
        cols = st.columns(per_row)
        for c in cols:
            if idx < total_cards:
                vid = VIDEO_IDS[idx]
                stats = by_video[by_video["video_id"]==vid]
                count = int(stats["total_komentar"].iloc[0]) if not stats.empty else 0
                users = int(stats["unik_user"].iloc[0]) if not stats.empty and "unik_user" in stats.columns else 0
                # metallic gradient inline
                color1 = METAL1
                color2 = METAL2
                st.markdown(f"""
                    <div class='video-card metallic' style='background: linear-gradient(135deg, {color1}, {color2});'>
                        <div style='display:flex;justify-content:space-between;align-items:center'>
                            <div style='font-size:13px' >Video <b>{idx+1}</b></div>
                            <div style='font-size:11px' class='tiny'>Users: {users}</div>
                        </div>
                        <div style='margin-top:8px'>
                            <div class='tiny'>Komentar</div>
                            <div style='font-weight:800;font-size:18px;color:{ACCENT}'>{count:,}</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                idx += 1
            else:
                st.write("")  # empty cell
    st.markdown("</div>", unsafe_allow_html=True)

# ---------- SENTIMEN (table + donut side-by-side equal widths) ----------
elif menu == "Sentimen":
    st.markdown("<div class='dashboard-card'>", unsafe_allow_html=True)
    st.subheader("💬 Sentimen")

    left, right = st.columns([1,1])
    with left:
        if df.empty:
            st.info("Belum ada komentar.")
        else:
            # table compact
            st.dataframe(df[["publishedAt","author","text","label"]].rename(columns={"publishedAt":"Waktu","author":"Author","text":"Komentar","label":"Label"}).sort_values("publishedAt",ascending=False), height=480)
    with right:
        if df.empty:
            st.info("No data")
        else:
            st.plotly_chart(donut_plotly(by_label), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ---------- ANALISIS (Forex candlestick-like + bar per video with labels Video 1/2/3...) ----------
elif menu == "Analisis":
    st.markdown("<div class='dashboard-card'>", unsafe_allow_html=True)
    st.subheader("📈 Analisis & Forex (Simulasi)")

    # simulate forex candles
    forex_df = simulate_forex(120)
    fig = go.Figure(data=[go.Candlestick(x=forex_df['time'],
                    open=forex_df['open'], high=forex_df['high'],
                    low=forex_df['low'], close=forex_df['close'],
                    increasing_line_color='green', decreasing_line_color='red')])
    fig.update_layout(margin=dict(l=10,r=10,t=20,b=10), xaxis_title="Waktu", yaxis_title="Harga", height=380, paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("<hr/>", unsafe_allow_html=True)

    # bar per video: labels as Video 1..n
    if by_video.empty:
        st.info("Belum ada data komentar.")
    else:
        df_bar = by_video.copy()
        df_bar = df_bar.reset_index(drop=True)
        df_bar["label_video"] = ["Video "+str(i+1) for i in range(len(df_bar))]
        fig2 = px.bar(df_bar.sort_values("total_komentar", ascending=False), x="label_video", y="total_komentar", text="total_komentar", title="Komentar per Video")
        fig2.update_layout(margin=dict(l=10,r=10,t=20,b=10), xaxis_title="", yaxis_title="Jumlah Komentar", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ---------- WORDCLOUD (with dominant word + interpretation) ----------
elif menu == "WordCloud":
    st.markdown("<div class='dashboard-card'>", unsafe_allow_html=True)
    st.subheader("☁️ WordCloud & Arti/Konteks")

    if df.empty:
        st.info("Belum ada komentar.")
    else:
        fig_wc = wordcloud_figure(df["text_clean"].tolist())
        st.pyplot(fig_wc)

        # top word
        words = " ".join(df["text_clean"].astype(str)).lower()
        tokens = re.findall(r"[a-zA-Z0-9_]+", words)
        freq = pd.Series(tokens).value_counts()
        if not freq.empty:
            top_word = freq.index[0]
            count_top = int(freq.iloc[0])
            # a safe interpretation (not a dictionary translation)
            interpretation = f"Kata dominan: '{top_word}' (muncul {count_top} kali). Kemungkinan konteks: topik/tema yang sering dibahas dalam komentar (mis. pujian, kritik, fitur, atau nama produk)."
            st.markdown(f"<div class='dashboard-card'><p class='tiny'><b>Kata Dominan</b></p><p style='font-size:18px;color:{ACCENT};font-weight:800'>{top_word}</p><p class='tiny'>{interpretation}</p></div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ---------- INSIGHT & REKOMENDASI (improved sentences) ----------
elif menu == "Insight & Rekomendasi":
    st.markdown("<div class='dashboard-card'>", unsafe_allow_html=True)
    st.subheader("📑 Insight & Rekomendasi")

    total = total_komen
    pos = int(by_label.get("positif",0))
    neg = int(by_label.get("negatif",0))
    net = int(by_label.get("netral",0))
    pos_pct = round((pos/total*100) if total else 0, 1)
    neg_pct = round((neg/total*100) if total else 0, 1)
    net_pct = round((net/total*100) if total else 0, 1)

    # top summary cards
    c1,c2,c3 = st.columns(3)
    with c1:
        st.markdown(f"<div style='padding:12px;border-radius:8px;background:{CARD};box-shadow:6px 6px 18px {SHADOW};'><div class='tiny'>Total Komentar</div><div class='card-value'>{total:,}</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div style='padding:12px;border-radius:8px;background:{CARD};box-shadow:6px 6px 18px {SHADOW};'><div class='tiny'>Positif</div><div style='font-weight:800;color:limegreen;font-size:18px'>{pos} ({pos_pct}%)</div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div style='padding:12px;border-radius:8px;background:{CARD};box-shadow:6px 6px 18px {SHADOW};'><div class='tiny'>Negatif</div><div style='font-weight:800;color:#ff6b6b;font-size:18px'>{neg} ({neg_pct}%)</div></div>", unsafe_allow_html=True)

    st.markdown("<hr/>", unsafe_allow_html=True)

    # richer recommendations (actionable & styled)
    recs = []
    if total == 0:
        recs.append("Tidak ada data komentar — pastikan API key & komentar publik tersedia.")
    else:
        if neg_pct >= 25:
            recs.append("Prioritaskan penanganan komentar negatif: buat tim respons cepat dan 5 template jawaban untuk keluhan umum.")
        else:
            recs.append("Respons cepat (<=24 jam) tetap diterapkan untuk menjaga engagement dan kepercayaan publik.")
        if pos_pct >= 40:
            recs.append("Amplifikasi sentimen positif: pin komentar terbaik, buat highlight testimoni, dan gunakan dalam materi promosi.")
        if net_pct >= 30:
            recs.append("Kurangi komentar netral dengan menambahkan FAQ, informasi jelas pada deskripsi, atau call-to-action agar pengguna memberikan feedback lebih spesifik.")
        if total < 100:
            recs.append("Dorong interaksi dengan CTA di akhir video (pertanyaan khusus) dan adakan sesi Q&A untuk meningkatkan volume komentar.")
        recs.append("Lakukan monitoring mingguan untuk tren kata kunci—gunakan top kata untuk insight topik yang berkembang.")

    st.markdown("<ul>", unsafe_allow_html=True)
    for r in recs:
        st.markdown(f"<li style='margin-bottom:6px'>{r}</li>", unsafe_allow_html=True)
    st.markdown("</ul>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# Footer small spacing
st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
