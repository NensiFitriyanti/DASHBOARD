import streamlit as st
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from googleapiclient.discovery import build
from streamlit_autorefresh import st_autorefresh
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import re
import json
import gspread
from gspread_dataframe import set_with_dataframe, get_as_dataframe
from datetime import datetime

# ================= CONFIG =================
st.set_page_config(page_title="DASHBOARD SENTIMENT ANALYSIS", layout="wide")

# Tambah CSS biar ada efek 3D & dark/light toggle
st.markdown("""
    <style>
    .big-title {text-align:center; font-size:32px; font-weight:bold; color:#2c3e50;}
    .menu-box {
        padding: 20px;
        border-radius: 20px;
        box-shadow: 5px 5px 15px #aaaaaa, -5px -5px 15px #ffffff;
        text-align: center;
        transition: transform 0.2s;
    }
    .menu-box:hover {
        transform: scale(1.05);
    }
    .small-text {
        font-size:14px;
        font-weight:500;
        color:#333333;
    }
    </style>
""", unsafe_allow_html=True)

# ================= LOAD YOUTUBE COMMENTS =================
def get_youtube_comments(api_key, video_ids, max_comments=100):
    youtube = build("youtube", "v3", developerKey=api_key)
    comments_data = []

    for video_id in video_ids:
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=min(max_comments, 100),
            textFormat="plainText"
        )
        response = request.execute()

        for item in response.get("items", []):
            comment = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
            author = item["snippet"]["topLevelComment"]["snippet"]["authorDisplayName"]
            comments_data.append({"video_id": video_id, "author": author, "comment": comment})

    return pd.DataFrame(comments_data)

# ================= SENTIMENT =================
analyzer = SentimentIntensityAnalyzer()

def analyze_sentiment(text):
    score = analyzer.polarity_scores(text)
    if score["compound"] >= 0.05:
        return "Positive"
    elif score["compound"] <= -0.05:
        return "Negative"
    else:
        return "Neutral"

# ================= CHARTS =================
def donut_sentiment_chart(df):
    counts = df["sentiment"].value_counts()
    fig = go.Figure(data=[go.Pie(
        labels=counts.index,
        values=counts.values,
        hole=0.5,
        pull=[0.05, 0.05, 0.05]
    )])
    fig.update_layout(title_text="Distribusi Sentimen (Donut Chart)")
    return fig

def bar_sentiment_counts(df):
    counts = df["sentiment"].value_counts().reset_index()
    counts.columns = ["sentiment", "jumlah"]
    fig = px.bar(counts, x="sentiment", y="jumlah", color="sentiment", text="jumlah", title="Jumlah Sentimen")
    return fig

def chart_per_video(df):
    counts = df.groupby("video_id")["comment"].count().reset_index()
    fig = px.bar(counts, x="video_id", y="comment", text="comment", title="Jumlah Komentar per Video (3D Style)")
    fig.update_traces(marker=dict(line=dict(width=1, color='DarkSlateGrey')))
    return fig

# ================= WORDCLOUD =================
def generate_wordcloud(df):
    text = " ".join(df["comment"].astype(str))
    wc = WordCloud(width=800, height=400, background_color="white").generate(text)
    return wc

# ================= INSIGHT =================
def generate_insight(df):
    total_comments = len(df)
    positives = len(df[df["sentiment"]=="Positive"])
    negatives = len(df[df["sentiment"]=="Negative"])
    neutrals = len(df[df["sentiment"]=="Neutral"])
    
    insight = f"""
    Dari total {total_comments} komentar:
    - {positives} komentar bernada positif
    - {negatives} komentar bernada negatif
    - {neutrals} komentar netral
    
    Rekomendasi untuk Samsat:
    - Tingkatkan respon terhadap komentar negatif dengan pendekatan solutif
    - Pertahankan konten yang mendapat komentar positif
    - Dorong interaksi lebih banyak agar komentar netral bisa berubah jadi positif
    """
    return insight

# ================= MAIN =================
def main():
    st.markdown("<h1 class='big-title'>DASHBOARD SENTIMENT ANALYSIS</h1>", unsafe_allow_html=True)

    # API Key
    api_key = st.secrets["YOUTUBE_API_KEY"]

    # Daftar link video
    video_links = [
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
    video_ids = [re.search(r"v=([^&]+)", link).group(1) if "v=" in link else link.split("/")[-1].split("?")[0] for link in video_links]

    # Ambil data
    df = get_youtube_comments(api_key, video_ids, max_comments=50)
    if not df.empty:
        df["sentiment"] = df["comment"].apply(analyze_sentiment)

    # Menu
    menu = st.sidebar.radio("Pilih Menu", ["All", "Postingan", "Sentimen", "Analisis", "WordCloud", "Insight & Rekomendasi"])

    if menu == "All":
        st.subheader("📊 Semua Data dalam Satu Box")
        with st.container():
            st.plotly_chart(donut_sentiment_chart(df), use_container_width=True)
            st.plotly_chart(chart_per_video(df), use_container_width=True)
            st.plotly_chart(bar_sentiment_counts(df), use_container_width=True)
            wc = generate_wordcloud(df)
            fig, ax = plt.subplots()
            ax.imshow(wc, interpolation="bilinear")
            ax.axis("off")
            st.pyplot(fig)
            st.text(generate_insight(df))

    elif menu == "Postingan":
        st.subheader("📌 Statistik Postingan")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("<div class='menu-box'><p class='small-text'>Total Video</p><h3>{}</h3></div>".format(len(video_ids)), unsafe_allow_html=True)
        with col2:
            st.markdown("<div class='menu-box'><p class='small-text'>Total Komentar</p><h3>{}</h3></div>".format(len(df)), unsafe_allow_html=True)
        with col3:
            st.markdown("<div class='menu-box'><p class='small-text'>Total User</p><h3>{}</h3></div>".format(df['author'].nunique()), unsafe_allow_html=True)

    elif menu == "Sentimen":
        st.subheader("💬 Komentar & Sentimen")
        st.dataframe(df[["author", "comment", "sentiment"]])
        st.plotly_chart(bar_sentiment_counts(df), use_container_width=True)

    elif menu == "Analisis":
        st.subheader("📈 Analisis Komentar per Video")
        st.plotly_chart(chart_per_video(df), use_container_width=True)

    elif menu == "WordCloud":
        st.subheader("☁️ WordCloud")
        wc = generate_wordcloud(df)
        fig, ax = plt.subplots()
        ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")
        st.pyplot(fig)

    elif menu == "Insight & Rekomendasi":
        st.subheader("📑 Insight & Rekomendasi untuk Samsat")
        st.text(generate_insight(df))

if __name__ == "__main__":
    main()