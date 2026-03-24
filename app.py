import streamlit as st
import sqlite3
import pandas as pd
import joblib
import os

from sklearn.linear_model import SGDClassifier
from sklearn.feature_extraction.text import HashingVectorizer
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from urllib.parse import urlparse, parse_qs

# ---------------- DATABASE ----------------

DB_PATH = os.path.join(os.getcwd(), "database.db")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

# ---------------- TABLES ----------------

cursor.execute("""CREATE TABLE IF NOT EXISTS comments(
id INTEGER PRIMARY KEY AUTOINCREMENT,
video_id TEXT,
comment_text TEXT UNIQUE
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS labels(
id INTEGER PRIMARY KEY AUTOINCREMENT,
comment_id INTEGER,
employee_name TEXT,
label TEXT
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS videos(
video_id TEXT PRIMARY KEY,
loaded_by TEXT
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS employee_video(
employee_name TEXT PRIMARY KEY,
video_id TEXT
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS employee_progress(
employee_name TEXT PRIMARY KEY,
last_index INTEGER
)""")

conn.commit()

# ---------------- MODEL ----------------

classes = ["negative","neutral","positive"]

vectorizer = HashingVectorizer(n_features=2**18, alternate_sign=False)

try:
    model = joblib.load("model.pkl")
except:
    model = SGDClassifier(loss="log_loss")

# ---------------- FUNCTIONS ----------------

def extract_video_id(url):
    try:
        parsed_url = urlparse(url)

        if "youtube.com" in url:
            return parse_qs(parsed_url.query).get("v", [None])[0]

        if "youtu.be" in url:
            return parsed_url.path.split("/")[1]

    except:
        return None

def fetch_comments(api_key, video_id):

    youtube = build("youtube","v3",developerKey=api_key)

    comments=[]
    next_page=None

    while True:
        try:
            request = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=100,
                textFormat="plainText",
                pageToken=next_page
            )

            response = request.execute()

        except HttpError as e:
            st.error(f"YouTube API Error: {e}")
            return []

        for item in response.get("items", []):
            text=item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
            comments.append(text)

        next_page=response.get("nextPageToken")

        if not next_page:
            break

    return comments

def is_video_loaded(video_id):
    df = pd.read_sql("SELECT * FROM videos WHERE video_id=?",conn,params=(video_id,))
    return len(df)>0

def get_employee_video(employee_name):
    df = pd.read_sql("SELECT video_id FROM employee_video WHERE employee_name=?",conn,params=(employee_name,))
    return df.iloc[0]["video_id"] if len(df)>0 else None

# ---------------- UI ----------------

st.title("Film Sentiment Labeling Dashboard")

employee_name = st.text_input("Employee Name")
api_key = st.text_input("YouTube API Key")
video_url = st.text_input("YouTube Video URL")

# ---------------- LOAD VIDEO ----------------

if st.button("Load Comments"):

    video_id = extract_video_id(video_url)

    # 🔥 VALIDATION
    if not video_id:
        st.error("Invalid YouTube URL")
        st.stop()

    if len(video_id) != 11:
        st.error("Invalid Video ID extracted")
        st.stop()

    if is_video_loaded(video_id):
        existing = pd.read_sql("SELECT loaded_by FROM videos WHERE video_id=?",conn,params=(video_id,))
        st.warning(f"Already loaded by {existing.iloc[0]['loaded_by']}")
    else:
        comments = fetch_comments(api_key,video_id)

        if not comments:
            st.warning("No comments found or API error")
            st.stop()

        for c in comments:
            try:
                cursor.execute(
                    "INSERT INTO comments(video_id,comment_text) VALUES(?,?)",
                    (video_id,c)
                )
            except:
                pass

        cursor.execute(
            "INSERT INTO videos(video_id,loaded_by) VALUES(?,?)",
            (video_id,employee_name)
        )
        conn.commit()

        st.success(f"{len(comments)} comments loaded")

    # assign video to employee
    existing = cursor.execute(
        "SELECT * FROM employee_video WHERE employee_name=?",
        (employee_name,)
    ).fetchone()

    if existing:
        cursor.execute(
            "UPDATE employee_video SET video_id=? WHERE employee_name=?",
            (video_id, employee_name)
        )
    else:
        cursor.execute(
            "INSERT INTO employee_video(employee_name,video_id) VALUES(?,?)",
            (employee_name, video_id)
        )

    conn.commit()

# ---------------- LOAD DATA ----------------

current_video = get_employee_video(employee_name)

if current_video:

    df = pd.read_sql("""
    SELECT comments.id,comments.comment_text,labels.label
    FROM comments
    LEFT JOIN labels ON comments.id=labels.comment_id
    WHERE comments.video_id=?
    """,conn,params=(current_video,))

    df["label"] = df["label"].fillna("")

    X = vectorizer.transform(df["comment_text"])

    try:
        df["prediction"] = model.predict(X)
        df["confidence"] = model.predict_proba(X).max(axis=1)
    except:
        df["prediction"] = ""
        df["confidence"] = ""

    edited_df = st.data_editor(
        df,
        column_config={
            "label": st.column_config.SelectboxColumn(
                "Label",
                options=["","positive","neutral","negative"]
            )
        },
        disabled=["id","comment_text","prediction","confidence"]
    )

    if st.button("Save Labels"):

        batch_texts=[]
        batch_labels=[]

        for _, row in edited_df.iterrows():

            if row["label"]!="":

                existing = cursor.execute(
                    "SELECT * FROM labels WHERE comment_id=?",
                    (row["id"],)
                ).fetchone()

                if existing:
                    cursor.execute(
                        "UPDATE labels SET label=? WHERE comment_id=?",
                        (row["label"],row["id"])
                    )
                else:
                    cursor.execute(
                        "INSERT INTO labels(comment_id,employee_name,label) VALUES(?,?,?)",
                        (row["id"],employee_name,row["label"])
                    )

                batch_texts.append(row["comment_text"])
                batch_labels.append(row["label"])

        conn.commit()

        if batch_texts:
            X_batch = vectorizer.transform(batch_texts)
            model.partial_fit(X_batch,batch_labels,classes=classes)
            joblib.dump(model,"model.pkl")

        st.success("Labels saved & model updated")