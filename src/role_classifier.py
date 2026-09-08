"""Sophisticated role classifier for professional job titles."""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Set, Tuple


def normalize_title(title: str) -> str:
    """Normalize job title for regex analysis.
    
    - Converts to lowercase
    - Normalizes ampersands '&' -> ' and '
    - Replaces punctuation, hyphens, and slashes with spaces
    - Collapses consecutive whitespace
    
    Args:
        title: Raw title string.
        
    Returns:
        Normalized title string.
    """
    if not title:
        return ""
    text = str(title).lower()
    # Replace & with ' and '
    text = re.sub(r"&", " and ", text)
    # Normalize hyphens inside words like co-founder -> cofounder or co founder
    text = re.sub(r"\bco[-_]founder", "cofounder", text)
    text = re.sub(r"\bnon[-_]executive", "non executive", text)
    # Replace separators/punctuation with space
    text = re.sub(r"[/\\|,;:•\-+]+", " ", text)
    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text).strip()
    return text


# Role match definitions with word boundaries
# Ordered patterns mapping to normalized role label
PATTERNS = [
    # FOUNDERS
    (
        "Founder",
        re.compile(r"\b(co[\s-]?founder|cofounder|founder|founding partner|founding director|founding member)\b", re.IGNORECASE)
    ),
    # C-SUITE
    (
        "CEO",
        re.compile(r"\b(ceo|chief executive officer)\b", re.IGNORECASE)
    ),
    (
        "CTO",
        re.compile(r"\b(cto|chief technology officer|chief technical officer)\b", re.IGNORECASE)
    ),
    (
        "CFO",
        re.compile(r"\b(cfo|chief financial officer|chief finance officer)\b", re.IGNORECASE)
    ),
    (
        "COO",
        re.compile(r"\b(coo|chief operating officer|chief operations officer)\b", re.IGNORECASE)
    ),
    (
        "CMO",
        re.compile(r"\b(cmo|chief marketing officer)\b", re.IGNORECASE)
    ),
    (
        "CIO",
        re.compile(r"\b(cio|chief information officer)\b", re.IGNORECASE)
    ),
    (
        "CPO",
        re.compile(r"\b(cpo|chief product officer|chief people officer)\b", re.IGNORECASE)
    ),
    (
        "CRO",
        re.compile(r"\b(cro|chief revenue officer)\b", re.IGNORECASE)
    ),
    (
        "CSO",
        re.compile(r"\b(cso|chief strategy officer|chief security officer)\b", re.IGNORECASE)
    ),
    (
        "C-Suite",
        re.compile(r"\b(chief [a-z]+ officer|cxo)\b", re.IGNORECASE)
    ),
    # DIRECTORS
    (
        "Managing Director",
        re.compile(r"\b(managing director|md)\b", re.IGNORECASE)
    ),
    (
        "Executive Director",
        re.compile(r"\bexecutive director\b", re.IGNORECASE)
    ),
    (
        "Director",
        re.compile(r"\b(non executive director|independent director|founding director|board director|director)\b", re.IGNORECASE)
    ),
    # SENIOR LEADERSHIP
    (
        "President",
        re.compile(r"\b(?<!vice\s)(?<!vice-)(president|co president)\b", re.IGNORECASE)
    ),
    (
        "SVP",
        re.compile(r"\b(svp|senior vice president|executive vice president|evp)\b", re.IGNORECASE)
    ),
    (
        "VP",
        re.compile(r"\b(?<!senior\s)(?<!executive\s)(vp|vice president|vice-president)\b", re.IGNORECASE)
    ),
    (
        "Head",
        re.compile(r"\b(head of|head)\b", re.IGNORECASE)
    ),
    (
        "Partner",
        re.compile(r"\b(general partner|managing partner|venture partner|equity partner|partner)\b", re.IGNORECASE)
    ),
    (
        "General Manager",
        re.compile(r"\b(general manager|gm)\b", re.IGNORECASE)
    ),
    # ENTREPRENEUR
    (
        "Entrepreneur",
        re.compile(r"\b(entrepreneur|business owner|owner|proprietor|solopreneur)\b", re.IGNORECASE)
    ),
]

