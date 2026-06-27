"""Google Sheets creation and formatting for the media plan."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from media_plan_generator import HEADERS, MediaPlan


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_NAME = "Media Plan"


def create_media_plan_sheet(
    media_plan: MediaPlan,
    credentials_path: Path,
) -> str:
    if not credentials_path.exists():
        raise FileNotFoundError(
            "Google service account file not found: " + str(credentials_path)
        )

    credentials = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    service = build("sheets", "v4", credentials=credentials)

    spreadsheet = (
        service.spreadsheets()
        .create(
            body={
                "properties": {"title": media_plan.title},
                "sheets": [{"properties": {"title": SHEET_NAME}}],
            },
            fields="spreadsheetId,spreadsheetUrl",
        )
        .execute()
    )

    spreadsheet_id = spreadsheet["spreadsheetId"]
    sheet_id = get_sheet_id(service, spreadsheet_id)

    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"{SHEET_NAME}!A1",
        valueInputOption="USER_ENTERED",
        body={"values": media_plan.values},
    ).execute()

    apply_media_plan_formatting(service, spreadsheet_id, sheet_id, media_plan)
    return spreadsheet["spreadsheetUrl"]


def get_sheet_id(service: Any, spreadsheet_id: str) -> int:
    spreadsheet = (
        service.spreadsheets()
        .get(spreadsheetId=spreadsheet_id, fields="sheets(properties(sheetId,title))")
        .execute()
    )
    for sheet in spreadsheet["sheets"]:
        properties = sheet["properties"]
        if properties["title"] == SHEET_NAME:
            return properties["sheetId"]
    raise RuntimeError("Media Plan sheet was not created.")


def apply_media_plan_formatting(
    service: Any,
    spreadsheet_id: str,
    sheet_id: int,
    media_plan: MediaPlan,
) -> None:
    row_count = len(media_plan.values)
    column_count = len(HEADERS)
    total_row_index = media_plan.total_row_index

    requests: list[dict[str, Any]] = [
        {
            "repeatCell": {
                "range": grid_range(sheet_id, 1, 1, 1, column_count),
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.42, "green": 0.66, "blue": 0.31},
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE",
                        "textFormat": {
                            "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                            "bold": True,
                        },
                    }
                },
                "fields": (
                    "userEnteredFormat(backgroundColor,"
                    "horizontalAlignment,verticalAlignment,textFormat)"
                ),
            }
        },
        {
            "repeatCell": {
                "range": grid_range(sheet_id, 2, row_count, 1, column_count),
                "cell": {
                    "userEnteredFormat": {
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE",
                    }
                },
                "fields": "userEnteredFormat(horizontalAlignment,verticalAlignment)",
            }
        },
        {
            "repeatCell": {
                "range": grid_range(sheet_id, 2, row_count, 3, 3),
                "cell": {
                    "userEnteredFormat": {
                        "numberFormat": {
                            "type": "CURRENCY",
                            "pattern": '"RMB" #,##0',
                        }
                    }
                },
                "fields": "userEnteredFormat.numberFormat",
            }
        },
        {
            "repeatCell": {
                "range": grid_range(sheet_id, 2, row_count, 8, 9),
                "cell": {
                    "userEnteredFormat": {
                        "numberFormat": {
                            "type": "CURRENCY",
                            "pattern": '"RMB" #,##0.00',
                        }
                    }
                },
                "fields": "userEnteredFormat.numberFormat",
            }
        },
        {
            "repeatCell": {
                "range": grid_range(sheet_id, 2, row_count, 4, 4),
                "cell": {
                    "userEnteredFormat": {
                        "numberFormat": {"type": "PERCENT", "pattern": "0.00%"}
                    }
                },
                "fields": "userEnteredFormat.numberFormat",
            }
        },
        {
            "repeatCell": {
                "range": grid_range(sheet_id, 2, row_count, 7, 7),
                "cell": {
                    "userEnteredFormat": {
                        "numberFormat": {"type": "PERCENT", "pattern": "0.00%"}
                    }
                },
                "fields": "userEnteredFormat.numberFormat",
            }
        },
        {
            "repeatCell": {
                "range": grid_range(sheet_id, 2, row_count, 5, 6),
                "cell": {
                    "userEnteredFormat": {
                        "numberFormat": {"type": "NUMBER", "pattern": "#,##0"}
                    }
                },
                "fields": "userEnteredFormat.numberFormat",
            }
        },
        {
            "repeatCell": {
                "range": grid_range(sheet_id, 2, row_count, 10, 10),
                "cell": {
                    "userEnteredFormat": {
                        "numberFormat": {"type": "NUMBER", "pattern": "#,##0"}
                    }
                },
                "fields": "userEnteredFormat.numberFormat",
            }
        },
        {
            "repeatCell": {
                "range": grid_range(sheet_id, total_row_index, total_row_index, 1, column_count),
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9},
                        "textFormat": {"bold": True},
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)",
            }
        },
        {
            "mergeCells": {
                "range": grid_range(sheet_id, total_row_index, total_row_index, 1, 2),
                "mergeType": "MERGE_ALL",
            }
        },
        {
            "updateBorders": {
                "range": grid_range(sheet_id, 1, row_count, 1, column_count),
                "top": border(),
                "bottom": border(),
                "left": border(),
                "right": border(),
                "innerHorizontal": border(),
                "innerVertical": border(),
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
                    "endIndex": column_count,
                }
            }
        },
    ]

    for start_row, end_row in media_plan.group_merge_ranges:
        requests.append(
            {
                "mergeCells": {
                    "range": grid_range(sheet_id, start_row, end_row, 1, 1),
                    "mergeType": "MERGE_ALL",
                }
            }
        )

    for row_index in media_plan.selected_row_indexes:
        requests.append(
            {
                "repeatCell": {
                    "range": grid_range(sheet_id, row_index, row_index, 2, 2),
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {
                                "red": 1.0,
                                "green": 0.9,
                                "blue": 0.3,
                            },
                            "textFormat": {"bold": True},
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat)",
                }
            }
        )

    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": requests},
    ).execute()


def grid_range(
    sheet_id: int,
    start_row: int,
    end_row: int,
    start_column: int,
    end_column: int,
) -> dict[str, int]:
    return {
        "sheetId": sheet_id,
        "startRowIndex": start_row - 1,
        "endRowIndex": end_row,
        "startColumnIndex": start_column - 1,
        "endColumnIndex": end_column,
    }


def border() -> dict[str, Any]:
    return {
        "style": "SOLID",
        "width": 1,
        "color": {"red": 0.75, "green": 0.75, "blue": 0.75},
    }
