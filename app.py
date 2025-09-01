import os
import re
import time
import json
import math
import random
import string
from datetime import datetime

import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from googleapiclient.discovery import build

# ================= LOAD API KEY =================
if "YOUTUBE_API_KEY" not in st.secrets:
    st.error("⚠️ API Key belum diatur di Streamlit Cloud → Secrets")
    st.stop()

API_KEY = st.secrets["YOUTUBE_API_KEY"]
youtube = build('youtube', 'v3', developerKey=API_KEY)

# ================= SCRAPER KOMENTAR =================
def get_comments(video_id, max_results=100):
    comments, authors, times, ids, video_ids, sentiments = [], [], [], [], [], []

    try:
        response = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=max_results,
            textFormat="plainText"
        ).execute()

        for item in response.get("items", []):
            snippet = item["snippet"]["topLevelComment"]["snippet"]
            comment_id = item["id"]
            text = snippet["textDisplay"]
            author = snippet["authorDisplayName"]
            time_published = snippet["publishedAt"]

            comments.append(text)
            authors.append(author)
            times.append(time_published)
            ids.append(comment_id)
            video_ids.append(video_id)

            # sentimen placeholder
            sentiments.append(random.choice(["positive", "negative", "neutral"]))

    except Exception as e:
        st.error(f"Gagal mengambil komentar: {e}")

    return pd.DataFrame({
        "comment_id": ids,
        "video_id": video_ids,
        "author": authors,
        "time": times,
        "text": comments,
        "sentiment": sentiments
    })

# ================= LOAD DATA =================
VIDEO_ID = "1951305320896274764"  # ganti sesuai kebutuhan
df = get_comments(VIDEO_ID, max_results=200)

# ================= SIDEBAR =================
menu = st.sidebar.radio("📌 Pilih Menu:", [
    "1. Dashboard",
    "2. Postingan",
    "3. Analisis",
    "4. Wordcloud & Pie"
])

# ==============================
# MENU 1: DASHBOARD
# ==============================
if menu.startswith("1."):
    st.title("📊 Dashboard Utama")

    c1, c2, c3, c4 = st.columns(4)

    total_komentar = len(df) if not df.empty else 0
    c1.metric("Total Komentar", total_komentar)

    if "author" in df.columns:
        total_user = df["author"].nunique()
    else:
        total_user = 0
    c2.metric("Total User", total_user)

    if "time" in df.columns and not df.empty:
        update_terakhir = df["time"].max()
    else:
        update_terakhir = "-"
    c3.metric("Update Terakhir", str(update_terakhir))

    if "video_id" in df.columns:
        total_postingan = df["video_id"].nunique()
    else:
        total_postingan = 0
    c4.metric("Total Postingan", total_postingan)

    st.markdown("---")

    if "sentiment" in df.columns and not df.empty:
        sentiment_counts = df["sentiment"].value_counts()
        total = sentiment_counts.sum()
        persen_pos = (sentiment_counts.get("positive", 0) / total) * 100 if total > 0 else 0
    else:
        persen_pos = 0

    gauge_fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=persen_pos,
        title={'text': "Dominasi Positif (%)"},
        gauge={'axis': {'range': [0, 100]}}
    ))
    st.plotly_chart(gauge_fig, use_container_width=True)

    if "sentiment" in df.columns and not df.empty:
        donut_fig = px.pie(df, names="sentiment", hole=0.5, title="Distribusi Sentimen")
        st.plotly_chart(donut_fig, use_container_width=True)

    if "sentiment" in df.columns and not df.empty:
        st.subheader("Tabel Sentimen")
        st.dataframe(df[["text", "sentiment"]])

    if "video_id" in df.columns and not df.empty:
        komentar_per_video = df.groupby("video_id")["comment_id"].count().reset_index()
        komentar_per_video = komentar_per_video.rename(columns={"comment_id": "jumlah_komentar"})
        bar_fig = px.bar(
            komentar_per_video, x="video_id", y="jumlah_komentar",
            title="Jumlah Komentar per Video"
        )
        st.plotly_chart(bar_fig, use_container_width=True)

# ==============================
# MENU 2: POSTINGAN
# ==============================
elif menu.startswith("2."):
    st.title("📺 Daftar Postingan")

    if not df.empty:
        for vid, group in df.groupby("video_id"):
            with st.container():
                st.markdown(f"### Video ID: `{vid}`")
                st.metric("Jumlah Komentar", len(group))
                st.dataframe(group[["author", "time", "text", "sentiment"]])
                st.markdown("---")
    else:
        st.info("Belum ada postingan / komentar yang terdeteksi.")

# ==============================
# MENU 3: ANALISIS
# ==============================
elif menu.startswith("3."):
    st.title("📈 Analisis Sentimen")

    if not df.empty:
        sentiment_counts = df["sentiment"].value_counts()
        st.write("### Distribusi Sentimen")
        st.bar_chart(sentiment_counts)

        st.write("### Detail Komentar per Sentimen")
        for s in ["positive", "neutral", "negative"]:
            st.subheader(s.capitalize())
            st.dataframe(df[df["sentiment"] == s][["author", "text", "time"]])
    else:
        st.warning("Data komentar kosong, tidak bisa analisis.")

# ==============================
# MENU 4: WORDCLOUD & PIE
# ==============================
elif menu.startswith("4."):
    st.title("☁️ Wordcloud & Pie Chart")

    if not df.empty:
        text_all = " ".join(df["text"].astype(str))
        wordcloud = WordCloud(width=800, height=400, background_color="white").generate(text_all)

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis("off")
        st.pyplot(fig)

        pie_fig = px.pie(df, names="sentiment", title="Persentase Sentimen")
        st.plotly_chart(pie_fig, use_container_width=True)
    else:
        st.info("Belum ada data untuk dibuat Wordcloud atau Pie Chart.")