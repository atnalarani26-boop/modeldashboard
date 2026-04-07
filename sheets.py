import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import os
import json
import base64
import tempfile

# Define the scope
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

CREDENTIALS_FILE = "credentials.json"


import streamlit as st

def get_sheet_client():
    """
    Authenticate and return the gspread client with maximum robustness.
    """
    creds_b64 = None
    
    # 1. Try Streamlit Secrets (The proper way on Cloud)
    try:
        if "GOOGLE_CREDENTIALS_BASE64" in st.secrets:
            creds_b64 = st.secrets["GOOGLE_CREDENTIALS_BASE64"]
    except Exception as e:
        pass

    # 2. Try Environment Variables (Backup)
    if not creds_b64:
        creds_b64 = os.environ.get("GOOGLE_CREDENTIALS_BASE64")

    # 3. If we found a base64 string, decode and authorize
    if creds_b64 and len(creds_b64) > 10:
        try:
            creds_json = json.loads(base64.b64decode(creds_b64))
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, SCOPE)
            return gspread.authorize(creds)
        except Exception as e:
            st.error(f"Error decoding cloud secrets: {e}")

    # 4. Fallback to local file (Local Dev only)
    if os.path.exists(CREDENTIALS_FILE):
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPE)
            return gspread.authorize(creds)
        except Exception as e:
            st.error(f"Error loading local credentials: {e}")

    # 5. Final Crash if everything fails
    raise FileNotFoundError(
        "CRITICAL: Could not find Google credentials! "
        "Please ensure 'GOOGLE_CREDENTIALS_BASE64' is set in your Streamlit Cloud 'Secrets' box."
    )


def write_label_to_sheet(comment, label, employee_name, video_id, sheet_name="Sentiment Labels"):
    """
    Append a new label to the Google Sheet.
    """
    client = get_sheet_client()
    try:
        sheet = client.open(sheet_name).sheet1
    except gspread.exceptions.SpreadsheetNotFound:
        # Create sheet if it doesn't exist
        spreadsheet = client.create(sheet_name)
        sheet = spreadsheet.sheet1
        sheet.append_row(["Comment", "Label", "Employee", "Video ID"])

    sheet.append_row([comment, label, employee_name, video_id])


def read_labeled_data(sheet_name="Sentiment Labels"):
    """
    Read all labeled data from the sheet for training.
    """
    client = get_sheet_client()
    try:
        sheet = client.open(sheet_name).sheet1
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        print(f"Error reading sheet: {e}")
        return pd.DataFrame(columns=["Comment", "Label", "Employee", "Video ID"])


if __name__ == "__main__":
    # Test connection
    try:
        client = get_sheet_client()
        print("Successfully authenticated with Google Sheets API.")
    except Exception as e:
        print(f"Authentication failed: {e}")
