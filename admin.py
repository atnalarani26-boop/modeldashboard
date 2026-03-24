import streamlit as st
import sqlite3
import pandas as pd
import joblib
import os

from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

# ---------------- DATABASE FIX ----------------

DB_PATH = os.path.join(os.getcwd(), "database.db")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)

st.title("Admin Dashboard")

st.write("DB Path:", DB_PATH)

if st.text_input("Password", type="password") != "admin123":
    st.stop()

if st.button("Refresh"):
    st.rerun()

# ---------------- DATA ----------------

labels = pd.read_sql("SELECT * FROM labels", conn)

st.metric("Total Labels", len(labels))

# ---------------- EMPLOYEE ----------------

emp = pd.read_sql("""

SELECT employee_name, COUNT(*) as total
FROM labels
GROUP BY employee_name

""", conn)

st.dataframe(emp)

# ---------------- ACCURACY ----------------

try:
    data = pd.read_sql("""

    SELECT comments.comment_text, labels.label
    FROM labels
    JOIN comments ON comments.id = labels.comment_id

    """, conn)

    if len(data) > 0:

        vectorizer = HashingVectorizer(n_features=2**18, alternate_sign=False)
        model = joblib.load("model.pkl")

        X = vectorizer.transform(data["comment_text"])

        y_true = data["label"]
        y_pred = model.predict(X)

        st.metric("Accuracy", round(accuracy_score(y_true,y_pred),3))
        st.metric("Precision", round(precision_score(y_true,y_pred,average="weighted"),3))
        st.metric("Recall", round(recall_score(y_true,y_pred,average="weighted"),3))
        st.metric("F1", round(f1_score(y_true,y_pred,average="weighted"),3))

except:
    st.warning("No data for metrics")