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
from matplotlib import cm
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from googleapiclient.discovery import build

# ====== CONFIG ========
st.set_page_config(
    page_title="DASBOARD SENTIMENT ANALYSIS",
    page_icon="📊",
    layout="wide"
)

# Auto-refresh setiap 60 menit
st_autorefresh(interval=60*60*1000, key="page_autorefresh")

# ====== Secrets / ENV ======
YOUTUBE_API_KEY = st.secrets.get("YOUTUBE_API_KEY", os.getenv("YOUTUBE_API_KEY", ""))
if not YOUTUBE_API_KEY:
    st.warning("YOUTUBE_API_KEY belum diset.")

# ====== Link Video ======
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

# ====== Dark/Light Theme ======
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

is_dark = st.sidebar.toggle("Mode Gelap/Terang", value=(st.session_state.theme == "dark"))
st.session_state.theme = "dark" if is_dark else "light"

PRIMARY_BG = "#0f172a" if is_dark else "#f8fafc"
PRIMARY_FG = "#e2e8f0" if is_dark else "#0f172a"
CARD_BG = "#111827" if is_dark else "#ffffff"
ACCENT = "#22d3ee" if is_dark else "#0ea5e9"
SHADOW = "rgba(0, 0, 0, 0.45)" if is_dark else "rgba(0, 0, 0, 0.12)"

