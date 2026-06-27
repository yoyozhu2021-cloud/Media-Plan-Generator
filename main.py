"""CLI entry point for creating a Google Sheet media plan."""

from __future__ import annotations

import argparse
from pathlib import Path

from google_sheets import create_media_plan_sheet
from media_plan_generator import build_media_plan, load_client_brief


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a formatted Google Sheet media plan from a client brief JSON."
    )
    parser.add_argument("client_brief_json", type=Path)
    parser.add_argument(
        "--credentials",
        type=Path,
        default=Path("service_account.json"),
        help="Path to the Google service account JSON key.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    brief = load_client_brief(args.client_brief_json)
    media_plan = build_media_plan(brief)
    spreadsheet_url = create_media_plan_sheet(media_plan, args.credentials)
    print("Google Sheet media plan created:")
    print(spreadsheet_url)


if __name__ == "__main__":
    main()
