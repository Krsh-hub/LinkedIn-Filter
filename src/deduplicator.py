"""Intelligent contact deduplication module."""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Set, Tuple
import pandas as pd

from src.utils import clean_text, normalize_linkedin_url, compute_data_quality_score

logger = logging.getLogger("linkedin_analyzer")


def normalize_name_and_company(name: str, company: str) -> str:
    """Create a canonical composite key from full name and company name."""
    clean_name = re.sub(r"[^\w\s]", "", clean_text(name).lower())
    clean_name = re.sub(r"\s+", " ", clean_name).strip()

    clean_comp = re.sub(r"[^\w\s]", "", clean_text(company).lower())
    clean_comp = re.sub(r"\s+", " ", clean_comp).strip()

    if not clean_name or not clean_comp:
        return ""

    return f"{clean_name}@@@{clean_comp}"


def merge_contact_records(primary: dict, secondary: dict) -> dict:
    """Merge two contact records, filling empty fields in primary with values from secondary."""
    merged = dict(primary)
    for k, v in secondary.items():
        if not clean_text(merged.get(k, "")) and clean_text(v):
            merged[k] = v

    # Recompute data quality score and pick highest seniority score
    merged["data_quality_score"] = compute_data_quality_score(merged)
    try:
        s1 = int(primary.get("seniority_score", 0))
        s2 = int(secondary.get("seniority_score", 0))
        merged["seniority_score"] = max(s1, s2)
    except (ValueError, TypeError):
        pass

    return merged


def deduplicate_contacts(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    """Deduplicate contact records using strict priority order.
    
    Priority order:
    1. Normalized LinkedIn URL (if present and non-empty)
    2. Email address (if present and non-empty)
    3. Full Name + Company (only if BOTH full name and company are non-empty)
    
    Ensures that two distinct individuals with the same name at different companies
    are NEVER merged.
    
    Args:
        df: DataFrame containing mapped contacts.
        
    Returns:
        Tuple of (deduplicated DataFrame, number of duplicates removed).
    """
    if df.empty:
        return df, 0

    records = df.to_dict(orient="records")
    initial_count = len(records)

    # Ensure data_quality_score is computed for each record first
    for rec in records:
        if "data_quality_score" not in rec or rec["data_quality_score"] == "":
            rec["data_quality_score"] = compute_data_quality_score(rec)

    # We will cluster records into connected groups using disjoint sets / graph
    parent: List[int] = list(range(initial_count))

    def find(i: int) -> int:
        if parent[i] == i:
            return i
        parent[i] = find(parent[i])
        return parent[i]

    def union(i: int, j: int) -> None:
        root_i = find(i)
        root_j = find(j)
        if root_i != root_j:
            # Union by data quality score: point lower score to higher score
            q_i = int(records[root_i].get("data_quality_score", 0))
            q_j = int(records[root_j].get("data_quality_score", 0))
            if q_i >= q_j:
                parent[root_j] = root_i
            else:
                parent[root_i] = root_j

    # Index maps for matching
    url_map: Dict[str, int] = {}
    email_map: Dict[str, int] = {}
    name_comp_map: Dict[str, int] = {}

    # Priority 1: LinkedIn URL
    for idx, rec in enumerate(records):
        raw_url = rec.get("linkedin_url", "")
        norm_url = normalize_linkedin_url(raw_url)
        if norm_url:
            if norm_url in url_map:
                union(idx, url_map[norm_url])
            else:
                url_map[norm_url] = idx

    # Priority 2: Email
    for idx, rec in enumerate(records):
        email = clean_text(rec.get("email", "")).lower()
        if email and "@" in email:
            if email in email_map:
                union(idx, email_map[email])
            else:
                email_map[email] = idx

    # Priority 3: Full Name + Company (strict: both must be non-empty)
    for idx, rec in enumerate(records):
        name = rec.get("full_name", "")
        comp = rec.get("company", "")
        name_comp_key = normalize_name_and_company(name, comp)
        if name_comp_key:
            if name_comp_key in name_comp_map:
                union(idx, name_comp_map[name_comp_key])
            else:
                name_comp_map[name_comp_key] = idx

    # Group records by root parent
    clusters: Dict[int, List[dict]] = {}
    for idx, rec in enumerate(records):
        root = find(idx)
        if root not in clusters:
            clusters[root] = []
        clusters[root].append(rec)

    # Merge records within each cluster
    merged_records: List[dict] = []
    for root, cluster_recs in clusters.items():
        if len(cluster_recs) == 1:
            merged_records.append(cluster_recs[0])
        else:
            # Sort by data quality score descending, then seniority score descending
            cluster_recs.sort(
                key=lambda r: (
                    int(r.get("data_quality_score", 0)),
                    int(r.get("seniority_score", 0))
                ),
                reverse=True
            )
            # Primary is highest quality record
            acc = cluster_recs[0]
            for sec in cluster_recs[1:]:
                acc = merge_contact_records(acc, sec)
            merged_records.append(acc)

    deduped_df = pd.DataFrame(merged_records)
    removed_count = initial_count - len(deduped_df)

    logger.info(f"Deduplication completed: {initial_count} initial records -> {len(deduped_df)} unique records ({removed_count} duplicates removed).")

    return deduped_df, removed_count
