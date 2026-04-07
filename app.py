import streamlit as st
import pandas as pd
import requests
import os
import plotly.express as px
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from youtube import extract_video_id, fetch_comments_from_youtube
from sheets import write_label_to_sheet, read_labeled_data
from train import load_model

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
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
        color: #f8fafc; /* Brighter body text */
    }
    /* Metric Card Styling */
    div[data-testid="stMetricValue"] {
        background: rgba(255, 255, 255, 0.07);
        backdrop-filter: blur(12px);
        padding: 24px;
        border-radius: 18px;
        border: 1px solid rgba(255, 255, 255, 0.15);
        color: #60a5fa !important;
        font-weight: 800;
    }
    /* Sidebar text color */
    [data-testid="stSidebar"] {
        background-color: rgba(15, 23, 42, 0.98) !important;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label {
        color: #cbd5e1 !important;
        font-weight: 600;
    }
    /* Main Heading Glow */
    h1 {
        background: linear-gradient(90deg, #60a5fa, #93c5fd, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
        text-shadow: 0 0 20px rgba(96, 165, 250, 0.3);
    }
    /* Tab Styling */
    .stTabs [data-baseweb="tab"] {
        color: #94a3b8 !important;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        color: #60a5fa !important;
        border-bottom-color: #60a5fa !important;
    }
    /* Premium Button Styling */
    .stButton>button {
        background: linear-gradient(90deg, #3b82f6 0%, #2563eb 100%) !important;
        color: #ffffff !important;
        border-radius: 10px !important;
        border: none !important;
        padding: 0.6rem 2.5rem !important;
        font-weight: 700 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(37, 99, 235, 0.3) !important;
    }
    .stButton>button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(37, 99, 235, 0.5) !important;
    }
    /* Input field styling */
    .stTextInput>div>div>input {
        background-color: rgba(255, 255, 255, 0.05) !important;
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ---------------- RENDER ----------------

if not st.session_state["authenticated"]:
    # LOGIN PAGE
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
            <div style='text-align: center; background: rgba(25,25,25,0.4); padding: 40px; border-radius: 20px; border: 1px solid rgba(255,255,255,0.1);'>
                <h1>🛡️ Access Secured</h1>
                <p style='color: #94a3b8;'>Please enter the administrative password to enter the Sentiment Intelligence Center.</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.text_input("Password", type="password", key="password_input", on_change=login)
        st.button("Enter Dashboard", on_click=login)
        
    st.stop() # Prevent further execution if not logged in

# ---------------- DASHBOARD LOGIC (AUTHENTICATED) ----------------

st.title("🛡️ Sentiment Intelligence Center")

# ---------------- SIDEBAR ----------------

with st.sidebar:
    st.header("Configuration")
    employee_name = st.text_input("Employee Name", placeholder="e.g. Rani", key="emp_name_sidebar")
    api_key = st.text_input("YouTube API Key", type="password", key="yt_key_sidebar")
    
    st.divider()
    
    st.header("System Status")
    # On Streamlit Cloud, the "backend" is integrated
    st.success("System: Ready & Secure")

    if st.button("🚀 Retrain Model"):
        with st.spinner("Retraining..."):
             train_model()
             st.success("Model updated with latest data!")
        
    st.divider()
    if st.button("🚪 Logout"):
        logout()

# ---------------- MAIN TABS ----------------

tab_label, tab_analytics = st.tabs(["🏷️ Labeling Workspace", "📊 Visual Analytics"])

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