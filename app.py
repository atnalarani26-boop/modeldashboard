import streamlit as st
import sqlite3
import pandas as pd
import joblib
from sklearn.linear_model import SGDClassifier
from sklearn.feature_extraction.text import HashingVectorizer
from googleapiclient.discovery import build

# -----------------------------
# DATABASE
# -----------------------------

conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS comments(
id INTEGER PRIMARY KEY AUTOINCREMENT,
video_id TEXT,
comment_text TEXT UNIQUE
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS labels(
id INTEGER PRIMARY KEY AUTOINCREMENT,
comment_id INTEGER,
employee_name TEXT,
label TEXT
)
""")

conn.commit()

# -----------------------------
# MODEL
# -----------------------------

classes = ["negative", "neutral", "positive"]

vectorizer = HashingVectorizer(
    n_features=2**18,
    alternate_sign=False
)

try:
    model = joblib.load("model.pkl")
except:
    model = SGDClassifier(loss="log_loss")

# -----------------------------
# YOUTUBE FUNCTIONS
# -----------------------------

def extract_video_id(url):

    if "watch?v=" in url:
        return url.split("watch?v=")[1]

    if "youtu.be/" in url:
        return url.split("youtu.be/")[1]


def fetch_comments(api_key, video_id):

    youtube = build("youtube", "v3", developerKey=api_key)

    comments = []
    next_page = None

    while True:

        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=100,
            textFormat="plainText",
            pageToken=next_page
        )

        response = request.execute()

        for item in response["items"]:

            text = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
            comments.append(text)

        next_page = response.get("nextPageToken")

        if not next_page:
            break

    return comments

# -----------------------------
# MODEL UPDATE
# -----------------------------

def update_model(comment, label):

    X = vectorizer.transform([comment])

    model.partial_fit(
        X,
        [label],
        classes=classes
    )

    joblib.dump(model, "model.pkl")

# -----------------------------
# STREAMLIT UI
# -----------------------------

st.title("Film Sentiment Labeling Dashboard")

employee_name = st.text_input("Employee Name")

api_key = st.text_input("YouTube API Key")

video_url = st.text_input("YouTube Video URL")

# -----------------------------
# LOAD COMMENTS
# -----------------------------

if st.button("Load Comments"):

    video_id = extract_video_id(video_url)

    comments = fetch_comments(api_key, video_id)

    inserted = 0

    for c in comments:

        try:
            cursor.execute(
            "INSERT INTO comments(video_id,comment_text) VALUES(?,?)",
            (video_id, c)
            )
            inserted += 1

        except:
            pass

    conn.commit()

    # reset session comments
    if "comments_list" in st.session_state:
        del st.session_state.comments_list
        del st.session_state.index

    st.success(f"{inserted} comments loaded")

# -----------------------------
# LOAD COMMENTS INTO SESSION
# -----------------------------

if "comments_list" not in st.session_state:

    comments_df = pd.read_sql("""

    SELECT *
    FROM comments
    WHERE id NOT IN (SELECT comment_id FROM labels)

    """, conn)

    st.session_state.comments_list = comments_df
    st.session_state.index = 0

# -----------------------------
# REMAINING COUNT
# -----------------------------

remaining = len(st.session_state.comments_list) - st.session_state.index

st.write("Comments Remaining:", remaining)

# -----------------------------
# DISPLAY COMMENT
# -----------------------------

if st.session_state.index < len(st.session_state.comments_list):

    row = st.session_state.comments_list.iloc[st.session_state.index]

    comment_id = row["id"]
    comment_text = row["comment_text"]

    st.subheader("Comment")
    st.write(comment_text)

    X = vectorizer.transform([comment_text])

    try:

        pred = model.predict(X)[0]
        confidence = model.predict_proba(X).max()

        st.write("Model Prediction:", pred)
        st.write("Confidence:", round(confidence, 3))

    except:

        st.write("Model Prediction: None")

    col1, col2, col3 = st.columns(3)

    # -----------------------------
    # POSITIVE
    # -----------------------------

    if col1.button("Positive"):

        cursor.execute(
        "INSERT INTO labels(comment_id,employee_name,label) VALUES(?,?,?)",
        (comment_id, employee_name, "positive")
        )

        conn.commit()

        update_model(comment_text, "positive")

        st.session_state.index += 1

        st.rerun()

    # -----------------------------
    # NEUTRAL
    # -----------------------------

    if col2.button("Neutral"):

        cursor.execute(
        "INSERT INTO labels(comment_id,employee_name,label) VALUES(?,?,?)",
        (comment_id, employee_name, "neutral")
        )

        conn.commit()

        update_model(comment_text, "neutral")

        st.session_state.index += 1

        st.rerun()

    # -----------------------------
    # NEGATIVE
    # -----------------------------

    if col3.button("Negative"):

        cursor.execute(
        "INSERT INTO labels(comment_id,employee_name,label) VALUES(?,?,?)",
        (comment_id, employee_name, "negative")
        )

        conn.commit()

        update_model(comment_text, "negative")

        st.session_state.index += 1

        st.rerun()

else:

    st.success("All comments labeled")
    
# -----------------------------
# EMPLOYEE PERFORMANCE REPORT
# -----------------------------

st.divider()
st.header("📊 My Performance Report")

if employee_name:

    # -----------------------------
    # EMPLOYEE STATS
    # -----------------------------

    report = pd.read_sql(f"""
    SELECT 
        COUNT(*) as total_labels,
        SUM(label='positive') as positive,
        SUM(label='neutral') as neutral,
        SUM(label='negative') as negative
    FROM labels
    WHERE employee_name = '{employee_name}'
    """, conn)

    total = int(report.iloc[0]["total_labels"])

    if total > 0:

        positive = int(report.iloc[0]["positive"])
        neutral = int(report.iloc[0]["neutral"])
        negative = int(report.iloc[0]["negative"])

        # -----------------------------
        # TOTAL DATASET SIZE
        # -----------------------------

        total_comments = pd.read_sql("""
        SELECT COUNT(*) as total FROM comments
        """, conn).iloc[0]["total"]

        # -----------------------------
        # CALCULATIONS
        # -----------------------------

        contribution = round((total / total_comments) * 100, 2) if total_comments > 0 else 0

        pos_pct = round((positive / total) * 100, 1)
        neu_pct = round((neutral / total) * 100, 1)
        neg_pct = round((negative / total) * 100, 1)

        # -----------------------------
        # DISPLAY METRICS
        # -----------------------------

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Total Labels", total)
        col2.metric("Positive", f"{positive} ({pos_pct}%)")
        col3.metric("Neutral", f"{neutral} ({neu_pct}%)")
        col4.metric("Negative", f"{negative} ({neg_pct}%)")

        # -----------------------------
        # PROGRESS BAR
        # -----------------------------

        st.progress(contribution / 100)
        st.write(f"📈 Contribution to dataset: **{contribution}%**")

        # -----------------------------
        # EMPLOYEE DATA TABLE
        # -----------------------------

        st.subheader("📝 Your Labeled Comments")

        dataset = pd.read_sql(f"""
        SELECT comments.comment_text, labels.label
        FROM labels
        JOIN comments ON comments.id = labels.comment_id
        WHERE labels.employee_name = '{employee_name}'
        """, conn)

        st.dataframe(dataset)

        # -----------------------------
        # DOWNLOAD REPORT
        # -----------------------------

        csv = dataset.to_csv(index=False)

        st.download_button(
            "⬇️ Download My Report",
            csv,
            f"{employee_name}_report.csv",
            "text/csv"
        )

    else:
        st.info("Start labeling to generate your report 🚀")

else:
    st.warning("Enter your name to view report")