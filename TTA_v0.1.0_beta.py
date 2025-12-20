#!/usr/bin/env python3
"""
Time Trends Auto (TTA v0.1.0 beta) by jb-trader
Finds optimal lookback period (in weeks) for Entry_Time × Day_of_week profit optimization.
Conducts walk-forward analysis to validate lookback selection.

Version 0.1.0 beta
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta, time
from calendar import monthrange
from pathlib import Path
import warnings
import requests
from io import BytesIO
import re
import pytz
import base64
from fpdf import FPDF

# Import config for Google Drive URL and exclusion dates
import config as cfg

warnings.filterwarnings('ignore')

# ============================================================================
# PDF GENERATION FOR TRADE PLAN
# ============================================================================

def generate_trade_plan_pdf(week_type, target_monday, target_friday, symbol, strategy, recommendations_df):
    """
    Generate a clean PDF of the trade plan.
    
    Args:
        week_type: "Next Week" or "Current Week"
        target_monday: Start date of trading week
        target_friday: End date of trading week
        symbol: Trading symbol (e.g., "SPX")
        strategy: Strategy name (e.g., "Butterfly")
        recommendations_df: DataFrame with Day_of_week and Entry_Time columns
    
    Returns:
        PDF bytes for download
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Title
    pdf.set_font('Helvetica', 'B', 18)
    pdf.cell(0, 12, 'TTA Trade Plan', ln=True, align='C')
    pdf.ln(5)
    
    # Week type indicator
    pdf.set_font('Helvetica', '', 12)
    week_indicator = f"({week_type})"
    pdf.cell(0, 8, week_indicator, ln=True, align='C')
    pdf.ln(3)
    
    # Trading week box
    pdf.set_fill_color(240, 248, 255)  # Light blue background
    pdf.set_font('Helvetica', 'B', 11)
    date_range = f"Trading Week: {target_monday:%B %d, %Y} - {target_friday:%B %d, %Y}"
    pdf.cell(0, 10, date_range, ln=True, align='C', fill=True)
    pdf.ln(5)
    
    # Symbol and Strategy
    pdf.set_font('Helvetica', '', 11)
    pdf.cell(0, 8, f"Symbol: {symbol} | Strategy: {strategy}", ln=True, align='C')
    pdf.ln(3)
    
    # "In-sample test stats" label
    pdf.set_font('Helvetica', 'I', 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, 'In-sample test stats', ln=True, align='C')
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)
    
    # Table - calculate column positions for centering
    table_width = 120
    col_width = table_width / 2  # 60 each
    x_start = (210 - table_width) / 2  # Center on A4 page (210mm width)
    
    # Table header
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_fill_color(245, 245, 245)
    pdf.set_x(x_start)
    pdf.cell(col_width, 10, 'Day', border=1, align='C', fill=True)
    pdf.cell(col_width, 10, 'Entry Time', border=1, align='C', fill=True)
    pdf.ln()
    
    # Table rows
    pdf.set_font('Helvetica', '', 11)
    for _, row in recommendations_df.iterrows():
        pdf.set_x(x_start)
        day = row['Day_of_week'] if 'Day_of_week' in row else row.get('Day', '')
        entry_time = row['Entry_Time'] if 'Entry_Time' in row else row.get('Entry Time', '')
        
        # Skip rows with no valid lookback
        if entry_time in ['No Valid Lookback', 'No Data', 'N/A', '']:
            continue
            
        pdf.cell(col_width, 10, str(day), border=1, align='C')
        pdf.cell(col_width, 10, str(entry_time), border=1, align='C')
        pdf.ln()
    
    pdf.ln(10)
    
    # Footer with timestamp
    pdf.set_font('Helvetica', 'I', 9)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(0, 6, f"Generated: {datetime.now():%Y-%m-%d %H:%M}", ln=True, align='C')
    pdf.cell(0, 6, "TTA - Time Trends Auto by jb-trader", ln=True, align='C')
    
    # Return PDF as bytes (convert bytearray to bytes for Streamlit)
    return bytes(pdf.output())


# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="Time Trends Auto (TTA v0.1.0 beta) by jb-trader",
    page_icon="🎱",
    layout="wide",
    initial_sidebar_state="expanded"
)

VERSION = "1.0"

# Theme CSS function
def get_theme_css(theme):
    """Return CSS based on selected theme."""
    if theme == "Light":
        bg_color = "#ffffff"
        sidebar_bg = "#f0f2f6"
        text_color = "#000000"
        header_bg = "#ffffff"
        table_header_bg = "#f5f5f5"
        border_color = "#ddd"
    else:  # Dark
        bg_color = "#0e1117"
        sidebar_bg = "#262730"
        text_color = "#fafafa"
        header_bg = "#0e1117"
        table_header_bg = "#262730"
        border_color = "#444"
    
    return f"""
    <style>
        /* ========================================
           HIDE STREAMLIT'S HAMBURGER MENU
           ======================================== */
        #MainMenu {{display: none !important;}}
        header [data-testid="stToolbar"] {{display: none !important;}}
        
        /* ========================================
           HIDE ONLY THE COLLAPSE BUTTON (not sidebar)
           ======================================== */
        button[data-testid="stSidebarCollapseButton"] {{
            display: none !important;
        }}
        
        /* Hide the >> expand button that appears on hover */
        button[data-testid="stSidebarNavCollapseButton"] {{
            display: none !important;
        }}
        [data-testid="stSidebarCollapsedControl"] {{
            display: none !important;
        }}
        [data-testid="collapsedControl"] {{
            display: none !important;
        }}
        
        /* Ensure sidebar stays visible */
        section[data-testid="stSidebar"] {{
            display: block !important;
            visibility: visible !important;
            opacity: 1 !important;
            transform: none !important;
        }}
        
        /* ========================================
           HEADER STYLING (override Streamlit theme)
           ======================================== */
        header[data-testid="stHeader"] {{
            background-color: {header_bg} !important;
        }}
        
        /* Theme colors */
        .stApp {{
            background-color: {bg_color} !important;
        }}
        .stApp [data-testid="stAppViewContainer"] {{
            background-color: {bg_color} !important;
        }}
        section[data-testid="stSidebar"] {{
            background-color: {sidebar_bg} !important;
        }}
        section[data-testid="stSidebar"] > div {{
            background-color: {sidebar_bg} !important;
        }}
        
        /* Text colors */
        .stApp, .stApp p, .stApp span, .stApp label, .stApp h1, .stApp h2, .stApp h3 {{
            color: {text_color} !important;
        }}
        section[data-testid="stSidebar"], 
        section[data-testid="stSidebar"] p, 
        section[data-testid="stSidebar"] span, 
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {{
            color: {text_color} !important;
        }}
        .stMarkdown, .stMarkdown p {{
            color: {text_color} !important;
        }}
        
        /* Sidebar width - desktop only */
        @media (min-width: 768px) {{
            section[data-testid="stSidebar"] {{
                width: 300px !important;
                min-width: 300px !important;
            }}
        }}
        
        .main .block-container {{
            padding-top: 1rem !important;
            max-width: 100% !important;
        }}
        
        /* Hide footer */
        footer {{
            display: none !important;
        }}
        
        /* Download buttons - always black text on white background */
        .stDownloadButton button {{
            background-color: #ffffff !important;
            color: #000000 !important;
            border: 1px solid #ddd !important;
        }}
        .stDownloadButton button:hover {{
            background-color: #f0f0f0 !important;
            color: #000000 !important;
        }}
        .stDownloadButton button p {{
            color: #000000 !important;
        }}
        
        /* Dataframe font size */
        .stDataFrame {{
            font-size: 14px !important;
        }}
        .stDataFrame table {{
            font-size: 14px !important;
        }}
        .stDataFrame th {{
            font-size: 14px !important;
            font-weight: bold !important;
            color: {text_color} !important;
        }}
        .stDataFrame td {{
            font-size: 14px !important;
            font-weight: bold !important;
            color: {text_color} !important;
        }}
        
        /* General text size */
        .stMarkdown {{
            font-size: 15px !important;
            font-weight: normal !important;
        }}
        .stMarkdown p {{
            font-size: 15px !important;
            font-weight: normal !important;
        }}
        
        /* Subheader size */
        h2 {{
            font-size: 24px !important;
        }}
        h3 {{
            font-size: 20px !important;
        }}
        
        /* Metric font sizes */
        [data-testid="stMetricValue"] {{
            font-size: 28px !important;
            font-weight: bold !important;
            color: {text_color} !important;
        }}
        [data-testid="stMetricLabel"] {{
            font-size: 14px !important;
            font-weight: bold !important;
            color: {text_color} !important;
        }}
        
        /* Info box text */
        .stAlert {{
            font-size: 14px !important;
            font-weight: normal !important;
        }}
        .stAlert p {{
            font-size: 14px !important;
            font-weight: normal !important;
        }}
        
        /* Selectbox and input labels */
        .stSelectbox label, .stNumberInput label {{
            font-size: 14px !important;
        }}
        
        /* Sidebar text sizes */
        section[data-testid="stSidebar"] .stMarkdown {{
            font-size: 14px !important;
            font-weight: normal !important;
        }}
        section[data-testid="stSidebar"] .stMarkdown p {{
            font-size: 14px !important;
            font-weight: normal !important;
        }}
        section[data-testid="stSidebar"] h2 {{
            font-size: 18px !important;
        }}
        section[data-testid="stSidebar"] h3 {{
            font-size: 16px !important;
        }}
        section[data-testid="stSidebar"] .stAlert {{
            font-size: 13px !important;
            font-weight: normal !important;
        }}
        section[data-testid="stSidebar"] .stAlert p {{
            font-size: 13px !important;
            font-weight: normal !important;
        }}
        section[data-testid="stSidebar"] label {{
            font-size: 13px !important;
        }}
        section[data-testid="stSidebar"] .stCheckbox label span {{
            font-size: 13px !important;
        }}
        
        /* Expanders in light green */
        .streamlit-expanderHeader {{
            background-color: #90EE90 !important;
            border-radius: 8px !important;
            padding: 8px 12px !important;
            font-size: 16px !important;
            font-weight: bold !important;
            color: #000000 !important;
        }}
        div[data-testid="stExpander"] > details > summary {{
            background-color: #90EE90 !important;
            border-radius: 8px !important;
            padding: 8px 12px !important;
            font-size: 16px !important;
            font-weight: bold !important;
            color: #000000 !important;
        }}
        
        /* Disclaimer - must be last to override theme colors */
        .disclaimer-box, 
        .disclaimer-box *, 
        div.disclaimer-box, 
        div.disclaimer-box span, 
        div.disclaimer-box strong {{
            color: #cc0000 !important;
            background-color: yellow !important;
        }}
    </style>
    """

