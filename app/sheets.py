import os
import json
import logging
import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger("sheets")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

_client = None
_sheet = None


def get_gspread_client():
    global _client
    if _client is not None:
        return _client

    raw_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "./service_account.json")
    if not raw_json:
        logger.warning("No GOOGLE_SERVICE_ACCOUNT_JSON provided.")
        return None

    try:
        # Check if raw_json is a file path or direct JSON string
        if raw_json.strip().startswith("{"):
            info = json.loads(raw_json)
            creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        elif os.path.exists(raw_json):
            creds = Credentials.from_service_account_file(raw_json, scopes=SCOPES)
        else:
            logger.warning(f"Google service account file not found at path: {raw_json}")
            return None

        _client = gspread.authorize(creds)
        return _client
    except Exception as e:
        logger.error(f"Failed to initialize Google Sheets client: {e}")
        return None


def _get_sheet():
    global _sheet
    if _sheet is not None:
        return _sheet

    client = get_gspread_client()
    if not client:
        return None

    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        logger.warning("GOOGLE_SHEET_ID environment variable not set.")
        return None

    try:
        _sheet = client.open_by_key(sheet_id).sheet1
        _ensure_headers(_sheet)
        return _sheet
    except Exception as e:
        logger.error(f"Failed to open Google Sheet ID '{sheet_id}': {e}")
        return None


def _ensure_headers(sheet):
    """Auto-detect and append missing verdict column headers to row 1."""
    try:
        header = sheet.row_values(1)
        if not header:
            # Empty sheet - create initial header
            sheet.update('A1:F1', [["name", "website", "fit", "confidence", "follow_up", "reasoning"]])
            return

        header_lower = [h.strip().lower() for h in header]
        required_cols = ["fit", "confidence", "follow_up", "reasoning"]
        missing = [c for c in required_cols if c not in header_lower]

        if missing:
            next_col_idx = len(header) + 1
            for col_name in missing:
                sheet.update_cell(1, next_col_idx, col_name)
                next_col_idx += 1
            logger.info(f"Auto-created missing headers in Google Sheet: {missing}")
    except Exception as e:
        logger.warning(f"Could not auto-ensure headers: {e}")


def read_companies(only_unprocessed: bool = False):
    """
    Reads company list from Google Sheet.
    Returns list of dicts with row_number (1-indexed).
    If only_unprocessed=True, skips rows where fit is already populated.
    """
    sheet = _get_sheet()
    if not sheet:
        logger.warning("Google Sheet not accessible. Returning empty list or mock list if configured.")
        return []

    def _get(rec, *keys):
        """Case-insensitive multi-key lookup on a record dict."""
        rec_lower = {k.strip().lower(): v for k, v in rec.items()}
        for key in keys:
            val = rec_lower.get(key.lower())
            if val is not None and str(val).strip():
                return str(val).strip()
        return ""

    try:
        records = sheet.get_all_records()  # list of dicts, header-driven
        companies = []
        for i, rec in enumerate(records, start=2):  # row 1 is header
            name = _get(rec, "company_name", "name", "company", "company name", "startup", "startup name")
            website = _get(rec, "website", "url", "link", "site", "homepage")
            fit_val = _get(rec, "fit", "verdict", "processed")

            if not name:
                continue

            if only_unprocessed and fit_val and fit_val.lower() not in ("false", "0", "", "no"):
                logger.info(f"Skipping already processed row {i} ({name})")
                continue

            companies.append({
                "row_number": i,
                "company_name": name,
                "website": website
            })

        logger.info(f"Loaded {len(companies)} companies from Google Sheet")
        return companies
    except Exception as e:
        logger.error(f"Error reading from Google Sheet: {e}")
        return []


def write_verdict(row_number: int, fit: bool, confidence: float, follow_up_question: str, reasoning: str = "") -> bool:
    """
    Writes verdict back into the Google Sheet.
    Dynamically finds column positions by header name.
    """
    sheet = _get_sheet()
    if not sheet:
        logger.warning(f"Cannot write verdict for row {row_number}: Google Sheet not connected.")
        return False

    try:
        header = sheet.row_values(1)

        def col_index(col_name):
            for idx, h in enumerate(header, start=1):
                if h.strip().lower() == col_name.lower():
                    return idx
            return None

        fit_col = col_index("fit") or 4
        conf_col = col_index("confidence") or 5
        followup_col = col_index("follow_up") or 6
        reasoning_col = col_index("reasoning") or 7
        proc_col = col_index("processed")

        sheet.update_cell(row_number, fit_col, "Yes" if fit else "No")
        sheet.update_cell(row_number, conf_col, round(confidence, 2))
        sheet.update_cell(row_number, followup_col, follow_up_question)
        if reasoning:
            sheet.update_cell(row_number, reasoning_col, reasoning)
        if proc_col:
            sheet.update_cell(row_number, proc_col, "TRUE")

        logger.info(f"Successfully wrote verdict back to Sheet row {row_number}")
        return True
    except Exception as e:
        logger.error(f"Failed to write verdict to Sheet row {row_number}: {e}")
        return False

