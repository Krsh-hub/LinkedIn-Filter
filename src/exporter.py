"""Data exporter for generating formatted CSVs and multi-tab Excel workbooks."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
import pandas as pd

from src.utils import clean_text

logger = logging.getLogger("linkedin_analyzer")

PRIMARY_COLUMN_ORDER = [
    "full_name",
    "first_name",
    "last_name",
    "company",
    "position",
    "primary_category",
    "secondary_categories",
    "lead_type",
    "seniority_level",
    "seniority_score",
    "linkedin_url",
    "email",
    "connected_on",
    "data_quality_score",
]


def format_dataframe_for_export(df: pd.DataFrame) -> pd.DataFrame:
    """Format columns and serialize lists for CSV and Excel output."""
    if df.empty:
        return df

    export_df = df.copy()

    # Format secondary_categories as comma-separated string
    if "secondary_categories" in export_df.columns:
        export_df["secondary_categories"] = export_df["secondary_categories"].apply(
            lambda x: ", ".join(x) if isinstance(x, (list, set, tuple)) else clean_text(x)
        )

    # Order columns with primary keys first, then any extra/original columns
    ordered_cols: List[str] = [col for col in PRIMARY_COLUMN_ORDER if col in export_df.columns]
    extra_cols: List[str] = [col for col in export_df.columns if col not in PRIMARY_COLUMN_ORDER]
    export_df = export_df[ordered_cols + extra_cols]

    return export_df


def export_csv(df: pd.DataFrame, output_path: str | Path) -> Path:
    """Export DataFrame to a UTF-8 CSV file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    clean_df = format_dataframe_for_export(df)
    clean_df.to_csv(path, index=False, encoding="utf-8-sig")
    logger.info(f"Exported {len(clean_df)} records to CSV: {path}")
    return path


def style_worksheet(ws: Any) -> None:
    """Apply professional styling to an openpyxl worksheet.
    
    - Navy header fill with white bold text
    - Subtle zebra striping
    - Light gray borders
    - Freeze header row
    - Enable auto-filter
    - Auto-adjust column widths
    """
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    alt_fill = PatternFill(start_color="F9FAFB", end_color="F9FAFB", fill_type="solid")
    white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    
    thin_border = Border(
        left=Side(style="thin", color="E2E8F0"),
        right=Side(style="thin", color="E2E8F0"),
        top=Side(style="thin", color="E2E8F0"),
        bottom=Side(style="thin", color="E2E8F0"),
    )

    center_align = Alignment(horizontal="center", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")

    max_row = ws.max_row
    max_col = ws.max_column

    if max_row < 1 or max_col < 1:
        return

    # Style Header
    ws.row_dimensions[1].height = 28
    for col in range(1, max_col + 1):
        cell = ws.cell(row=1, column=col)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center_align
        cell.border = thin_border

    # Style Data rows
    for row in range(2, max_row + 1):
        ws.row_dimensions[row].height = 20
        fill = alt_fill if row % 2 == 0 else white_fill
        for col in range(1, max_col + 1):
            cell = ws.cell(row=row, column=col)
            cell.fill = fill
            cell.border = thin_border
            cell.font = Font(name="Calibri", size=10)

            # Center align scores and quality numbers
            col_name = str(ws.cell(row=1, column=col).value).lower()
            if "score" in col_name or "date" in col_name or "connected" in col_name:
                cell.alignment = center_align
            else:
                cell.alignment = left_align

    # Freeze header
    ws.freeze_panes = "A2"

    # Enable auto filter
    ws.auto_filter.ref = ws.dimensions

    # Auto-fit column widths
    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = 0
        for cell in col:
            val_str = str(cell.value or "")
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)