VERSION = "1.0"

# ============================================================================
# CONSTANTS
# ============================================================================
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
WEEKDAY_ORDER = {day: i for i, day in enumerate(WEEKDAYS)}

# ============================================================================
# DATA LOADING (from Google Drive - same pattern as TTV)
# ============================================================================

def _download_drive_bytes() -> bytes:
    """Download parquet file from Google Drive."""
    sess = requests.Session()
    url = cfg.get_data_url()
    r = sess.get(url, headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=True, timeout=30)
    if "text/html" in r.headers.get("Content-Type", ""):
        m = re.search(r'href="([^"]+confirm[^"]+)"', r.text)
        if m:
            confirm_url = "https://drive.google.com" + m.group(1).replace("&amp;", "&")
            r = sess.get(confirm_url, headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=True, timeout=30)
    r.raise_for_status()
    return r.content


def get_cache_key():
    """
    Generate a cache key that changes at 4:30 PM ET each trading day.
    This causes automatic data refresh after market data is updated.
    """
    et = pytz.timezone('US/Eastern')
    now = datetime.now(et)
    today = now.date()
    refresh_time = time(16, 30)  # 4:30 PM ET
    
    # If it's after 4:30 PM, use today's date as key
    # If it's before 4:30 PM, use yesterday's date as key
    if now.time() >= refresh_time:
        cache_date = today
    else:
        cache_date = today - timedelta(days=1)
    
    return f"{cache_date}"


@st.cache_data(ttl=3600)  # 1 hour cache as backup
def load_data(cache_key: str):
    """Load data from Google Drive with local fallback."""
    _ = cache_key  # Used for cache invalidation
    local_path = Path(r"D:/_Documents/Magic 8 Ball/data/dfe_table.parquet")
    
    df = pd.DataFrame()
    source = "none"
    
    try:
        data_bytes = _download_drive_bytes()
        df = pd.read_parquet(BytesIO(data_bytes))
        source = "cloud"
    except Exception as e:
        st.sidebar.warning(f"Cloud download issue ({e}). Using local file if available.")
        if local_path.exists():
            df = pd.read_parquet(local_path)
            source = "local"
        else:
            st.error("No local fallback file found.")
            return pd.DataFrame(), source
    
    # Basic preprocessing
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df[df['Entry_Time'] <= '15:45'].copy()
    df = df[df['Date'].dt.dayofweek < 5].copy()  # Exclude weekends
    df = df[df['Date'] > '2024-08-01'].copy()  # Start from Aug 2024
    
    return df, source


# ============================================================================
# MONTH-END / T-1 EXCLUSION HELPERS
# ============================================================================

def load_market_holidays():
    """Return default US market holidays (2024-2026)."""
    default_holidays = [
        "2024-01-01", "2024-01-15", "2024-02-19", "2024-03-29", "2024-05-27",
        "2024-06-19", "2024-07-04", "2024-09-02", "2024-11-28", "2024-12-25",
        "2025-01-01", "2025-01-20", "2025-02-17", "2025-04-18", "2025-05-26",
        "2025-06-19", "2025-07-04", "2025-09-01", "2025-11-27", "2025-12-25",
        "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25",
        "2026-06-19", "2026-07-03", "2026-09-07", "2026-11-26", "2026-12-25",
    ]
    return set(datetime.strptime(d, "%Y-%m-%d").date() for d in default_holidays)


def roll_to_trading_day(date_obj, market_holidays):
    """Roll a date backward to find a valid trading day."""
    while True:
        if date_obj.weekday() >= 5:
            date_obj -= timedelta(days=1)
            continue
        if date_obj in market_holidays:
            date_obj -= timedelta(days=1)
            continue
        return date_obj


@st.cache_data
def compute_rebalancing_dates(min_date, max_date):
    """Compute month-end, T-1, and T-2 dates for the date range.
    
    Returns dict mapping date -> {'type': 'month_end'|'t_minus_1'|'t_minus_2', 'is_quarter_end': bool}
    """
    market_holidays = load_market_holidays()
    rebalancing_dates = {}
    
    current = datetime(min_date.year, min_date.month, 1)
    end = datetime(max_date.year, max_date.month, 1) + timedelta(days=62)
    
    while current <= end:
        _, last_day = monthrange(current.year, current.month)
        month_end_calendar = datetime(current.year, current.month, last_day).date()
        
        # Roll to trading day (handles weekends)
        month_end = roll_to_trading_day(month_end_calendar, market_holidays)
        
        # T-1: one day before month_end, then roll backward
        t_minus_1 = roll_to_trading_day(month_end - timedelta(days=1), market_holidays)
        
        # T-2: one day before T-1, then roll backward
        t_minus_2 = roll_to_trading_day(t_minus_1 - timedelta(days=1), market_holidays)
        
        # Quarter-end flag (March=3, June=6, September=9, December=12)
        is_quarter_end = current.month in [3, 6, 9, 12]
        
        rebalancing_dates[month_end] = {'type': 'month_end', 'is_quarter_end': is_quarter_end}
        rebalancing_dates[t_minus_1] = {'type': 't_minus_1', 'is_quarter_end': is_quarter_end}
        rebalancing_dates[t_minus_2] = {'type': 't_minus_2', 'is_quarter_end': is_quarter_end}
        
        # Move to next month
        if current.month == 12:
            current = datetime(current.year + 1, 1, 1)
        else:
            current = datetime(current.year, current.month + 1, 1)
    
    return rebalancing_dates


