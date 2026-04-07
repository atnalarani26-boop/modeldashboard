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
    /* Modern Business Light Theme */
    .stApp {
        background-color: #f8fafc;
        color: #1e293b;
    }
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e2e8f0;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] label {
        color: #0f172a !important;
    }
    /* Primary Large Action Button */
    .stButton>button {
        background-color: #2563eb !important;
        color: #ffffff !important;
        border-radius: 6px !important;
        width: 100% !important;
        height: 3rem !important;
        font-weight: 600 !important;
        border: none !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
    }
    .stButton>button:hover {
        background-color: #1d4ed8 !important;
        transform: translateY(-1px);
    }
    /* Input Fields */
    .stTextInput>div>div>input {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 6px !important;
    }
    /* Heading Style */
    h1 {
        color: #0f172a !important;
        font-weight: 800 !important;
        border-bottom: 2px solid #2563eb;
        padding-bottom: 10px;
    }
    h2, h3 {
        color: #334155 !important;
    }
    /* Data Frame Styling */
    [data-testid="stDataFrame"] {
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid #e2e8f0;
    }
    /* Metric Cards */
    div[data-testid="stMetricValue"] {
        color: #2563eb !important;
        font-weight: 700;
        background: white;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
    }
    </style>
    """, unsafe_allow_html=True)

# ---------------- RENDER ----------------

if not st.session_state["authenticated"]:
    # PROFESSIONAL LOGIN PAGE
    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("""
            <div style='background-color: white; padding: 40px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); border: 1px solid #e2e8f0;'>
                <h2 style='text-align: center; margin-top: 0;'>Secure Terminal Access</h2>
                <p style='text-align: center; color: #64748b;'>Enter administrative credentials to proceed</p>
            </div>
        """, unsafe_allow_html=True)
        st.text_input("Password", type="password", key="password_input", on_change=login)
        st.button("Validate Access", on_click=login)
    st.stop()

# ---------------- DASHBOARD LOGIC (AUTHENTICATED) ----------------

st.markdown("<h1>📊 Professional Sentiment Analytics Dashboard</h1>", unsafe_allow_html=True)

# ---------------- SIDEBAR ----------------

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1041/1041916.png", width=80) 
    st.header("Operator Panel")
    employee_name = st.text_input("Full Name", placeholder="e.g. Rani", key="emp_name_sidebar")
    api_key = st.text_input("System Access Key", type="password", key="yt_key_sidebar")
    
    st.divider()
    if st.button("Logout from Session"):
        logout()

# ---------------- MAIN TABS ----------------

tab_label, tab_analytics = st.tabs(["📝 Data Collection & Labeling", "👨‍💻 Management Report"])

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