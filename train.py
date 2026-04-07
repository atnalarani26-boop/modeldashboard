import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sheets import read_labeled_data
from storage import upload_model
import os
import logging

logger = logging.getLogger(__name__)

MODEL_PATH = "model.pkl"


def train_model():
    """
    Fetch labeled data from Google Sheets, train a new model, save it locally,
    and upload to GCS for persistence across container restarts.
    """
    logger.info("Fetching data from Google Sheets...")
    df = read_labeled_data()

    if df.empty or len(df) < 5:  # Basic check to ensure we have enough data
        logger.warning("Not enough data to train. Need at least 5 labeled samples.")
        return False

    # Check for required columns
    if "Comment" not in df.columns or "Label" not in df.columns:
        logger.warning("Required columns 'Comment' and 'Label' not found in spreadsheet.")
        return False

    # Filter out empty labels or comments
    df = df.dropna(subset=["Comment", "Label"])
    df = df[df["Label"] != ""]

    if df.empty:
        logger.warning("No valid labeled data found after filtering.")
        return False

    X = df["Comment"]
    y = df["Label"]

    # Check if we have more than one class
    if len(y.unique()) < 2:
        logger.warning("Only one class found in data. Training requires at least two classes.")
        return False

    logger.info(f"Training on {len(df)} samples...")

    # Pipeline: TF-IDF + Logistic Regression
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(max_features=5000, stop_words='english')),
        ('clf', LogisticRegression(solver='liblinear', random_state=42))
    ])

    pipeline.fit(X, y)

    # Save the model locally
    joblib.dump(pipeline, MODEL_PATH)
    logger.info(f"Model saved to {MODEL_PATH}")

    # Upload to GCS for persistence across container restarts
    try:
        upload_model()
    except Exception as e:
        logger.warning(f"Could not upload model to GCS (non-fatal): {e}")

    return True


def load_model():
    """
    Load the trained model from disk.
    """
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    train_model()
