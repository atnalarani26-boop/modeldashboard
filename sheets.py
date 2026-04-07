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


def get_sheet_client():
    """
    Authenticate and return the gspread client.
    
    Priority:
    1. GOOGLE_CREDENTIALS_BASE64 env var (for Cloud Run / CI)
    2. credentials.json file on disk (for local development)
    """
    # --- Option 1: Base64-encoded credentials from environment ---
    creds_b64 = os.environ.get("GOOGLE_CREDENTIALS_BASE64", "")
    if creds_b64:
        try:
            creds_json = json.loads(base64.b64decode(creds_b64))
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, SCOPE)
            client = gspread.authorize(creds)
            return client
        except Exception as e:
            print(f"Error loading credentials from env var: {e}")

    # --- Option 2: credentials.json file on disk ---
    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(
            f"{CREDENTIALS_FILE} not found and GOOGLE_CREDENTIALS_BASE64 env var is not set.\n"
            "For cloud deployment, set the GOOGLE_CREDENTIALS_BASE64 environment variable.\n"
            "For local dev, place credentials.json in the project root."
        )

    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPE)
    client = gspread.authorize(creds)
    return client


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