def get_rebalancing_dates_to_exclude(rebalancing_dates, exclude_month_end, exclude_t1, exclude_t2, quarter_end_only):
    """Get set of dates to exclude based on rebalancing filter settings."""
    dates_to_exclude = set()
    
    # If Only Quarter End is checked but no day checkboxes, default to month-end
    if quarter_end_only and not (exclude_month_end or exclude_t1 or exclude_t2):
        exclude_month_end = True
    
    for date_obj, info in rebalancing_dates.items():
        # Skip if we're only excluding quarter-end and this isn't quarter-end
        if quarter_end_only and not info['is_quarter_end']:
            continue
        
        # Check which day types to include
        if info['type'] == 'month_end' and exclude_month_end:
            dates_to_exclude.add(date_obj)
        elif info['type'] == 't_minus_1' and exclude_t1:
            dates_to_exclude.add(date_obj)
        elif info['type'] == 't_minus_2' and exclude_t2:
            dates_to_exclude.add(date_obj)
    
    return dates_to_exclude


def load_fomc_dates():
    """Load FOMC announcement dates from config."""
    try:
        dates = set()
        if hasattr(cfg, 'FOMC_DATES'):
            fomc = pd.to_datetime(cfg.FOMC_DATES, errors='coerce').dropna()
            dates.update(d.date() for d in fomc)
        return dates
    except Exception:
        return set()


def load_earnings_dates():
    """Load earnings dates from config (E: earnings day only)."""
    try:
        dates = set()
        if hasattr(cfg, 'EARNINGS_DATES'):
            earn = pd.to_datetime(cfg.EARNINGS_DATES, errors='coerce').dropna()
            dates.update(d.date() for d in earn)
        return dates
    except Exception:
        return set()


def load_earnings_plus1_dates():
    """Load earnings +1 dates from config (E+1: next business day after earnings)."""
    try:
        dates = set()
        if hasattr(cfg, 'EARNINGS_DATES'):
            earn = pd.to_datetime(cfg.EARNINGS_DATES, errors='coerce').dropna()
            for d in earn:
                next_day = d + pd.offsets.BDay(1)
                dates.add(next_day.date())
        return dates
    except Exception:
        return set()


# ============================================================================
# WEEK UTILITIES
# ============================================================================

def get_week_start(date):
    """Get Monday of the week containing the given date."""
    return date - timedelta(days=date.weekday())


def get_week_end(date):
    """Get Friday of the week containing the given date."""
    return get_week_start(date) + timedelta(days=4)


def get_all_weeks(df):
    """Get all unique week start dates (Mondays) in the dataset."""
    df = df.copy()
    df['week_start'] = df['Date'].apply(lambda x: get_week_start(x.date()) if pd.notna(x) else None)
    weeks = sorted(df['week_start'].dropna().unique())
    return [w for w in weeks if w is not None]


# ============================================================================
# R-SQUARED CALCULATION
# ============================================================================

def calculate_r_squared_equity(profits):
    """
    R² of accumulated profit vs a linear trend over trade/week index.
    
    Measures how consistently profits accumulate in a straight line.
    - R² > 0.7 = strong consistency
    - R² > 0.85 = excellent (smooth equity curve)
    - R² < 0.5 = erratic (profits come in unpredictable bursts)
    
    Returns 0.0 for very small samples.
    """
    s = pd.Series(pd.to_numeric(profits, errors='coerce')).dropna()
    if len(s) < 3:
        return 0.0
    y = s.cumsum().values.astype(float)
    x = np.arange(1, len(y) + 1, dtype=float)
    x_mean = x.mean()
    y_mean = y.mean()
    ss_tot = ((y - y_mean) ** 2).sum()
    if ss_tot == 0:
        return 0.0
    b = ((x - x_mean) * (y - y_mean)).sum() / ((x - x_mean) ** 2).sum()
    a = y_mean - b * x_mean
    y_hat = a + b * x
    ss_res = ((y - y_hat) ** 2).sum()
    r2 = 1.0 - (ss_res / ss_tot)
    return float(r2)


def get_r_squared_descriptor(r2):
    """
    Return a qualitative descriptor for an R² value.
    """
    if r2 >= 0.90:
        return "Excellent"
    elif r2 >= 0.80:
        return "Strong"
    elif r2 >= 0.70:
        return "Good"
    elif r2 >= 0.50:
        return "Moderate"
    else:
        return "Weak"


# ============================================================================
# WALK-FORWARD ANALYSIS (Per Day of Week) - SIMPLIFIED
# ============================================================================

@st.cache_data
def precompute_weekly_stats(df):
    """
    Pre-compute aggregated stats by week × day × entry_time.
    This is the key optimization - do the heavy groupby once.
    """
    df = df.copy()
    df['week_start'] = df['Date'].apply(lambda x: get_week_start(x.date()) if pd.notna(x) else None)
    
    # Aggregate by week × day × entry_time
    weekly_stats = df.groupby(['week_start', 'Day_of_week', 'Entry_Time']).agg(
        total_profit=('Profit', 'sum'),
        trade_count=('Profit', 'count'),
        avg_profit=('Profit', 'mean'),
        win_count=('Profit', lambda x: (x > 0).sum())
    ).reset_index()
    
    weekly_stats['win_rate'] = weekly_stats['win_count'] / weekly_stats['trade_count']
    
    return weekly_stats


def run_walk_forward_analysis(df, progress_bar=None, max_lookback=20):
    """
    Run walk-forward analysis for each day of week across lookback periods.
    
    For each day and each lookback:
    1. Look back N weeks, find the SINGLE Entry_Time with highest avg profit
    2. Measure how that Entry_Time performed in the test week
    3. Track results across all test weeks
    
    Pick the lookback with highest AVERAGE walk-forward profit per day.
    """
    # Pre-compute all weekly stats (cached)
    weekly_stats = precompute_weekly_stats(df)
    
    weeks = sorted(weekly_stats['week_start'].unique())
    num_weeks = len(weeks)
    
    if num_weeks < 3:
        st.error(f"Not enough data. Need at least 3 weeks, have {num_weeks}.")
        return None, None
    
    # Test lookback periods from 2 to min(max_lookback, num_weeks - 1), step by 2
    effective_max = min(max_lookback, num_weeks - 1)
    lookback_range = list(range(2, effective_max + 1, 2))  # [2, 4, 6, 8, 10, ...]
    
    weeks_list = list(weeks)
    
    results = []
    total_iterations = len(weeks_list[2:]) * len(WEEKDAYS) * len(lookback_range)
    current_iteration = 0
    
    # Pre-filter weekly_stats by day for faster lookup
    stats_by_day = {day: weekly_stats[weekly_stats['Day_of_week'] == day] for day in WEEKDAYS}
    
    for day_of_week in WEEKDAYS:
        day_stats = stats_by_day[day_of_week]
        
        for lookback_weeks in lookback_range:
            # Need at least lookback_weeks + 1 weeks to have a test week
            if lookback_weeks >= num_weeks:
                continue
                
            for test_week_idx in range(lookback_weeks, num_weeks):
                current_iteration += 1
                if progress_bar and current_iteration % 100 == 0:
                    progress_bar.progress(min(current_iteration / total_iterations, 1.0))
                
                test_week = weeks_list[test_week_idx]
                
                # Get lookback window weeks
                lookback_weeks_list = weeks_list[test_week_idx - lookback_weeks:test_week_idx]
                
                # Get training data for lookback period (this day only)
                train_data = day_stats[day_stats['week_start'].isin(lookback_weeks_list)]
                
                if train_data.empty:
                    continue
                
                # Aggregate by Entry_Time across the lookback weeks
                train_agg = train_data.groupby('Entry_Time').agg(
                    total_profit=('total_profit', 'sum'),
                    total_trades=('trade_count', 'sum')
                ).reset_index()
                train_agg['avg_profit'] = train_agg['total_profit'] / train_agg['total_trades']
                
                # Find the SINGLE Entry_Time with highest avg profit
                if train_agg.empty:
                    continue
                    
                best_row = train_agg.loc[train_agg['avg_profit'].idxmax()]
                best_entry_time = best_row['Entry_Time']
                
                # Get test week data for this day and this Entry_Time
                test_data = day_stats[
                    (day_stats['week_start'] == test_week) & 
                    (day_stats['Entry_Time'] == best_entry_time)
                ]
                
                if test_data.empty:
                    # No trade data for that Entry_Time on test week
                    actual_profit = 0
                    actual_trades = 0
                    win_rate = 0
                else:
                    actual_profit = test_data['total_profit'].sum()
                    actual_trades = test_data['trade_count'].sum()
                    win_rate = test_data['win_count'].sum() / actual_trades if actual_trades > 0 else 0
                
                results.append({
                    'day_of_week': day_of_week,
                    'lookback_weeks': lookback_weeks,
                    'test_week': test_week,
                    'predicted_entry_time': best_entry_time,
                    'actual_profit': actual_profit,
                    'actual_trades': int(actual_trades),
                    'win_rate': win_rate
                })
    
    if progress_bar:
        progress_bar.progress(1.0)
    
    if not results:
        return None, None
    
    results_df = pd.DataFrame(results)
    
    # Summary by day of week × lookback period - using AVERAGE profit
    summary = results_df.groupby(['day_of_week', 'lookback_weeks']).agg(
        total_profit=('actual_profit', 'sum'),
        avg_profit=('actual_profit', 'mean'),  # KEY: avg profit per test week
        total_trades=('actual_trades', 'sum'),
        avg_win_rate=('win_rate', 'mean'),
        weeks_tested=('test_week', 'count')
    ).reset_index()
    
    # Calculate R² for each day × lookback combination
    # R² measures how consistently the walk-forward profits accumulated
    def calc_group_r2(group_key):
        day, lb = group_key
        group_data = results_df[
            (results_df['day_of_week'] == day) & 
            (results_df['lookback_weeks'] == lb)
        ].sort_values('test_week')
        return calculate_r_squared_equity(group_data['actual_profit'].values)
    
    summary['r_squared'] = summary.apply(
        lambda row: calc_group_r2((row['day_of_week'], row['lookback_weeks'])), 
        axis=1
    )
    
    # Filter: require >20 trades in walk-forward test results
    summary = summary[summary['total_trades'] > 20]
    
    if summary.empty:
        st.error("No lookback periods produced >20 walk-forward trades. Try with more data.")
        return None, None, None
    
    return results_df, summary


