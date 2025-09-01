import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from googleapiclient.discovery import build
import os, re
from dotenv import load_dotenv

# ========================
# 1. Load ENV / Secrets
# ========================
if "YOUTUBE_API_KEY" in st.secrets:
    API_KEY = st.secrets["YOUTUBE_API_KEY"]
    APP_USERNAME = st.secrets["APP_USERNAME"]
    APP_PASSWORD = st.secrets["APP_PASSWORD"]
else:
    load_dotenv()
    API_KEY = os.getenv("YOUTUBE_API_KEY")
    APP_USERNAME = os.getenv("APP_USERNAME")
    APP_PASSWORD = os.getenv("APP_PASSWORD")

# ========================
# 2. Daftar URL Video Awal
# ========================
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

# ========================
# 3. Fungsi Utilitas
# ========================
def extract_video_id(url: str):
    """Ekstrak video ID dari URL YouTube"""
    match = re.search(r"v=([a-zA-Z0-9_-]{11})", url)
    if match:
        return match.group(1)
    match = re.search(r"youtu.be/([a-zA-Z0-9_-]{11})", url)
    if match:
        return match.group(1)
    return None

def get_comments(video_id, max_results=100):
    """Ambil komentar dari YouTube API"""
    youtube = build("youtube", "v3", developerKey=API_KEY)
    comments, dates = [], []
    request = youtube.commentThreads().list(
        part="snippet",
        videoId=video_id,
        maxResults=max_results,
        textFormat="plainText"
    )
    response = request.execute()
    for item in response["items"]:
        snippet = item["snippet"]["topLevelComment"]["snippet"]
        comments.append(snippet["textDisplay"])
        dates.append(snippet["publishedAt"])
    return comments, dates

def analyze_sentiment(comments, dates, video_label):
    """Analisis komentar dengan VADER"""
    analyzer = SentimentIntensityAnalyzer()
    results = []
    for c, d in zip(comments, dates):
        score = analyzer.polarity_scores(c)
        if score["compound"] >= 0.05:
            sentiment = "Positif"
        elif score["compound"] <= -0.05:
            sentiment = "Negatif"
        else:
            sentiment = "Netral"
        results.append([video_label, c, sentiment, score["compound"], d])
    return pd.DataFrame(results, columns=["Video", "Komentar", "Sentimen", "Skor", "Tanggal"])

@st.cache_data
def load_initial_data():
    """Load data awal dari daftar video"""
    all_data = []
    for idx, url in enumerate(video_urls, start=1):
        vid = extract_video_id(url)
        if vid:
            try:
                comments, dates = get_comments(vid, max_results=50)
                df = analyze_sentiment(comments, dates, f"Video {idx}")
                all_data.append(df)
            except Exception as e:
                st.warning(f"Gagal ambil data Video {idx}: {e}")
    if all_data:
        return pd.concat(all_data, ignore_index=True)
    return pd.DataFrame(columns=["Video","Komentar","Sentimen","Skor","Tanggal"])

# ========================
# 4. State Awal
# ========================
if "final_df" not in st.session_state:
    st.session_state["final_df"] = load_initial_data()
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ========================
# 5. Login Page
# ========================
if not st.session_state.logged_in:
    st.title("🔐 VoxMeter - Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username == APP_USERNAME and password == APP_PASSWORD:
            st.session_state.logged_in = True
        else:
            st.error("❌ Username/Password salah!")

# ========================
# 6. Main App (Setelah Login)
# ========================
else:
    # Styling biar logo nempel di atas sidebar
    st.markdown("""
        <style>
        [data-testid="stSidebar"] {
            padding-top: 0rem;
        }
        </style>
    """, unsafe_allow_html=True)

    # Sidebar custom
    st.sidebar.image("logo_voxmeter.png", width=120)
    st.sidebar.markdown("<h3 style='text-align:center;'>Administrator</h3>", unsafe_allow_html=True)

    menu = st.sidebar.radio("Menu", ["Dashboard", "Kelola Sentimen", "Dataset", "Logout"])
    df = st.session_state.final_df

    # -------------------- Dashboard --------------------
    if menu == "Dashboard":
        st.title("📊 Dashboard VoxMeter")
        if not df.empty:
            # Filter bulan & tahun
            col1, col2 = st.columns(2)
            bulan = col1.selectbox("Pilih Bulan", list(range(1,13)))
            tahun = col2.selectbox("Pilih Tahun", list(range(2020,2030)))

            df["Tanggal"] = pd.to_datetime(df["Tanggal"])
            df_filtered = df[(df["Tanggal"].dt.month == bulan) & (df["Tanggal"].dt.year == tahun)]
            counts = df_filtered["Sentimen"].value_counts()

            # Ringkasan angka
            c1, c2, c3 = st.columns(3)
            c1.metric("Sentimen Positif", counts.get("Positif",0))
            c2.metric("Sentimen Netral", counts.get("Netral",0))
            c3.metric("Sentimen Negatif", counts.get("Negatif",0))

            # Grafik tren per hari
            daily = df_filtered.groupby(df_filtered["Tanggal"].dt.date)["Sentimen"].count()
            st.line_chart(daily)

            # Donut chart
            fig, ax = plt.subplots()
            ax.pie(counts, labels=counts.index, autopct='%1.1f%%', startangle=90,
                   wedgeprops=dict(width=0.4))
            ax.axis("equal")
            st.pyplot(fig)
        else:
            st.info("Belum ada data.")

    # -------------------- Kelola Sentimen --------------------
    elif menu == "Kelola Sentimen":
        st.title("🗂️ Kelola Sentimen")
        search = st.text_input("🔍 Cari komentar...")
        df_filtered = df[df["Komentar"].str.contains(search, case=False)] if search else df
        st.dataframe(df_filtered, use_container_width=True)

        col1, col2, col3 = st.columns(3)
        col1.download_button("📄 Export CSV", df.to_csv(index=False), "sentimen.csv", "text/csv")
        col2.download_button("📊 Export Excel", df.to_excel("sentimen.xlsx", index=False), "sentimen.xlsx")
        col3.download_button("📕 Export PDF", df.to_csv(index=False), "sentimen.pdf")

    # -------------------- Dataset --------------------
    elif menu == "Dataset":
        st.title("📂 Dataset Per Video")
        if not df.empty:
            stats = df.groupby("Video").size()
            for v, n in stats.items():
                st.metric(v, n)

        st.subheader("➕ Tambah Video Baru")
        new_url = st.text_input("Masukkan URL Video YouTube")
        if st.button("Analisis Video Baru"):
            vid = extract_video_id(new_url)
            if vid:
                comments, dates = get_comments(vid)
                new_df = analyze_sentiment(comments, dates, f"Video {len(df['Video'].unique())+1}")
                st.session_state.final_df = pd.concat([st.session_state.final_df, new_df], ignore_index=True)
                st.success("Video berhasil dianalisis & ditambahkan!")
            else:
                st.error("URL tidak valid")

    # -------------------- Logout --------------------
    elif menu == "Logout":
        st.session_state.logged_in = False
        st.experimental_rerun()