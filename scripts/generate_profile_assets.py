#!/usr/bin/env python3
"""Generate local SVG assets for a GitHub profile README.

The script intentionally uses only the Python standard library. It reads public
profile/repository data from GitHub's APIs and writes static SVG files into the
profile repository, avoiding runtime dependencies on public badge services.
"""

from __future__ import annotations

import calendar
import html
import json
import math
import os
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

PROFILE_USERNAME = os.getenv("PROFILE_USERNAME", "ronfinn")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
OUTPUT_DIRECTORY = Path(__file__).resolve().parents[1] / "assets"

FLAGSHIP_REPOSITORIES = (
    "dataswamp-biosystems",
    "cell-painting-anndata-validator",
    "bio-run-crate",
)

REST_API = "https://api.github.com"
GRAPHQL_API = "https://api.github.com/graphql"
USER_AGENT = "ronfinn-profile-asset-generator/1.0"


@dataclass(frozen=True)
class Theme:
    background: str
    panel: str
    border: str
    text: str
    muted: str
    accent: str
    accent_two: str
    grid: str


DARK = Theme(
    background="#0B1220",
    panel="#111B2E",
    border="#26344D",
    text="#F8FAFC",
    muted="#A8B3C7",
    accent="#14B8A6",
    accent_two="#38BDF8",
    grid="#22314A",
)

LIGHT = Theme(
    background="#F8FAFC",
    panel="#FFFFFF",
    border="#CBD5E1",
    text="#0F172A",
    muted="#475569",
    accent="#0F766E",
    accent_two="#0369A1",
    grid="#E2E8F0",
)


def request_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url=url,
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API returned HTTP {error.code}: {body}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Unable to reach the GitHub API: {error}") from error


def get_user() -> dict[str, Any]:
    result = request_json(f"{REST_API}/users/{PROFILE_USERNAME}")
    if not isinstance(result, dict):
        raise RuntimeError("Unexpected user response from GitHub.")
    return result


def get_repository(name: str) -> dict[str, Any]:
    result = request_json(f"{REST_API}/repos/{PROFILE_USERNAME}/{name}")
    if not isinstance(result, dict):
        raise RuntimeError(f"Unexpected repository response for {name}.")
    return result


def month_keys(end_day: date, count: int = 12) -> list[str]:
    year = end_day.year
    month = end_day.month
    keys: list[str] = []

    for _ in range(count):
        keys.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            month = 12
            year -= 1

    return list(reversed(keys))


def get_contribution_calendar() -> tuple[list[str], list[int], int]:
    """Return month keys, monthly totals and the 12-month contribution total."""

    today = datetime.now(timezone.utc)
    start = today - timedelta(days=365)

    query = """
    query ProfileActivity($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                contributionCount
                date
              }
            }
          }
        }
      }
    }
    """

    result = request_json(
        GRAPHQL_API,
        method="POST",
        payload={
            "query": query,
            "variables": {
                "login": PROFILE_USERNAME,
                "from": start.isoformat(),
                "to": today.isoformat(),
            },
        },
    )

    if result.get("errors"):
        raise RuntimeError(f"GitHub GraphQL returned errors: {result['errors']}")

    calendar_data = (
        result.get("data", {})
        .get("user", {})
        .get("contributionsCollection", {})
        .get("contributionCalendar", {})
    )

    monthly: dict[str, int] = defaultdict(int)
    for week in calendar_data.get("weeks", []):
        for day in week.get("contributionDays", []):
            key = str(day.get("date", ""))[:7]
            monthly[key] += int(day.get("contributionCount", 0))

    keys = month_keys(today.date())
    values = [monthly.get(key, 0) for key in keys]
    total = int(calendar_data.get("totalContributions", sum(values)))
    return keys, values, total


def svg_text(value: object) -> str:
    return html.escape(str(value), quote=True)


def short_number(value: int) -> str:
    if value < 1_000:
        return str(value)
    if value < 1_000_000:
        return f"{value / 1_000:.1f}k".rstrip("0").rstrip(".")
    return f"{value / 1_000_000:.1f}m".rstrip("0").rstrip(".")


def latest_repository_date(repositories: Iterable[dict[str, Any]]) -> str:
    dates: list[datetime] = []
    for repository in repositories:
        pushed_at = repository.get("pushed_at")
        if not pushed_at:
            continue
        dates.append(datetime.fromisoformat(str(pushed_at).replace("Z", "+00:00")))

    if not dates:
        return "—"

    latest = max(dates)
    return latest.strftime("%d %b %Y")