def select_optimal_lookbacks(summary, min_r_squared=0.0):
    """
    Select optimal lookback for each day based on avg_profit, with optional R² filter.
    
    Args:
        summary: DataFrame with walk-forward summary stats including r_squared
        min_r_squared: Minimum R² threshold (0.0 = no filter, 0.5 = moderate, 0.7 = strict)
    
    Returns:
        optimal_by_day DataFrame
    """
    # Apply R² filter if threshold > 0
    if min_r_squared > 0:
        filtered_summary = summary[summary['r_squared'] >= min_r_squared].copy()
        
        if filtered_summary.empty:
            st.warning(f"⚠️ No lookback periods meet R² ≥ {min_r_squared}. Using all available data instead.")
            filtered_summary = summary.copy()
        else:
            # Check which days lost all their lookbacks due to R² filter
            original_days = set(summary['day_of_week'].unique())
            filtered_days = set(filtered_summary['day_of_week'].unique())
            excluded_days = original_days - filtered_days
            
            if excluded_days:
                excluded_list = ", ".join(sorted(excluded_days, key=lambda d: WEEKDAY_ORDER.get(d, 99)))
                
                # Find the best R² available for excluded days to suggest a threshold
                excluded_day_data = summary[summary['day_of_week'].isin(excluded_days)]
                if not excluded_day_data.empty:
                    best_r2_for_excluded = excluded_day_data['r_squared'].max()
                    suggested_threshold = round(best_r2_for_excluded - 0.05, 1)  # Suggest slightly below their best
                    suggested_threshold = max(0.0, suggested_threshold)  # Don't go negative
                    
                    st.warning(
                        f"⚠️ **R² filter (≥{min_r_squared}) excluded all lookbacks for: {excluded_list}**\n\n"
                        f"👉 **To include these days:** Lower the *Min R²* slider in the sidebar "
                        f"(try **{suggested_threshold:.1f}** or lower) and click **Run Walk-Forward Analysis**."
                    )
                else:
                    st.warning(
                        f"⚠️ **R² filter (≥{min_r_squared}) excluded all lookbacks for: {excluded_list}**\n\n"
                        f"👉 **To include these days:** Lower the *Min R²* slider in the sidebar "
                        f"and click **Run Walk-Forward Analysis**."
                    )
    else:
        filtered_summary = summary.copy()
    
    # Find optimal lookback for each day of week by HIGHEST AVG PROFIT
    # Only include days that have valid lookback periods
    days_with_data = filtered_summary['day_of_week'].unique()
    optimal_by_day = filtered_summary.loc[filtered_summary.groupby('day_of_week')['avg_profit'].idxmax()].copy()
    
    # Add placeholder rows for days without valid data
    for day in WEEKDAYS:
        if day not in days_with_data:
            optimal_by_day = pd.concat([optimal_by_day, pd.DataFrame([{
                'day_of_week': day,
                'lookback_weeks': 0,
                'total_profit': 0,
                'avg_profit': 0,
                'total_trades': 0,
                'avg_win_rate': 0,
                'weeks_tested': 0,
                'r_squared': 0
            }])], ignore_index=True)
    
    optimal_by_day['day_order'] = optimal_by_day['day_of_week'].map(WEEKDAY_ORDER)
    optimal_by_day = optimal_by_day.sort_values('day_order').drop('day_order', axis=1)
    
    return optimal_by_day


