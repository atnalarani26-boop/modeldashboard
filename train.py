import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from sheets import read_labeled_data
from storage import upload_model
import os
import logging

logger = logging.getLogger(__name__)

MODEL_PATH = "model.pkl"


def train_model():
    """
    Fetch labeled data from Google Sheets, train a new model with a proper
    train/test split to prevent data leakage, save it locally, and upload
    to GCS for persistence across container restarts.
    """
    logger.info("Fetching data from Google Sheets...")
    df = read_labeled_data()

    if df.empty or len(df) < 10:  # Need enough for a meaningful split
        logger.warning("Not enough data to train. Need at least 10 labeled samples.")
        return False

    # Check for required columns
    if "Comment" not in df.columns or "Label" not in df.columns:
        logger.warning("Required columns 'Comment' and 'Label' not found in spreadsheet.")
        return False

    # Filter out empty labels or comments
    df = df.dropna(subset=["Comment", "Label"])
    df = df[df["Label"] != ""]
    
    # --- EXTRA LEAKAGE PROTECTION: Drop Duplicates ---
    # If the same comment exists twice, it must not be in both train and test.
    original_count = len(df)
    df = df.drop_duplicates(subset=["Comment"])
    if len(df) < original_count:
        logger.info(f"Dropped {original_count - len(df)} duplicate records.")

    if df.empty:
        logger.warning("No valid labeled data found after filtering.")
        return False

    X = df["Comment"]
    y = df["Label"]

    # Check if we have more than one class
    if len(y.unique()) < 2:
        logger.warning("Only one class found in data. Training requires at least two classes.")
        return False

    logger.info(f"Total samples available: {len(df)}")

    # --- FIX: Split BEFORE fitting to prevent data leakage ---
    # The TF-IDF vectorizer must ONLY see training data during fit.
    # test_size=0.2 reserves 20% for honest evaluation.
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=42,
        stratify=y if len(y.unique()) >= 2 else None
    )

    logger.info(f"Training on {len(X_train)} samples, evaluating on {len(X_test)} held-out samples...")

    # Pipeline: TF-IDF + Logistic Regression
    # The pipeline is fit ONLY on X_train — no leakage into test data.
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(max_features=5000, stop_words='english')),
        ('clf', LogisticRegression(solver='liblinear', random_state=42))
    ])

    pipeline.fit(X_train, y_train)

    # Evaluate on the held-out test set (no leakage)
    y_pred = pipeline.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    logger.info(f"Test Accuracy (no leakage): {acc:.4f}")
    logger.info("Classification Report:\n" + classification_report(y_test, y_pred))

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
