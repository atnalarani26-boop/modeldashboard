from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List
import joblib
import os
import logging
import asyncio
from train import train_model, load_model
from storage import download_model

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Sentiment Analysis API")


@app.on_event("startup")
async def startup_event():
    """
    On startup:
    1. Try to download the latest model from GCS (Cloud Run persistence).
    2. Fall back to local model.pkl if GCS is unavailable.
    3. Log the model status.
    """
    logger.info("Starting up — checking for model...")

    # Try downloading from GCS first (for Cloud Run deployments)
    if not os.path.exists("model.pkl"):
        logger.info("No local model.pkl found, attempting GCS download...")
        try:
            downloaded = download_model()
            if downloaded:
                logger.info("Model downloaded from GCS successfully.")
            else:
                logger.info("No model in GCS either — bootstrap model will be used.")
        except Exception as e:
            logger.warning(f"GCS download failed (non-fatal): {e}")
    else:
        logger.info("Local model.pkl found.")

    model = load_model()
    if model:
        logger.info("Model loaded and ready for predictions.")
    else:
        logger.warning("No model available. Train one via POST /train.")


class PredictionRequest(BaseModel):
    text: str


class PredictionResponse(BaseModel):
    sentiment: str
    confidence: float


@app.get("/")
def read_root():
    return {"status": "Sentiment Analysis API is running"}


@app.get("/health")
def health_check():
    model = load_model()
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "model_path": "model.pkl"
    }


@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest):
    model = load_model()
    if not model:
        logger.warning("Prediction requested but model is not loaded.")
        raise HTTPException(status_code=503, detail="Model not loaded or not yet trained.")

    try:
        prediction = model.predict([request.text])[0]
        # Get probability if available
        if hasattr(model, "predict_proba"):
            probs = model.predict_proba([request.text])[0]
            confidence = float(max(probs))
        else:
            confidence = 1.0

        logger.info(f"Prediction: '{request.text[:50]}...' -> {prediction} (conf: {confidence:.2f})")
        return PredictionResponse(sentiment=prediction, confidence=confidence)
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/train")
def trigger_training(background_tasks: BackgroundTasks):
    """
    Trigger model retraining. Can be called manually or via automation.
    Runs in background to avoid blocking.
    """
    background_tasks.add_task(train_model)
    return {"message": "Training started in background"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
