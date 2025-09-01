
import re
import base64
from datetime import datetime
from io import BytesIO

import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
from wordcloud import WordCloud

# YouTube API
try:
    from googleapiclient.discovery import build
except:
    build = None

# --------------------------
# CONFIG DASAR
# --------------------------
st.set_page_config(page_title="DASHBOARD ANALYSIS", layout="wide")
st_autorefresh(interval=60 * 60 * 1000, key="refresh_each_60m")  # refresh otomatis

# --------------------------
# THEME MODE
# --------------------------
with st.sidebar:
    theme_mode = st.radio("Pilih Tema:", ["🌙 Gelap", "☀️ Terang"], index=0)

is_dark = theme_mode.startswith("🌙")
BG = "#0f1226" if is_dark else "#eef1f8"
FG = "#f5f7ff" if is_dark else "#0e1329"
ACCENT = "#18a0fb"

st.markdown(
    f"""
    <style>
      body, [data-testid="stAppViewContainer"] {{
        background: {BG} !important;
        color: {FG} !important;
      }}
      [data-testid="stHeader"] {{ background: transparent; }}
      .title-center {{
        text-align:center; font-size:30px; font-weight:800;
        background: linear-gradient(135deg,#cfd3da,#7e8697,#cfd3da);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
      }}
      .neo-card {{
        background: linear-gradient(145deg,#cfd3da,#9ea5b3);
        border-radius: 18px; padding: 18px;
        box-shadow: 8px 8px 20px rgba(0,0,0,.35), -6px -6px 18px rgba(255,255,255,.25);
        transition: transform .25s ease;
      }}
      .neo-card.dark {{
        background: linear-gradient(145deg,#1a1f3a,#0b0e1e);
      }}
      .neo-card:hover {{ transform: translateY(-3px); }}
    </style>
    """,
    unsafe_allow_html=True,
)

card_class = "neo-card dark" if is_dark else "neo-card"

# --------------------------
# YOUTUBE DATA FETCH
# --------------------------
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
VIDEO_IDS = [re.search(r"v=([\\w-]{11})", url) or re.search(r"youtu\\.be/([\\w-]{11})", url) for url in VIDEO_URLS]
VIDEO_IDS = [m.group(1) for m in VIDEO_IDS if m]

# Fallback kalau API mati
def get_comments(video_ids):
    if build is None or "YOUTUBE_API_KEY" not in st.secrets:
        # Dummy
        rng = np.random.default_rng(42)
        data = []
        for v in video_ids:
            for i in range(rng.integers(20, 50)):
                s = np.random.choice(["positive", "negative", "neutral"])
                data.append(
                    {
                        "video_id": v,
                        "comment_id": f"c{i}{v}",
                        "author": f"user{rng.integers(1000)}",
                        "text": "Komentar contoh...",
                        "sentiment": s,
                        "views": int(rng.integers(5000, 20000)),
                        "time": datetime.now(),
                    }
                )
        return pd.DataFrame(data)
    else:
        youtube = build("youtube", "v3", developerKey=st.secrets["YOUTUBE_API_KEY"])
        rows = []
        for vid in video_ids:
            req = youtube.commentThreads().list(part="snippet", videoId=vid, maxResults=100, order="time")
            res = req.execute()
            for item in res["items"]:
                sn = item["snippet"]["topLevelComment"]["snippet"]
                rows.append(
                    {
                        "video_id": vid,
                        "comment_id": item["id"],
                        "author": sn["authorDisplayName"],
                        "text": sn["textDisplay"],
                        "sentiment": "neutral",  # nanti scoring NLP
                        "views": np.random.randint(5000, 20000),
                        "time": pd.to_datetime(sn["publishedAt"]),
                    }
                )
        return pd.DataFrame(rows)

df = get_comments(VIDEO_IDS)

# --------------------------
# MENU
# --------------------------
menu = st.sidebar.radio(
    "Menu",
    ["1. Dashboard", "2. Postingan", "3. Table Komentar", "4. Analisis", "5. Insight & Rekomendasi"],
)

st.markdown('<div class="title-center">DASHBOARD ANALYSIS</div>', unsafe_allow_html=True)

