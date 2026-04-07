import streamlit as st
import pandas as pd
import requests
import os
import plotly.express as px
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from youtube import extract_video_id, fetch_comments_from_youtube
from sheets import write_label_to_sheet, read_labeled_data
from train import load_model, train_model

# --- CONFIG & SECRETS ---
try:
    # Prioritize Streamlit Cloud Secrets
    ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]
    GOOGLE_CREDENTIALS_BASE64 = st.secrets["GOOGLE_CREDENTIALS_BASE64"]
except:
    # Fallback to local environment variables
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
    GOOGLE_CREDENTIALS_BASE64 = os.environ.get("GOOGLE_CREDENTIALS_BASE64", "")

API_URL = os.environ.get("API_URL", "http://localhost:5000")

st.set_page_config(
    page_title="Sentiment Intelligence Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------- AUTH LOGIC ----------------

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

def login():
    if st.session_state["password_input"] == ADMIN_PASSWORD:
        st.session_state["authenticated"] = True
    else:
        st.error("Invalid password. Please try again.")

def logout():
    st.session_state["authenticated"] = False
    st.rerun()

# ---------------- PREMIUM STYLING ----------------
st.markdown("""
    <style>
    /* Premium 3D Depth Theme */
    .stApp {
        background-color: #f0f4f8;
        color: #2c3e50;
    }
    /* 3D Floating Sidebar */
    [data-testid="stSidebar"] {
        background: white !important;
        box-shadow: 10px 0 30px rgba(0,0,0,0.05) !important;
        border-radius: 0 30px 30px 0 !important;
        margin: 20px 20px 20px 0 !important;
        height: calc(100vh - 40px) !important;
    }
    /* Neumorphic Metric Cards */
    div[data-testid="stMetricValue"] {
        background: white;
        box-shadow: 8px 8px 16px #d1d9e6, -8px -8px 16px #ffffff;
        padding: 25px;
        border-radius: 20px;
        color: #3498db !important;
        font-weight: 800;
        border: none;
    }
    /* 3D Soft Buttons */
    .stButton>button {
        background: #ffffff !important;
        color: #3498db !important;
        border-radius: 12px !important;
        box-shadow: 5px 5px 10px #d1d9e6, -5px -5px 10px #ffffff !important;
        width: 100% !important;
        height: 3.5rem !important;
        font-weight: 700 !important;
        border: 2px solid transparent !important;
        transition: all 0.2s ease !important;
    }
    .stButton>button:active {
        box-shadow: inset 5px 5px 10px #d1d9e6, inset -5px -5px 10px #ffffff !important;
    }
    .stButton>button:hover {
        border: 2px solid #3498db !important;
    }
    /* 3D Floating Headings */
    h1 {
        color: #2c3e50 !important;
        font-weight: 900 !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        padding: 20px;
        background: white;
        border-radius: 15px;
        box-shadow: 4px 4px 10px rgba(0,0,0,0.02);
    }
    /* Input Depth */
    .stTextInput>div>div>input {
        background: #ffffff !important;
        box-shadow: inset 4px 4px 8px #d1d9e6, inset -4px -4px 8px #ffffff !important;
        border-radius: 12px !important;
        border: none !important;
        color: #2c3e50 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ---------------- RENDER ----------------

if not st.session_state["authenticated"]:
    # 3D LOGIN CARD
    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.3, 1])
    with col2:
        st.markdown("""
            <div style='background: white; padding: 40px; border-radius: 25px; box-shadow: 20px 20px 60px #d1d9e6, -20px -20px 60px #ffffff; text-align: center;'>
                <h1 style='box-shadow: none; padding: 0;'>🔐 Portal Login</h1>
                <p style='color: #7f8c8d; margin-top: 10px;'>Secure Depth Interface Access</p>
            </div>
        """, unsafe_allow_html=True)
        st.text_input("Access Password", type="password", key="password_input", on_change=login)
        st.button("Launch System", on_click=login)
    st.stop()

# ---------------- DASHBOARD LOGIC (AUTHENTICATED) ----------------

st.markdown("<h1>🌟 Sentiment Analytic Intelligence</h1>", unsafe_allow_html=True)

# ---------------- SIDEBAR ----------------

with st.sidebar:
    st.markdown("<div style='text-align: center;'><img src='https://cdn-icons-png.flaticon.com/512/1041/1041916.png' width='100'></div>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; color: #2c3e50;'>Operator Control</h2>", unsafe_allow_html=True)
    employee_name = st.text_input("Name", placeholder="e.g. Rani", key="emp_name_sidebar")
    api_key = st.text_input("Key", type="password", key="yt_key_sidebar")
    
    st.divider()
    if st.button("Close Session"):
        logout()

# ---------------- MAIN TABS ----------------

tab_label, tab_analytics = st.tabs(["🧩 Labeling Factory", "📋 Global Management Leaderboard"])

# ---------------- TAB 1: LABELING ----------------

with tab_label:
    video_url = st.text_input("YouTube Video URL", placeholder="https://www.youtube.com/watch?v=...")

    if st.button("🔍 Fetch Comments"):
        if not employee_name or not api_key:
            st.error("Please fill in Configuration in sidebar")
        else:
            video_id = extract_video_id(video_url)
            if video_id:
                with st.spinner("Fetching..."):
                    comments = fetch_comments_from_youtube(api_key, video_id)
                    if comments:
                        st.session_state['comments_df'] = pd.DataFrame({
                            "comment": comments,
                            "label": ["" for _ in comments],
                            "video_id": [video_id for _ in comments]
                        })
            else:
                st.error("Invalid URL")

    if 'comments_df' in st.session_state:
        df = st.session_state['comments_df']
        
        if st.checkbox("Enable AI Assistance"):
            with st.spinner("Analyzing..."):
                preds = []
                for c in df["comment"][:20]: # Limit for demo speed
                    try:
                        res = requests.post(f"{API_URL}/predict", json={"text": c}, timeout=1).json()
                        preds.append(f"{res['sentiment']} ({res['confidence']:.2f})")
                    except: preds.append("N/A")
                if len(preds) < len(df): preds.extend(["N/A"] * (len(df)-len(preds)))
                df["AI Suggestion"] = preds

        edited_df = st.data_editor(
            df,
            column_config={
                "label": st.column_config.SelectboxColumn("Label", options=["positive", "neutral", "negative", ""]),
                "comment": st.column_config.TextColumn("Comment", width="large")
            },
            disabled=["comment", "AI Suggestion", "video_id"],
            use_container_width=True
        )

        if st.button("💾 Save to Google Sheets"):
            labeled = edited_df[edited_df["label"] != ""]
            if not labeled.empty:
                for _, row in labeled.iterrows():
                    write_label_to_sheet(row["comment"], row["label"], employee_name, row["video_id"])
                st.success("Saved! Model retraining triggered.")
                requests.post(f"{API_URL}/train")

# ---------------- TAB 2: ANALYTICS ----------------

with tab_analytics:
    st.header("Global Sentiment Insights")
    
    if st.button("🔄 Refresh Data Insights"):
        with st.spinner("Calculating metrics..."):
            all_data = read_labeled_data()
            
            if not all_data.empty:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Labeled", len(all_data))
                with col2:
                    pos_rate = len(all_data[all_data["Label"] == "positive"]) / len(all_data)
                    st.metric("Positive Rate", f"{pos_rate:.1%}")
                with col3:
                    unique_videos = all_data["Video ID"].nunique()
                    st.metric("Videos Processed", unique_videos)

                st.divider()

                col_left, col_right = st.columns(2)

                with col_left:
                    st.subheader("Sentiment Distribution")
                    fig_pie = px.pie(all_data, names='Label', hole=0.4, 
                                     color='Label',
                                     color_discrete_map={'positive':'#10b981', 'neutral':'#6b7280', 'negative':'#ef4444'})
                    fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="#f8fafc")
                    st.plotly_chart(fig_pie, use_container_width=True)

                with col_right:
                    st.subheader("Employee Productivity")
                    emp_counts = all_data["Employee"].value_counts().reset_index()
                    emp_counts.columns = ["Employee", "Count"]
                    fig_bar = px.bar(emp_counts, x="Employee", y="Count", color="Count", color_continuous_scale="Viridis")
                    fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="#f8fafc")
                    st.plotly_chart(fig_bar, use_container_width=True)

                st.divider()
                
                st.subheader("Comment Word Cloud")
                text = " ".join(all_data["Comment"].astype(str).tolist())
                if text.strip():
                    wc = WordCloud(width=800, height=400, background_color=None, mode="RGBA", colormap="Blues").generate(text)
                    plt.figure(figsize=(10, 5))
                    plt.imshow(wc, interpolation='bilinear')
                    plt.axis("off")
                    st.pyplot(plt)
                else:
                    st.info("Not enough text for Word Cloud")

            else:
                st.info("No data found in Google Sheets. Start labeling first!")