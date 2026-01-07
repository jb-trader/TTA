"""
Configuration file for TTA (Time Trends Auto)

Works with:
- Railway (environment variables)
- Streamlit Cloud (st.secrets)
- Local development (fallback)
"""

import os
import streamlit as st

# ============================================================================
# GOOGLE DRIVE DATA SOURCE
# ============================================================================

def get_file_id():
    """
    Get Google Drive file ID from environment variable, Streamlit secrets, or fallback.
    """
    # 1. Try environment variable (Railway)
    file_id = os.environ.get("GOOGLE_DRIVE_FILE_ID")
    if file_id:
        return file_id
    
    # 2. Try Streamlit secrets (Streamlit Cloud)
    try:
        return st.secrets["GOOGLE_DRIVE_FILE_ID"]
    except (KeyError, FileNotFoundError):
        pass
    
    # 3. Local development fallback
    return "YOUR_FILE_ID_HERE"


def get_data_url():
    """Build the Google Drive download URL."""
    file_id = get_file_id()
    return f"https://drive.google.com/uc?id={file_id}&export=download"


def get_data_version():
    """
    Return a version string for cache busting.
    Change this when your data file updates to force a reload.
    """
    return "2024-12-18-v1"


# Exclusion dates
#  use this source:   https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
FOMC_DATES = [
    "2024-01-31", "2024-03-20", "2024-05-01", "2024-06-12",
    "2024-07-31", "2024-09-18", "2024-11-07", "2024-12-18",
    "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18",
    "2025-07-30", "2025-09-17", "2025-10-29", "2025-12-10",
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17",
    "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09"
]


# NVDA, MSFT, AAPL, AMZN, META, GOOGL 

EARNINGS_DATES = [
 
    "2024-01-30", "2024-01-31", "2024-02-01", "2024-02-21",
    "2024-04-23", "2024-04-24", "2024-05-02", "2024-05-22",
    "2024-07-23", "2024-07-24", "2024-08-01", "2024-08-21",
    "2024-10-22", "2024-10-23", "2024-10-31", "2024-11-20",
    "2025-01-28", "2025-01-29", "2025-01-30", "2025-02-19",
    "2025-04-29", "2025-04-30", "2025-05-01", "2025-05-21",
    "2025-07-29", "2025-07-30", "2025-07-31", "2025-08-01",
    "2025-08-20", "2025-10-28", "2025-10-29", "2025-10-30",
    "2025-11-19", "2026-01-28", "2026-01-29", "2026-02-18", 
    "2026-04-28", "2026-04-29", "2026-04-30", "2026-05-20", 
    "2026-07-28", "2026-07-29", "2026-07-30", "2026-08-19", 
    "2026-10-27", "2026-10-28", "2026-10-29", "2026-11-18", 
    "2026-02-25", "2026-02-05", "2026-02-03"
]
