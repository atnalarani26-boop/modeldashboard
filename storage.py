"""
storage.py — Google Cloud Storage helper for model persistence.

Cloud Run containers are ephemeral, so we store model.pkl in a
GCS bucket and download it on startup / upload after training.
"""

import os
import logging

logger = logging.getLogger(__name__)

MODEL_PATH = "model.pkl"
BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "")
BLOB_NAME = "models/model.pkl"


def _get_bucket():
    """Get the GCS bucket object. Returns None if GCS is not configured."""
    if not BUCKET_NAME:
        logger.info("GCS_BUCKET_NAME not set — skipping cloud storage.")
        return None
    try:
        from google.cloud import storage
        client = storage.Client()
        return client.bucket(BUCKET_NAME)
    except Exception as e:
        logger.warning(f"Could not connect to GCS: {e}")
        return None


def download_model():
    """
    Download model.pkl from GCS to local disk.
    Returns True if successful, False otherwise.
    """
    bucket = _get_bucket()
    if bucket is None:
        return False

    blob = bucket.blob(BLOB_NAME)
    if not blob.exists():
        logger.info(f"No model found in gs://{BUCKET_NAME}/{BLOB_NAME}")
        return False

    blob.download_to_filename(MODEL_PATH)
    logger.info(f"Downloaded model from gs://{BUCKET_NAME}/{BLOB_NAME}")
    return True


def upload_model():
    """
    Upload model.pkl from local disk to GCS.
    Returns True if successful, False otherwise.
    """
    bucket = _get_bucket()
    if bucket is None:
        return False

    if not os.path.exists(MODEL_PATH):
        logger.warning(f"Local {MODEL_PATH} not found — nothing to upload.")
        return False

    blob = bucket.blob(BLOB_NAME)
    blob.upload_from_filename(MODEL_PATH)
    logger.info(f"Uploaded model to gs://{BUCKET_NAME}/{BLOB_NAME}")
    return True