st.markdown(
    f"""
    <style>
      :root {{
        --bg: {PRIMARY_BG};
        --fg: {PRIMARY_FG};
        --card: {CARD_BG};
        --accent: {ACCENT};
        --shadow: {SHADOW};
      }}
      .main, .stApp {{ background: var(--bg); color: var(--fg); }}

      .nav3d .element-container button {{
        background: linear-gradient(145deg, rgba(255,255,255,0.04), rgba(0,0,0,0.25));
        color: var(--fg);
        border: 0;
        padding: 12px 18px;
        border-radius: 16px;
        box-shadow: 6px 6px 14px var(--shadow), -6px -6px 14px rgba(255,255,255,0.05);
        transition: transform .08s ease, box-shadow .2s ease;
      }}
      .nav3d .element-container button:hover {{ transform: translateY(-1px); }}
      .nav3d .element-container button:active {{ transform: translateY(2px); box-shadow: inset 4px 4px 10px var(--shadow); }}

      .card3d {{
        background: var(--card);
        border-radius: 22px;
        padding: 18px 18px 14px 18px;
        box-shadow: 14px 14px 28px var(--shadow), -10px -10px 24px rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.06);
      }}

      .stat3d {{
        background: var(--card);
        border-radius: 20px;
        padding: 14px 16px;
        text-align: center;
        border: 1px solid rgba(255,255,255,0.06);
        box-shadow: 10px 10px 20px var(--shadow), -6px -6px 18px rgba(255,255,255,0.05);
      }}
      .stat3d h3 {{ margin: 0; font-size: 14px; opacity: .8; }}
      .stat3d p {{ margin: 4px 0 0; font-size: 22px; font-weight: 700; color: var(--accent); }}

      .bigstat3d {{
        background: var(--card);
        border-radius: 24px;
        padding: 20px;
        border: 1px solid rgba(255,255,255,0.06);
        box-shadow: 14px 14px 30px var(--shadow), -10px -10px 24px rgba(255,255,255,0.05);
      }}
      .bigstat3d h2 {{ margin: 0; font-size: 16px; opacity: .85; }}
      .bigstat3d p {{ margin: 6px 0 0; font-size: 28px; font-weight: 800; color: var(--accent); }}

      hr.sep {{ border: none; height: 1px; background: rgba(255,255,255,.08); margin: 8px 0 16px; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# =====================
# ====== UTILS ========
# =====================
VIDEO_ID_RE = re.compile(r"(?:v=|youtu.be/)([A-Za-z0-9_-]{11})")

@st.cache_data(show_spinner=False)
def extract_video_id(url: str) -> str:
    m = VIDEO_ID_RE.search(url)
    return m.group(1) if m else ""

@st.cache_data(ttl=3600, show_spinner=True)
def fetch_comments_for_video(video_id: str, max_pages: int = 20) -> pd.DataFrame:
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
            order="time"
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

@st.cache_data(ttl=3600, show_spinner=True)
def fetch_all_comments(video_urls: list[str]) -> pd.DataFrame:
    frames = []
    for url in video_urls:
        vid = extract_video_id(url)
        if not vid:
            continue
        frames.append(fetch_comments_for_video(vid))
    if frames:
        df = pd.concat(frames, ignore_index=True)
        return df.drop_duplicates(subset=["comment_id"]).reset_index(drop=True)
    return pd.DataFrame(columns=["video_id","comment_id","author","text","publishedAt"])

# Text cleanup
EMOJI_RE = re.compile(r"[\U00010000-\U0010ffff]", flags=re.UNICODE)
URL_RE = re.compile(r"https?://\S+|www\.\S+")
TAG_RE = re.compile(r"<.*?>")

@st.cache_data(show_spinner=False)
def clean_text(s: str) -> str:
    s = TAG_RE.sub(" ", s)
    s = URL_RE.sub(" ", s)
    s = EMOJI_RE.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

@st.cache_resource(show_spinner=False)
def get_analyzer():
    return SentimentIntensityAnalyzer()

@st.cache_data(ttl=3600, show_spinner=True)
def score_sentiment(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.assign(text_clean="", score=0.0, label="netral")
    an = get_analyzer()
    texts = df["text"].fillna("").astype(str).apply(clean_text)
    scores = texts.apply(lambda t: an.polarity_scores(t)["compound"])
    def to_label(v):
        if v >= 0.05: return "positif"
        elif v <= -0.05: return "negatif"
        else: return "netral"
    labels = scores.apply(to_label)
    out = df.copy()
    out["text_clean"] = texts
    out["score"] = scores
    out["label"] = labels
    return out

# =====================
# ====== DATA =========
# =====================
st.title("DASBOARD SENTIMENT ANALYSIS")
st.caption("Komentar YouTube • Auto-refresh 60 menit • NLP VADER")

with st.spinner("Mengambil komentar dari YouTube..."):
    raw_df = fetch_all_comments(VIDEO_URLS)
    df = score_sentiment(raw_df)

by_video = df.groupby("video_id").agg(total_komentar=("comment_id","count"), unik_user=("author","nunique")).reset_index()
by_label = df["label"].value_counts().reindex(["positif","negatif","netral"]).fillna(0).astype(int)

# =====================
# ====== NAV ==========
# =====================
st.sidebar.subheader("Menu")
menu = st.sidebar.radio(
    "Pilih halaman:",
    options=["Dashboard", "All", "Sentimen", "Analisis", "WordCloud", "Insight & Rekomendasi"],
    index=0
)
st.sidebar.markdown("<div class='nav3d'></div>", unsafe_allow_html=True)

# =====================
# ====== UI HELPERS ===
# =====================
def donut_sentiment_chart(series_counts: pd.Series):
    import plotly.graph_objects as go
    fig = go.Figure(data=[go.Pie(labels=series_counts.index, values=series_counts.values, hole=.55)])
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(margin=dict(l=10,r=10,t=10,b=10), height=380, paper_bgcolor='rgba(0,0,0,0)')
    return fig

@st.cache_data(show_spinner=False)
def build_wordcloud(texts: list[str]) -> Figure:
    wc = WordCloud(width=1000, height=500, background_color="black" if is_dark else "white")
    wc_img = wc.generate(" ".join(texts))
    fig = plt.figure(figsize=(9,4))
    plt.imshow(wc_img)
    plt.axis('off')
    return fig

def bar_sentiment_counts(series_counts: pd.Series):
    import plotly.express as px
    dfc = series_counts.reset_index()
    dfc.columns = ["label","jumlah"]
    fig = px.bar(dfc, x="label", y="jumlah")
    fig.update_layout(margin=dict(l=10,r=10,t=10,b=10), height=360, paper_bgcolor='rgba(0,0,0,0)')
    return fig

def bar_per_video(dfv: pd.DataFrame):
    import plotly.express as px
    fig = px.bar(dfv, x="video_id", y="total_komentar")
    fig.update_layout(xaxis_title="Video ID", yaxis_title="Jumlah Komentar",
                      margin=dict(l=10,r=10,t=10,b=10), height=380,
                      paper_bgcolor='rgba(0,0,0,0)')
    return fig

def bar3d_per_video(dfv: pd.DataFrame) -> Figure:
    fig = plt.figure(figsize=(10,5))
    ax = fig.add_subplot(111, projection='3d')
    xs = list(range(len(dfv)))
    zs = dfv["total_komentar"].astype(float).tolist()
    ax.bar(xs, zs)
    ax.set_xticks(xs)
    ax.set_xticklabels(dfv["video_id"].tolist(), rotation=40, ha='right', fontsize=8)
    ax.set_zlabel('Komentar')
    ax.set_title('Jumlah Komentar per Video (3D)')
    fig.tight_layout()
    return fig

@st.cache_data(show_spinner=False)
def make_insights(df_scored: pd.DataFrame) -> dict:
    total = len(df_scored)
    pos = (df_scored.label == 'positif').sum()
    neg = (df_scored.label == 'negatif').sum()
    neu = (df_scored.label == 'netral').sum()
    pos_pct = (pos/total*100) if total else 0
    neg_pct = (neg/total*100) if total else 0
    neu_pct = (neu/total*100) if total else 0

    all_text = " ".join(df_scored.text_clean.tolist()).lower()
    words = re.findall(r"[a-zA-ZÀ-ÿ0-9_]+", all_text)
    freq = pd.Series(words).value_counts().head(10).to_dict() if len(words) else {}

    rekomendasi = []
    if neg_pct >= 40:
        rekomendasi.append("Perbanyak respons cepat pada komentar keluhan; siapkan template jawaban & prioritas antrian layanan.")
    if pos_pct >= 50:
        rekomendasi.append("Dorong testimoni pengguna puas (pin komentar positif, buat highlight).")
    if neu_pct >= 40:
        rekomendasi.append("Berikan FAQ ringkas terkait persyaratan/biaya/jam layanan agar komentar informasional tidak berulang.")
    if not rekomendasi:
        rekomendasi.append("Pertahankan ritme komunikasi; monitor harian & tindak lanjut dalam 24–48 jam untuk komentar negatif.")

    return {
        "ringkasan": {"total": total, "positif": pos, "negatif": neg, "netral": neu,
                      "positif_%": round(pos_pct,2), "negatif_%": round(neg_pct,2), "netral_%": round(neu_pct,2)},
        "top_kata": freq,
        "rekomendasi": rekomendasi
    }

ins = make_insights(df)

# =====================
# ====== PAGES =========
# =====================
if menu == "Dashboard":
    st.subheader("Dashboard Sentimen YouTube")

    # --- 4 kotak utama ---
    total_komen = int(df.shape[0])
    unique_user = int(df["author"].nunique())
    last_update = df["publishedAt"].max() if not df.empty else None
    total_posting = df["video_id"].nunique() if not df.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(label="Total Komentar", value=f"{total_komen:,}", delta=None)
    with c2:
        st.metric(label="Total User", value=f"{unique_user:,}", delta=None)
    with c3:
        st.metric(label="Waktu Update Terakhir", value=f"{last_update}" if last_update else "-")
    with c4:
        st.metric(label="Total Postingan Aktif", value=f"{total_posting}")

    st.markdown("<hr class='sep' />", unsafe_allow_html=True)

    # --- Speedometer sentimen (positif-negatif-netral) ---
    from plotly.subplots import make_subplots
    import plotly.graph_objects as go

    total = total_komen if total_komen > 0 else 1
    pos_pct = round((by_label.get("positif",0)/total)*100,1)
    neg_pct = round((by_label.get("negatif",0)/total)*100,1)
    neu_pct = round((by_label.get("netral",0)/total)*100,1)

    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = pos_pct,
        title = {'text': "Sentimen Positif (%)"},
        gauge = {'axis': {'range': [0, 100]},
                 'bar': {'color': "green"},
                 'steps': [
                     {'range': [0, neg_pct], 'color': "red"},
                     {'range': [neg_pct, neg_pct+neu_pct], 'color': "gray"},
                     {'range': [neg_pct+neu_pct, 100], 'color': "green"}]}))
    st.plotly_chart(fig_gauge