# ==============================
# MENU 1: DASHBOARD
# ==============================
if menu.startswith("1."):
    st.title("📊 Dashboard Utama")

    # Buat box 4 kolom
    c1, c2, c3, c4 = st.columns(4)

    # Total komentar
    total_komentar = len(df) if not df.empty else 0
    c1.metric("Total Komentar", total_komentar)

    # Total user (cek kolom author/authorDisplayName)
    if "author" in df.columns:
        total_user = df["author"].nunique()
    elif "authorDisplayName" in df.columns:
        total_user = df["authorDisplayName"].nunique()
    else:
        total_user = 0
    c2.metric("Total User", total_user)

    # Update terakhir (cek kolom publishedAt)
    if "publishedAt" in df.columns and not df.empty:
        update_terakhir = df["publishedAt"].max()
    else:
        update_terakhir = "-"
    c3.metric("Update Terakhir", str(update_terakhir))

    # Total postingan
    total_postingan = df["video_id"].nunique() if "video_id" in df.columns else 0
    c4.metric("Total Postingan", total_postingan)

    st.markdown("---")

    # Spidometer (gauge chart sentimen dominan)
    if "sentiment" in df.columns and not df.empty:
        sentiment_counts = df["sentiment"].value_counts()
        total = sentiment_counts.sum()
        if total > 0:
            persen_pos = (sentiment_counts.get("positive", 0) / total) * 100
            persen_neg = (sentiment_counts.get("negative", 0) / total) * 100
            persen_net = (sentiment_counts.get("neutral", 0) / total) * 100
        else:
            persen_pos = persen_neg = persen_net = 0
    else:
        persen_pos = persen_neg = persen_net = 0

    gauge_fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=persen_pos,
        title={'text': "Dominasi Positif (%)"},
        gauge={'axis': {'range': [0, 100]}}
    ))
    st.plotly_chart(gauge_fig, use_container_width=True)

    # Donut Chart Sentimen
    if "sentiment" in df.columns and not df.empty:
        donut_fig = px.pie(
            df, names="sentiment", hole=0.5,
            title="Distribusi Sentimen"
        )
        st.plotly_chart(donut_fig, use_container_width=True)

    # Tabel sentimen
    if "sentiment" in df.columns and not df.empty:
        st.subheader("Tabel Sentimen")
        st.dataframe(df[["comment", "sentiment"]])

    # Grafik jumlah komentar per postingan
    if "video_id" in df.columns and not df.empty:
        komentar_per_video = df.groupby("video_id")["comment"].count().reset_index()
        komentar_per_video = komentar_per_video.rename(columns={"comment": "jumlah_komentar"})
        bar_fig = px.bar(
            komentar_per_video, x="video_id", y="jumlah_komentar",
            title="Jumlah Komentar per Video"
        )
        st.plotly_chart(bar_fig, use_container_width=True)

# --------------------------
# 2) POSTINGAN
# --------------------------
elif menu.startswith("2."):
    st.subheader("Komentar per Video")
    agg = df.groupby("video_id").size().reset_index(name="Jumlah Komentar")
    for _, row in agg.iterrows():
        st.markdown(f'<div class="{card_class}">Video {row.video_id}: {row["Jumlah Komentar"]} komentar</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f'<div class="{card_class}">Total Komentar: {len(df)}</div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="{card_class}">Total User: {df["author"].nunique()}</div>', unsafe_allow_html=True)

# --------------------------
# 3) TABLE KOMENTAR
# --------------------------
elif menu.startswith("3."):
    st.subheader("Tabel Semua Komentar")
    st.dataframe(df[["video_id", "author", "text", "sentiment", "time"]])

    st.subheader("Komentar per Sentimen")
    for s in ["positive", "negative", "neutral"]:
        st.markdown(f"**{s.title()}**")
        st.dataframe(df[df["sentiment"] == s][["video_id", "author", "text"]])

# --------------------------
# 4) ANALISIS
# --------------------------
elif menu.startswith("4."):
    st.subheader("Analisis")

    # Diagram garis
    st.write("📈 Peningkatan jumlah komentar dan views per postingan")
    agg = df.groupby("video_id").agg({"comment_id": "count", "views": "max"}).reset_index()
    fig4 = go.Figure()
    fig4.add_trace(go.Scatter(x=agg["video_id"], y=agg["comment_id"], mode="lines+markers", name="Komentar"))
    fig4.add_trace(go.Scatter(x=agg["video_id"], y=agg["views"], mode="lines+markers", name="Views"))
    st.plotly_chart(fig4, use_container_width=True)

    # Diagram batang
    st.write("📊 Hasil Sentimen")
    fig5 = px.bar(df["sentiment"].value_counts().reset_index(), x="index", y="sentiment", labels={"index": "Sentimen", "sentiment": "Jumlah"})
    st.plotly_chart(fig5, use_container_width=True)

    # Wordcloud
    st.write("☁️ WordCloud Komentar")
    text = " ".join(df["text"].astype(str).tolist())
    wc = WordCloud(width=800, height=400, background_color="black" if is_dark else "white").generate(text)
    fig6, ax = plt.subplots()
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    st.pyplot(fig6)

# --------------------------
# 5) INSIGHT & REKOMENDASI
# --------------------------
elif menu.startswith("5."):
    st.subheader("💡 Insight & Rekomendasi untuk SAMSAT")

    st.markdown(f"""
    <div class="{card_class}">
    <h4>Insight:</h4>
    <ul>
        <li>Komentar positif dominan menunjukkan masyarakat puas dengan pelayanan.</li>
        <li>Komentar negatif terutama terkait antrian panjang & sistem error.</li>
        <li>Postingan dengan jumlah komentar tinggi cenderung memiliki views lebih tinggi juga.</li>
    </ul>
    <h4>Rekomendasi:</h4>
    <ul>
        <li>Percepat pelayanan untuk mengurangi keluhan antrian.</li>
        <li>Tingkatkan stabilitas sistem untuk mengurangi error.</li>
        <li>Terus tingkatkan komunikasi di media sosial untuk membangun kepercayaan publik.</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)