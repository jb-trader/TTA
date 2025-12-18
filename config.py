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


# ============================================================================
# FOMC DATES (Fed announcement days - typically volatile)
# ============================================================================

FOMC_DATES = [
    # 2024
    "2024-01-31", "2024-03-20", "2024-05-01", "2024-06-12",
    "2024-07-31", "2024-09-18", "2024-11-07", "2024-12-18",
    # 2025
    "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18",
    "2025-07-30", "2025-09-17", "2025-11-05", "2025-12-17",
    # 2026
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17",
    "2026-07-29", "2026-09-16", "2026-11-04", "2026-12-16",
]


# ============================================================================
# EARNINGS DATES (Major earnings that move SPX)
# ============================================================================

EARNINGS_DATES = [
    # Add your earnings dates here as needed
    # Format: "YYYY-MM-DD"
]
