"""Render recent public GitHub events using only Python's standard library."""

from datetime import datetime, timezone
from html import escape
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen


USERNAME = "datongyi"
PROFILE_REPOSITORY = f"{USERNAME}/{USERNAME}".lower()
OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "recent-activity.svg"


def activity_row(event):
    """Return a truthful one-line summary for a supported public event."""
    repository = event["repo"]["name"]
    if repository.lower() == PROFILE_REPOSITORY:
        return None
    payload = event["payload"]
    event_type = event["type"]
    detail = ""
    if event_type == "PushEvent":
        title = f"Pushed to {repository}"
        detail = payload["head"][:7]
    elif event_type == "WatchEvent":
        title = f"Starred {repository}"
    elif event_type == "CreateEvent":
        title = f"Created {payload['ref_type']} in {repository}"
    elif event_type == "PullRequestEvent":
        action = "merged" if payload["pull_request"].get("merged") else payload["action"]
        title = f"{action.capitalize()} PR in {repository}"
        detail = f"#{payload['number']}"
    elif event_type == "IssuesEvent":
        title = f"{payload['action'].capitalize()} issue in {repository}"
        detail = f"#{payload['issue']['number']}"
    elif event_type == "ReleaseEvent":
        title = f"Published release in {repository}"
        detail = payload["release"]["tag_name"]
    elif event_type == "ForkEvent":
        title = f"Forked {repository}"
    elif event_type == "IssueCommentEvent":
        title = f"Commented in {repository}"
        detail = f"#{payload['issue']['number']}"
    else:
        return None
    date = datetime.fromisoformat(event["created_at"].replace("Z", "+00:00"))
    return title, detail, date


def fetch_rows():
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": f"{USERNAME}-profile-activity",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(
        f"https://api.github.com/users/{USERNAME}/events/public?per_page=100",
        headers=headers,
    )
    with urlopen(request, timeout=30) as response:
        events = json.load(response)
    rows = [row for event in events if (row := activity_row(event)) is not None]
    rows.sort(key=lambda row: row[2], reverse=True)
    if not rows:
        raise RuntimeError("No supported public activity outside the profile repository was returned")
    return rows[:5]


def fit(text, length):
    return text if len(text) <= length else text[: length - 1] + "…"


def render(rows):
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    height = 106 + 30 * len(rows)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="{height}" '
        f'viewBox="0 0 900 {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Recent public activity for datongyi</title>',
        '<desc id="desc">Public GitHub events, newest first, excluding the profile repository. Dates are UTC.</desc>',
        f'<rect x="0.5" y="0.5" width="899" height="{height - 1}" rx="18" fill="#102F3C" stroke="#29505C"/>',
        '<g font-family="Segoe UI,Microsoft YaHei,PingFang SC,sans-serif">',
        '<text x="28" y="35" fill="#78DEC6" font-size="22" font-weight="600">Recent activity · 最近公开动态</text>',
        '<text x="28" y="57" fill="#9DBDC4" font-size="13">Small steps, visible progress.</text>',
    ]
    for index, (title, detail, date) in enumerate(rows):
        y = 88 + 30 * index
        parts.extend(
            [
                f'<circle cx="33" cy="{y - 5}" r="3" fill="#78DEC6"/>',
                f'<text x="48" y="{y}" fill="#F6F2E7" font-size="16">{escape(fit(title, 57))}</text>',
                f'<text x="666" y="{y}" fill="#9DBDC4" font-size="13" text-anchor="end">{escape(fit(detail, 12))}</text>',
                f'<text x="868" y="{y}" fill="#9DBDC4" font-size="14" text-anchor="end">{date:%Y-%m-%d %H:%M}</text>',
            ]
        )
    parts.extend(
        [
            f'<text x="28" y="{height - 16}" fill="#9DBDC4" font-size="12">Latest {len(rows)} public events · UTC · Updated {updated}</text>',
            '</g></svg>',
        ]
    )
    return "\n".join(parts) + "\n"


def main():
    rows = fetch_rows()
    svg = render(rows)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(svg, encoding="utf-8")
    print(f"Generated {OUTPUT.name} from {len(rows)} public events")


if __name__ == "__main__":
    main()