def render_stats_svg(
    *,
    theme: Theme,
    user: dict[str, Any],
    repositories: list[dict[str, Any]],
) -> str:
    stars = sum(int(repository.get("stargazers_count", 0)) for repository in repositories)
    forks = sum(int(repository.get("forks_count", 0)) for repository in repositories)
    followers = int(user.get("followers", 0))
    updated = latest_repository_date(repositories)

    cards = [
        ("FLAGSHIP SYSTEMS", str(len(repositories)), "Curated original projects"),
        ("REPOSITORY STARS", short_number(stars), "Across flagship systems"),
        ("FOLLOWERS", short_number(followers), "Public GitHub profile"),
        ("LATEST UPDATE", updated, "Most recent flagship push"),
    ]

    card_width = 270
    card_gap = 20
    start_x = 30
    cards_markup: list[str] = []

    for index, (label, value, description) in enumerate(cards):
        x = start_x + index * (card_width + card_gap)
        value_size = 34 if len(value) <= 8 else 24
        cards_markup.append(
            f"""
            <rect x="{x}" y="92" width="{card_width}" height="130" rx="16"
                  fill="{theme.panel}" stroke="{theme.border}"/>
            <text x="{x + 20}" y="124" fill="{theme.muted}" font-size="13"
                  font-weight="700" letter-spacing="1.1">{svg_text(label)}</text>
            <text x="{x + 20}" y="170" fill="{theme.text}" font-size="{value_size}"
                  font-weight="750">{svg_text(value)}</text>
            <text x="{x + 20}" y="201" fill="{theme.muted}" font-size="13">
              {svg_text(description)}
            </text>
            """
        )

    repo_rows: list[str] = []
    row_y = 278
    for repository in repositories:
        name = str(repository.get("name", "repository"))
        description = str(repository.get("description") or "No description supplied.")
        if len(description) > 96:
            description = description[:93] + "..."
        language = str(repository.get("language") or "Multi-language")
        stars_count = int(repository.get("stargazers_count", 0))
        repo_rows.append(
            f"""
            <circle cx="44" cy="{row_y - 5}" r="5" fill="{theme.accent}"/>
            <text x="62" y="{row_y}" fill="{theme.text}" font-size="17"
                  font-weight="700">{svg_text(name)}</text>
            <text x="360" y="{row_y}" fill="{theme.muted}" font-size="14">
              {svg_text(language)} · ★ {stars_count}
            </text>
            <text x="530" y="{row_y}" fill="{theme.muted}" font-size="14">
              {svg_text(description)}
            </text>
            """
        )
        row_y += 38

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="420"
        viewBox="0 0 1200 420" role="img"
        aria-label="GitHub open-source portfolio metrics for {svg_text(PROFILE_USERNAME)}">
      <rect width="1200" height="420" rx="22" fill="{theme.background}"/>
      <rect x="1" y="1" width="1198" height="418" rx="21"
            fill="none" stroke="{theme.border}"/>
      <circle cx="42" cy="44" r="8" fill="{theme.accent}"/>
      <text x="64" y="50" fill="{theme.text}" font-size="24" font-weight="750">
        Open-source portfolio pulse
      </text>
      <text x="64" y="73" fill="{theme.muted}" font-size="14">
        Curated metrics for current scientific data and engineering projects
      </text>
      {''.join(cards_markup)}
      <text x="30" y="252" fill="{theme.muted}" font-size="13"
            font-weight="700" letter-spacing="1.1">FLAGSHIP REPOSITORIES</text>
      {''.join(repo_rows)}
    </svg>
    """


def line_path(values: list[int], *, x: int, y: int, width: int, height: int) -> str:
    if not values:
        return ""

    maximum = max(max(values), 1)
    points: list[tuple[float, float]] = []

    for index, value in enumerate(values):
        px = x + (width * index / max(len(values) - 1, 1))
        py = y + height - (height * value / maximum)
        points.append((px, py))

    return " ".join(
        ("M" if index == 0 else "L") + f" {px:.1f} {py:.1f}"
        for index, (px, py) in enumerate(points)
    )


def render_activity_svg(
    *,
    theme: Theme,
    keys: list[str],
    values: list[int],
    total: int,
) -> str:
    chart_x = 80
    chart_y = 100
    chart_width = 1040
    chart_height = 190
    maximum = max(max(values, default=0), 1)
    path = line_path(
        values,
        x=chart_x,
        y=chart_y,
        width=chart_width,
        height=chart_height,
    )

    grid_lines: list[str] = []
    for index in range(5):
        gy = chart_y + chart_height * index / 4
        label_value = round(maximum * (4 - index) / 4)
        grid_lines.append(
            f"""
            <line x1="{chart_x}" y1="{gy:.1f}" x2="{chart_x + chart_width}"
                  y2="{gy:.1f}" stroke="{theme.grid}" stroke-width="1"/>
            <text x="{chart_x - 18}" y="{gy + 5:.1f}" text-anchor="end"
                  fill="{theme.muted}" font-size="12">{label_value}</text>
            """
        )

    labels: list[str] = []
    points: list[str] = []
    for index, (key, value) in enumerate(zip(keys, values, strict=True)):
        px = chart_x + chart_width * index / max(len(values) - 1, 1)
        py = chart_y + chart_height - chart_height * value / maximum
        year, month = key.split("-")
        label = calendar.month_abbr[int(month)]
        if month == "01":
            label = f"{label} {year[-2:]}"
        labels.append(
            f"""
            <text x="{px:.1f}" y="{chart_y + chart_height + 30}"
                  text-anchor="middle" fill="{theme.muted}" font-size="12">
              {svg_text(label)}
            </text>
            """
        )
        points.append(
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4.5" '
            f'fill="{theme.background}" stroke="{theme.accent}" stroke-width="3"/>'
        )

    peak = max(values, default=0)
    peak_month = "—"
    if values and peak > 0:
        peak_index = values.index(peak)
        year, month = keys[peak_index].split("-")
        peak_month = f"{calendar.month_abbr[int(month)]} {year}"

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="370"
        viewBox="0 0 1200 370" role="img"
        aria-label="Twelve-month GitHub contribution activity">
      <rect width="1200" height="370" rx="22" fill="{theme.background}"/>
      <rect x="1" y="1" width="1198" height="368" rx="21"
            fill="none" stroke="{theme.border}"/>
      <circle cx="42" cy="44" r="8" fill="{theme.accent_two}"/>
      <text x="64" y="50" fill="{theme.text}" font-size="24" font-weight="750">
        Twelve-month contribution activity
      </text>
      <text x="64" y="73" fill="{theme.muted}" font-size="14">
        Public GitHub contributions aggregated by month
      </text>
      <text x="1118" y="44" text-anchor="end" fill="{theme.text}"
            font-size="22" font-weight="750">{total}</text>
      <text x="1118" y="65" text-anchor="end" fill="{theme.muted}"
            font-size="12">TOTAL CONTRIBUTIONS</text>
      {''.join(grid_lines)}
      <path d="{path}" fill="none" stroke="{theme.accent}" stroke-width="4"
            stroke-linecap="round" stroke-linejoin="round"/>
      {''.join(points)}
      {''.join(labels)}
      <text x="80" y="350" fill="{theme.muted}" font-size="12">
        Peak month: {svg_text(peak_month)} · {peak} contribution(s)
      </text>
    </svg>
    """


