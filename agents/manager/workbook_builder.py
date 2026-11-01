"""
Excel Workbook Builder
Produces a polished, professional Excel workbook (.xlsx) with:
- Summary sheet (executive overview, key metrics, decision summary)
- Cleaned data sheet (the final cleaned dataset)
- Analysis sheet (key metrics, charts, pattern findings)
- Audit trail sheet (transparent record of all corrections)
"""

import json
import csv
import pandas as pd
import os
import logging
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import (
    Font, PatternFill, Alignment, Border, Side, numbers
)
from openpyxl.chart import BarChart, PieChart, Reference
from openpyxl.utils import get_column_letter
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.formatting.rule import CellIsRule

logger = logging.getLogger("manager.workbook_builder")

MAX_DATA_ROWS = 1_000_000      # Excel hard limit is 1,048,576 rows
STYLED_ROW_LIMIT = 5_000       # per-cell styling is slow; style the first rows only
MAX_LOG_ROWS = 2_000


def _excel_value(v):
    """Make a value safe to put in an Excel cell without changing its meaning."""
    if v is None:
        return None
    if hasattr(v, "item") and callable(getattr(v, "item", None)):
        try:
            v = v.item()
        except (ValueError, TypeError):
            v = str(v)
    if isinstance(v, float) and (v != v or v in (float("inf"), float("-inf"))):
        return None
    if isinstance(v, str):
        return ILLEGAL_CHARACTERS_RE.sub("", v)
    if isinstance(v, (list, dict, tuple, set)):
        return ILLEGAL_CHARACTERS_RE.sub("", json.dumps(v, default=str))[:32000]
    return v


def _put(ws, row, col, value):
    """Write a cell. Text that begins with '=' is stored as text, never as a formula."""
    value = _excel_value(value)
    cell = ws.cell(row=row, column=col)
    if isinstance(value, str):
        cell.value = value[:32000]
        if value.startswith("="):
            cell.data_type = "s"
    else:
        cell.value = value
    return cell


# --- Style Constants ---
HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
HEADER_FILL = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
SUBHEADER_FONT = Font(name="Calibri", size=11, bold=True, color="1F4E79")
SUBHEADER_FILL = PatternFill(start_color="D6E4F0", end_color="D6E4F0", fill_type="solid")
TITLE_FONT = Font(name="Calibri", size=16, bold=True, color="1F4E79")
SECTION_FONT = Font(name="Calibri", size=12, bold=True, color="2E75B6")
BODY_FONT = Font(name="Calibri", size=10)
BOLD_FONT = Font(name="Calibri", size=10, bold=True)
THIN_BORDER = Border(
    left=Side(style="thin", color="B4C6E7"),
    right=Side(style="thin", color="B4C6E7"),
    top=Side(style="thin", color="B4C6E7"),
    bottom=Side(style="thin", color="B4C6E7"),
)
ALT_ROW_FILL = PatternFill(start_color="F2F7FB", end_color="F2F7FB", fill_type="solid")
GREEN_FILL = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
RED_FILL = PatternFill(start_color="FCE4EC", end_color="FCE4EC", fill_type="solid")
YELLOW_FILL = PatternFill(start_color="FFF9C4", end_color="FFF9C4", fill_type="solid")
FOOTER_FONT = Font(name="Calibri", size=8, italic=True, color="808080")


def _auto_width(ws, min_width=10, max_width=45, scan_rows=1000):
    """Auto-adjust column widths based on the first rows of content."""
    for col_cells in ws.iter_cols(max_row=min(ws.max_row, scan_rows)):
        max_len = 0
        col_letter = get_column_letter(col_cells[0].column)
        for cell in col_cells:
            if cell.value is not None:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = min(max(max_len + 2, min_width), max_width)


def _apply_header_style(ws, row, max_col):
    """Apply header styling to a row."""
    for col in range(1, max_col + 1):
        cell = ws.cell(row=row, column=col)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = THIN_BORDER


def _apply_body_style(ws, start_row, end_row, max_col):
    """Apply body styling to a range of rows."""
    for r in range(start_row, end_row + 1):
        for c in range(1, max_col + 1):
            cell = ws.cell(row=r, column=c)
            cell.font = BODY_FONT
            cell.border = THIN_BORDER
            cell.alignment = Alignment(vertical="center", wrap_text=True)
            if (r - start_row) % 2 == 1:
                cell.fill = ALT_ROW_FILL


