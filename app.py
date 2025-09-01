# ==============================
# DASHBOARD ANALYSIS - STREAMLIT
# ==============================

import streamlit as st
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from googleapiclient.discovery import build
from streamlit_autorefresh import st_autorefresh
import datetime

# ==============================
# KONFIGURASI
# ==============================
st.set_page_config(page_title="DASHBOARD ANALYSIS", layout="wide")

# Theme Switcher (Gelap / Terang)
theme_mode = st.sidebar.radio("🌗 Pilih Tema:", ["Light", "Dark"])
if theme_mode == "Dark":
    st.markdown(
        """
        <style>
        body {
            background-color: #0e1117;
            color: white;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

# ==============================
# MENU UTAMA
# ==============================
menu = st.sidebar.radio("📌 Menu:", [
    "Dashboard",
    "Postingan",
    "Table Komentar",
    "Analisis",
    "Insight & Rekomendasi"
])

# ==============================
# YOUTUBE API SETUP
# ==============================
if "YOUTUBE_API_KEY" not in st.secrets:
    st.error("⚠️ API Key belum diatur di Streamlit Cloud → Secrets")
    st.stop()

API_KEY = st.secrets["YOUTUBE_API_KEY"]
youtube = build('youtube', 'v3', developerKey=API_KEY)
analyzer = SentimentIntensityAnalyzer()

# Daftar Video
video_urls = [
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

# ==============================
# MENU: DASHBOARD
# ==============================
if menu == "Dashboard":
    st.title("📊 DASHBOARD ANALYSIS")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Komentar", "12,450", "+3.5%")
    with col2:
        st.metric("Total User", "1,245", "+1.2%")
    with col3:
        st.metric("Jumlah Video", str(len(video_urls)))

    col4, col5 = st.columns(2)
    with col4:
        st.subheader("Sales Pipeline (contoh tampilan)")
        fig = px.funnel(x=[20.5, 28.2, 20.5, 17.9, 12.8],
                        y=["Stage 1", "Stage 2", "Stage 3", "Stage 4", "Stage 5"])
        st.plotly_chart(fig, use_container_width=True)
    with col5:
        st.subheader("Leads by Source (contoh)")
        fig = px.pie(values=[31.1, 24.9, 24.3, 7.3, 12.4],
                     names=["Web", "Trade show", "Referral", "Ads", "Email"])
        st.plotly_chart(fig, use_container_width=True)

# ==============================
# MENU: POSTINGAN
# ==============================
elif menu == "Postingan":
    st.title("📺 Postingan")
    st.write("Jumlah komentar per video")

    cols = st.columns(3)
    for i, url in enumerate(video_urls, start=1):
        with cols[(i-1) % 3]:
            st.markdown(f"""
            <div style="padding:15px; border-radius:15px; background:linear-gradient(145deg,#e6e6e6,#ffffff); box-shadow: 5px 5px 15px #bebebe,-5px -5px 15px #ffffff;">
            🎥 <b>Video {i}</b><br>
            Komentar: {100+i*10}
            </div>
            """, unsafe_allow_html=True)

    colA, colB = st.columns(2)
    with colA:
        st.success("📊 Total Komentar: 12,450")
    with colB:
        st.info("👥 Total User: 1,245")

# ==============================
# MENU: TABLE KOMENTAR
# ==============================
elif menu == "Table Komentar":
    st.title("💬 Tabel Komentar")
    df = pd.DataFrame({
        "User": ["A","B","C","D"],
        "Komentar": ["Bagus sekali","Kurang puas","Netral","Mantap"],
        "Sentimen": ["Positif","Negatif","Netral","Positif"]
    })
    st.dataframe(df, use_container_width=True)

    st.subheader("📌 Komentar per Sentimen")
    for senti in ["Positif", "Negatif", "Netral"]:
        st.markdown(f"### {senti}")
        st.dataframe(df[df["Sentimen"]==senti], use_container_width=True)

# ==============================
# MENU: ANALISIS
# ==============================
elif menu == "Analisis":
    st.title("📈 Analisis")

    st.subheader("📉 Diagram Forex (Jumlah Komentar & Tayangan per Postingan)")
    df_line = pd.DataFrame({
        "Postingan": range(1,14),
        "Komentar": [120,180,140,220,260,240,300,280,310,290,330,350,370],
        "Tayangan": [1000,1200,1150,1400,1600,1550,1700,1650,1750,1800,1900,2000,2100]
    })
    fig_line = px.line(df_line, x="Postingan", y=["Komentar","Tayangan"], markers=True)
    st.plotly_chart(fig_line, use_container_width=True)

    st.subheader("📊 Diagram Batang Hasil Sentimen")
    df_bar = pd.DataFrame({
        "Sentimen":["Positif","Negatif","Netral"],
        "Jumlah":[320,120,200]
    })
    fig_bar = px.bar(df_bar, x="Sentimen", y="Jumlah", color="Sentimen")
    st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("☁️ WordCloud")
    text = "Bagus sekali Samsat cepat pelayanan buruk lambat antrian netral pelayanan baik"
    wordcloud = WordCloud(width=800, height=400, background_color="white").generate(text)
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis("off")
    st.pyplot()

# ==============================
# MENU: INSIGHT & REKOMENDASI
# ==============================
elif menu == "Insight & Rekomendasi":
    st.title("💡 Insight & Rekomendasi")
    st.markdown("""
    ### Insight:
    - Mayoritas komentar bersifat positif, artinya masyarakat cukup puas.
    - Ada peningkatan jumlah komentar pada video dengan topik pelayanan cepat.
    - Sentimen negatif dominan terkait antrian panjang.

    ### Rekomendasi untuk SAMSAT:
    1. Tingkatkan kapasitas pelayanan di jam sibuk.
    2. Buat sistem antrian online agar lebih efisien.
    3. Fokus pada promosi layanan unggulan yang mendapat respon positif.
    """)