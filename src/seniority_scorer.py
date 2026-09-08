"""Seniority scoring, seniority level mapping, and lead type assignment."""

from __future__ import annotations

import re
from typing import Dict, List, Tuple
from src.role_classifier import normalize_title

# Role to score mapping based on prompt specification
SCORE_RULES: List[Tuple[re.Pattern, int, str]] = [
    # Pattern, Score, Canonical Key
    (re.compile(r"\b(co[\s-]?founder|cofounder|founder|founding partner|founding director|founding member)\b", re.IGNORECASE), 100, "Founder"),
    (re.compile(r"\b(ceo|chief executive officer)\b", re.IGNORECASE), 98, "CEO"),
    (re.compile(r"\b(cto|chief technology officer|chief technical officer)\b", re.IGNORECASE), 98, "CTO"),
    (re.compile(r"\b(cfo|chief financial officer|chief finance officer)\b", re.IGNORECASE), 95, "CFO"),
    (re.compile(r"\b(coo|chief operating officer|chief operations officer)\b", re.IGNORECASE), 95, "COO"),
    (re.compile(r"\b(cmo|chief marketing officer)\b", re.IGNORECASE), 93, "CMO"),
    (re.compile(r"\b(cio|chief information officer)\b", re.IGNORECASE), 93, "CIO"),
    (re.compile(r"\b(cpo|chief product officer|chief people officer)\b", re.IGNORECASE), 92, "CPO"),
    (re.compile(r"\b(cro|chief revenue officer|cso|chief strategy officer|chief security officer)\b", re.IGNORECASE), 92, "C-Suite"),
    (re.compile(r"\b(chief [a-z]+ officer|cxo)\b", re.IGNORECASE), 92, "C-Suite"),
    (re.compile(r"\b(managing director|md)\b", re.IGNORECASE), 92, "Managing Director"),
    (re.compile(r"\bexecutive director\b", re.IGNORECASE), 90, "Executive Director"),
    (re.compile(r"\b(?<!vice\s)(?<!vice-)(president|co president)\b", re.IGNORECASE), 85, "President"),
    (re.compile(r"\b(partner|general partner|managing partner|venture partner)\b", re.IGNORECASE), 85, "Partner"),
    (re.compile(r"\b(non executive director|independent director|founding director|board director|director)\b", re.IGNORECASE), 85, "Director"),
    (re.compile(r"\b(svp|senior vice president|executive vice president|evp)\b", re.IGNORECASE), 82, "SVP"),
    (re.compile(r"\b(?<!senior\s)(?<!executive\s)(vp|vice president|vice-president)\b", re.IGNORECASE), 80, "VP"),
    (re.compile(r"\b(head of|head)\b", re.IGNORECASE), 75, "Head"),
    (re.compile(r"\b(general manager|gm)\b", re.IGNORECASE), 75, "General Manager"),
    (re.compile(r"\b(entrepreneur|business owner|owner|proprietor|solopreneur)\b", re.IGNORECASE), 70, "Entrepreneur"),
]


def calculate_seniority_score(title: str) -> int:
    """Calculate seniority score from 0 to 100 based on job title.
    
    If multiple senior roles exist in the title, assigns the highest relevant score.
    
    Examples:
        "Founder & CEO" -> 100
        "Co-Founder & CTO" -> 100
        "CTO" -> 98
        "Managing Director" -> 92
        "Director" -> 85
        "Senior Vice President" -> 82
        "VP of Sales" -> 80
        "Head of Engineering" -> 75
        "Entrepreneur" -> 70
        "Intern" -> 0
        
    Args:
        title: Job title string.
        
    Returns:
        Integer score between 0 and 100.
    """
    if not title:
        return 0

    norm = normalize_title(title)
    if not norm:
        return 0

    matched_scores = [score for pattern, score, _ in SCORE_RULES if pattern.search(norm)]
    if not matched_scores:
        return 0

    return max(matched_scores)


def assign_seniority_level(primary_category: str, title: str, score: int) -> str:
    """Assign seniority level.
    
    Possible values:
        - Founder
        - C-Suite
        - Executive
        - Senior Leadership
        - Entrepreneur
        - Other
        
    Args:
        primary_category: Primary classified category.
        title: Raw title string.
        score: Calculated seniority score.
        
    Returns:
        One of the six standardized seniority levels.
    """
    if score == 0 or primary_category == "Other":
        return "Other"

    if primary_category == "Founder":
        return "Founder"

    c_suite_set = {"CEO", "CTO", "CFO", "COO", "CMO", "CIO", "CPO", "CRO", "CSO", "C-Suite"}
    if primary_category in c_suite_set:
        return "C-Suite"

    norm = normalize_title(title)
    if primary_category == "Director" or "managing director" in norm or "executive director" in norm or primary_category in ("Partner", "President"):
        return "Executive"

    if primary_category in ("VP", "SVP", "Head", "General Manager"):
        return "Senior Leadership"

    if primary_category == "Entrepreneur":
        return "Entrepreneur"

    return "Other"


def assign_lead_type(primary_category: str, seniority_score: int) -> str:
    """Assign lead type primarily based on role classification.
    
    Possible values:
        - Founder
        - C-Suite
        - Director
        - Senior Leadership
        - Entrepreneur
        - Other
        
    Args:
        primary_category: Primary classified category.
        seniority_score: Computed score.
        
    Returns:
        One of the six standardized lead types.
    """
    if seniority_score == 0 or primary_category == "Other":
        return "Other"

    if primary_category == "Founder":
        return "Founder"

    c_suite_set = {"CEO", "CTO", "CFO", "COO", "CMO", "CIO", "CPO", "CRO", "CSO", "C-Suite"}
    if primary_category in c_suite_set:
        return "C-Suite"

    if primary_category == "Director":
        return "Director"

    if primary_category in ("President", "Partner", "VP", "SVP", "Head", "General Manager"):
        return "Senior Leadership"

    if primary_category == "Entrepreneur":
        return "Entrepreneur"

    return "Other"
