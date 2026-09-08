"""Robust CSV loader for LinkedIn connection exports."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Tuple, List, Optional
import pandas as pd

logger = logging.getLogger("linkedin_analyzer")

# Common keywords that indicate the actual header row in a LinkedIn CSV export
HEADER_CANDIDATE_KEYWORDS = {
    "first name", "firstname", "last name", "lastname",
    "url", "profile url", "linkedin url",
    "company", "organization", "company name",
    "position", "job title", "title", "role",
    "email", "email address", "connected on"
}


def detect_header_row(file_path: Path, encoding: str, max_search_lines: int = 15) -> int:
    """Scan the first few lines of a CSV file to locate the actual header row.
    
    LinkedIn connection exports frequently include a multi-line explanatory
    notes preamble at the top of the file before the CSV columns start.
    
    Args:
        file_path: Path to the CSV file.
        encoding: Text encoding to use when reading.
        max_search_lines: Maximum number of lines to inspect.
        
    Returns:
        Zero-based index of the header row (0 if no preamble detected).
    """
    try:
        with open(file_path, mode="r", encoding=encoding, errors="replace") as f:
            reader = csv.reader(f)
            for idx, row in enumerate(reader):
                if idx >= max_search_lines:
                    break
                if not row:
                    continue
                # Normalize row items to lowercase stripped strings
                row_items = [str(item).strip().lower() for item in row if str(item).strip()]
                # Count how many header keywords match cells in this row
                matches = sum(1 for item in row_items if item in HEADER_CANDIDATE_KEYWORDS)
                # If 2 or more expected keywords match, this is our header row
                if matches >= 2:
                    return idx
    except Exception as e:
        logger.debug(f"Error while scanning header rows in {file_path}: {e}")
    return 0


def load_csv(file_path: str | Path) -> pd.DataFrame:
    """Load a LinkedIn connections CSV file robustly.
    
    Handles:
    - Multiple encodings (utf-8-sig, utf-8, latin1, cp1252)
    - Preamble notes commonly present in LinkedIn exports
    - Malformed rows (skips bad lines with warnings)
    - Empty cells (preserves as empty strings, no NaN issues)
    - Type preservation as strings
    
    Args:
        file_path: Path to the CSV file.
        
    Returns:
        pandas DataFrame containing loaded and cleaned string data.
        
    Raises:
        FileNotFoundError: If the CSV file does not exist.
        ValueError: If the file is empty or cannot be parsed.
    """
    path = Path(file_path)
    if not path.exists():
        err_msg = f"CSV file not found: {path.resolve()}"
        logger.error(err_msg)
        raise FileNotFoundError(err_msg)

    if not path.is_file():
        err_msg = f"Path is not a regular file: {path.resolve()}"
        logger.error(err_msg)
        raise ValueError(err_msg)

    encodings_to_try = ["utf-8-sig", "utf-8", "cp1252", "latin1"]
    last_exception: Optional[Exception] = None
    df: Optional[pd.DataFrame] = None
    successful_encoding: Optional[str] = None

    for enc in encodings_to_try:
        try:
            skip = detect_header_row(path, enc)
            df = pd.read_csv(
                path,
                encoding=enc,
                skiprows=skip,
                dtype=str,
                keep_default_na=False,
                na_values=[""],
                on_bad_lines="skip"
            )
            successful_encoding = enc
            logger.info(f"Successfully read {path.name} with encoding '{enc}' (skipped {skip} preamble rows).")
            break
        except (UnicodeDecodeError, pd.errors.ParserError) as e:
            last_exception = e
            logger.debug(f"Failed to load {path.name} with encoding '{enc}': {e}")
            continue

    if df is None or successful_encoding is None:
        err_msg = f"Failed to parse CSV file '{path.name}' with any supported encoding. Last error: {last_exception}"
        logger.error(err_msg)
        raise ValueError(err_msg)

    # Clean whitespace and strip column headers
    df.columns = [str(c).strip() for c in df.columns]
    
    # Fill any remaining NaNs with empty string
    df = df.fillna("")

    # If df has 0 rows or 0 columns
    if df.empty:
        err_msg = f"CSV file '{path.name}' is empty or contains no data rows."
        logger.error(err_msg)
        raise ValueError(err_msg)

    logger.info(f"Loaded {len(df)} rows and {len(df.columns)} columns from '{path.name}'.")
    logger.info(f"Detected raw columns: {list(df.columns)}")

    return df