def create_summary_sheet(
    wb: openpyxl.Workbook,
    total_connections: int,
    senior_df: pd.DataFrame,
    founders_df: pd.DataFrame,
    c_suite_df: pd.DataFrame,
    directors_df: pd.DataFrame,
    entrepreneurs_df: pd.DataFrame
) -> None:
    """Create a professionally formatted Executive Summary KPI tab."""
    ws = wb.create_sheet(title="Summary", index=0)
    ws.views.sheetView[0].showGridLines = True

    # Title Banner
    ws.merge_cells("A1:C1")
    title_cell = ws["A1"]
    title_cell.value = "LinkedIn Network Analysis - Executive Summary"
    title_cell.font = Font(name="Calibri", size=16, bold=True, color="1F4E79")
    ws.row_dimensions[1].height = 36

    # Header row for KPI Table
    headers = ["Metric", "Count / Value", "Description"]
    ws.row_dimensions[3].height = 26
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")

    for col_idx, text in enumerate(headers, start=1):
        c = ws.cell(row=3, column=col_idx, value=text)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal="center", vertical="center")

    # Metrics calculation
    senior_count = len(senior_df)
    avg_score = round(senior_df["seniority_score"].astype(float).mean(), 1) if not senior_df.empty else 0
    with_email = len(senior_df[senior_df["email"].str.contains("@", na=False)]) if not senior_df.empty else 0
    with_url = len(senior_df[senior_df["linkedin_url"].str.len() > 0]) if not senior_df.empty else 0

    kpis = [
        ("Total connections", total_connections, "Total processed contacts in your export"),
        ("Senior contacts", senior_count, "Contacts classified with leadership seniority"),
        ("Founders", len(founders_df), "Founders, Co-Founders, and Founding Partners"),
        ("C-Suite", len(c_suite_df), "CEOs, CTOs, CFOs, COOs, and Chief Executives"),
        ("Directors", len(directors_df), "Managing, Executive, and Board Directors"),
        ("Entrepreneurs", len(entrepreneurs_df), "Entrepreneurs and Business Owners"),
        ("Average seniority score", avg_score, "Mean score across all senior contacts (0-100)"),
        ("Contacts with email", with_email, "Senior contacts with a verified email address"),
        ("Contacts with LinkedIn URL", with_url, "Senior contacts with a profile URL link"),
    ]

    border = Border(
        left=Side(style="thin", color="E2E8F0"),
        right=Side(style="thin", color="E2E8F0"),
        top=Side(style="thin", color="E2E8F0"),
        bottom=Side(style="thin", color="E2E8F0")
    )
    alt_fill = PatternFill(start_color="F9FAFB", end_color="F9FAFB", fill_type="solid")

    for idx, (label, val, desc) in enumerate(kpis, start=4):
        ws.row_dimensions[idx].height = 22
        fill = alt_fill if idx % 2 == 0 else PatternFill(fill_type=None)

        c1 = ws.cell(row=idx, column=1, value=label)
        c2 = ws.cell(row=idx, column=2, value=val)
        c3 = ws.cell(row=idx, column=3, value=desc)

        for c in (c1, c2, c3):
            c.border = border
            c.font = Font(name="Calibri", size=10)
            c.fill = fill

        c1.font = Font(name="Calibri", size=10, bold=True)
        c2.alignment = Alignment(horizontal="center", vertical="center")
        c2.font = Font(name="Calibri", size=10, bold=True, color="1F4E79")

    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 50


def export_excel(
    all_senior_df: pd.DataFrame,
    founders_df: pd.DataFrame,
    c_suite_df: pd.DataFrame,
    directors_df: pd.DataFrame,
    entrepreneurs_df: pd.DataFrame,
    total_connections: int,
    output_path: str | Path
) -> Path:
    """Generate a multi-tab, professionally styled Excel workbook.
    
    Sheets:
    - Summary
    - All Senior
    - Founders
    - C-Suite
    - Directors
    - Entrepreneurs
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)

    # Helper to populate and format a data tab
    def add_data_tab(title: str, df: pd.DataFrame) -> None:
        clean_df = format_dataframe_for_export(df)
        ws = wb.create_sheet(title=title)
        ws.views.sheetView[0].showGridLines = True

        if clean_df.empty:
            ws.cell(row=1, column=1, value="No records found.")
            return

        # Write header
        for col_idx, col_name in enumerate(clean_df.columns, start=1):
            ws.cell(row=1, column=col_idx, value=col_name)

        # Write rows
        for row_idx, row_vals in enumerate(clean_df.itertuples(index=False), start=2):
            for col_idx, val in enumerate(row_vals, start=1):
                ws.cell(row=row_idx, column=col_idx, value=val)

        style_worksheet(ws)

    # Add data tabs
    add_data_tab("All Senior", all_senior_df)
    add_data_tab("Founders", founders_df)
    add_data_tab("C-Suite", c_suite_df)
    add_data_tab("Directors", directors_df)
    add_data_tab("Entrepreneurs", entrepreneurs_df)

    # Add Summary Sheet
    create_summary_sheet(
        wb,
        total_connections=total_connections,
        senior_df=all_senior_df,
        founders_df=founders_df,
        c_suite_df=c_suite_df,
        directors_df=directors_df,
        entrepreneurs_df=entrepreneurs_df
    )

    wb.save(path)
    logger.info(f"Exported multi-tab Excel workbook to: {path}")
    return path
