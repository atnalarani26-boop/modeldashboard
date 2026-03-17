import streamlit as st
import sqlite3
from sklearn.linear_model import SGDClassifier
import numpy as np

# -----------------------------
# DATABASE SETUP (FIXED)
# -----------------------------

def get_db():
    conn = sqlite3.connect('comments.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(conn):
    conn.execute("""
    CREATE TABLE IF NOT EXISTS comments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        comment_text TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS labels(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        comment_id INTEGER,
        label INTEGER
    )
    """)

    conn.commit()

def fetch_next_comment(conn):
    return conn.execute("""
        SELECT c.id, c.comment_text
        FROM comments c
        LEFT JOIN labels l ON c.id = l.comment_id
        WHERE l.comment_id IS NULL
        ORDER BY c.id ASC
        LIMIT 1
    """).fetchone()

def save_label(conn, comment_id, label):
    conn.execute(
        "INSERT INTO labels (comment_id, label) VALUES (?, ?)",
        (comment_id, label)
    )
    conn.commit()

# -----------------------------
# MODEL (AUTO LEARNING)
# -----------------------------

def init_model():
    if "model" not in st.session_state:
        st.session_state.model = SGDClassifier(loss="log_loss")
        st.session_state.training_buffer = []
        st.session_state.model_initialized = False

def update_model(comment_text, label):

    X = np.array([[hash(comment_text) % 10000]])
    y = np.array([label])

    st.session_state.training_buffer.append((X, y))

    if len(st.session_state.training_buffer) >= 10:

        X_batch = np.vstack([x for x, _ in st.session_state.training_buffer])
        y_batch = np.array([y for _, y in st.session_state.training_buffer])

        model = st.session_state.model

        if not st.session_state.model_initialized:
            model.partial_fit(X_batch, y_batch, classes=np.array([0,1,2]))
            st.session_state.model_initialized = True
        else:
            model.partial_fit(X_batch, y_batch)

        st.session_state.training_buffer.clear()
        st.success("✅ Model updated")

# -----------------------------
# APP START
# -----------------------------

st.title("🎬 Employee Comment Labeling Dashboard")

conn = get_db()
init_db(conn)   # 🔥 FIX: ensures tables exist
init_model()

# -----------------------------
# OPTIONAL: ADD SAMPLE DATA
# -----------------------------

if st.button("Load Sample Comments"):
    sample_comments = [
        "Great movie!",
        "Worst experience ever",
        "It was okay, not bad",
        "Amazing acting!",
        "I didn't like the ending",
        "Fantastic direction!",
        "Average storyline",
        "Loved the visuals!",
        "Too slow and boring",
        "Best film of the year!"
    ]

    for c in sample_comments:
        conn.execute("INSERT INTO comments(comment_text) VALUES (?)", (c,))
    
    conn.commit()
    st.success("Sample comments added")
    st.rerun()

# -----------------------------
# SESSION STATE CONTROL (KEY FIX)
# -----------------------------

if "current_comment" not in st.session_state:
    st.session_state.current_comment = fetch_next_comment(conn)

comment_row = st.session_state.current_comment

# -----------------------------
# DISPLAY LOGIC
# -----------------------------

if comment_row is None:
    st.success("🎉 All comments labeled!")

else:
    comment_id = comment_row["id"]
    comment_text = comment_row["comment_text"]

    st.subheader("Comment")
    st.info(comment_text)

    # -----------------------------
    # MODEL PREDICTION
    # -----------------------------

    try:
        X = np.array([[hash(comment_text) % 10000]])

        if st.session_state.model_initialized:
            pred = st.session_state.model.predict(X)[0]
            probs = st.session_state.model.predict_proba(X)
            conf = probs.max()

            labels_map = {0: "Positive", 1: "Neutral", 2: "Negative"}

            st.write(f"🤖 Model: {labels_map[pred]} ({round(conf*100,1)}%)")
        else:
            st.write("🤖 Model: Not trained yet")

    except:
        st.write("Model error")

    # -----------------------------
    # LABEL HANDLER
    # -----------------------------

    def handle_label(label):

        # Prevent duplicate
        row = conn.execute(
            "SELECT 1 FROM labels WHERE comment_id=?",
            (comment_id,)
        ).fetchone()

        if row is None:
            save_label(conn, comment_id, label)
            update_model(comment_text, label)

        # Move to next comment
        st.session_state.current_comment = fetch_next_comment(conn)

        st.rerun()

    # -----------------------------
    # BUTTONS
    # -----------------------------

    col1, col2, col3 = st.columns(3)

    if col1.button("Positive ✅", key=f"pos_{comment_id}"):
        handle_label(0)

    if col2.button("Neutral ⚪", key=f"neu_{comment_id}"):
        handle_label(1)

    if col3.button("Negative ❌", key=f"neg_{comment_id}"):
        handle_label(2)

# -----------------------------
# RESET OPTION
# -----------------------------

if st.button("🔄 Reset Labels"):
    conn.execute("DELETE FROM labels")
    conn.commit()
    st.session_state.current_comment = fetch_next_comment(conn)
    st.success("Reset done")
    st.rerun()