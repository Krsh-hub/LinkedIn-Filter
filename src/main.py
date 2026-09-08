"""Main orchestrator and CLI entry point for LinkedIn Network Analyzer."""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import Optional
import pandas as pd

from src.column_mapper import map_and_normalize_dataframe
from src.csv_loader import load_csv
from src.deduplicator import deduplicate_contacts
from src.exporter import export_csv, export_excel
from src.role_classifier import classify_role, matches_role_filter
from src.seniority_scorer import assign_lead_type, assign_seniority_level, calculate_seniority_score
from src.utils import compute_data_quality_score, setup_logging


def parse_arguments(args: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="linkedin-network-analyzer",
        description="Local personal utility to analyze, classify, and export professional LinkedIn connections.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py --input input/Connections.csv
  python run.py --input input/Connections.csv --role founder
  python run.py --input input/Connections.csv --role cto
  python run.py --input input/Connections.csv --role c-suite
  python run.py --input input/Connections.csv --company "Google"
  python run.py --input input/Connections.csv --company-contains "tech"
  python run.py --input input/Connections.csv --search "AI"
  python run.py --input input/Connections.csv --location "India"
        """
    )

    parser.add_argument(
        "--input", "-i",
        default="input/Connections.csv",
        help="Path to the LinkedIn Connections CSV export file (default: input/Connections.csv)"
    )
    parser.add_argument(
        "--output-dir", "-o",
        default="output",
        help="Directory to save generated CSV and XLSX reports (default: output)"
    )
    parser.add_argument(
        "--role", "-r",
        choices=["founder", "cto", "ceo", "director", "entrepreneur", "c-suite", "senior"],
        help="Filter output by specific leadership role"
    )
    parser.add_argument(
        "--company", "-c",
        help="Filter output by exact company name (case-insensitive)"
    )
    parser.add_argument(
        "--company-contains",
        help="Filter output by company name substring (case-insensitive)"
    )
    parser.add_argument(
        "--search", "-s",
        help="Search query across name, company, and position"
    )
    parser.add_argument(
        "--location", "-l",
        help="Filter by location if location column is present"
    )
    parser.add_argument(
        "--export",
        choices=["founders", "c_suite", "directors", "entrepreneurs", "senior", "all"],
        help="Export target subset (default: exports all standard files)"
    )
    parser.add_argument(
        "--log-dir",
        default="logs",
        help="Directory for application log files (default: logs)"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)"
    )

    return parser.parse_args(args)


def process_connections(
    input_path: str | Path,
    output_dir: str | Path = "output",
    log_dir: str | Path = "logs",
    log_level: str = "INFO",
    role_filter: Optional[str] = None,
    company_filter: Optional[str] = None,
    company_contains: Optional[str] = None,
    search_query: Optional[str] = None,
    location_filter: Optional[str] = None,
    export_filter: Optional[str] = None,
) -> int:
    """Execute the LinkedIn Network Analyzer pipeline.
    
    Returns:
        0 on success, non-zero exit code on error.
    """
    logger = setup_logging(log_dir=log_dir, log_level=log_level)
    input_file = Path(input_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info(f"Starting LinkedIn Network Analyzer for: {input_file.resolve()}")

    # 1. Load CSV
    try:
        raw_df = load_csv(input_file)
    except FileNotFoundError as e:
        print(f"\n[ERROR] {e}", file=sys.stderr)
        print(f"Please ensure your LinkedIn export file exists at: {input_file}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"\n[ERROR] {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n[FATAL ERROR] Unexpected error loading CSV: {e}", file=sys.stderr)
        logger.exception("Unexpected error during CSV loading")
        return 1

    total_connections_raw = len(raw_df)

    # 2. Intelligent Column Mapping
    mapped_df, display_map = map_and_normalize_dataframe(raw_df)

    # 3. Role Classification & Seniority Scoring
    primary_categories: list[str] = []
    secondary_categories_list: list[list[str]] = []
    seniority_scores: list[int] = []
    seniority_levels: list[str] = []
    lead_types: list[str] = []
    quality_scores: list[int] = []

    for _, row in mapped_df.iterrows():
        pos = str(row.get("position", "")).strip()
        prim, sec = classify_role(pos)
        score = calculate_seniority_score(pos)
        level = assign_seniority_level(prim, pos, score)
        l_type = assign_lead_type(prim, score)
        q_score = compute_data_quality_score(row)

        primary_categories.append(prim)
        secondary_categories_list.append(sec)
        seniority_scores.append(score)
        seniority_levels.append(level)
        lead_types.append(l_type)
        quality_scores.append(q_score)

    mapped_df["primary_category"] = primary_categories
    mapped_df["secondary_categories"] = secondary_categories_list
    mapped_df["seniority_score"] = seniority_scores
    mapped_df["seniority_level"] = seniority_levels
    mapped_df["lead_type"] = lead_types
    mapped_df["data_quality_score"] = quality_scores

    # 4. Intelligent Deduplication
    deduped_df, duplicates_removed = deduplicate_contacts(mapped_df)
    total_unique_connections = len(deduped_df)

    # 5. Segment Categorization (Unfiltered)
    all_senior_df = deduped_df[
        (deduped_df["seniority_score"] > 0) & (deduped_df["lead_type"] != "Other")
    ].copy()

    founders_df = deduped_df[
        (deduped_df["lead_type"] == "Founder") | (deduped_df["primary_category"] == "Founder")
    ].copy()

    c_suite_df = deduped_df[deduped_df["lead_type"] == "C-Suite"].copy()
    directors_df = deduped_df[deduped_df["lead_type"] == "Director"].copy()
    entrepreneurs_df = deduped_df[deduped_df["lead_type"] == "Entrepreneur"].copy()
    senior_leadership_df = deduped_df[deduped_df["lead_type"] == "Senior Leadership"].copy()

    # 6. Apply Active Filters (if specified by CLI)
    filtered_df = all_senior_df.copy()
    is_filtered = False

    if role_filter:
        is_filtered = True
        mask = filtered_df.apply(
            lambda r: matches_role_filter(
                role_filter,
                r.get("primary_category", ""),
                r.get("secondary_categories", []),
                r.get("lead_type", "")
            ),
            axis=1
        )
        filtered_df = filtered_df[mask]
        logger.info(f"Applied role filter '{role_filter}': {len(filtered_df)} matches remaining.")

    if company_filter:
        is_filtered = True
        clean_target = company_filter.strip().lower()
        mask = filtered_df["company"].str.lower() == clean_target
        filtered_df = filtered_df[mask]
        logger.info(f"Applied company filter '{company_filter}': {len(filtered_df)} matches remaining.")

    if company_contains:
        is_filtered = True
        mask = filtered_df["company"].str.contains(re.escape(company_contains.strip()), case=False, na=False)
        filtered_df = filtered_df[mask]
        logger.info(f"Applied company-contains filter '{company_contains}': {len(filtered_df)} matches remaining.")

    if search_query:
        is_filtered = True
        q = re.escape(search_query.strip())
        mask = (
            filtered_df["full_name"].str.contains(q, case=False, na=False) |
            filtered_df["company"].str.contains(q, case=False, na=False) |
            filtered_df["position"].str.contains(q, case=False, na=False)
        )
        filtered_df = filtered_df[mask]
        logger.info(f"Applied search query '{search_query}': {len(filtered_df)} matches remaining.")

    if location_filter:
        is_filtered = True
        if "location" in filtered_df.columns and filtered_df["location"].str.len().sum() > 0:
            mask = filtered_df["location"].str.contains(re.escape(location_filter.strip()), case=False, na=False)
            filtered_df = filtered_df[mask]
            logger.info(f"Applied location filter '{location_filter}': {len(filtered_df)} matches remaining.")
        else:
            logger.warning("Location filter requested, but no location information was found in the CSV.")

    # 7. File Exports
    senior_csv_path = out_dir / "senior_connections.csv"
    senior_xlsx_path = out_dir / "senior_connections.xlsx"
    founders_csv_path = out_dir / "founders.csv"
    c_suite_csv_path = out_dir / "c_suite.csv"
    directors_csv_path = out_dir / "directors.csv"
    entrepreneurs_csv_path = out_dir / "entrepreneurs.csv"

    # Export main CSVs
    export_csv(all_senior_df, senior_csv_path)
    export_csv(founders_df, founders_csv_path)
    export_csv(c_suite_df, c_suite_csv_path)
    export_csv(directors_df, directors_csv_path)
    export_csv(entrepreneurs_df, entrepreneurs_csv_path)

    # Export formatted Excel workbook
    export_excel(
        all_senior_df=all_senior_df,
        founders_df=founders_df,
        c_suite_df=c_suite_df,
        directors_df=directors_df,
        entrepreneurs_df=entrepreneurs_df,
        total_connections=total_unique_connections,
        output_path=senior_xlsx_path
    )

    # If active filter was applied, export dedicated filtered file as well
    filtered_csv_path: Optional[Path] = None
    if is_filtered:
        filtered_csv_path = out_dir / "filtered_connections.csv"
        export_csv(filtered_df, filtered_csv_path)

    # 8. Terminal Summary
    email_count = len(all_senior_df[all_senior_df["email"].str.contains("@", na=False)])
    url_count = len(all_senior_df[all_senior_df["linkedin_url"].str.len() > 0])

    print("\n" + "=" * 45)
    print("LinkedIn Network Analyzer\n")
    print(f"Input:\n{input_file.name}\n")
    print(f"Total connections: {total_unique_connections:,}\n")
    print(f"Senior contacts: {len(all_senior_df):,}\n")
    print("Breakdown:")
    print(f"Founders: {len(founders_df):,}")
    print(f"C-Suite: {len(c_suite_df):,}")
    print(f"Directors: {len(directors_df):,}")
    print(f"Entrepreneurs: {len(entrepreneurs_df):,}")
    print(f"Senior Leadership: {len(senior_leadership_df):,}\n")
    print("Data quality:")
    print(f"With email: {email_count:,}")
    print(f"With LinkedIn URL: {url_count:,}\n")
    print("Output:")
    print(f"{senior_csv_path}")
    print(f"{senior_xlsx_path}")
    if is_filtered and filtered_csv_path:
        print(f"Filtered results ({len(filtered_df)} matches): {filtered_csv_path}")
    print("=" * 45 + "\n")

    return 0


def main() -> None:
    """CLI script entrypoint."""
    args = parse_arguments()
    sys.exit(
        process_connections(
            input_path=args.input,
            output_dir=args.output_dir,
            log_dir=args.log_dir,
            log_level=args.log_level,
            role_filter=args.role,
            company_filter=args.company,
            company_contains=args.company_contains,
            search_query=args.search,
            location_filter=args.location,
            export_filter=args.export,
        )
    )


if __name__ == "__main__":
    main()
