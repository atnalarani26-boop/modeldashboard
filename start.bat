@echo off
echo ===================================================
echo 🛡️ Starting Sentiment Intelligence Center...
echo ===================================================

:: Run bootstrap once to ensure model exists
echo [*] Bootstrapping model...
python bootstrap.py

:: Start the FastAPI Backend in a new window
echo [*] Launching API Backend (Uvicorn)...
start "Sentiment API" cmd /k "uvicorn main:app --host 0.0.0.0 --port 5000"

:: Start the Streamlit UI in the current window
echo [*] Launching Dashboard (Streamlit)...
streamlit run app.py
