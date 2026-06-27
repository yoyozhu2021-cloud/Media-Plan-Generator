#!/usr/bin/env python3
"""Generate a formatted Google Sheet media plan from a structured strategy JSON."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

try:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
except ImportError:
    Credentials = None
    build = None


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

HEADERS = [
    "Market",
    "Channel",
    "Campaign Name",
    "Funnel Stage",
    "Audience",
    "Budget",
    "KPI Target",
    "Creative Angle",
    "Expected CPL Range",
    "Notes",
]

FUNNEL_ORDER = ["TOF", "MOF", "BOF"]


class StrategyValidationError(ValueError):
    """Raised when a strategy JSON object is missing required structure."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a structured strategy JSON into a Google Sheet media plan."
    )
    parser.add_argument("strategy_json", type=Path, help="Path to the strategy JSON file.")
    parser.add_argument(
        "--credentials",
        type=Path,
        default=Path("service_account.json"),
        help="Path to a Google service account JSON key.",
    )
    parser.add_argument(
        "--spreadsheet-title",
        default="Media Plan",
        help="Google Sheet title to create.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write a local CSV preview instead of creating a Google Sheet.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("media_plan_preview.csv"),
        help="CSV output path used with --dry-run.",
    )
    return parser.parse_args()


def load_strategy(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as file:
        strategy = json.load(file)

    validate_strategy(strategy)
    return strategy


def validate_strategy(strategy: dict[str, Any]) -> None:
    required = [
        "market_insight",
        "funnel",
        "budget_split",
        "channel_strategy",
        "kpi_forecast",
        "creative_strategy",
    ]
    missing = [key for key in required if key not in strategy]
    if missing:
        raise StrategyValidationError("Missing required key(s): " + ", ".join(missing))

    for stage in FUNNEL_ORDER:
        if stage not in strategy["funnel"]:
            raise StrategyValidationError("Missing funnel stage: " + stage)
        if stage not in strategy["budget_split"]:
            raise StrategyValidationError("Missing budget split stage: " + stage)

    if "cpl_range" not in strategy["kpi_forecast"]:
        raise StrategyValidationError("Missing kpi_forecast.cpl_range")

    if "angles" not in strategy["creative_strategy"]:
        raise StrategyValidationError("Missing creative_strategy.angles")


def generate_media_plan(strategy: dict[str, Any]) -> list[list[Any]]:
    rows: list[list[Any]] = []
    market_insight = strategy["market_insight"]
    funnel = strategy["funnel"]
    budget_split = strategy["budget_split"]
    kpi_forecast = strategy["kpi_forecast"]
    creative_strategy = strategy["creative_strategy"]

    for market, insight in market_insight.items():
        for stage in FUNNEL_ORDER:
            for channel in funnel[stage]:
                channel_root = channel_family(channel)
                channel_rules = strategy["channel_strategy"].get(channel_root, {})
                rows.append(
                    [
                        market,
                        channel,
                        campaign_name(market, channel, stage),
                        stage,
                        strategy.get("audience", ""),
                        budget_value(budget_split[stage]),
                        kpi_target(kpi_forecast, channel_root),
                        creative_angle(creative_strategy),
                        kpi_forecast["cpl_range"],
                        notes(insight, channel_rules),
                    ]
                )

    return rows


def channel_family(channel: str) -> str:
    normalized = channel.lower()
    if "google" in normalized:
        return "Google"
    if "meta" in normalized:
        return "Meta"
    if "tiktok" in normalized:
        return "TikTok"
    return channel.split()[0]


def campaign_name(market: str, channel: str, stage: str) -> str:
    return "_".join([slug(market), slug(channel), slug(stage), "Media-Plan"])


def slug(value: Any) -> str:
    text = str(value).strip()
    text = re.sub(r"[^A-Za-z0-9]+", "-", text)
    return text.strip("-")


def budget_value(split: Any) -> str:
    if isinstance(split, (int, float)):
        return str(round(split * 100, 2)).rstrip("0").rstrip(".") + "%"
    return str(split)


def kpi_target(kpi_forecast: dict[str, Any], channel_root: str) -> str:
    parts = []
    if "ctr_range" in kpi_forecast:
        parts.append("CTR " + str(kpi_forecast["ctr_range"]))
    cpc_range = kpi_forecast.get("cpc_range", {})
    if isinstance(cpc_range, dict):
        cpc = cpc_range.get(channel_root.lower())
        if cpc:
            parts.append("CPC " + str(cpc))
    if "cvr_range" in kpi_forecast:
        parts.append("CVR " + str(kpi_forecast["cvr_range"]))
    return "; ".join(parts)


def creative_angle(creative_strategy: dict[str, Any]) -> str:
    angles = creative_strategy.get("angles", [])
    formats = creative_strategy.get("formats", [])
    angle_text = ", ".join(str(angle) for angle in angles)
    format_text = ", ".join(str(fmt) for fmt in formats)

    if angle_text and format_text:
        return angle_text + " | Formats: " + format_text
    if angle_text:
        return angle_text
    return format_text


def notes(market_insight: str, channel_rules: dict[str, Any]) -> str:
    parts = []
    if market_insight:
        parts.append("Market insight: " + str(market_insight))
    if "role" in channel_rules:
        parts.append("Channel role: " + str(channel_rules["role"]))
    if "priority" in channel_rules:
        parts.append("Priority: " + str(channel_rules["priority"]))
    return "; ".join(parts)


def create_google_sheet(title: str, rows: list[list[Any]], credentials_path: Path) -> str:
    if Credentials is None or build is None:
        raise RuntimeError(
            "Google API dependencies are not installed. Run: pip install -r requirements.txt"
        )

    if not credentials_path.exists():
        raise FileNotFoundError(
            "Google credentials file not found: " + str(credentials_path)
            + ". Use --dry-run for a local CSV preview."
        )

    credentials = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    service = build("sheets", "v4", credentials=credentials)

    spreadsheet = (
        service.spreadsheets()
        .create(
            body={
                "properties": {"title": title},
                "sheets": [{"properties": {"title": "Media Plan"}}],
            },
            fields="spreadsheetId,spreadsheetUrl",
        )
        .execute()
    )

    spreadsheet_id = spreadsheet["spreadsheetId"]
    values = [HEADERS] + rows

    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range="Media Plan!A1",
        valueInputOption="USER_ENTERED",
        body={"values": values},
    ).execute()

    apply_formatting(service, spreadsheet_id, len(values))
    return spreadsheet["spreadsheetUrl"]


