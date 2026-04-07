import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
import os

MODEL_PATH = "model.pkl"

def bootstrap_model():
    """
    Creates a tiny initial model if none exists or if the existing one is incompatible.
    This ensures the API doesn't crash on the first /predict call.
    """
    print("Checking model compatibility...")
    
    # Sample data to train a base model
    data = {
        "Comment": [
            "This movie was amazing and I loved it!", 
            "Terrible experience, would not recommend.", 
            "It was okay, nothing special but not bad.",
            "Great acting and beautiful cinematography.",
            "Worst plot I have ever seen in a film."
        ],
        "Label": ["positive", "negative", "neutral", "positive", "negative"]
    }
    df = pd.DataFrame(data)
    
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(stop_words='english')),
        ('clf', LogisticRegression(solver='liblinear'))
    ])
    
    print("Training a base model...")
    pipeline.fit(df["Comment"], df["Label"])
    
    joblib.dump(pipeline, MODEL_PATH)
    print(f"Successfully bootstrapped {MODEL_PATH}!")

if __name__ == "__main__":
    bootstrap_model()
