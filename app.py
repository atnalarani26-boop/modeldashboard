import streamlit as st
import sqlite3
import pandas as pd
import joblib
from sklearn.linear_model import SGDClassifier
from sklearn.feature_extraction.text import HashingVectorizer
from googleapiclient.discovery import build

# ---------------- DATABASE ----------------

conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

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
    if "watch?v=" in url:
        return url.split("watch?v=")[1]
    if "youtu.be/" in url:
        return url.split("youtu.be/")[1]

def fetch_comments(api_key, video_id):

    youtube = build("youtube","v3",developerKey=api_key)

    comments=[]
    next_page=None

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
            text=item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
            comments.append(text)

        next_page=response.get("nextPageToken")

        if not next_page:
            break

    return comments

def update_model(text,label):
    X = vectorizer.transform([text])
    model.partial_fit(X,[label],classes=classes)
    joblib.dump(model,"model.pkl")

def is_video_loaded(video_id):
    df = pd.read_sql("SELECT * FROM videos WHERE video_id=?",conn,params=(video_id,))
    return len(df)>0

def get_employee_video(employee_name):
    df = pd.read_sql("SELECT video_id FROM employee_video WHERE employee_name=?",conn,params=(employee_name,))
    return df.iloc[0]["video_id"] if len(df)>0 else None

def save_progress(employee_name,index):
    cursor.execute("""
    INSERT INTO employee_progress(employee_name,last_index)
    VALUES(?,?)
    ON CONFLICT(employee_name)
    DO UPDATE SET last_index=excluded.last_index
    """,(employee_name,index))
    conn.commit()

def load_progress(employee_name):
    df = pd.read_sql("SELECT last_index FROM employee_progress WHERE employee_name=?",conn,params=(employee_name,))
    return int(df.iloc[0]["last_index"]) if len(df)>0 else 0

# ---------------- UI ----------------

st.title("Film Sentiment Labeling Dashboard")

employee_name = st.text_input("Employee Name")
api_key = st.text_input("YouTube API Key")
video_url = st.text_input("YouTube Video URL")

# ---------------- LOAD VIDEO ----------------

if st.button("Load Comments"):

    video_id = extract_video_id(video_url)

    if is_video_loaded(video_id):

        existing = pd.read_sql("SELECT loaded_by FROM videos WHERE video_id=?",conn,params=(video_id,))
        st.warning(f"⚠️ Already loaded by {existing.iloc[0]['loaded_by']}")

    else:

        comments = fetch_comments(api_key,video_id)

        for c in comments:
            try:
                cursor.execute("INSERT INTO comments(video_id,comment_text) VALUES(?,?)",(video_id,c))
            except:
                pass

        cursor.execute("INSERT INTO videos(video_id,loaded_by) VALUES(?,?)",(video_id,employee_name))

        conn.commit()

        st.success(f"{len(comments)} comments loaded")

    # set employee video
    cursor.execute("""
    INSERT INTO employee_video(employee_name,video_id)
    VALUES(?,?)
    ON CONFLICT(employee_name)
    DO UPDATE SET video_id=excluded.video_id
    """,(employee_name,video_id))
    conn.commit()

    # reset session
    st.session_state.index = 0

# ---------------- GET CURRENT VIDEO ----------------

current_video = get_employee_video(employee_name)

if current_video:
    st.write("Current Video:", current_video)

# ---------------- LOAD COMMENTS ----------------

if current_video:

    df = pd.read_sql("""
    SELECT comments.id,comments.comment_text,labels.label
    FROM comments
    LEFT JOIN labels ON comments.id=labels.comment_id
    WHERE comments.video_id=?
    """,conn,params=(current_video,))

    df["label"] = df["label"].fillna("")

    # predictions
    X = vectorizer.transform(df["comment_text"])
    try:
        df["prediction"] = model.predict(X)
        df["confidence"] = model.predict_proba(X).max(axis=1)
    except:
        df["prediction"] = ""
        df["confidence"] = ""

    # load progress
    if "index" not in st.session_state:
        st.session_state.index = load_progress(employee_name)

    st.write("Current Position:", st.session_state.index)

    # ---------------- PAUSE / RESUME ----------------

    colp1,colp2 = st.columns(2)

    if colp1.button("Pause"):
        save_progress(employee_name, st.session_state.index)
        st.warning("Progress saved")

    if colp2.button("Resume"):
        st.session_state.index = load_progress(employee_name)
        st.success("Resumed")

    # ---------------- DATA TABLE ----------------

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

    # ---------------- SAVE ----------------

    if st.button("Save Labels"):

        for _, row in edited_df.iterrows():

            if row["label"] != "":

                existing = pd.read_sql(
                    "SELECT * FROM labels WHERE comment_id=?",
                    conn,
                    params=(row["id"],)
                )

                if len(existing)>0:
                    cursor.execute("UPDATE labels SET label=? WHERE comment_id=?",(row["label"],row["id"]))
                else:
                    cursor.execute("INSERT INTO labels(comment_id,employee_name,label) VALUES(?,?,?)",
                                   (row["id"],employee_name,row["label"]))

                update_model(row["comment_text"],row["label"])

        conn.commit()

        save_progress(employee_name, st.session_state.index)

        st.success("Saved & Model Updated")