def apply_formatting(service: Any, spreadsheet_id: str, row_count: int) -> None:
    sheet_id = 0
    requests = [
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": len(HEADERS),
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.12, "green": 0.21, "blue": 0.32},
                        "horizontalAlignment": "CENTER",
                        "textFormat": {
                            "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                            "bold": True,
                        },
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)",
            }
        },
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {"frozenRowCount": 1},
                },
                "fields": "gridProperties.frozenRowCount",
            }
        },
        {
            "autoResizeDimensions": {
                "dimensions": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": len(HEADERS),
                }
            }
        },
        {
            "setBasicFilter": {
                "filter": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": row_count,
                        "startColumnIndex": 0,
                        "endColumnIndex": len(HEADERS),
                    }
                }
            }
        },
    ]

    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"requests": requests}
    ).execute()


def write_csv(path: Path, rows: list[list[Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(HEADERS)
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    strategy = load_strategy(args.strategy_json)
    rows = generate_media_plan(strategy)

    if args.dry_run:
        write_csv(args.output_csv, rows)
        print("CSV preview created: " + str(args.output_csv))
        return

    spreadsheet_url = create_google_sheet(args.spreadsheet_title, rows, args.credentials)
    print("Google Sheet created: " + spreadsheet_url)


if __name__ == "__main__":
    main()
