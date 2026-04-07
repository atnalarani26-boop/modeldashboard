#!/bin/bash

# Create temp directories for Nginx (required for Replit/non-root)
mkdir -p /tmp/client_body /tmp/proxy /tmp/fastcgi /tmp/uwsgi /tmp/scgi

# Start FastAPI in the background
echo "Starting FastAPI backend on port 5000..."
gunicorn -w 2 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:5000 --timeout 120 &

# Start Streamlit in the background
echo "Starting Streamlit UI on port 8501..."
streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true &

# Start Nginx in the foreground to unify everything on :8080
echo "Starting Nginx reverse proxy on port 8080..."
nginx -c "$(pwd)/nginx.conf" -g "daemon off;"
