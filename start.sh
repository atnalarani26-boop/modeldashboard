#!/bin/bash

# Start FastAPI in the background
echo "Starting FastAPI backend..."
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:5000 &

# Start Streamlit in the foreground
echo "Starting Streamlit UI..."
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
