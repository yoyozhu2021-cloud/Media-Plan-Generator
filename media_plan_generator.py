"""Build media plan rows and Google Sheets formulas from a client brief."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


HEADERS = [
    "Channel",
    "Ad Platform",
    "Budget Allocation (RMB)",
    "Budget %",
    "Estimated Clicks",
    "Estimated Impressions",
    "Estimated CTR",
    "Estimated Avg. CPC (RMB)",
    "Estimated Avg. CPR (RMB)",
    "Estimated Registrations",
]


CHANNEL_GROUPS = [
    {
        "channel": "Search Advertising",
        "platforms": ["Google Keyword Search", "Yandex", "Google PMax"],
    },
    {
        "channel": "Display Ad Network",
        "platforms": ["Google Remarketing"],
    },
    {
        "channel": "Social Media Advertising",
        "platforms": [
            "Facebook & IG Website Traffic",
            "Facebook & IG Lead Ads",
            "TikTok",
            "LinkedIn Lead Ads",
        ],
    },
]


DEFAULT_BENCHMARKS = {
    "Google Keyword Search": {"cpc": 8, "ctr": 0.02, "cpr": 120},
    "Yandex": {"cpc": 6, "ctr": 0.02, "cpr": 120},
    "Google PMax": {"cpc": 3, "ctr": 0.03, "cpr": 110},
    "Google Remarketing": {"cpc": 2, "ctr": 0.012, "cpr": 120},
    "Facebook & IG Website Traffic": {"cpc": 4, "ctr": 0.006, "cpr": 200},
    "Facebook & IG Lead Ads": {"cpc": 4, "ctr": 0.006, "cpr": 100},
    "TikTok": {"cpc": 3, "ctr": 0.006, "cpr": 150},
    "LinkedIn Lead Ads": {"cpc": 28, "ctr": 0.006, "cpr": 800},
}


ALL_PLATFORMS = [
    platform
    for group in CHANNEL_GROUPS
    for platform in group["platforms"]
]


@dataclass(frozen=True)
class MediaPlan:
    title: str
    values: list[list[Any]]
    group_merge_ranges: list[tuple[int, int]]
    selected_row_indexes: list[int]
    total_row_index: int


def load_client_brief(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as file:
        brief = json.load(file)
    validate_client_brief(brief)
    return brief


def validate_client_brief(brief: dict[str, Any]) -> None:
    if "total_budget_rmb" not in brief:
        raise ValueError("Missing required field: total_budget_rmb")

    total_budget = parse_number(brief["total_budget_rmb"])
    if total_budget <= 0:
        raise ValueError("total_budget_rmb must be greater than 0")

    selected_platforms = brief.get("selected_platforms", ALL_PLATFORMS)
    unknown = [platform for platform in selected_platforms if platform not in ALL_PLATFORMS]
    if unknown:
        raise ValueError("Unknown selected platform(s): " + ", ".join(unknown))

    platform_budgets = brief.get("platform_budgets_rmb", {})
    unknown_budget_platforms = [
        platform for platform in platform_budgets if platform not in ALL_PLATFORMS
    ]
    if unknown_budget_platforms:
        raise ValueError(
            "Unknown platform budget key(s): " + ", ".join(unknown_budget_platforms)
        )

    platform_percentages = brief.get("platform_budget_percentages", {})
    unknown_percentage_platforms = [
        platform for platform in platform_percentages if platform not in ALL_PLATFORMS
    ]
    if unknown_percentage_platforms:
        raise ValueError(
            "Unknown platform percentage key(s): "
            + ", ".join(unknown_percentage_platforms)
        )


def build_media_plan(brief: dict[str, Any]) -> MediaPlan:
    title = sheet_title(brief)
    total_budget = parse_number(brief["total_budget_rmb"])
    total_row_index = len(ALL_PLATFORMS) + 2
    selected_platforms = set(brief.get("selected_platforms", ALL_PLATFORMS))
    benchmarks = merge_benchmarks(brief.get("benchmarks", {}))
    budgets = allocate_budgets(brief, total_budget, selected_platforms)

    rows: list[list[Any]] = [HEADERS]
    group_merge_ranges: list[tuple[int, int]] = []
    selected_row_indexes: list[int] = []

    for group in CHANNEL_GROUPS:
        group_start_row = len(rows) + 1
        for platform in group["platforms"]:
            sheet_row = len(rows) + 1
            budget = budgets.get(platform, 0)
            benchmark = benchmarks[platform]
            rows.append(
                [
                    group["channel"],
                    platform,
                    budget,
                    f"=C{sheet_row}/$C${total_row_index}",
                    f"=C{sheet_row}/H{sheet_row}",
                    f"=E{sheet_row}/G{sheet_row}",
                    benchmark["ctr"],
                    benchmark["cpc"],
                    benchmark["cpr"],
                    f"=C{sheet_row}/I{sheet_row}",
                ]
            )
            if platform in selected_platforms:
                selected_row_indexes.append(sheet_row)

        group_end_row = len(rows)
        if group_end_row > group_start_row:
            group_merge_ranges.append((group_start_row, group_end_row))

    rows.append(
        [
            "Total",
            "",
            f"=SUM(C2:C{total_row_index - 1})",
            "100%",
            f"=SUM(E2:E{total_row_index - 1})",
            f"=SUM(F2:F{total_row_index - 1})",
            f"=E{total_row_index}/F{total_row_index}",
            f"=C{total_row_index}/E{total_row_index}",
            f"=C{total_row_index}/J{total_row_index}",
            f"=SUM(J2:J{total_row_index - 1})",
        ]
    )

    return MediaPlan(
        title=title,
        values=rows,
        group_merge_ranges=group_merge_ranges,
        selected_row_indexes=selected_row_indexes,
        total_row_index=total_row_index,
    )


def sheet_title(brief: dict[str, Any]) -> str:
    client_name = str(brief.get("client_name", "Client")).strip() or "Client"
    market = str(brief.get("market", "")).strip()
    if market:
        return f"{client_name} {market} Media Plan"
    return f"{client_name} Media Plan"


def merge_benchmarks(custom_benchmarks: dict[str, Any]) -> dict[str, dict[str, float]]:
    benchmarks = {
        platform: values.copy()
        for platform, values in DEFAULT_BENCHMARKS.items()
    }

    for platform, values in custom_benchmarks.items():
        if platform not in benchmarks:
            raise ValueError("Unknown benchmark platform: " + platform)
        for metric in ("cpc", "ctr", "cpr"):
            if metric in values:
                benchmarks[platform][metric] = parse_metric(values[metric], metric)

    return benchmarks


def allocate_budgets(
    brief: dict[str, Any], total_budget: float, selected_platforms: set[str]
) -> dict[str, float]:
    budgets = {platform: 0.0 for platform in ALL_PLATFORMS}
    explicit_budgets = brief.get("platform_budgets_rmb", {})
    explicit_percentages = brief.get("platform_budget_percentages", {})

    if explicit_budgets:
        for platform, amount in explicit_budgets.items():
            budgets[platform] = parse_number(amount)
        return budgets

    if explicit_percentages:
        for platform, percentage in explicit_percentages.items():
            budgets[platform] = total_budget * parse_percentage(percentage)
        return budgets

    if not selected_platforms:
        return budgets

    even_budget = total_budget / len(selected_platforms)
    for platform in selected_platforms:
        budgets[platform] = even_budget
    return budgets


def parse_metric(value: Any, metric: str) -> float:
    if metric == "ctr":
        return parse_percentage(value)
    return parse_number(value)


def parse_number(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = str(value).replace(",", "").replace("RMB", "").replace("¥", "").strip()
    if not cleaned:
        raise ValueError("Expected numeric value, got blank")
    return float(cleaned)


def parse_percentage(value: Any) -> float:
    if isinstance(value, (int, float)):
        numeric = float(value)
        return numeric / 100 if numeric > 1 else numeric
    text = str(value).strip()
    if text.endswith("%"):
        return float(text[:-1].strip()) / 100
    numeric = float(text)
    return numeric / 100 if numeric > 1 else numeric
