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

# ================== CONFIG ==================
st.set_page_config(page_title="Dashboard Sentimen", layout="wide")

# ================== CSS 3D BOX + NAVBAR ==================
st.markdown("""
<style>
/* Menu aktif */
.stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
    background: linear-gradient(135deg, #4A90E2, #357ABD);
    color: white !important;
    font-weight: bold;
    border-radius: 10px;
}

/* Card box 3D */
.card {
    background: linear-gradient(145deg, #ffffff, #f0f0f0);
    border-radius: 15px;
    padding: 20px;
    text-align: center;
    box-shadow: 5px 5px 15px #c5c5c5, -5px -5px 15px #ffffff;
    transition: all 0.3s ease-in-out;
}
.card:hover {
    transform: translateY(-5px) scale(1.02);
    box-shadow: 8px 8px 20px #b8b8b8, -8px -8px 20px #ffffff;
}
.card-title {
    font-size: 16px;
    font-weight: 700;
    margin-bottom: 5px;
}
.card-value {
    font-size: 22px;
    font-weight: bold;
    color: #4A90E2;
}
</style>
""", unsafe_allow_html=True)

# ================== MENU ==================
menu = st.tabs(["All", "Postingan", "Analisis", "Wordcloud", "Insight & Rekomendasi"])

# ================== DUMMY DATA ==================
total_comments = 3200
total_users = 780
last_update = "01-09-2025"
video_monitored = 13

comments_per_video = np.random.randint(50, 400, size=13)
videos = [f"Video {i+1}" for i in range(13)]

# ================== MENU ALL ==================
# ---------- BAGIAN ATAS ----------
col1, col2 = st.columns([2, 1])  

with col1:
    box1, box2 = st.columns(2)
    with box1:
        st.metric("Total Komentar", "1200")
    with box2:
        st.metric("Total User", "350")

    box3, box4 = st.columns(2)
    with box3:
        st.metric("Update Terakhir", "18:33")
    with box4:
        st.metric("Video Terpantau", "13")

with col2:
    # Spidometer Sentimen
    gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=72,
        title={'text': "Sentimen"},
        gauge={'axis': {'range': [0, 100]}}
    ))
    st.plotly_chart(gauge, use_container_width=True)

# ---------- BAGIAN BAWAH ----------
col3, col4 = st.columns([1, 1])

with col3:
    st.subheader("Tabel Sentimen")
    data = {
        "Video": [f"Video {i}" for i in range(1, 8)],
        "Positif": [30, 50, 40, 60, 55, 70, 80],
        "Negatif": [10, 20, 15, 25, 30, 20, 15],
        "Netral": [5, 10, 8, 12, 10, 15, 20]
    }
    df = pd.DataFrame(data)
    st.dataframe(df)

with col4:
    st.subheader("Grafik Komentar per Video")
    bar = px.bar(df, x="Video", y=["Positif", "Negatif", "Netral"], barmode="group")
    st.plotly_chart(bar, use_container_width=True)

# ================== MENU POSTINGAN ==================
with menu[1]:
    st.subheader("📩 Komentar per Postingan")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="card"><div class="card-title">Total Komentar</div><div class="card-value">{total_comments}</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="card"><div class="card-title">Total User</div><div class="card-value">{total_users}</div></div>', unsafe_allow_html=True)

    st.write("### Jumlah Komentar per Video")
    for row in range(0, 13, 3):
        cols = st.columns(3)
        for i in range(3):
            if row+i < len(videos):
                cols[i].markdown(
                    f'<div class="card"><div class="card-title">{videos[row+i]}</div><div class="card-value">{comments_per_video[row+i]}</div></div>',
                    unsafe_allow_html=True
                )

# ================== MENU ANALISIS ==================
with menu[2]:
    st.subheader("📈 Analisis Komentar")

    st.write("### Grafik Garis Jumlah Komentar (Model Forex)")
    fig3, ax3 = plt.subplots()
    ax3.plot(videos, comments_per_video, marker="o", linestyle="-")
    ax3.set_xticklabels(videos, rotation=45, ha="right")
    st.pyplot(fig3)

    st.write("### Grafik Batang per Video")
    fig4, ax4 = plt.subplots()
    ax4.bar(videos, comments_per_video, color="skyblue")
    ax4.set_xticklabels(videos, rotation=45, ha="right")
    st.pyplot(fig4)

# ================== MENU WORDCLOUD ==================
with menu[3]:
    st.subheader("☁️ Wordcloud Komentar")

    text = "positif mantap bagus keren negatif kecewa buruk senang bahagia amazing wow top"
    wc = WordCloud(width=600, height=400, background_color="white").generate(text)

    fig5, ax5 = plt.subplots()
    ax5.imshow(wc, interpolation="bilinear")
    ax5.axis("off")
    st.pyplot(fig5)

# ================== MENU INSIGHT & REKOMENDASI ==================
with menu[4]:
    st.subheader("💡 Insight & Rekomendasi")

    st.markdown("""
    <div class="card" style="text-align:left">
    <div class="card-title">Insight</div>
    <ul>
        <li>Komentar positif mendominasi (55%), menandakan respon audiens cukup baik.</li>
        <li>Video 5 dan Video 9 paling banyak menyumbang komentar.</li>
        <li>Aktivitas komentar cenderung naik pada akhir pekan.</li>
    </ul>
    <div class="card-title">Rekomendasi</div>
    <ul>
        <li>Tingkatkan interaksi pada video dengan engagement rendah.</li>
        <li>Gunakan kata kunci positif yang sering muncul pada wordcloud.</li>
        <li>Fokus upload video baru di jam sibuk audiens (malam hari).</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

