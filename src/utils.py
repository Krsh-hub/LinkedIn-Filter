"""Utility functions for logging, URL normalization, string sanitization, and data quality scoring."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse


def setup_logging(log_dir: str | Path = "logs", log_level: str = "INFO") -> logging.Logger:
    """Configure logging to write to both logs/app.log and the console.
    
    Args:
        log_dir: Path to directory where log files should be stored.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR).
        
    Returns:
        Configured logger instance.
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    log_file = log_path / "app.log"

    level = getattr(logging, log_level.upper(), logging.INFO)
    logger = logging.getLogger("linkedin_analyzer")
    logger.setLevel(level)

    # Avoid duplicate handlers if setup_logging is called multiple times
    if not logger.handlers:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # File handler (logs/app.log)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_formatter = logging.Formatter("[%(levelname)s] %(message)s")
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    return logger


def clean_text(val: Any) -> str:
    """Safely convert any value (NaN, None, float, etc.) to a stripped string.
    
    Args:
        val: Input value of any type.
        
    Returns:
        Clean stripped string, or empty string if None/NaN.
    """
    if val is None:
        return ""
    # Check for pandas/numpy NaN or float NaN
    if isinstance(val, float):
        import math
        if math.isnan(val):
            return ""
    text = str(val).strip()
    if text.lower() in ("nan", "none", "null", "undefined"):
        return ""
    return text


def normalize_linkedin_url(url: Any) -> str:
    """Normalize a LinkedIn profile URL for reliable deduplication and comparison.
    
    Examples:
        https://www.linkedin.com/in/example/ -> linkedin.com/in/example
        http://linkedin.com/in/example?trk=public-profile -> linkedin.com/in/example
        www.linkedin.com/in/example/ -> linkedin.com/in/example
        
    Args:
        url: Raw URL string or other type.
        
    Returns:
        Canonical URL string without protocol, 'www.', query params, or trailing slash.
    """
    raw = clean_text(url).lower()
    if not raw:
        return ""

    # Ensure URL has a scheme for urlparse if missing
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw

    parsed = urlparse(raw)
    hostname = parsed.netloc or ""
    # Strip leading www.
    hostname = re.sub(r"^www\.", "", hostname)

    # Clean path: remove trailing slashes and normalize multiple slashes
    path = parsed.path.strip("/")
    if path:
        path = "/" + re.sub(r"/+", "/", path)
    else:
        path = ""

    # Check if this resembles a valid linkedin domain
    if "linkedin" in hostname:
        normalized = f"{hostname}{path}"
        return normalized.rstrip("/")

    return f"{hostname}{path}".rstrip("/")


def compute_data_quality_score(row: Mapping[str, Any]) -> int:
    """Compute data quality score (0 to 100) based on availability of key fields.
    
    Scoring weights:
        - Full Name or First Name present: +20
        - Company present: +20
        - Position present: +20
        - LinkedIn URL present: +20
        - Email present: +20
        
    Args:
        row: Dictionary or pandas Series representing a contact.
        
    Returns:
        Integer quality score between 0 and 100.
    """
    score = 0
    
    # 1. Name (+20)
    full_name = clean_text(row.get("full_name", ""))
    first_name = clean_text(row.get("first_name", ""))
    if full_name or first_name:
        score += 20
        
    # 2. Company (+20)
    if clean_text(row.get("company", "")):
        score += 20
        
    # 3. Position (+20)
    if clean_text(row.get("position", "")):
        score += 20
        
    # 4. LinkedIn URL (+20)
    if clean_text(row.get("linkedin_url", "")):
        score += 20
        
    # 5. Email (+20)
    email = clean_text(row.get("email", ""))
    if email and "@" in email:
        score += 20
        
    return score
