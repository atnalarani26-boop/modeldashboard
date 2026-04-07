# 🛡️ Sentiment Intelligence Center — Cloud Deployment

A production-ready **Film Sentiment Analysis Dashboard** deployed on **Google Cloud Run**.

| Component | Technology |
|-----------|-----------|
| API Backend | FastAPI + Gunicorn |
| Dashboard UI | Streamlit |
| Data Store | Google Sheets |
| Model Storage | Google Cloud Storage |
| ML Pipeline | scikit-learn (TF-IDF + LogReg) |
| Deployment | Docker → Cloud Run |
| CI/CD | GitHub Actions |

---

## 🏗️ Architecture

```
User Browser
     │
     ▼
┌──────────────────────────────────────┐
│  Google Cloud Run (single container) │
│                                      │
│  nginx :8080 (reverse proxy)         │
│    ├── /        → Streamlit :8501    │
│    └── /api/*   → FastAPI :5000     │
│                                      │
│  supervisord (process manager)       │
└──────────────────────────────────────┘
     │              │            │
     ▼              ▼            ▼
Google Sheets   Cloud Storage  YouTube API
 (labels)       (model.pkl)    (comments)
```

---

## 🚀 Quick Start (Local Development)

### 1. Prerequisites
- Python 3.11+
- `credentials.json` (Google Service Account with Sheets + Drive API access)

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Bootstrap & Run
```bash
# Windows
start.bat

# Linux/Mac
chmod +x start.sh && ./start.sh
```

### 4. Access
- **Dashboard**: http://localhost:8501
- **API**: http://localhost:5000
- **API Docs**: http://localhost:5000/docs

---

## ☁️ Cloud Deployment (Google Cloud Run)

### Step 1: GCP Project Setup

```bash
# Install gcloud CLI: https://cloud.google.com/sdk/docs/install

# Login and create project
gcloud auth login
gcloud projects create YOUR_PROJECT_ID --name="Sentiment Dashboard"
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    containerregistry.googleapis.com \
    storage.googleapis.com \
    secretmanager.googleapis.com
```

### Step 2: Create a GCS Bucket (Model Storage)

```bash
gsutil mb -l us-central1 gs://sentiment-model-store
```

### Step 3: Encode Credentials

```bash
# Linux/Mac
base64 -w 0 credentials.json > creds_b64.txt

# Windows (PowerShell)
[Convert]::ToBase64String([IO.File]::ReadAllBytes("credentials.json")) | Out-File creds_b64.txt
```

### Step 4a: Deploy via gcloud CLI (Manual)

```bash
# Build and push image
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/sentiment-dashboard

# Deploy to Cloud Run
gcloud run deploy sentiment-dashboard \
    --image gcr.io/YOUR_PROJECT_ID/sentiment-dashboard \
    --region us-central1 \
    --platform managed \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --port 8080 \
    --set-env-vars "GCS_BUCKET_NAME=sentiment-model-store" \
    --set-env-vars "ADMIN_PASSWORD=your-secure-password" \
    --set-env-vars "GOOGLE_CREDENTIALS_BASE64=$(cat creds_b64.txt)"
```

### Step 4b: Deploy via GitHub Actions (Automated CI/CD)

Add these **GitHub Secrets** in your repo → Settings → Secrets:

| Secret Name | Value |
|------------|-------|
| `GCP_PROJECT_ID` | Your GCP project ID |
| `GCP_SA_KEY` | Full JSON of a service account key with Cloud Run Admin + Storage Admin roles |
| `GCP_REGION` | e.g. `us-central1` |
| `GCS_BUCKET_NAME` | e.g. `sentiment-model-store` |
| `ADMIN_PASSWORD` | Dashboard login password |
| `GOOGLE_CREDENTIALS_BASE64` | Base64-encoded `credentials.json` |

Then push to `main` — the workflow deploys automatically.

### Step 5: Verify Deployment

```bash
# Get the deployed URL
gcloud run services describe sentiment-dashboard \
    --region us-central1 \
    --format 'value(status.url)'

# Test health
curl https://YOUR-URL.run.app/api/health

# Test prediction
curl -X POST https://YOUR-URL.run.app/api/predict \
    -H "Content-Type: application/json" \
    -d '{"text": "This movie was amazing!"}'
```

---

## ☁️ Cloud Deployment (Replit)

This project has been optimized for a frictionless deployment on **Replit**.

### Step 1: Import to Replit
Simply import your GitHub repository into Replit or upload the files manually into a new Python project.

### Step 2: Configure Environment Variables
Inside Replit, go to the **Tools > Secrets** panel and add the following keys securely (do not commit them to your repository):
- `GOOGLE_CREDENTIALS_BASE64`: Your securely encoded `credentials.json` credentials.
- `ADMIN_PASSWORD`: Your password for accessing the Streamlit operations dashboard.
- `GCS_BUCKET_NAME` (optional for local GCS testing): `sentiment-model-store`

### Step 3: Run and Deploy
Click **Run** inside the Replit interface! 
- Replit will automatically read `.replit` and `replit.nix` files to install Python 3.11, NGINX, and Supervisord.
- Supervisord will start FastAPI, Streamlit, and NGINX on `http://0.0.0.0:8080` which is natively exposed by Replit's public HTTPS URL.
- To make it "Always On" permanently, navigate to Replit Deploy and select **Autodeploy (Background)** to keep it live!

---

## 🐳 Deployment (Google Cloud Run)

If you prefer GCP over Replit:
*(Follow typical Google Cloud setup: `gcloud run deploy ...`)*

---

## 🐳 Docker (Local Testing)

```bash
# Build
docker build -t sentiment-dashboard .

# Run
docker run -p 8080:8080 \
    -e ADMIN_PASSWORD=admin123 \
    -e GOOGLE_CREDENTIALS_BASE64="$(base64 -w 0 credentials.json)" \
    -e GCS_BUCKET_NAME=sentiment-model-store \
    sentiment-dashboard

# Access at http://localhost:8080
```

---

## 📁 Project Structure

```
├── main.py              # FastAPI backend (predictions, training)
├── app.py               # Streamlit dashboard (labeling, analytics)
├── train.py             # ML pipeline (TF-IDF + LogReg)
├── sheets.py            # Google Sheets integration
├── youtube.py           # YouTube comment fetcher
├── storage.py           # GCS model persistence
├── bootstrap.py         # Seed model generator
├── Dockerfile           # Production container image
├── nginx.conf           # Reverse proxy config
├── supervisord.conf     # Process manager config
├── cloudbuild.yaml      # Google Cloud Build config
├── requirements.txt     # Python dependencies
├── Procfile             # Container entrypoint
├── .env.example         # Environment variable template
├── .dockerignore        # Docker build exclusions
└── .github/
    └── workflows/
        └── deploy.yml   # GitHub Actions CI/CD
```

---

## 🔒 Security Notes

- **Never commit `credentials.json`** — it's in `.gitignore`
- Use **environment variables** for all secrets in production
- Change `ADMIN_PASSWORD` from the default before deploying
- Consider using **Google Cloud Secret Manager** for production credentials