def fallback_activity() -> tuple[list[str], list[int], int]:
    keys = month_keys(date.today())
    return keys, [0] * len(keys), 0


def main() -> int:
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    try:
        user = get_user()
        repositories = [get_repository(name) for name in FLAGSHIP_REPOSITORIES]
    except RuntimeError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    try:
        keys, values, total = get_contribution_calendar()
    except RuntimeError as error:
        print(f"WARNING: contribution activity unavailable: {error}", file=sys.stderr)
        keys, values, total = fallback_activity()

    outputs = {
        "profile-stats-dark.svg": render_stats_svg(
            theme=DARK,
            user=user,
            repositories=repositories,
        ),
        "profile-stats-light.svg": render_stats_svg(
            theme=LIGHT,
            user=user,
            repositories=repositories,
        ),
        "activity-dark.svg": render_activity_svg(
            theme=DARK,
            keys=keys,
            values=values,
            total=total,
        ),
        "activity-light.svg": render_activity_svg(
            theme=LIGHT,
            keys=keys,
            values=values,
            total=total,
        ),
    }

    for filename, content in outputs.items():
        path = OUTPUT_DIRECTORY / filename
        path.write_text(content, encoding="utf-8")
        print(f"Wrote {path.relative_to(OUTPUT_DIRECTORY.parent)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