# Order of precedence when assigning primary_category
PRIMARY_PRECEDENCE = [
    "Founder",
    "CEO",
    "CTO",
    "CFO",
    "COO",
    "CMO",
    "CIO",
    "CPO",
    "CRO",
    "CSO",
    "C-Suite",
    "Managing Director",
    "Executive Director",
    "Director",
    "President",
    "SVP",
    "VP",
    "Head",
    "Partner",
    "General Manager",
    "Entrepreneur",
]


def classify_role(title: str) -> Tuple[str, List[str]]:
    """Classify a professional job title into primary and secondary categories.
    
    Args:
        title: Raw or normalized job title.
        
    Returns:
        Tuple of (primary_category, list_of_secondary_categories).
        If no senior category matched, returns ("Other", []).
    """
    if not title:
        return "Other", []

    normalized = normalize_title(title)
    if not normalized:
        return "Other", []

    detected_roles: List[str] = []
    seen: Set[str] = set()

    for role_name, pattern in PATTERNS:
        if pattern.search(normalized):
            # Consolidate Managing/Executive Director to Director if needed, or keep specific
            mapped_role = role_name
            if mapped_role in ("Managing Director", "Executive Director"):
                # Track Director category
                mapped_role = "Director"

            if mapped_role not in seen:
                seen.add(mapped_role)
                detected_roles.append(mapped_role)

    if not detected_roles:
        return "Other", []

    # Determine primary category by precedence
    primary = "Other"
    for cand in PRIMARY_PRECEDENCE:
        canonical_cand = "Director" if cand in ("Managing Director", "Executive Director") else cand
        if canonical_cand in seen:
            primary = canonical_cand
            break

    # If no candidate matched precedence order (fallback)
    if primary == "Other" and detected_roles:
        primary = detected_roles[0]

    # Secondary categories are all other detected roles
    secondary = [r for r in detected_roles if r != primary]

    return primary, secondary


def matches_role_filter(
    filter_role: str,
    primary_category: str,
    secondary_categories: List[str],
    lead_type: str
) -> bool:
    """Check whether a contact matches a given CLI role filter.
    
    Supported filters (case-insensitive):
    - 'founder': matches if Founder in primary/secondary/lead_type
    - 'cto': matches if CTO in primary/secondary
    - 'ceo': matches if CEO in primary/secondary
    - 'director': matches if Director in primary/secondary/lead_type
    - 'entrepreneur': matches if Entrepreneur in primary/secondary/lead_type
    - 'c-suite': matches if lead_type == 'C-Suite' or any C-level role
    - 'senior': matches any senior contact (lead_type != 'Other')
    """
    filt = filter_role.strip().lower()
    all_categories = {primary_category.lower()} | {s.lower() for s in secondary_categories}
    lead_type_lower = lead_type.lower()

    if filt == "founder":
        return "founder" in all_categories or lead_type_lower == "founder"
    elif filt == "cto":
        return "cto" in all_categories
    elif filt == "ceo":
        return "ceo" in all_categories
    elif filt == "director":
        return "director" in all_categories or lead_type_lower == "director"
    elif filt == "entrepreneur":
        return "entrepreneur" in all_categories or lead_type_lower == "entrepreneur"
    elif filt in ("c-suite", "csuite", "cxo"):
        c_suite_roles = {"ceo", "cto", "cfo", "coo", "cmo", "cio", "cpo", "cro", "cso", "c-suite"}
        return lead_type_lower == "c-suite" or bool(all_categories & c_suite_roles)
    elif filt in ("senior", "senior-leadership", "leadership"):
        return lead_type_lower != "other"
    else:
        # Generic match across primary, secondary, or lead_type
        return filt in all_categories or filt == lead_type_lower
