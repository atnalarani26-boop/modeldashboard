import streamlit as st
import sqlite3
import pandas as pd

conn = sqlite3.connect("database.db")

st.title("📊 Admin Analytics Dashboard")

# -----------------------------
# AUTH
# -----------------------------

password = st.text_input("Admin Password", type="password")

if password != "admin123":
    st.warning("Enter correct password")
    st.stop()

# -----------------------------
# REFRESH BUTTON
# -----------------------------

if st.button("🔄 Refresh Data"):
    st.rerun()

# -----------------------------
# TOTAL DATASET SIZE
# -----------------------------

total_labels = pd.read_sql(
    "SELECT COUNT(*) as total FROM labels",
    conn
)

st.metric("Total Labeled Comments", total_labels.iloc[0]["total"])

# -----------------------------
# EMPLOYEE PERFORMANCE
# -----------------------------

st.subheader("👨‍💻 Employee Performance")

employee_report = pd.read_sql("""

SELECT 
employee_name,
COUNT(*) as total_labels,
SUM(label='positive') as positive,
SUM(label='neutral') as neutral,
SUM(label='negative') as negative

FROM labels
GROUP BY employee_name

""", conn)

st.dataframe(employee_report)

# -----------------------------
# EMPLOYEE CURRENT VIDEO
# -----------------------------

st.subheader("🎬 Current Work (Video Assignment)")

video_report = pd.read_sql("""

SELECT 
employee_video.employee_name,
employee_video.video_id

FROM employee_video

""", conn)

st.dataframe(video_report)

# -----------------------------
# VIDEO-WISE DATASET SIZE
# -----------------------------

st.subheader("📺 Video-wise Dataset")

video_stats = pd.read_sql("""

SELECT 
video_id,
COUNT(*) as total_comments

FROM comments
GROUP BY video_id

""", conn)

st.dataframe(video_stats)

# -----------------------------
# LABEL DISTRIBUTION
# -----------------------------

st.subheader("📊 Overall Sentiment Distribution")

dist = pd.read_sql("""

SELECT 
label,
COUNT(*) as count

FROM labels
GROUP BY label

""", conn)

st.bar_chart(dist.set_index("label"))

# -----------------------------
# DOWNLOAD EMPLOYEE REPORT
# -----------------------------

st.subheader("⬇️ Download Reports")

csv_report = employee_report.to_csv(index=False)

st.download_button(
    "Download Employee Report",
    csv_report,
    "employee_report.csv",
    "text/csv"
)

# -----------------------------
# DOWNLOAD FULL DATASET
# -----------------------------

dataset = pd.read_sql("""

SELECT 
comments.comment_text,
labels.label,
labels.employee_name,
comments.video_id

FROM labels
JOIN comments
ON comments.id = labels.comment_id

""", conn)

csv_dataset = dataset.to_csv(index=False)

st.download_button(
    "Download Full Dataset",
    csv_dataset,
    "sentiment_dataset.csv",
    "text/csv"
)