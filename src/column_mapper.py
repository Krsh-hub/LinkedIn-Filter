"""Intelligent column mapping for LinkedIn connection exports."""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Set, Tuple
import pandas as pd

logger = logging.getLogger("linkedin_analyzer")

# Synonym lookup dictionary (lowercase, stripped)
SYNONYMS: Dict[str, List[str]] = {
    "first_name": [
        "first name", "firstname", "first_name", "fname", "given name", "first"
    ],
    "last_name": [
        "last name", "lastname", "last_name", "lname", "surname", "family name", "last"
    ],
    "full_name": [
        "full name", "fullname", "full_name", "name", "contact name", "person name"
    ],
    "linkedin_url": [
        "url", "profile url", "linkedin url", "linkedin", "profile_url",
        "linkedin_profile", "link", "profile link", "linkedin_url"
    ],
    "email": [
        "email address", "email", "e-mail", "email_address", "contact email", "mail"
    ],
    "company": [
        "company", "company name", "company_name", "organization",
        "organization name", "current company", "employer", "business"
    ],
    "position": [
        "position", "job title", "title", "job_title", "current position",
        "role", "designation", "headline", "occupation"
    ],
    "connected_on": [
        "connected on", "connection date", "connected date", "connected_on",
        "connection_date", "created at", "date connected", "connected"
    ],
    "location": [
        "location", "city", "country", "region", "geographic area", "address"
    ]
}


def normalize_header_name(header: str) -> str:
    """Normalize header text for comparison by removing special characters and lowering case."""
    clean = re.sub(r"[_\-]+", " ", str(header).strip().lower())
    clean = re.sub(r"\s+", " ", clean)
    return clean


def identify_columns(raw_columns: List[str]) -> Tuple[Dict[str, Optional[str]], Dict[str, str]]:
    """Identify and map raw CSV column names to standardized schema fields.
    
    Args:
        raw_columns: List of column names directly from the loaded CSV.
        
    Returns:
        Tuple containing:
        1. schema_map: dict mapping target field name -> raw column name (or None)
        2. display_map: dict describing how each target was resolved for user presentation
    """
    normalized_raw = {normalize_header_name(col): col for col in raw_columns}
    schema_map: Dict[str, Optional[str]] = {}
    display_map: Dict[str, str] = {}

    used_cols: Set[str] = set()

    # Pass 1: Exact matches
    for target, syn_list in SYNONYMS.items():
        matched_raw: Optional[str] = None
        for syn in syn_list:
            norm_syn = normalize_header_name(syn)
            if norm_syn in normalized_raw:
                cand_col = normalized_raw[norm_syn]
                # Avoid assigning First Name / Last Name column to full_name
                if target == "full_name" and norm_syn in ("name",) and (schema_map.get("first_name") or "first name" in normalized_raw):
                    continue
                matched_raw = cand_col
                used_cols.add(cand_col)
                break
        schema_map[target] = matched_raw

    # Pass 2: Fallback substring matching for unassigned targets
    for target, syn_list in SYNONYMS.items():
        if schema_map.get(target):
            continue
        matched_raw = None
        for syn in syn_list:
            norm_syn = normalize_header_name(syn)
            if norm_syn in ("name", "first", "last"):
                # Avoid over-broad substring matches for short generic words
                continue
            for norm_cand, orig_col in normalized_raw.items():
                if orig_col in used_cols:
                    continue
                if f" {norm_syn} " in f" {norm_cand} ":
                    matched_raw = orig_col
                    used_cols.add(orig_col)
                    break
            if matched_raw:
                break
        schema_map[target] = matched_raw

    # If first_name or last_name is mapped, ensure full_name does not duplicate them
    if schema_map.get("full_name") in (schema_map.get("first_name"), schema_map.get("last_name")):
        schema_map["full_name"] = None

    # Build display map
    has_fn = bool(schema_map.get("first_name"))
    has_ln = bool(schema_map.get("last_name"))
    has_full = bool(schema_map.get("full_name"))

    if has_fn and has_ln:
        display_map["Name"] = f"{schema_map['first_name']} + {schema_map['last_name']}"
    elif has_full:
        display_map["Name"] = f"{schema_map['full_name']}"
    elif has_fn:
        display_map["Name"] = f"{schema_map['first_name']}"
    else:
        display_map["Name"] = "(Not detected)"

    display_map["Position"] = schema_map.get("position") or "(Not detected)"
    display_map["Company"] = schema_map.get("company") or "(Not detected)"
    display_map["LinkedIn URL"] = schema_map.get("linkedin_url") or "(Not detected)"
    display_map["Email"] = schema_map.get("email") or "(Not detected)"
    display_map["Connected On"] = schema_map.get("connected_on") or "(Not detected)"
    if schema_map.get("location"):
        display_map["Location"] = schema_map["location"]

    return schema_map, display_map