def get_week_recommendations(df, optimal_by_day, week_offset=1):
    """
    Generate potentials for a target week using day-specific optimal lookback periods.
    
    Args:
        df: DataFrame with trade data
        optimal_by_day: DataFrame with optimal lookback for each day
        week_offset: 0 = current week, 1 = next week (default)
    
    For each day, use its optimal lookback to find the single best Entry_Time.
    """
    max_date = df['Date'].max().date()
    current_week_start = get_week_start(max_date)
    
    # Adjust the reference point based on week_offset
    if week_offset == 0:
        # Current week: use data through previous Friday
        reference_week_start = current_week_start - timedelta(weeks=1)
        lookback_end = current_week_start - timedelta(days=3)  # Previous Friday
    else:
        # Next week (default): use all available data
        reference_week_start = current_week_start
        lookback_end = max_date
    
    recommendations = []
    
    for _, row in optimal_by_day.iterrows():
        day_of_week = row['day_of_week']
        optimal_lookback = int(row['lookback_weeks'])
        
        # Skip days without valid lookback period
        if optimal_lookback == 0:
            recommendations.append({
                'Day_of_week': day_of_week,
                'Entry_Time': 'No Valid Lookback',
                'optimal_lookback': 0,
                'avg_profit': 0,
                'total_profit': 0,
                'trade_count': 0,
                'win_rate': 0
            })
            continue
        
        # Lookback window for this day
        lookback_start = reference_week_start - timedelta(weeks=optimal_lookback)
        
        # Get training data for this day
        train_data = df[
            (df['Date'].dt.date >= lookback_start) & 
            (df['Date'].dt.date <= lookback_end) &
            (df['Day_of_week'] == day_of_week)
        ].copy()
        
        if train_data.empty:
            recommendations.append({
                'Day_of_week': day_of_week,
                'Entry_Time': 'No Data',
                'optimal_lookback': optimal_lookback,
                'avg_profit': 0,
                'total_profit': 0,
                'trade_count': 0,
                'win_rate': 0
            })
            continue
        
        # Calculate stats by Entry_Time
        stats = train_data.groupby('Entry_Time').agg(
            avg_profit=('Profit', 'mean'),
            total_profit=('Profit', 'sum'),
            trade_count=('Profit', 'count'),
            win_rate=('Profit', lambda x: (x > 0).mean())
        ).reset_index()
        
        if stats.empty:
            recommendations.append({
                'Day_of_week': day_of_week,
                'Entry_Time': 'No Data',
                'optimal_lookback': optimal_lookback,
                'avg_profit': 0,
                'total_profit': 0,
                'trade_count': 0,
                'win_rate': 0
            })
            continue
        
        # Get the SINGLE best Entry_Time by avg profit
        best_row = stats.loc[stats['avg_profit'].idxmax()]
        
        recommendations.append({
            'Day_of_week': day_of_week,
            'Entry_Time': best_row['Entry_Time'],
            'optimal_lookback': optimal_lookback,
            'avg_profit': best_row['avg_profit'],
            'total_profit': best_row['total_profit'],
            'trade_count': int(best_row['trade_count']),
            'win_rate': best_row['win_rate']
        })
    
    result = pd.DataFrame(recommendations)
    
    # Sort by day of week
    result['day_order'] = result['Day_of_week'].map(WEEKDAY_ORDER)
    result = result.sort_values('day_order').drop('day_order', axis=1)
    
    return result


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    # ========================================================================
    # THEME SECTION
    # ========================================================================
    st.sidebar.markdown("**🎨 Theme**")
    theme = st.sidebar.radio("Mode", ["Light", "Dark"], index=0, horizontal=True, label_visibility="collapsed")
    
    # PDF button placeholders - will be rendered after recommendations are generated
    print_button_placeholder = st.sidebar.empty()
    
    st.sidebar.markdown("---")
    
    # Apply theme CSS
    st.markdown(get_theme_css(theme), unsafe_allow_html=True)
    
    st.markdown("# 🎱 Time Trends Auto (TTA v0.1.0 beta) <span style='font-size: 18px; font-style: italic; color: blue;'>by jb-trader</span>", unsafe_allow_html=True)
    st.markdown("*TTA uses walk-forward analysis to automatically find the optimal lookback period for each day of the week, then presents the best entry time per day based on historical average profit.*")
    
    with st.expander("ℹ️ About TTA - Key Features & How It Differs from TTD & TTV  👇 CLICK HERE"):
        st.markdown("""
<div style="font-size: 14px;">

**Key Features:**
- **Automatic Optimization** - Finds the optimal lookback period (2 to N weeks) for each day of the week
- **Walk-Forward Testing** - Shows actual out-of-sample performance, not just backtested results
- **R² Quality Filter** - Optional filter to only consider lookbacks with consistent equity curves
- **Weekly Potential Trades** - Outputs one potential entry time per day based on optimal lookback
- **One-Click Analysis** - Just select Symbol/Strategy and run

**How TTA Differs from TTD and TTV:**

| | TTA | TTD | TTV |
|---|---|---|---|
| **Platform** | Web app | Web app | Web app |
| **Approach** | Prescriptive - "here's what to consider" | Exploratory - "analyze what you select" | Visual - charts & equity curves |
| **Automation** | Auto-finds optimal lookbacks | User chooses parameters | User chooses parameters |
| **Complexity** | Simple, focused | Feature-rich | Most detailed |
| **Metrics** | Avg Profit + R² | WF + Monte Carlo + Stability | R², Sortino, Sharpe, Profit Factor |
| **Best For** | Weekly planning | Deep pattern research | Visual pattern discovery |

**TTA** = Quick answer → **TTD** = Deep investigation → **TTV** = Visual deep-dive

</div>
        """, unsafe_allow_html=True)
    
    # Load data (cache key changes at 4:30 PM ET for auto-refresh)
    cache_key = get_cache_key()
    with st.spinner("Loading data from Google Drive..."):
        df, source = load_data(cache_key)
    
    if df.empty:
        st.error("No data available. Please check your data source.")
        return
    
    # Show latest date and refresh button in sidebar
    if pd.notna(df['Date'].max()):
        date_col, refresh_col = st.sidebar.columns([2, 1])
        with date_col:
            st.caption(f"Latest date: {df['Date'].max():%m/%d/%Y}")
        with refresh_col:
            if st.button("🔄", help="Refresh data from source"):
                st.cache_data.clear()
                st.rerun()
    
    # ========================================================================
    # SIDEBAR FILTERS
    # ========================================================================
    
    # Symbol selection
    symbols = sorted(df['Symbol'].dropna().unique())
    default_symbol_idx = symbols.index('SPX') if 'SPX' in symbols else 0
    selected_symbol = st.sidebar.selectbox("Symbol", symbols, index=default_symbol_idx)
    
    # Strategy selection (filtered by symbol)
    df_symbol = df[df['Symbol'] == selected_symbol]
    names = sorted(df_symbol['Name'].dropna().unique())
    selected_name = st.sidebar.selectbox("Strategy", names, index=0)
    
    # Filter data
    filtered_df = df[(df['Symbol'] == selected_symbol) & (df['Name'] == selected_name)].copy()
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📅 Exclusions")
    
    # Compute rebalancing dates
    min_date = filtered_df['Date'].min()
    max_date = filtered_df['Date'].max()
    rebalancing_dates = compute_rebalancing_dates(min_date.date(), max_date.date())
    fomc_dates = load_fomc_dates()
    earnings_dates = load_earnings_dates()
    earnings_plus1_dates = load_earnings_plus1_dates()
    
    # FOMC filter
    exclude_fomc = st.sidebar.checkbox("Exclude FOMC", value=True, help="FOMC announcement days")
    
    # Earnings filters - separate E and E+1
    exclude_earnings_e = st.sidebar.checkbox("Exclude Earnings (E)", value=True, help="Major earnings announcement days")
    exclude_earnings_e1 = st.sidebar.checkbox("Exclude Earnings (E+1)", value=True, help="Day after major earnings")
    
    # Butterfly Strike Liquidity filter - only show for Butterfly strategies
    exclude_illiquid_strikes = False
    predict_distance_enabled = False
    predict_distance_value = 18
    if 'Butterfly' in selected_name:
        exclude_illiquid_strikes = st.sidebar.checkbox(
            "Exclude Illiquid Strikes (25/40/65/80)", 
            value=True,
            help="Exclude butterfly trades where center strike ends in 25, 40, 65, or 80"
        )
        predict_distance_enabled = st.sidebar.checkbox(
            "Predict Distance Filter",
            value=False,
            help="Exclude trades where |Center - Predicted| > threshold"
        )
        if predict_distance_enabled:
            predict_distance_value = st.sidebar.number_input(
                "Distance Threshold",
                min_value=1,
                max_value=100,
                value=18,
                step=1,
                help="Include trades where |Center - Predicted| ≤ this value"
            )
            st.sidebar.caption(f"🔍 Active: |Center-Predicted| ≤ {predict_distance_value}")
    
    # Institutional Rebalancing Filter (matching TTV)
    st.sidebar.markdown("**Institutional Rebalancing Filter**")
    rebal_month_end = st.sidebar.checkbox("End of Month", value=True, help="Month-end trading day")
    rebal_t1 = st.sidebar.checkbox("First Prior Day (T-1)", value=True, help="One trading day before month-end")
    rebal_t2 = st.sidebar.checkbox("Second Prior Day (T-2)", value=False, help="Two trading days before month-end")
    rebal_qtr_only = st.sidebar.checkbox("Only Quarter End", value=False, help="Only exclude quarter-end dates (Mar, Jun, Sep, Dec)")
    
    # Build dates to exclude
    dates_to_exclude = set()
    
    # Add rebalancing dates
    rebal_dates = get_rebalancing_dates_to_exclude(rebalancing_dates, rebal_month_end, rebal_t1, rebal_t2, rebal_qtr_only)
    dates_to_exclude.update(rebal_dates)
    
    # Add FOMC dates
    if exclude_fomc:
        dates_to_exclude.update(fomc_dates)
    
    # Add Earnings (E) dates
    if exclude_earnings_e:
        dates_to_exclude.update(earnings_dates)
    
    # Add Earnings (E+1) dates
    if exclude_earnings_e1:
        dates_to_exclude.update(earnings_plus1_dates)
    
    if dates_to_exclude:
        filtered_df = filtered_df[~filtered_df['Date'].dt.date.isin(dates_to_exclude)]
    
    # Apply butterfly strike liquidity filter
    if exclude_illiquid_strikes and 'center_strike' in filtered_df.columns:
        illiquid_endings = {25, 40, 65, 80}
        filtered_df = filtered_df[~(filtered_df['center_strike'] % 100).isin(illiquid_endings)]
    
    # Apply Predict Distance filter (Butterfly only)
    if predict_distance_enabled and 'Center' in filtered_df.columns and 'Predicted' in filtered_df.columns:
        mask_has_center = filtered_df['Center'].notna()
        if mask_has_center.any():
            distance = abs(filtered_df.loc[mask_has_center, 'Center'] - filtered_df.loc[mask_has_center, 'Predicted'])
            valid_distance = distance <= predict_distance_value
            # Keep all non-butterfly trades and butterfly trades within distance
            keep_mask = ~mask_has_center | (mask_has_center & valid_distance)
            filtered_df = filtered_df[keep_mask]
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📈 Quality Filter")
    
    # R² threshold slider
    min_r_squared = st.sidebar.slider(
        "Min R² (Equity Curve Consistency)",
        min_value=0.0,
        max_value=0.9,
        value=0.7,
        step=0.1,
        help="R² measures how consistently profits accumulate. Higher = smoother equity curve. "
             "0.0 = no filter, 0.5 = moderate, 0.7 = strict. "
             "Only lookback periods meeting this threshold will be considered."
    )
    
    # R² qualitative description
    if min_r_squared >= 0.9:
        r2_desc = "Excellent"
    elif min_r_squared >= 0.8:
        r2_desc = "Strong"
    elif min_r_squared >= 0.7:
        r2_desc = "Good"
    elif min_r_squared >= 0.5:
        r2_desc = "Moderate"
    elif min_r_squared > 0:
        r2_desc = "Weak"
    else:
        r2_desc = "No filter"
    
    if min_r_squared > 0:
        st.sidebar.caption(f"*Only considering lookbacks with R² ≥ {min_r_squared} ({r2_desc})*")
    else:
        st.sidebar.caption(f"*{r2_desc} - all lookbacks included*")
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("⚡ Performance")
    
    # Max Lookback slider
    max_lookback = st.sidebar.slider(
        "Max Lookback (weeks)",
        min_value=4,
        max_value=52,
        value=40,
        step=2,
        help="Limit the maximum lookback period to test. Lower = faster analysis."
    )
    st.sidebar.caption(f"*Testing lookbacks: 2, 4, 6... up to {max_lookback} weeks*")
    
    # Define current filters for comparison (needed before button)
    current_filters = {
        'selected_symbol': selected_symbol,
        'selected_name': selected_name,
        'rebal_month_end': rebal_month_end,
        'rebal_t1': rebal_t1,
        'rebal_t2': rebal_t2,
        'rebal_qtr_only': rebal_qtr_only,
        'exclude_fomc': exclude_fomc,
        'exclude_earnings_e': exclude_earnings_e,
        'exclude_earnings_e1': exclude_earnings_e1,
        'exclude_illiquid_strikes': exclude_illiquid_strikes,
        'predict_distance_enabled': predict_distance_enabled,
        'predict_distance_value': predict_distance_value,
        'min_r_squared': min_r_squared,
        'max_lookback': max_lookback
    }
    
    st.sidebar.markdown("---")
    run_button = st.sidebar.button("🚀 Run Walk-Forward Analysis", type="primary", use_container_width=True)
    auto_run = st.sidebar.checkbox("Auto-run on filter change", value=False, 
                                    help="Automatically re-run analysis when filters change")
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Data Summary")
    
    # Calculate weeks available
    weeks_available = len(get_all_weeks(filtered_df))
    
    st.sidebar.write(f"**Trades:** {len(filtered_df):,}")
    st.sidebar.write(f"**Date Range:** {filtered_df['Date'].min():%Y-%m-%d} to {filtered_df['Date'].max():%Y-%m-%d}")
    st.sidebar.write(f"**Weeks Available:** {weeks_available}")
    effective_max = min(max_lookback, weeks_available - 1)
    # Actual max is the largest even number <= effective_max
    actual_max = effective_max if effective_max % 2 == 0 else effective_max - 1
    st.sidebar.write(f"**Lookback Range:** 2, 4, 6... {actual_max} weeks")
    st.sidebar.write(f"**Min WF Trades:** >20 (walk-forward test period)")
    
    # ========================================================================
    # RUN ANALYSIS
    # ========================================================================
    
    # Check if we should auto-run (filters changed and auto-run enabled)
    filters_changed = False
    if 'last_run_filters' in st.session_state:
        filters_changed = current_filters != st.session_state['last_run_filters']
    
    # Auto-run on first load (no previous results)
    first_load = 'summary_df' not in st.session_state
    
    should_run = run_button or first_load or (auto_run and filters_changed and 'summary_df' in st.session_state)
    
    if should_run:
        status_placeholder = st.empty()
        status_placeholder.subheader("⏳ Running Walk-Forward Analysis...")
        progress_bar = st.progress(0)
        
        result = run_walk_forward_analysis(
            filtered_df, 
            progress_bar=progress_bar,
            max_lookback=max_lookback
        )
        
        # Clear the status message and progress bar
        status_placeholder.empty()
        progress_bar.empty()
        
        if result[0] is None:
            st.error("Analysis failed. Check data availability.")
            return
        
        results_df, summary_df = result
        
        # Select optimal lookbacks with R² filter
        optimal_by_day = select_optimal_lookbacks(summary_df, min_r_squared=min_r_squared)
        
        # Store in session state
        st.session_state['results_df'] = results_df
        st.session_state['summary_df'] = summary_df
        st.session_state['optimal_by_day'] = optimal_by_day
        st.session_state['filtered_df'] = filtered_df
        st.session_state['selected_symbol'] = selected_symbol
        st.session_state['selected_name'] = selected_name
        st.session_state['min_r_squared'] = min_r_squared
        st.session_state['max_lookback'] = max_lookback
        # Store filter settings used in this run
        st.session_state['last_run_filters'] = current_filters
    
    # ========================================================================
    # DISPLAY RESULTS
    # ========================================================================
    
    if 'summary_df' in st.session_state:
        # Check if filter settings have changed since last run (for warning)
        if 'last_run_filters' in st.session_state:
            if current_filters != st.session_state['last_run_filters'] and not auto_run:
                st.warning("⚠️ Filter settings have changed. Click **Run Walk-Forward Analysis** to update displayed results.")
        
        summary_df = st.session_state['summary_df']
        results_df = st.session_state['results_df']
        optimal_by_day = st.session_state['optimal_by_day']
        filtered_df = st.session_state['filtered_df']
        selected_symbol = st.session_state['selected_symbol']
        selected_name = st.session_state['selected_name']
        
        
        # ====================================================================
        # WEEKLY POTENTIALS
        # ====================================================================
        st.markdown("---")
        st.subheader("🎱 Weekly Potential Trades (Best Entry Time per Day)")
        
        # Week selection toggle
        week_selection = st.radio(
            "Select Week:",
            ["Next Week", "Current Week"],
            horizontal=True,
            help="Next Week uses all available data. Current Week uses data through previous Friday."
        )
        week_offset = 0 if week_selection == "Current Week" else 1
        
        recommendations = get_week_recommendations(filtered_df, optimal_by_day, week_offset=week_offset)
        
        if recommendations.empty:
            st.warning("No slots meet the criteria for weekly potentials.")
            st.session_state['recommendations'] = None
        else:
            # Calculate target week dates
            max_date = filtered_df['Date'].max().date()
            current_week_start = get_week_start(max_date)
            
            if week_offset == 0:
                # Current week
                target_monday = current_week_start
                target_friday = target_monday + timedelta(days=4)
            else:
                # Next week
                target_monday = current_week_start + timedelta(weeks=1)
                target_friday = target_monday + timedelta(days=4)
            
            # Store recommendations for PDF export
            st.session_state['recommendations'] = {
                'week_type': week_selection,
                'target_monday': target_monday,
                'target_friday': target_friday,
                'symbol': selected_symbol,
                'strategy': selected_name,
                'df': recommendations.copy()
            }
            
            # Render PDF download button in sidebar placeholder
            rec_data = st.session_state['recommendations']
            pdf_bytes = generate_trade_plan_pdf(
                week_type=rec_data['week_type'],
                target_monday=rec_data['target_monday'],
                target_friday=rec_data['target_friday'],
                symbol=rec_data['symbol'],
                strategy=rec_data['strategy'],
                recommendations_df=rec_data['df']
            )
            # Print button - downloads PDF for printing/saving
            print_filename = f"TTA_TradePlan_{rec_data['symbol']}_{rec_data['target_monday']:%Y%m%d}.pdf"
            print_button_placeholder.download_button(
                label="🖨️ Print Trade Plan (PDF)",
                data=pdf_bytes,
                file_name=print_filename,
                mime="application/pdf"
            )
            
            st.info(f"**Trading Week:** {target_monday:%B %d, %Y} - {target_friday:%B %d, %Y}")
            st.write(f"**Symbol:** {selected_symbol} | **Strategy:** {selected_name}")
            st.markdown("*In-sample test stats*")
            
            # Format potentials table
            display_recs = recommendations.copy()
            
            display_recs['optimal_lookback'] = display_recs['optimal_lookback'].apply(lambda x: 'N/A' if x == 0 else f"{int(x)} wks")
            display_recs['avg_profit'] = display_recs.apply(lambda r: 'N/A' if r['trade_count'] == 0 else f"${r['avg_profit']:,.0f}", axis=1)
            display_recs['win_rate'] = display_recs.apply(lambda r: 'N/A' if r['trade_count'] == 0 else f"{r['win_rate']:.1%}", axis=1)
            display_recs['trade_count'] = display_recs['trade_count'].astype(int)
            
            display_recs = display_recs[['Day_of_week', 'Entry_Time', 'avg_profit', 'win_rate', 'trade_count', 'optimal_lookback']]
            display_recs.columns = ['Day', 'Entry Time', 'Avg Profit', 'Win Rate', 'Trades', 'Lookback']
            
            # Generate HTML table with theme-aware colors
            if theme == "Light":
                th_style = 'font-size: 14px; font-weight: bold; color: black; padding: 8px; border: 1px solid #ddd; background-color: #f5f5f5; text-align: center;'
                td_style = 'font-size: 14px; font-weight: bold; color: black; padding: 8px; border: 1px solid #ddd; text-align: center;'
            else:
                th_style = 'font-size: 14px; font-weight: bold; color: #fafafa; padding: 8px; border: 1px solid #444; background-color: #262730; text-align: center;'
                td_style = 'font-size: 14px; font-weight: bold; color: #fafafa; padding: 8px; border: 1px solid #444; text-align: center;'
            
            html_recs = display_recs.to_html(index=False, escape=False)
            html_recs = html_recs.replace('<table', '<table style="width:100%; border-collapse: collapse;"')
            html_recs = html_recs.replace('<th>', f'<th style="{th_style}">')
            html_recs = html_recs.replace('<td>', f'<td style="{td_style}">')
            st.markdown(html_recs, unsafe_allow_html=True)
            
            # Summary stats - use raw numeric values from potentials before formatting
            col1, col2 = st.columns(2)
            with col1:
                valid_recs = recommendations[recommendations['trade_count'] > 0]
                avg_profit = valid_recs['avg_profit'].mean() if not valid_recs.empty else 0
                st.metric("Avg Expected Profit", f"${avg_profit:,.0f}")
            with col2:
                avg_wr = valid_recs['win_rate'].mean() * 100 if not valid_recs.empty else 0
                st.metric("Avg Win Rate", f"{avg_wr:.1f}%")
            
            st.markdown("<span style='color: red; font-style: italic;'>Stats above are from the lookback training window. Actual walk-forward performance shown in graphs in next section below.</span> <span style='font-style: italic;'>Scroll down there is more...</span>", unsafe_allow_html=True)
            
            # Drill-down chart for selected day
            st.markdown("")
            st.markdown("---")
            st.markdown("### 📈 Walk-Forward Performance Details by Day &nbsp;&nbsp;<span style='font-size: 14px; font-weight: normal; color: gray;'>*(filter changes applied when rerun)*</span>", unsafe_allow_html=True)
            
            with st.expander("ℹ️ What is Walk-Forward Analysis? Why is this data unbiased?  👇 CLICK HERE"):
                st.markdown("""
<div style="font-size: 18px;">

**What is Walk-Forward Analysis?**

Walk-forward analysis is a rigorous testing method that simulates how a strategy would perform in real-time trading. Here's how it works:

1. **Training Window** - The system looks back N weeks (the "lookback period") to find the best entry time based on historical performance
2. **Test Week** - It then trades that entry time in the *following* week and records the actual result
3. **Roll Forward** - The window advances one week, and the process repeats

**Why This Data is Unbiased (Out-of-Sample):**

Unlike traditional backtesting where you optimize on the same data you're testing, walk-forward analysis:

- ✅ **Never peeks ahead** - Decisions are made only with data available at that point in time
- ✅ **Tests on unseen data** - Each test week's results come from data that was NOT used to select the entry time
- ✅ **Simulates real trading** - This is exactly how you would use the system live
- ✅ **Exposes overfitting** - Strategies that only work on cherry-picked data will fail in walk-forward testing

**The charts below show actual walk-forward results** - what would have happened if you followed the system's potentials week by week, making decisions only with the information available at that time.

This is as close to "real" performance as you can get without live trading.

</div>
                """, unsafe_allow_html=True)
            
            valid_days = recommendations[recommendations['trade_count'] > 0]['Day_of_week'].tolist()
            if valid_days:
                selected_day_detail = st.radio(
                    "Select Day of Week",
                    valid_days,
                    key="day_detail_select",
                    horizontal=True
                )
                
                # Get optimal lookback for selected day
                day_optimal_lb = int(optimal_by_day[optimal_by_day['day_of_week'] == selected_day_detail]['lookback_weeks'].values[0])
                
                if day_optimal_lb > 0:
                    # Get walk-forward results for this day and lookback
                    day_wf_results = results_df[
                        (results_df['day_of_week'] == selected_day_detail) & 
                        (results_df['lookback_weeks'] == day_optimal_lb)
                    ].copy()
                    day_wf_results = day_wf_results.sort_values('test_week')
                    day_wf_results['cumulative_profit'] = day_wf_results['actual_profit'].cumsum()
                    
                    # Get the entry time for this day
                    day_entry_time = recommendations[recommendations['Day_of_week'] == selected_day_detail]['Entry_Time'].values[0]
                    
                    # Create combined bar and line chart
                    fig_detail = go.Figure()
                    
                    # Add bars for individual trade profit (green positive, red negative)
                    colors_bars = ['#28a745' if p >= 0 else '#dc3545' for p in day_wf_results['actual_profit']]
                    fig_detail.add_trace(go.Bar(
                        x=day_wf_results['test_week'],
                        y=day_wf_results['actual_profit'],
                        name='Weekly Profit',
                        marker_color=colors_bars,
                        opacity=0.7
                    ))
                    
                    # Add line for cumulative profit
                    fig_detail.add_trace(go.Scatter(
                        x=day_wf_results['test_week'],
                        y=day_wf_results['cumulative_profit'],
                        mode='lines+markers',
                        name='Cumulative Profit',
                        line=dict(color='#1f77b4', width=3),
                        marker=dict(size=6)
                    ))
                    
                    # Theme-aware chart colors
                    if theme == "Light":
                        chart_bg = 'white'
                        grid_color = '#e0e0e0'
                        font_color = '#000000'
                    else:
                        chart_bg = '#0e1117'
                        grid_color = '#333333'
                        font_color = '#fafafa'
                    
                    fig_detail.update_layout(
                        title=dict(
                            text=f"{selected_day_detail} @ {day_entry_time} - Walk-Forward Performance ({day_optimal_lb} wk lookback)<br>"
                                 f"<span style='font-size:12px;color:#666'>{selected_symbol} - {selected_name}</span>",
                            x=0.5,
                            xanchor='center',
                            font=dict(size=18, color=font_color)
                        ),
                        xaxis_title="Test Week",
                        yaxis_title="Profit ($)",
                        height=500,
                        hovermode='x unified',
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color=font_color)),
                        plot_bgcolor=chart_bg,
                        paper_bgcolor=chart_bg,
                        barmode='overlay',
                        font=dict(color=font_color)
                    )
                    fig_detail.update_yaxes(tickformat="$,.0f", gridcolor=grid_color, zeroline=True, zerolinecolor='#666', zerolinewidth=1)
                    fig_detail.update_xaxes(gridcolor=grid_color)
                    
                    st.plotly_chart(fig_detail, use_container_width=True)
                    
                    # Summary stats for this day (trade-based win rate)
                    total_profit = day_wf_results['actual_profit'].sum()
                    total_trades = day_wf_results['actual_trades'].sum()
                    # Calculate winning trades from win_rate * trades per week
                    winning_trades = (day_wf_results['win_rate'] * day_wf_results['actual_trades']).sum()
                    trade_win_rate = winning_trades / total_trades if total_trades > 0 else 0
                    
                    # Get R² for this day's optimal lookback
                    day_r_squared = optimal_by_day[optimal_by_day['day_of_week'] == selected_day_detail]['r_squared'].values[0] if 'r_squared' in optimal_by_day.columns else 0
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Win Rate", f"{int(winning_trades)}/{int(total_trades)} ({trade_win_rate:.0%})" if total_trades > 0 else "N/A")
                    with col2:
                        avg_trade = total_profit / total_trades if total_trades > 0 else 0
                        st.metric("Avg Trade Profit", f"${avg_trade:,.0f}")
                    with col3:
                        r2_descriptor = get_r_squared_descriptor(day_r_squared)
                        st.metric("R² (Consistency)", f"{day_r_squared:.3f} ({r2_descriptor})")
        
        # ====================================================================
        # CUMULATIVE WALK-FORWARD PROFIT CHART BY DAY
        # ====================================================================
        st.markdown("---")
        st.subheader("📊 Cumulative Walk-Forward Profit by Day of Week")
        
        fig = go.Figure()
        colors = {'Monday': '#2E86AB', 'Tuesday': '#A23B72', 'Wednesday': '#F18F01', 
                  'Thursday': '#C73E1D', 'Friday': '#3B1F2B'}
        
        for day in WEEKDAYS:
            day_optimal_lb = int(optimal_by_day[optimal_by_day['day_of_week'] == day]['lookback_weeks'].values[0])
            
            # Skip days without valid lookback
            if day_optimal_lb == 0:
                continue
                
            day_results = results_df[
                (results_df['day_of_week'] == day) & 
                (results_df['lookback_weeks'] == day_optimal_lb)
            ].copy()
            day_results = day_results.sort_values('test_week')
            day_results['cumulative_profit'] = day_results['actual_profit'].cumsum()
            
            fig.add_trace(go.Scatter(
                x=day_results['test_week'],
                y=day_results['cumulative_profit'],
                mode='lines+markers',
                name=f'{day} ({day_optimal_lb}wk)',
                line=dict(color=colors.get(day, '#666'), width=2),
                marker=dict(size=4)
            ))
        
        # Theme-aware chart colors for summary chart
        if theme == "Light":
            chart_bg = 'white'
            grid_color = '#e0e0e0'
            font_color = '#000000'
        else:
            chart_bg = '#0e1117'
            grid_color = '#333333'
            font_color = '#fafafa'
        
        fig.update_layout(
            title=dict(
                text=f"Walk-Forward Performance by Day (Using Optimal Lookback per Day)<br>"
                     f"<span style='font-size:12px;color:#666'>{selected_symbol} - {selected_name}</span>",
                x=0.5,
                xanchor='center',
                font=dict(size=18, color=font_color)
            ),
            xaxis_title="Test Week",
            yaxis_title="Cumulative Profit ($)",
            height=600,
            hovermode='x unified',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color=font_color)),
            plot_bgcolor=chart_bg,
            paper_bgcolor=chart_bg,
            font=dict(color=font_color)
        )
        fig.update_yaxes(tickformat="$,.0f", gridcolor=grid_color)
        fig.update_xaxes(gridcolor=grid_color)
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Total stats across all days using optimal lookbacks (trade-based)
        total_wf_profit = 0
        total_trades = 0
        winning_trades = 0
        r_squared_values = []
        for day in WEEKDAYS:
            day_optimal_lb = int(optimal_by_day[optimal_by_day['day_of_week'] == day]['lookback_weeks'].values[0])
            
            # Skip days without valid lookback
            if day_optimal_lb == 0:
                continue
            
            # Get R² for this day
            if 'r_squared' in optimal_by_day.columns:
                day_r2 = optimal_by_day[optimal_by_day['day_of_week'] == day]['r_squared'].values[0]
                r_squared_values.append(day_r2)
                
            day_results = results_df[
                (results_df['day_of_week'] == day) & 
                (results_df['lookback_weeks'] == day_optimal_lb)
            ]
            total_wf_profit += day_results['actual_profit'].sum()
            total_trades += day_results['actual_trades'].sum()
            winning_trades += (day_results['win_rate'] * day_results['actual_trades']).sum()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            trade_win_rate = winning_trades / total_trades if total_trades > 0 else 0
            st.metric("Win Rate (All Days)", f"{int(winning_trades)}/{int(total_trades)} ({trade_win_rate:.0%})" if total_trades > 0 else "N/A")
        with col2:
            st.metric("Avg Trade Profit", f"${total_wf_profit/total_trades:,.0f}" if total_trades > 0 else "N/A")
        with col3:
            avg_r2 = np.mean(r_squared_values) if r_squared_values else 0
            avg_r2_descriptor = get_r_squared_descriptor(avg_r2)
            st.metric("Avg R² (Consistency)", f"{avg_r2:.3f} ({avg_r2_descriptor})")
        
        # ====================================================================
        # EXPORT
        # ====================================================================
        st.markdown("---")
        st.markdown("**CSV Download Files**")
        
        # Download buttons in a row
        col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
        
        with col1:
            csv_optimal = optimal_by_day.to_csv(index=False)
            st.download_button(
                label="📥 Optimal by Day",
                data=csv_optimal,
                file_name=f"WF_OptimalByDay_{selected_symbol}_{selected_name}_{datetime.now():%Y%m%d}.csv",
                mime="text/csv"
            )
        
        with col2:
            csv_summary = summary_df.to_csv(index=False)
            st.download_button(
                label="📥 Full Summary",
                data=csv_summary,
                file_name=f"WF_Summary_{selected_symbol}_{selected_name}_{datetime.now():%Y%m%d}.csv",
                mime="text/csv"
            )
        
        with col3:
            if not recommendations.empty:
                potentials_df = recommendations[['Day_of_week', 'Entry_Time']].copy()
                potentials_df.columns = ['Day', 'Entry_Time']
                csv_potentials = potentials_df.to_csv(index=False)
                st.download_button(
                    label="📥 Potential Trades",
                    data=csv_potentials,
                    file_name=f"WF_PotentialTrades_{selected_symbol}_{selected_name}_{datetime.now():%Y%m%d}.csv",
                    mime="text/csv"
                )
        
        with col4:
            st.markdown(
                "<div class='disclaimer-box' style='font-size: 12px; color: #cc0000 !important; background-color: yellow; margin-top: 0px; padding: 6px;'>"
                "<strong style='color: #cc0000 !important;'>Disclaimer:</strong> "
                "<span style='color: #cc0000 !important;'>Educational use only – not financial advice. Past performance ≠ future results. "
                "Do not trade with money you cannot afford to lose.</span>"
                "</div>",
                unsafe_allow_html=True
            )
        
        # File descriptions in expanders - full width below buttons
        with st.expander("ℹ️ What's in these files? (click to expand)"):
            desc_col1, desc_col2, desc_col3 = st.columns(3)
            
            with desc_col1:
                st.markdown("""
**📥 Optimal by Day**

Best lookback for each day:
- `day_of_week` - Mon-Fri
- `lookback_weeks` - Optimal period
- `avg_profit` - Avg per test week
- `total_trades` - WF trade count
- `avg_win_rate` - Win rate
- `r_squared` - Consistency (0-1)
                """)
            
            with desc_col2:
                st.markdown("""
**📥 Full Summary**

ALL day × lookback combos:
- `day_of_week` - Mon-Fri
- `lookback_weeks` - Each tested
- `avg_profit` - Avg per test week
- `total_trades` - Trade count (>20)
- `avg_win_rate` - Win rate
- `r_squared` - Consistency (0-1)
                """)
            
            with desc_col3:
                st.markdown("""
**📥 Potential Trades**

Simple 2-column actionable output:
- `Day` - Monday-Friday
- `Entry_Time` - Recommended time

*Use this for next week's trading.*
                """)


if __name__ == "__main__":
    main()
