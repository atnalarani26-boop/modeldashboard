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

# --- CONFIG ---
API_URL = os.environ.get("API_URL", "http://localhost:5000")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

st.set_page_config(page_title="Sentiment Intelligence Center", layout="wide")

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
        color: #e2e8f0;
    }
    div[data-testid="stMetricValue"] {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        padding: 20px;
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        color: #60a5fa !important;
    }
    [data-testid="stSidebar"] {
        background-color: rgba(15, 23, 42, 0.95) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }
    .stButton>button {
        background: linear-gradient(90deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 2rem;
        font-weight: 600;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4);
    }
    h1 {
        background: linear-gradient(90deg, #60a5fa, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
    }
    /* Glassmorphism Login Card */
    .login-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(20px);
        padding: 40px;
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        text-align: center;
        max-width: 400px;
        margin: auto;
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
            <div style='text-align: center;'>
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
    employee_name = st.text_input("Employee Name", placeholder="e.g. John Doe")
    api_key = st.text_input("YouTube API Key", type="password")
    
    st.divider()
    
    st.header("System Status")
    try:
        response = requests.get(f"{API_URL}/health", timeout=1)
        if response.status_code == 200:
            st.success("Backend: Online")
        else:
            st.error("Backend: Error")
    except:
        st.error("Backend: Offline")

    if st.button("🚀 Retrain Model"):
        requests.post(f"{API_URL}/train")
        st.info("Retraining started...")
        
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