def format_column_mapping_display(display_map: Dict[str, str]) -> str:
    """Format the detected column mappings for printing to console or log."""
    lines = ["Detected columns:"]
    for key, val in display_map.items():
        lines.append(f"  {key} → {val}")
    return "\n".join(lines)


def map_and_normalize_dataframe(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """Map raw dataframe columns to the standardized internal schema while preserving original columns.
    
    Standardized internal schema:
    - first_name
    - last_name
    - full_name
    - linkedin_url
    - email
    - company
    - position
    - connected_on
    - location (if detected)
    
    Args:
        df: Raw pandas DataFrame.
        
    Returns:
        Tuple of (normalized DataFrame, display_map dictionary).
    """
    raw_cols = list(df.columns)
    schema_map, display_map = identify_columns(raw_cols)

    # Log & print detected column mappings
    log_display = format_column_mapping_display(display_map)
    logger.info("\n" + log_display)

    mapped_df = df.copy()

    # Extract or synthesize standardized fields
    first_name_col = schema_map.get("first_name")
    last_name_col = schema_map.get("last_name")
    full_name_col = schema_map.get("full_name")

    # 1. first_name
    if first_name_col and first_name_col in mapped_df.columns:
        mapped_df["first_name"] = mapped_df[first_name_col].astype(str).str.strip()
    else:
        mapped_df["first_name"] = ""

    # 2. last_name
    if last_name_col and last_name_col in mapped_df.columns:
        mapped_df["last_name"] = mapped_df[last_name_col].astype(str).str.strip()
    else:
        mapped_df["last_name"] = ""

    # 3. full_name
    if full_name_col and full_name_col in mapped_df.columns:
        mapped_df["full_name"] = mapped_df[full_name_col].astype(str).str.strip()
        # If first/last are missing, attempt split
        mask_missing = (mapped_df["first_name"] == "") & (mapped_df["full_name"] != "")
        if mask_missing.any():
            split_names = mapped_df.loc[mask_missing, "full_name"].str.split(" ", n=1, expand=True)
            mapped_df.loc[mask_missing, "first_name"] = split_names[0].fillna("")
            if split_names.shape[1] > 1:
                mapped_df.loc[mask_missing, "last_name"] = split_names[1].fillna("")
    else:
        # Synthesize from first and last
        mapped_df["full_name"] = (mapped_df["first_name"] + " " + mapped_df["last_name"]).str.strip()

    # 4. linkedin_url
    url_col = schema_map.get("linkedin_url")
    mapped_df["linkedin_url"] = mapped_df[url_col].astype(str).str.strip() if url_col else ""

    # 5. email
    email_col = schema_map.get("email")
    mapped_df["email"] = mapped_df[email_col].astype(str).str.strip() if email_col else ""

    # 6. company
    company_col = schema_map.get("company")
    mapped_df["company"] = mapped_df[company_col].astype(str).str.strip() if company_col else ""

    # 7. position
    pos_col = schema_map.get("position")
    mapped_df["position"] = mapped_df[pos_col].astype(str).str.strip() if pos_col else ""

    # 8. connected_on
    conn_col = schema_map.get("connected_on")
    mapped_df["connected_on"] = mapped_df[conn_col].astype(str).str.strip() if conn_col else ""

    # 9. location (optional)
    loc_col = schema_map.get("location")
    if loc_col and loc_col in mapped_df.columns:
        mapped_df["location"] = mapped_df[loc_col].astype(str).str.strip()
    else:
        mapped_df["location"] = ""

    return mapped_df, display_map
