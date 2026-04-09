import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import os
import json
import base64
import tempfile
from datetime import datetime

# Define the scope
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

CREDENTIALS_FILE = "credentials.json"


import streamlit as st

# Get Sheet ID from Streamlit Secrets or environment
def get_sheet_id():
    """
    Get the Google Sheet ID from Streamlit Secrets or environment variables.
    """
    try:
        if "SHEET_ID" in st.secrets:
            return st.secrets["SHEET_ID"]
    except:
        pass
    
    return os.environ.get("SHEET_ID", "1E6p32QXz0xyt0ZR5T6Eii1losMxNRtYLwQYpZ3z8HYU")

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
            # Self-healing: Detect if raw JSON was pasted instead of Base64
            clean_input = creds_b64.strip()
            if clean_input.startswith("{") and clean_input.endswith("}"):
                creds_json = json.loads(clean_input)
            else:
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
    Legacy single-row update (maintained for compatibility).
    Uses the new batch logic internally for consistency.
    """
    upsert_labels_to_sheet([{
        "comment": comment,
        "label": label,
        "employee_name": employee_name,
        "video_id": video_id
    }], sheet_name)


def upsert_labels_to_sheet(rows_to_save, sheet_name="Sentiment Labels"):
    """
    Efficiently updates existing rows or appends new ones in batch.
    rows_to_save: List of dicts with keys [comment, label, employee_name, video_id]
    """
    if not rows_to_save:
        return

    client = get_sheet_client()
    try:
        # Open spreadsheet by ID (more reliable than by name)
        sheet_id = get_sheet_id()
        spreadsheet = client.open_by_key(sheet_id)
        sheet = spreadsheet.sheet1
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"Could not find spreadsheet with ID: {get_sheet_id()}")
        st.error("Please check that: 1) The Sheet ID is correct, 2) The service account has access, 3) The new email is shared with Editor permissions")
        return

    # Fetch all current data to find duplicates locally (faster than querying API per row)
    all_data = sheet.get_all_values()
    headers = all_data[0] if all_data else ["Timestamp", "Comment", "Label", "Employee", "Video ID"]
    
    # Map comment to its row index (1-indexed for gspread)
    # Header is row 1, data starts row 2
    comment_to_row = {row[1]: i + 1 for i, row in enumerate(all_data) if len(row) > 1}

    curr_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    new_rows = []
    updates = []

    for item in rows_to_save:
        comment = item["comment"]
        row_data = [curr_time, comment, item["label"], item["employee_name"], item["video_id"]]
        
        if comment in comment_to_row:
            row_idx = comment_to_row[comment]
            # range string like 'A5:E5'
            row_range = f"A{row_idx}:E{row_idx}"
            updates.append({'range': row_range, 'values': [row_data]})
        else:
            new_rows.append(row_data)

    # Perform updates in bulk
    if updates:
        sheet.batch_update(updates)
    
    # Append new rows in one call
    if new_rows:
        sheet.append_rows(new_rows)


def read_labeled_data(sheet_name="Sentiment Labels"):
    """
    Read all labeled data from the sheet for training.
    """
    client = _id = get_sheet_id()
        sheet = client.open_by_key(sheet_id).sheet1
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        print(f"Error reading sheet with ID {get_sheet_id()}
    except Exception as e:
        print(f"Error reading sheet: {e}")
        return pd.DataFrame(columns=["Timestamp", "Comment", "Label", "Employee", "Video ID"])


if __name__ == "__main__":
    # Test connection
    try:
        client = get_sheet_client()
        print("Successfully authenticated with Google Sheets API.")
    except Exception as e:
        print(f"Authentication failed: {e}")