def _add_title(ws, title, row=1):
    """Add a title to the sheet."""
    ws.cell(row=row, column=1, value=title).font = TITLE_FONT
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=8)
    return row + 1


def _add_subtitle(ws, subtitle, row=2):
    """Add a subtitle/date."""
    cell = ws.cell(row=row, column=1, value=subtitle)
    cell.font = Font(name="Calibri", size=10, italic=True, color="666666")
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=8)
    return row + 1


def _add_section_header(ws, title, row):
    """Add a section header."""
    cell = ws.cell(row=row, column=1, value=title)
    cell.font = SECTION_FONT
    cell.fill = SUBHEADER_FILL
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=8)
    cell.border = THIN_BORDER
    return row + 1


class WorkbookBuilder:
    """Builds the final professional Excel workbook."""

    def __init__(self, session_dir: str, memo: dict):
        self.session_dir = session_dir
        self.memo = memo
        self.wb = Workbook()

    def build(self, output_path: str):
        """Build and save the complete workbook."""
        self._build_summary_sheet()
        self._build_cleaned_data_sheet()
        self._build_analysis_sheet()
        self._build_audit_trail_sheet()
        self.wb.save(output_path)
        logger.info(f"Workbook saved to {output_path}")
        return output_path

    def _build_summary_sheet(self):
        """Sheet 1: Executive Summary with key metrics and decision overview."""
        ws = self.wb.active
        ws.title = "Summary"
        ws.sheet_properties.tabColor = "1F4E79"

        row = 1
        row = _add_title(ws, "Verity Analytics — Executive Summary", row)
        row = _add_subtitle(ws, f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", row)
        row += 1

        # Data Overview
        row = _add_section_header(ws, "Data Overview", row)
        row += 1
        profile = self.memo.get("data_profile", {})
        overview_items = [
            ("Source", profile.get("source", profile.get("file_name", "N/A"))),
            ("Rows", str(profile.get("row_count", profile.get("rows", "N/A")))),
            ("Columns", str(profile.get("column_count", profile.get("columns", "N/A")))),
            ("Missing Values", str(profile.get("missing_count", profile.get("missing_values", "N/A")))),
        ]
        ws.cell(row=row, column=1, value="Metric").font = BOLD_FONT
        ws.cell(row=row, column=2, value="Value").font = BOLD_FONT
        ws.cell(row=row, column=1).fill = SUBHEADER_FILL
        ws.cell(row=row, column=2).fill = SUBHEADER_FILL
        ws.cell(row=row, column=1).border = THIN_BORDER
        ws.cell(row=row, column=2).border = THIN_BORDER
        row += 1
        for metric, val in overview_items:
            ws.cell(row=row, column=1, value=metric).font = BODY_FONT
            ws.cell(row=row, column=2, value=val).font = BODY_FONT
            ws.cell(row=row, column=1).border = THIN_BORDER
            ws.cell(row=row, column=2).border = THIN_BORDER
            row += 1

        row += 1

        # Conflict Resolution Summary
        row = _add_section_header(ws, "Conflict Resolution Summary", row)
        row += 1
        conflict_data = self.memo.get("conflict_resolution", {}).get("summary", {})
        conflict_items = [
            ("Total Findings", str(conflict_data.get("total_findings", 0))),
            ("Confirmed (Both)", str(conflict_data.get("confirmed", 0))),
            ("Auditor Corrections", str(conflict_data.get("auditor_only", 0))),
            ("Analyst Insights", str(conflict_data.get("analyst_only", 0))),
            ("Total Resolutions", str(conflict_data.get("resolutions_count", 0))),
        ]
        ws.cell(row=row, column=1, value="Category").font = BOLD_FONT
        ws.cell(row=row, column=2, value="Count").font = BOLD_FONT
        ws.cell(row=row, column=1).fill = SUBHEADER_FILL
        ws.cell(row=row, column=2).fill = SUBHEADER_FILL
        ws.cell(row=row, column=1).border = THIN_BORDER
        ws.cell(row=row, column=2).border = THIN_BORDER
        row += 1
        for cat, val in conflict_items:
            ws.cell(row=row, column=1, value=cat).font = BODY_FONT
            ws.cell(row=row, column=2, value=val).font = BODY_FONT
            ws.cell(row=row, column=1).border = THIN_BORDER
            ws.cell(row=row, column=2).border = THIN_BORDER
            row += 1

        row += 1

        # Executive Summary
        row = _add_section_header(ws, "Executive Summary", row)
        row += 1
        exec_summary = self.memo.get("executive_summary", "No summary available.")
        cell = ws.cell(row=row, column=1, value=exec_summary)
        cell.font = BODY_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=row, start_column=1, end_row=row + 2, end_column=8)
        row += 4

        # Recommendations
        row = _add_section_header(ws, "Recommendations", row)
        row += 1
        recommendations = self.memo.get("recommendations", [])
        ws.cell(row=row, column=1, value="#").font = BOLD_FONT
        ws.cell(row=row, column=2, value="Source").font = BOLD_FONT
        ws.cell(row=row, column=3, value="Recommendation").font = BOLD_FONT
        for c in range(1, 4):
            ws.cell(row=row, column=c).fill = SUBHEADER_FILL
            ws.cell(row=row, column=c).border = THIN_BORDER
        row += 1
        for i, rec in enumerate(recommendations, 1):
            if isinstance(rec, dict):
                source = rec.get("source", "")
                recommendation = rec.get("recommendation", "")
                if isinstance(recommendation, dict):
                    recommendation = recommendation.get("recommendation", str(recommendation))
                if isinstance(source, dict):
                    source = source.get("source", str(source))
            else:
                source = ""
                recommendation = str(rec)
            ws.cell(row=row, column=1, value=i).font = BODY_FONT
            ws.cell(row=row, column=2, value=str(source)).font = BODY_FONT
            ws.cell(row=row, column=3, value=str(recommendation)).font = BODY_FONT
            for c in range(1, 4):
                ws.cell(row=row, column=c).border = THIN_BORDER
            row += 1

        row += 1
        # Disclaimer
        disclaimer = self.memo.get("appendix", {}).get(
            "disclaimer",
            "This analysis was produced by automated AI agents. Review by a qualified professional is recommended.",
        )
        cell = ws.cell(row=row, column=1, value=disclaimer)
        cell.font = FOOTER_FONT
        cell.alignment = Alignment(wrap_text=True)
        ws.merge_cells(start_row=row, start_column=1, end_row=row + 1, end_column=8)

        _auto_width(ws)
        ws.column_dimensions["C"].width = 60

    def _build_cleaned_data_sheet(self):
        """Sheet 2: Cleaned data from auditor's output."""
        ws = self.wb.create_sheet("Cleaned Data")
        ws.sheet_properties.tabColor = "2E75B6"

        row = 1
        row = _add_title(ws, "Cleaned Dataset", row)
        row = _add_subtitle(ws, "Data after Auditor validation and cleaning", row)
        row += 1

        csv_path = os.path.join(self.session_dir, "cleaned_data.csv")
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            truncated = len(df) > MAX_DATA_ROWS
            if truncated:
                df = df.iloc[:MAX_DATA_ROWS]

            headers = [str(c) for c in df.columns]
            for col_idx, header in enumerate(headers, 1):
                _put(ws, row, col_idx, header)
            _apply_header_style(ws, row, len(headers))
            header_row = row
            row += 1

            for record in df.itertuples(index=False, name=None):
                for col_idx, val in enumerate(record, 1):
                    _put(ws, row, col_idx, None if pd.isna(val) else val)
                row += 1

            if headers and len(df):
                _apply_body_style(ws, header_row + 1, min(row - 1, header_row + STYLED_ROW_LIMIT), len(headers))
                ws.auto_filter.ref = f"A{header_row}:{get_column_letter(len(headers))}{row - 1}"
            if truncated:
                _put(ws, row + 1, 1, f"Note: output truncated to the first {MAX_DATA_ROWS:,} rows (Excel's limit).")
        else:
            ws.cell(row=row, column=1, value="No cleaned data available. Run the Auditor module first.").font = BODY_FONT

        _auto_width(ws)
        ws.freeze_panes = "A4"

    def _build_analysis_sheet(self):
        """Sheet 3: Analysis findings with chart visualizations."""
        ws = self.wb.create_sheet("Analysis")
        ws.sheet_properties.tabColor = "548235"

        row = 1
        row = _add_title(ws, "Analysis Findings & Visualizations", row)
        row = _add_subtitle(ws, "Key metrics, patterns, and anomalies identified by the Analyst", row)
        row += 1

        analysis = self.memo.get("analysis_findings", {})

        if analysis and analysis != {"status": "No analysis available"}:
            # Key Metrics
            if "key_metrics" in analysis:
                row = _add_section_header(ws, "Key Metrics", row)
                row += 1
                metrics = analysis["key_metrics"]
                if isinstance(metrics, dict):
                    ws.cell(row=row, column=1, value="Metric").font = BOLD_FONT
                    ws.cell(row=row, column=2, value="Value").font = BOLD_FONT
                    ws.cell(row=row, column=1).fill = SUBHEADER_FILL
                    ws.cell(row=row, column=2).fill = SUBHEADER_FILL
                    ws.cell(row=row, column=1).border = THIN_BORDER
                    ws.cell(row=row, column=2).border = THIN_BORDER
                    row += 1
                    numeric_rows = []
                    for key, val in metrics.items():
                        ws.cell(row=row, column=1, value=str(key)).font = BODY_FONT
                        is_num = isinstance(val, (int, float)) and not isinstance(val, bool)
                        _put(ws, row, 2, val if is_num else (", ".join(map(str, val)) if isinstance(val, list) else str(val))).font = BODY_FONT
                        ws.cell(row=row, column=1).border = THIN_BORDER
                        ws.cell(row=row, column=2).border = THIN_BORDER
                        if is_num:
                            numeric_rows.append(row)
                        row += 1

                    count_rows = [r for r in numeric_rows if str(ws.cell(row=r, column=1).value).endswith("_count")]
                    if count_rows and count_rows == list(range(count_rows[0], count_rows[-1] + 1)):
                        try:
                            chart = BarChart()
                            chart.type = "col"
                            chart.title = "Dataset Size"
                            chart.style = 10
                            chart.add_data(Reference(ws, min_col=2, min_row=count_rows[0], max_row=count_rows[-1]), titles_from_data=False)
                            chart.set_categories(Reference(ws, min_col=1, min_row=count_rows[0], max_row=count_rows[-1]))
                            chart.legend = None
                            ws.add_chart(chart, "E4")
                        except Exception as e:  # noqa: BLE001
                            logger.warning(f"Could not create chart for key metrics: {e}")
                row += 1

            row += 1

            # Anomalies
            if "anomalies" in analysis:
                row = _add_section_header(ws, "Anomalies Detected", row)
                row += 1
                anomalies = analysis["anomalies"]
                if isinstance(anomalies, list):
                    ws.cell(row=row, column=1, value="#").font = BOLD_FONT
                    ws.cell(row=row, column=2, value="Description").font = BOLD_FONT
                    ws.cell(row=row, column=3, value="Severity").font = BOLD_FONT
                    for c in range(1, 4):
                        ws.cell(row=row, column=c).fill = SUBHEADER_FILL
                        ws.cell(row=row, column=c).border = THIN_BORDER
                    row += 1
                    for i, anom in enumerate(anomalies, 1):
                        ws.cell(row=row, column=1, value=i).font = BODY_FONT
                        desc = anom.get("description") or (
                            f"Row {anom['row_index']}: {anom.get('reason', 'flagged')}" if "row_index" in anom
                            else anom.get("reason", anom.get("field", str(anom)))
                        )
                        sev = anom.get("severity", anom.get("severity", "medium"))
                        ws.cell(row=row, column=2, value=str(desc)).font = BODY_FONT
                        sev_cell = ws.cell(row=row, column=3, value=str(sev))
                        sev_cell.font = BODY_FONT
                        if str(sev).lower() == "high":
                            sev_cell.fill = RED_FILL
                        elif str(sev).lower() == "medium":
                            sev_cell.fill = YELLOW_FILL
                        else:
                            sev_cell.fill = GREEN_FILL
                        for c in range(1, 4):
                            ws.cell(row=row, column=c).border = THIN_BORDER
                        row += 1
                elif isinstance(anomalies, dict):
                    ws.cell(row=row, column=1, value="Field").font = BOLD_FONT
                    ws.cell(row=row, column=2, value="Finding").font = BOLD_FONT
                    ws.cell(row=row, column=1).fill = SUBHEADER_FILL
                    ws.cell(row=row, column=2).fill = SUBHEADER_FILL
                    ws.cell(row=row, column=1).border = THIN_BORDER
                    ws.cell(row=row, column=2).border = THIN_BORDER
                    row += 1
                    for key, val in anomalies.items():
                        ws.cell(row=row, column=1, value=str(key)).font = BODY_FONT
                        ws.cell(row=row, column=2, value=str(val)).font = BODY_FONT
                        ws.cell(row=row, column=1).border = THIN_BORDER
                        ws.cell(row=row, column=2).border = THIN_BORDER
                        row += 1
                row += 1

            row += 1

            # Patterns found
            if "patterns" in analysis:
                row = _add_section_header(ws, "Patterns Identified", row)
                row += 1
                patterns = analysis["patterns"]
                if isinstance(patterns, list):
                    for i, p in enumerate(patterns, 1):
                        cell = ws.cell(row=row, column=1, value=f"{i}. {p}")
                        cell.font = BODY_FONT
                        cell.alignment = Alignment(wrap_text=True)
                        row += 1
                elif isinstance(patterns, str):
                    cell = ws.cell(row=row, column=1, value=patterns)
                    cell.font = BODY_FONT
                    cell.alignment = Alignment(wrap_text=True)
                    row += 1
                row += 1

            # Data Quality
            if "data_quality" in analysis:
                row = _add_section_header(ws, "Data Quality Assessment", row)
                row += 1
                dq = analysis["data_quality"]
                if isinstance(dq, dict):
                    for key, val in dq.items():
                        ws.cell(row=row, column=1, value=str(key)).font = BOLD_FONT
                        ws.cell(row=row, column=2, value=str(val)).font = BODY_FONT
                        ws.cell(row=row, column=1).border = THIN_BORDER
                        ws.cell(row=row, column=2).border = THIN_BORDER
                        row += 1
                elif isinstance(dq, str):
                    cell = ws.cell(row=row, column=1, value=dq)
                    cell.font = BODY_FONT
                    cell.alignment = Alignment(wrap_text=True)
                    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=8)
                    row += 1
        else:
            ws.cell(row=row, column=1, value="No analysis data available. Run the Analyst module first.").font = BODY_FONT

        _auto_width(ws)
        ws.freeze_panes = "A2"

    def _build_audit_trail_sheet(self):
        """Sheet 4: Audit trail showing all corrections and data quality actions."""
        ws = self.wb.create_sheet("Audit Trail")
        ws.sheet_properties.tabColor = "BF8F00"

        row = 1
        row = _add_title(ws, "Audit Trail — Data Cleaning & Validation Record", row)
        row = _add_subtitle(ws, "Complete record of all corrections, standardizations, and quality actions", row)
        row += 1

        audit = self.memo.get("audit_trail", {})

        if audit and audit != {"status": "No audit trail available"}:
            # Summary stats
            row = _add_section_header(ws, "Audit Summary", row)
            row += 1
            summary_fields = ["total_corrections", "records_affected", "issues_found", "issues_resolved"]
            ws.cell(row=row, column=1, value="Metric").font = BOLD_FONT
            ws.cell(row=row, column=2, value="Value").font = BOLD_FONT
            ws.cell(row=row, column=1).fill = SUBHEADER_FILL
            ws.cell(row=row, column=2).fill = SUBHEADER_FILL
            ws.cell(row=row, column=1).border = THIN_BORDER
            ws.cell(row=row, column=2).border = THIN_BORDER
            row += 1
            for field in summary_fields:
                if field in audit:
                    ws.cell(row=row, column=1, value=field.replace("_", " ").title()).font = BODY_FONT
                    ws.cell(row=row, column=2, value=str(audit[field])).font = BODY_FONT
                    ws.cell(row=row, column=1).border = THIN_BORDER
                    ws.cell(row=row, column=2).border = THIN_BORDER
                    row += 1
            row += 1

            # List all corrections
            if "corrections" in audit:
                row = _add_section_header(ws, "Individual Corrections", row)
                row += 1
                corrections = audit["corrections"]
                if isinstance(corrections, list):
                    # Get all keys from all corrections for dynamic headers
                    all_keys = set()
                    for c in corrections:
                        all_keys.update(c.keys())
                    sorted_keys = sorted(all_keys)
                    for col_idx, key in enumerate(sorted_keys, 1):
                        ws.cell(row=row, column=col_idx, value=key.replace("_", " ").title())
                    _apply_header_style(ws, row, len(sorted_keys))
                    row += 1
                    for c in corrections:
                        for col_idx, key in enumerate(sorted_keys, 1):
                            val = c.get(key, "")
                            _put(ws, row, col_idx, str(val))
                        row += 1
                    _apply_body_style(ws, row - len(corrections), row - 1, len(sorted_keys))
                elif isinstance(corrections, dict):
                    for key, val in corrections.items():
                        ws.cell(row=row, column=1, value=str(key)).font = BODY_FONT
                        ws.cell(row=row, column=2, value=str(val)).font = BODY_FONT
                        ws.cell(row=row, column=1).border = THIN_BORDER
                        ws.cell(row=row, column=2).border = THIN_BORDER
                        row += 1
                row += 1

            # Data quality issues
            if "data_quality_issues" in audit:
                row = _add_section_header(ws, "Data Quality Issues", row)
                row += 1
                dq = audit["data_quality_issues"]
                if isinstance(dq, list):
                    for i, issue in enumerate(dq, 1):
                        if isinstance(issue, dict):
                            ws.cell(row=row, column=1, value=f"Issue {i}").font = BOLD_FONT
                            ws.cell(row=row, column=1).border = THIN_BORDER
                            col = 2
                            for key, val in issue.items():
                                ws.cell(row=row, column=col, value=f"{key}: {val}").font = BODY_FONT
                                ws.cell(row=row, column=col).border = THIN_BORDER
                                col += 1
                            row += 1
                        else:
                            ws.cell(row=row, column=1, value=str(issue)).font = BODY_FONT
                            ws.cell(row=row, column=1).border = THIN_BORDER
                            row += 1
                elif isinstance(dq, str):
                    ws.cell(row=row, column=1, value=dq).font = BODY_FONT
                    ws.cell(row=row, column=1).border = THIN_BORDER
                    row += 1
                row += 1

            # Cell-level change log
            change_log = audit.get("log")
            if isinstance(change_log, list) and change_log:
                row = _add_section_header(ws, "Change Log (cell level)", row)
                row += 1
                log_keys = ["file", "row", "column", "old_value", "new_value", "reason", "auto_fixed"]
                for col_idx, key in enumerate(log_keys, 1):
                    ws.cell(row=row, column=col_idx, value=key.replace("_", " ").title())
                _apply_header_style(ws, row, len(log_keys))
                row += 1
                first = row
                for entry in change_log[:MAX_LOG_ROWS]:
                    for col_idx, key in enumerate(log_keys, 1):
                        _put(ws, row, col_idx, entry.get(key, ""))
                    row += 1
                _apply_body_style(ws, first, row - 1, len(log_keys))
                if len(change_log) > MAX_LOG_ROWS:
                    _put(ws, row, 1, f"... {len(change_log) - MAX_LOG_ROWS} more entries omitted.")
                    row += 1
                row += 1

            # Standardizations
            if "standardizations" in audit:
                row = _add_section_header(ws, "Standardizations Applied", row)
                row += 1
                std = audit["standardizations"]
                if isinstance(std, list):
                    for s in std:
                        if isinstance(s, dict):
                            for key, val in s.items():
                                ws.cell(row=row, column=1, value=str(key)).font = BOLD_FONT
                                ws.cell(row=row, column=2, value=str(val)).font = BODY_FONT
                                ws.cell(row=row, column=1).border = THIN_BORDER
                                ws.cell(row=row, column=2).border = THIN_BORDER
                                row += 1
                        else:
                            ws.cell(row=row, column=1, value=str(s)).font = BODY_FONT
                            ws.cell(row=row, column=1).border = THIN_BORDER
                            row += 1
                elif isinstance(std, dict):
                    for key, val in std.items():
                        ws.cell(row=row, column=1, value=str(key)).font = BOLD_FONT
                        ws.cell(row=row, column=2, value=str(val)).font = BODY_FONT
                        ws.cell(row=row, column=1).border = THIN_BORDER
                        ws.cell(row=row, column=2).border = THIN_BORDER
                        row += 1
                row += 1

        else:
            ws.cell(row=row, column=1, value="No audit trail available. Run the Auditor module first.").font = BODY_FONT

        _auto_width(ws)
        ws.freeze_panes = "A2"

        # Add footer to all sheets
        for sheet in self.wb.sheetnames:
            ws = self.wb[sheet]
            last_row = ws.max_row + 2
            cell = ws.cell(row=last_row, column=1, value="Generated by Verity Analytics — Virtual Accounting & Analytics Firm")
            cell.font = FOOTER_FONT
            ws.merge_cells(start_row=last_row, start_column=1, end_row=last_row, end_column=8)


def build_workbook(session_dir: str, memo: dict, output_path: str = None) -> str:
    """Convenience function to build and save the workbook."""
    if output_path is None:
        output_path = os.path.join(session_dir, "final_workbook.xlsx")
    builder = WorkbookBuilder(session_dir, memo)
    return builder.build(output_path)