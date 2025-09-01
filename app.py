# app.py
import os
import re
import time
import math
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from googleapiclient.discovery import build
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go

# ============ CONFIG ============
st.set_page_config(page_title="DASHBOARD SENTIMENT ANALYSIS", layout="wide")
st_autorefresh(interval=60 * 60 * 1000, key="auto_reload")  # auto refresh tiap 60 menit

# ============ THEME (dark/light) ============
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "Gelap"

mode_choice = st.sidebar.selectbox("🌗 Mode Tampilan", ["Gelap", "Terang"], index=0 if st.session_state.theme_mode == "Gelap" else 1)
st.session_state.theme_mode = mode_choice

# CSS theme & general styles
if st.session_state.theme_mode == "Gelap":
    BG = "#0e1117"
    FG = "#e6eef6"
    CARD = "#11141a"
    ACCENT = "#3dd0e0"
    SHADOW = "rgba(0,0,0,0.6)"
    small_text_color = "#cfd8e3"
else:
    BG = "#f5f7fb"
    FG = "#0f172a"
    CARD = "#ffffff"
    ACCENT = "#0ea5e9"
    SHADOW = "rgba(0,0,0,0.12)"
    small_text_color = "#334155"

st.markdown(
    f"""
    <style>
      .stApp {{ background: {BG}; color: {FG}; }}
      .big-title {{ text-align:center; font-size:28px; font-weight:700; color:{FG}; margin-bottom:6px; }}
      .dashboard-card {{
          background: {CARD};
          border-radius: 14px;
          padding: 14px;
          box-shadow: 10px 10px 24px {SHADOW}, -6px -6px 18px rgba(255,255,255,0.02);
          border: 1px solid rgba(255,255,255,0.02);
      }}
      .small-muted {{ color: {small_text_color}; font-size:12px; }}
      .stat-small h4 {{ margin:6px 0 2px; font-size:13px; color:{FG}; }}
      .stat-small p {{ margin:0; font-size:18px; font-weight:700; color:{ACCENT}; }}
      /* sidebar menu boxes */
      .menu-button {{
        width:100%;
        padding:10px;
        border-radius:10px;
        margin-bottom:8px;
        text-align:left;
        cursor:pointer;
      }}
      .menu-active{{ box-shadow: 6px 6px 18px {SHADOW}; transform: translateY(-2px); }}
      .metallic {{
        background: linear-gradient(135deg, rgba(255,255,255,0.02), rgba(255,255,255,0.06));
        border: 1px solid rgba(255,255,255,0.04);
      }}
      .video-card {{
        border-radius:12px;
        padding:10px;
        text-align:left;
      }}
      .tiny {{ font-size:12px; color:{small_text_color}; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ============ MENU BUTTONS (sidebar as boxes) ============
if "menu" not in st.session_state:
    st.session_state.menu = "All"

def menu_button(label):
    clicked = st.sidebar.button(label)
    if clicked:
        st.session_state.menu = label

# Custom styled menu with small description (we use buttons to set menu)
st.sidebar.markdown("<div style='padding:6px 4px'><b>MENU</b></div>", unsafe_allow_html=True)
menu_button("All")
menu_button("Postingan")
menu_button("Sentimen")
menu_button("Analisis")
menu_button("WordCloud")
menu_button("Insight & Rekomendasi")
st.sidebar.markdown("---", unsafe_allow_html=True)

# ============ YOUTUBE CONFIG ============
YOUTUBE_API_KEY = st.secrets.get("YOUTUBE_API_KEY", os.getenv("YOUTUBE_API_KEY", ""))
if not YOUTUBE_API_KEY:
    st.sidebar.error("YOUTUBE_API_KEY belum diset di Secrets!")

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
    "https://youtu.be/xvHiRY7skIk?si=nzAUYB71fQpLD2lv",
]

VIDEO_ID_RE = re.compile(r"(?:v=|youtu.be/)([A-Za-z0-9_-]{11})")
def extract_video_id(url: str) -> str:
    m = VIDEO_ID_RE.search(url)
    return m.group(1) if m else url.split("/")[-1].split("?")[0]

VIDEO_IDS = [extract_video_id(u) for u in VIDEO_URLS]

@st.cache_data(ttl=3600)
def fetch_comments_for_video(video_id: str, max_pages: int = 5) -> pd.DataFrame:
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
def fetch_all_comments(video_ids):
    frames = []
    for vid in video_ids:
        frames.append(fetch_comments_for_video(vid, max_pages=3))
    if frames:
        df = pd.concat(frames, ignore_index=True)
        return df.drop_duplicates(subset=["comment_id"]).reset_index(drop=True)
    return pd.DataFrame(columns=["video_id","comment_id","author","text","publishedAt"])

# ============ TEXT CLEAN + SENTIMENT ============
EMOJI_RE = re.compile(r"[\U00010000-\U0010ffff]", flags=re.UNICODE)
URL_RE = re.compile(r"https?://\S+|www\.\S+")
TAG_RE = re.compile(r"<.*?>")

def clean_text(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = TAG_RE.sub(" ", s)
    s = URL_RE.sub(" ", s)
    s = EMOJI_RE.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

analyzer = SentimentIntensityAnalyzer()
def score_label(text):
    sc = analyzer.polarity_scores(clean_text(text))["compound"]
    if sc >= 0.05: return "positif"
    if sc <= -0.05: return "negatif"
    return "netral"

# ============ LOAD DATA (fetch) ============
with st.spinner("Mengambil komentar... (cache 60 menit)"):
    raw_df = fetch_all_comments(VIDEO_IDS)
if raw_df.empty:
    df = raw_df.copy()
else:
    df = raw_df.copy()
    df["text_clean"] = df["text"].astype(str).apply(clean_text)
    df["label"] = df["text_clean"].apply(score_label)

# Aggregations
by_video = df.groupby("video_id").agg(total_komentar=("comment_id","count"), unik_user=("author","nunique")).reset_index()
by_label = df["label"].value_counts().reindex(["positif","negatif","netral"]).fillna(0).astype(int)

total_komen = int(df.shape[0])
unique_user = int(df["author"].nunique()) if not df.empty else 0
last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ============ HELPERS VISUAL ============
def build_wordcloud_figure(texts):
    big_text = " ".join(texts)
    wc = WordCloud(width=800, height=400, background_color="black" if st.session_state.theme_mode=="Gelap" else "white").generate(big_text)
    fig, ax = plt.subplots(figsize=(10,4))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    return fig

def donut_fig_from_counts(counts):
    labels = counts.index.tolist()
    values = counts.values.tolist()
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.5)])
    fig.update_traces(textinfo="percent+label")
    fig.update_layout(margin=dict(l=10,r=10,t=20,b=10), paper_bgcolor="rgba(0,0,0,0)")
    return fig

def bar_per_video_fig(dfv):
    if dfv.empty:
        return go.Figure()
    fig = px.bar(dfv, x="video_id", y="total_komentar", text="total_komentar")
    fig.update_layout(margin=dict(l=10,r=10,t=20,b=10), paper_bgcolor="rgba(0,0,0,0)")
    return fig

# ============ FOREX 3D ANIMATION (simulated) ============
def simulate_forex_series(n_steps=60):
    # simulate 1-minute timeseries for 60 points
    t = np.arange(n_steps)
    base = 1.10 + 0.02 * np.sin(t / 5.0)  # base oscillation
    noise = np.cumsum(np.random.normal(scale=0.002, size=n_steps))
    series = base + noise
    return t, series

def forex_3d_animation():
    t, series = simulate_forex_series(80)
    # create frames for animation
    frames = []
    for i in range(1, len(t)):
        frames.append(go.Frame(data=[go.Scatter3d(
            x=t[:i], y=series[:i], z=np.zeros(i),
            mode='lines+markers',
            line=dict(width=6, color='gold'),
            marker=dict(size=3)
        )], name=str(i)))
    fig = go.Figure(
        data=[go.Scatter3d(x=t[:2], y=series[:2], z=np.zeros(2), mode='lines+markers', line=dict(width=6, color='gold'))],
        frames=frames
    )
    fig.update_layout(scene=dict(xaxis_title='Time', yaxis_title='Price', zaxis_title=''), margin=dict(l=10,r=10,t=20,b=10))
    # add play button
    fig.update_layout(updatemenus=[dict(type='buttons', showactive=False,
                                       y=1, x=1.15,
                                       buttons=[dict(label='Play',
                                                     method='animate',
                                                     args=[None, {"frame": {"duration": 80, "redraw": True}, "fromcurrent": True}])])])
    return fig

# ============ PAGE RENDERING ============
st.markdown(f"<div class='big-title'>DASBOARD SENTIMENT ANALYSIS</div>", unsafe_allow_html=True)

menu = st.session_state.menu

# ---------- ALL: single big card with grid ----------
if menu == "All":
    st.markdown("<div class='dashboard-card'>", unsafe_allow_html=True)
    st.markdown(f"<div style='display:flex;gap:14px;align-items:flex-start;'>", unsafe_allow_html=True)

    # Left column: stats grid (4 boxes), small table
    left_col, right_col = st.columns([1.2, 1])
    with left_col:
        # top grid 2x2
        r1c1, r1c2 = st.columns(2)
        with r1c1:
            st.markdown("<div class='stat-small'>", unsafe_allow_html=True)
            st.markdown(f"<h4 class='tiny'>Total Komentar</h4><p class='tiny' style='font-size:20px;color:{ACCENT};font-weight:800'>{total_komen:,}</p>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with r1c2:
            st.markdown("<div class='stat-small'>", unsafe_allow_html=True)
            st.markdown(f"<h4 class='tiny'>Total User</h4><p class='tiny' style='font-size:20px;color:{ACCENT};font-weight:800'>{unique_user:,}</p>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        r2c1, r2c2 = st.columns(2)
        with r2c1:
            st.markdown("<div class='stat-small'>", unsafe_allow_html=True)
            st.markdown(f"<h4 class='tiny'>Update Terakhir</h4><p class='tiny' style='font-size:14px;color:{small_text_color}'>{last_update}</p>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with r2c2:
            st.markdown("<div class='stat-small'>", unsafe_allow_html=True)
            st.markdown(f"<h4 class='tiny'>Video Terpantau</h4><p class='tiny' style='font-size:16px;color:{ACCENT};font-weight:700'>{len(VIDEO_IDS)}</p>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<hr/>", unsafe_allow_html=True)
        # compact comments table (latest 8)
        if not df.empty:
            st.markdown("<div style='max-height:240px;overflow:auto;'>", unsafe_allow_html=True)
            preview = df.sort_values("publishedAt", ascending=False).head(8)[["publishedAt","author","text"]]
            preview["publishedAt"] = preview["publishedAt"].astype(str)
            st.table(preview.rename(columns={"publishedAt":"Waktu","author":"Author","text":"Komentar"}))
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("Belum ada komentar untuk ditampilkan.")

    # Right column: charts stack
    with right_col:
        # Donut + bar inside single stacked layout (fit in one big box)
        st.markdown("<div style='display:flex;flex-direction:column;gap:10px'>", unsafe_allow_html=True)
        with st.container():
            st.markdown("<div style='display:flex;gap:10px'>", unsafe_allow_html=True)
            d1, d2 = st.columns([1,1])
            with d1:
                st.markdown("<div class='dashboard-card'>", unsafe_allow_html=True)
                if not df.empty:
                    st.plotly_chart(donut_fig_from_counts(by_label), use_container_width=True)
                else:
                    st.info("No data")
                st.markdown("</div>", unsafe_allow_html=True)
            with d2:
                st.markdown("<div class='dashboard-card'>", unsafe_allow_html=True)
                st.plotly_chart(bar_per_video_fig(by_video), use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div style='margin-top:8px'>", unsafe_allow_html=True)
        # Wordcloud + insight
        wcol, icol = st.columns([1, 1])
        with wcol:
            st.markdown("<div class='dashboard-card'>", unsafe_allow_html=True)
            if not df.empty:
                fig_wc = build_wordcloud_figure(df["text_clean"].tolist())
                st.pyplot(fig_wc)
            else:
                st.info("Belum ada data wordcloud")
            st.markdown("</div>", unsafe_allow_html=True)
        with icol:
            st.markdown("<div class='dashboard-card'>", unsafe_allow_html=True)
            # nice insight box
            total = total_komen
            pos = int(by_label.get("positif", 0))
            neg = int(by_label.get("negatif", 0))
            net = int(by_label.get("netral", 0))
            st.markdown(f"<h4 style='margin:0'>Insight Singkat</h4>", unsafe_allow_html=True)
            st.markdown(f"<p class='tiny'>Total komentar: <b>{total:,}</b></p>", unsafe_allow_html=True)
            st.markdown(f"<p class='tiny'>Positif: <b style='color:limegreen'>{pos}</b>  Negatif: <b style='color:#ff6b6b'>{neg}</b>  Netral: <b style='color:{small_text_color}'>{net}</b></p>", unsafe_allow_html=True)
            # recommendations
            st.markdown("<ul class='tiny'>", unsafe_allow_html=True)
            if neg >= max(5, int(total*0.15)):
                st.markdown("<li>Prioritaskan penanganan komentar negatif. Siapkan template jawaban.</li>", unsafe_allow_html=True)
            else:
                st.markdown("<li>Respons cepat pada komentar - jaga engagement.</li>", unsafe_allow_html=True)
            st.markdown("<li>Pin komentar positif & buat highlight konten.</li>", unsafe_allow_html=True)
            st.markdown("</ul>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ---------- POSTINGAN: metallic cards per video ----------
elif menu == "Postingan":
    st.markdown("<div class='dashboard-card'>", unsafe_allow_html=True)
    st.subheader("📌 Postingan (Komentar per Video)")

    # summary row at top
    c1, c2 = st.columns([1,1])
    with c1:
        st.markdown(f"<div class='stat-small'><h4 class='tiny'>Total Komentar</h4><p style='font-size:20px;color:{ACCENT};font-weight:800'>{total_komen:,}</p></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='stat-small'><h4 class='tiny'>Total User</h4><p style='font-size:20px;color:{ACCENT};font-weight:800'>{unique_user:,}</p></div>", unsafe_allow_html=True)

    st.markdown("<hr/>", unsafe_allow_html=True)

    # create grid of video cards (metallic look)
    cards_per_row = 4
    rows = math.ceil(len(VIDEO_IDS)/cards_per_row)
    idx = 0
    for r in range(rows):
        cols = st.columns(cards_per_row)
        for c in cols:
            if idx < len(VIDEO_IDS):
                vid = VIDEO_IDS[idx]
                stats = by_video[by_video["video_id"]==vid]
                count = int(stats["total_komentar"].iloc[0]) if not stats.empty else 0
                unique_u = int(stats["unik_user"].iloc[0]) if not stats.empty and "unik_user" in stats.columns else "-"
                # metallic gradient colors via inline style
                color1 = "#3a3f44" if st.session_state.theme_mode=="Gelap" else "#e6eef9"
                color2 = "#6b7280" if st.session_state.theme_mode=="Gelap" else "#dbeafe"
                st.markdown(f"""
                    <div class='video-card metallic' style='background: linear-gradient(135deg,{color1}, {color2});'>
                        <div style='display:flex;justify-content:space-between;align-items:center'>
                            <div style='font-size:13px;color:{small_text_color}'>Video: <code style='color:{FG}'>{vid}</code></div>
                            <div style='font-size:11px;color:{small_text_color}'>Users: {unique_u}</div>
                        </div>
                        <div style='margin-top:8px'>
                            <div style='font-size:12px;color:{small_text_color}'>Komentar</div>
                            <div style='font-weight:800;font-size:20px;color:{ACCENT}'>{count:,}</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                idx += 1
            else:
                st.write("")  # empty column
    st.markdown("</div>", unsafe_allow_html=True)

# ---------- SENTIMEN: table & small charts ----------
elif menu == "Sentimen":
    st.markdown("<div class='dashboard-card'>", unsafe_allow_html=True)
    st.subheader("💬 Komentar & Sentimen")
    if df.empty:
        st.info("Belum ada komentar.")
    else:
        # table + small donut
        tcol, ccol = st.columns([2,1])
        with tcol:
            st.dataframe(df[["publishedAt","author","text","label"]].sort_values("publishedAt", ascending=False).rename(columns={"publishedAt":"Waktu","author":"Author","text":"Komentar","label":"Label"}), height=420)
        with ccol:
            st.plotly_chart(donut_fig_from_counts(by_label), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ---------- ANALISIS: add forex 3D anim + bar ----------
elif menu == "Analisis":
    st.markdown("<div class='dashboard-card'>", unsafe_allow_html=True)
    st.subheader("📈 Analisis & Grafik Forex (Simulasi)")

    # forex 3d anim
    st.markdown("<div style='margin-bottom:14px'>", unsafe_allow_html=True)
    forex_fig = forex_3d_animation()
    st.plotly_chart(forex_fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # jumlah komentar per video (3d bar via plotly surface-looking)
    st.plotly_chart(bar_per_video_fig(by_video), use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ---------- WORDCLOUD ----------
elif menu == "WordCloud":
    st.markdown("<div class='dashboard-card'>", unsafe_allow_html=True)
    st.subheader("☁️ WordCloud")
    if df.empty:
        st.info("Belum ada komentar.")
    else:
        fig_wc = build_wordcloud_figure(df["text_clean"].tolist())
        st.pyplot(fig_wc)
    st.markdown("</div>", unsafe_allow_html=True)

# ---------- INSIGHT & REKOMENDASI ----------
elif menu == "Insight & Rekomendasi":
    st.markdown("<div class='dashboard-card'>", unsafe_allow_html=True)
    st.subheader("📑 Insight & Rekomendasi (Didesain Menarik)")

    # top insight cards
    ic1, ic2, ic3 = st.columns([1,1,1])
    with ic1:
        st.markdown(f"<div style='padding:12px;border-radius:10px;background:{CARD};box-shadow:6px 6px 18px {SHADOW};'><div class='tiny'>Total Komentar</div><div style='font-weight:800;color:{ACCENT};font-size:20px'>{total_komen:,}</div></div>", unsafe_allow_html=True)
    with ic2:
        st.markdown(f"<div style='padding:12px;border-radius:10px;background:{CARD};box-shadow:6px 6px 18px {SHADOW};'><div class='tiny'>Komentar Negatif</div><div style='font-weight:800;color:#ff6b6b;font-size:20px'>{by_label.get('negatif',0):,}</div></div>", unsafe_allow_html=True)
    with ic3:
        st.markdown(f"<div style='padding:12px;border-radius:10px;background:{CARD};box-shadow:6px 6px 18px {SHADOW};'><div class='tiny'>Komentar Positif</div><div style='font-weight:800;color:limegreen;font-size:20px'>{by_label.get('positif',0):,}</div></div>", unsafe_allow_html=True)

    st.markdown("<hr/>", unsafe_allow_html=True)

    # long recommendations card
    st.markdown("<div style='padding:12px;border-radius:12px;background:{0};box-shadow:8px 8px 20px {1};'>".format(CARD, SHADOW), unsafe_allow_html=True)
    st.markdown("<h4 style='margin:0 0 6px'>Rekomendasi Otomatis</h4>", unsafe_allow_html=True)
    # dynamic recommendations
    recs = []
    neg_pct = (by_label.get("negatif",0) / total_komen * 100) if total_komen else 0
    pos_pct = (by_label.get("positif",0) / total_komen * 100) if total_komen else 0
    if neg_pct >= 30:
        recs.append("Segera tindak lanjuti komentar negatif — siapkan tim respons & template jawaban.")
    if pos_pct >= 40:
        recs.append("Promosikan komentar positif ke highlight & gunakan sebagai testimoni.")
    if total_komen < 50:
        recs.append("Tingkatkan call-to-action di postingan agar jumlah komentar naik.")
    if not recs:
        recs.append("Monitor terus & jaga respons cepat (<=24 jam) pada komentar kritis.")
    for r in recs:
        st.markdown(f"- {r}", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# Footer
st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
