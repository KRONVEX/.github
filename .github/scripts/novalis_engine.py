#!/usr/bin/env python3
"""
NOVALIS Organization Telemetry & Animated SVG Engine
==========================================================
Generates 4 adaptive dark/light SVG visual panels (8 files total) for the
N-O-V-A-L-I-S GitHub Organization profile (.github/profile/README.md) and
automatically syncs the Flagship Ecosystem repository table.

Generated Assets (assets/):
  1. hero_command_dark.svg / hero_command_light.svg
  2. architecture_pillars_dark.svg / architecture_pillars_light.svg
  3. org_telemetry_dark.svg / org_telemetry_light.svg
  4. intelligence_radar_dark.svg / intelligence_radar_light.svg

Uses Python standard library (+ optional yfinance for live market data).
"""

from __future__ import annotations

import argparse
import csv
import datetime
import io
import json
import math
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from xml.sax.saxutils import escape


DEFAULT_ORG = "N-O-V-A-L-I-S"
GRAPHQL_URL = "https://api.github.com/graphql"
REST_API_URL = "https://api.github.com"

FALLBACK_LANG_COLORS = {
    "Python": "#3572A5",
    "TypeScript": "#3178C6",
    "JavaScript": "#F1E05A",
    "Rust": "#DEA584",
    "Dart": "#00B4AB",
    "Go": "#00ADD8",
    "Java": "#B07219",
    "C++": "#F34B7D",
    "HTML": "#E34C26",
    "CSS": "#563D7C",
    "Shell": "#89E051",
    "Jupyter Notebook": "#DA5B0B",
    "Dockerfile": "#384D54",
    "SQL": "#E38C00",
}

LANG_DISPLAY_NAMES = {
    "Jupyter Notebook": "Jupyter",
    "Objective-C++": "Obj-C++",
    "Objective-C": "Obj-C",
    "Dockerfile": "Docker",
}

THEMES = {
    "dark": {
        "bg_outer": "#090D16",
        "bg_outer_end": "#0D1322",
        "bg_panel": "#0F1624",
        "bg_subpanel": "#131C2E",
        "bg_ticker": "#070B12",
        "border": "#1E293B",
        "border_bright": "#334155",
        "grid": "#162033",
        "text_primary": "#F8FAFC",
        "text_secondary": "#94A3B8",
        "text_muted": "#64748B",
        "cyan": "#38BDF8",
        "cyan_soft": "#0EA5E9",
        "violet": "#818CF8",
        "violet_deep": "#6366F1",
        "emerald": "#10B981",
        "emerald_soft": "#059669",
        "amber": "#F59E0B",
        "rose": "#F43F5E",
        "pill_bg": "#172036",
        "pill_text": "#BAE6FD",
        "pill_violet_bg": "#1E1B4B",
        "pill_violet_text": "#C7D2FE",
        "pill_emerald_bg": "#063327",
        "pill_emerald_text": "#6EE7B7",
        "glow_opacity": "0.14",
        "grid_opacity": "0.45",
        "wordmark_start": "#F8FAFC",
        "wordmark_mid": "#7DD3FC",
        "wordmark_end": "#A5B4FC",
    },
    "light": {
        "bg_outer": "#FFFFFF",
        "bg_outer_end": "#F8FAFC",
        "bg_panel": "#F8FAFC",
        "bg_subpanel": "#F1F5F9",
        "bg_ticker": "#F1F5F9",
        "border": "#CBD5E1",
        "border_bright": "#94A3B8",
        "grid": "#E2E8F0",
        "text_primary": "#0F172A",
        "text_secondary": "#475569",
        "text_muted": "#64748B",
        "cyan": "#0284C7",
        "cyan_soft": "#0369A1",
        "violet": "#4F46E5",
        "violet_deep": "#4338CA",
        "emerald": "#059669",
        "emerald_soft": "#047857",
        "amber": "#D97706",
        "rose": "#E11D48",
        "pill_bg": "#E0F2FE",
        "pill_text": "#0369A1",
        "pill_violet_bg": "#EEF2FF",
        "pill_violet_text": "#4338CA",
        "pill_emerald_bg": "#D1FAE5",
        "pill_emerald_text": "#047857",
        "glow_opacity": "0.08",
        "grid_opacity": "0.55",
        "wordmark_start": "#0F172A",
        "wordmark_mid": "#0284C7",
        "wordmark_end": "#4F46E5",
    },
}

GENESIS_STACK = [
    {"name": "Python", "pct": 34.0, "color": "#3572A5"},
    {"name": "TypeScript", "pct": 28.0, "color": "#3178C6"},
    {"name": "Rust", "pct": 16.0, "color": "#DEA584"},
    {"name": "Dart", "pct": 12.0, "color": "#00B4AB"},
    {"name": "SQL", "pct": 10.0, "color": "#E38C00"},
]

GENESIS_ROADMAP = [
    {"name": "novalis-cross-core", "tag": "CROSS-PLATFORM", "status": "ARCHITECTURE", "color": "#38BDF8"},
    {"name": "novalis-market-intel", "tag": "MARKET INTEL", "status": "R&D PIPELINE", "color": "#10B981"},
    {"name": "novalis-ai-runtime", "tag": "MISSION AI", "status": "INCUBATING", "color": "#818CF8"},
]

FALLBACK_MACRO = {
    "SPX": {
        "symbol": "SPX",
        "name": "S&P 500",
        "price": 5980.0,
        "change_pct": 0.42,
        "series": [5890, 5905, 5898, 5920, 5935, 5928, 5946, 5958, 5964, 5980],
        "live": False,
    },
    "GOLD": {
        "symbol": "GOLD",
        "name": "XAU/OZ",
        "price": 2740.0,
        "change_pct": 0.65,
        "series": [2690, 2702, 2698, 2710, 2718, 2714, 2722, 2731, 2728, 2740],
        "live": False,
    },
    "BTC": {
        "symbol": "BTC-USD",
        "name": "BITCOIN",
        "price": 92400.0,
        "change_pct": 1.85,
        "series": [88500, 89200, 89000, 90100, 90800, 90400, 91200, 91900, 91600, 92400],
        "live": False,
    },
}


# ---------------------------------------------------------------------------
# Network & API Utilities
# ---------------------------------------------------------------------------

def http_get_text(url: str, headers: dict[str, str] | None = None, timeout: int = 15) -> str:
    req_headers = {
        "User-Agent": "NOVALIS-Org-Telemetry-Engine/2.0",
        "Accept": "application/json,text/csv,*/*",
    }
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def graphql_request(query: str, variables: dict, token: str) -> dict:
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "NOVALIS-Org-Telemetry-Engine/2.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if "errors" in payload and not payload.get("data"):
        raise RuntimeError(f"GitHub GraphQL error: {payload['errors']}")
    return payload["data"]


def _parse_iso_dt(value: str | None) -> datetime.datetime | None:
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def build_weekly_velocity(push_dates: list[datetime.datetime], weeks: int = 16) -> list[int]:
    """Buckets repository commit/push timestamps into a 16-week activity series."""
    now = datetime.datetime.now(datetime.timezone.utc)
    buckets = [0] * weeks
    for dt in push_dates:
        delta_days = (now - dt).days
        if 0 <= delta_days < weeks * 7:
            week_idx = weeks - 1 - (delta_days // 7)
            if 0 <= week_idx < weeks:
                buckets[week_idx] += 1
    return buckets


def fetch_org_stats_graphql(org: str, token: str) -> dict:
    """Fetches rich organization metrics via GitHub GraphQL v4 API."""
    query = """
    query($login: String!, $cursor: String) {
      organization(login: $login) {
        name
        login
        description
        websiteUrl
        membersWithRole {
          totalCount
        }
        repositories(
          first: 100
          after: $cursor
          privacy: PUBLIC
          isFork: false
          orderBy: {field: PUSHED_AT, direction: DESC}
        ) {
          totalCount
          pageInfo {
            endCursor
            hasNextPage
          }
          nodes {
            name
            description
            url
            stargazerCount
            forkCount
            pushedAt
            isArchived
            primaryLanguage {
              name
              color
            }
            repositoryTopics(first: 5) {
              nodes {
                topic {
                  name
                }
              }
            }
            languages(first: 8, orderBy: {field: SIZE, direction: DESC}) {
              edges {
                size
                node {
                  name
                  color
                }
              }
            }
            defaultBranchRef {
              target {
                ... on Commit {
                  history(first: 40) {
                    totalCount
                    nodes {
                      committedDate
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    data = graphql_request(query, {"login": org, "cursor": None}, token)
    org_obj = data.get("organization")
    if not org_obj:
        raise RuntimeError(f"Organization '{org}' not found via GraphQL.")

    repos_conn = org_obj["repositories"]
    nodes = list(repos_conn.get("nodes") or [])
    while repos_conn.get("pageInfo", {}).get("hasNextPage"):
        next_data = graphql_request(
            query,
            {"login": org, "cursor": repos_conn["pageInfo"]["endCursor"]},
            token,
        )
        repos_conn = next_data["organization"]["repositories"]
        nodes.extend(repos_conn.get("nodes") or [])

    return _process_org_nodes(
        org=org_obj.get("login") or org,
        members_count=int((org_obj.get("membersWithRole") or {}).get("totalCount") or 1),
        repo_nodes=nodes,
        source="GRAPHQL",
    )


def fetch_org_stats_rest(org: str, token: str | None = None) -> dict:
    """Fallback fetcher using GitHub REST API for public org repositories."""
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    org_info = json.loads(http_get_text(f"{REST_API_URL}/orgs/{urllib.parse.quote(org)}", headers=headers))
    repos_raw = json.loads(
        http_get_text(
            f"{REST_API_URL}/orgs/{urllib.parse.quote(org)}/repos?type=public&sort=pushed&per_page=100",
            headers=headers,
        )
    )
    members_raw = []
    try:
        members_raw = json.loads(
            http_get_text(
                f"{REST_API_URL}/orgs/{urllib.parse.quote(org)}/public_members?per_page=100",
                headers=headers,
            )
        )
    except Exception:
        members_raw = []

    nodes = []
    for r in repos_raw:
        if r.get("fork"):
            continue
        lang_name = r.get("language")
        lang_edges = []
        if lang_name:
            lang_edges.append(
                {
                    "size": max(int(r.get("size") or 1), 1) * 1024,
                    "node": {
                        "name": lang_name,
                        "color": FALLBACK_LANG_COLORS.get(lang_name, "#38BDF8"),
                    },
                }
            )
        nodes.append(
            {
                "name": r.get("name", ""),
                "description": r.get("description") or "",
                "url": r.get("html_url") or f"https://github.com/{org}/{r.get('name', '')}",
                "stargazerCount": int(r.get("stargazers_count") or 0),
                "forkCount": int(r.get("forks_count") or 0),
                "pushedAt": r.get("pushed_at"),
                "isArchived": bool(r.get("archived")),
                "primaryLanguage": {
                    "name": lang_name,
                    "color": FALLBACK_LANG_COLORS.get(lang_name or "", "#38BDF8"),
                }
                if lang_name
                else None,
                "repositoryTopics": {
                    "nodes": [{"topic": {"name": t}} for t in (r.get("topics") or [])[:5]]
                },
                "languages": {"edges": lang_edges},
                "defaultBranchRef": None,
            }
        )

    return _process_org_nodes(
        org=org_info.get("login") or org,
        members_count=max(len(members_raw), 1),
        repo_nodes=nodes,
        source="REST",
    )


def _process_org_nodes(org: str, members_count: int, repo_nodes: list[dict], source: str) -> dict:
    product_repos = []
    lang_totals: dict[str, int] = {}
    lang_colors: dict[str, str] = {}
    commit_dates: list[datetime.datetime] = []
    total_commits = 0
    total_stars = 0
    total_forks = 0

    for node in repo_nodes:
        name = node.get("name") or ""
        if not name or node.get("isArchived"):
            continue

        stars = int(node.get("stargazerCount") or 0)
        forks = int(node.get("forkCount") or 0)
        total_stars += stars
        total_forks += forks

        # Track commits across all repos (including .github for velocity pulse)
        branch_ref = node.get("defaultBranchRef") or {}
        target = branch_ref.get("target") or {}
        history = target.get("history") or {}
        repo_commits = int(history.get("totalCount") or 0)
        total_commits += repo_commits
        for cnode in history.get("nodes") or []:
            dt = _parse_iso_dt(cnode.get("committedDate"))
            if dt:
                commit_dates.append(dt)
        if not history.get("nodes"):
            pdt = _parse_iso_dt(node.get("pushedAt"))
            if pdt:
                commit_dates.append(pdt)

        # Exclude special org metadata repo from product showcase & primary stack skew
        if name == ".github":
            continue

        for edge in (node.get("languages") or {}).get("edges") or []:
            lname = edge["node"]["name"]
            lsize = int(edge.get("size") or 0)
            lcolor = edge["node"].get("color") or FALLBACK_LANG_COLORS.get(lname, "#64748B")
            lang_totals[lname] = lang_totals.get(lname, 0) + lsize
            lang_colors[lname] = lcolor

        plang = node.get("primaryLanguage") or {}
        topics = [
            t["topic"]["name"]
            for t in ((node.get("repositoryTopics") or {}).get("nodes") or [])
            if t.get("topic") and t["topic"].get("name")
        ]
        product_repos.append(
            {
                "name": name,
                "description": (node.get("description") or "").strip(),
                "url": node.get("url") or f"https://github.com/{org}/{name}",
                "stars": stars,
                "forks": forks,
                "pushed_at": node.get("pushedAt") or "",
                "language": plang.get("name") or "Multi-Stack",
                "language_color": plang.get("color")
                or FALLBACK_LANG_COLORS.get(plang.get("name") or "", "#38BDF8"),
                "topics": topics,
            }
        )

    # Sort showcase repos by stars desc, then pushed_at desc
    product_repos.sort(key=lambda r: (r["stars"], r["pushed_at"]), reverse=True)

    total_lang_bytes = sum(lang_totals.values())
    languages = []
    if total_lang_bytes > 0:
        for lname, lsize in sorted(lang_totals.items(), key=lambda x: x[1], reverse=True)[:5]:
            languages.append(
                {
                    "name": LANG_DISPLAY_NAMES.get(lname, lname),
                    "pct": round((lsize / total_lang_bytes) * 100.0, 1),
                    "color": lang_colors.get(lname, "#38BDF8"),
                }
            )

    velocity = build_weekly_velocity(commit_dates, weeks=16)
    is_genesis = len(product_repos) == 0

    return {
        "org": org,
        "live": True,
        "source": source,
        "genesis": is_genesis,
        "public_repos": len(product_repos),
        "all_repos": len(repo_nodes),
        "total_stars": total_stars,
        "total_forks": total_forks,
        "total_commits": total_commits,
        "members": max(members_count, 1),
        "languages": languages if languages else GENESIS_STACK,
        "velocity": velocity if sum(velocity) > 0 else [2, 3, 4, 3, 6, 5, 8, 7, 9, 11, 10, 13, 12, 15, 16, 19],
        "repos": product_repos,
        "updated_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


def offline_genesis_stats(org: str) -> dict:
    return {
        "org": org,
        "live": False,
        "source": "GENESIS",
        "genesis": True,
        "public_repos": 0,
        "all_repos": 1,
        "total_stars": 0,
        "total_forks": 0,
        "total_commits": 0,
        "members": 1,
        "languages": GENESIS_STACK,
        "velocity": [2, 3, 4, 4, 6, 5, 8, 7, 10, 11, 12, 14, 13, 16, 18, 21],
        "repos": [],
        "updated_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


# ---------------------------------------------------------------------------
# Live Market Intelligence Fetchers (Multi-Source Resilient)
# ---------------------------------------------------------------------------

def fetch_yf_ticker(symbol: str) -> dict | None:
    try:
        import yfinance as yf  # type: ignore

        hist = yf.Ticker(symbol).history(period="1mo", interval="1d")
        if hist is None or hist.empty or "Close" not in hist:
            return None
        closes = [float(v) for v in hist["Close"].dropna().tolist()]
        if len(closes) < 2:
            return None
        latest, prev = closes[-1], closes[-2]
        pct = ((latest - prev) / prev * 100.0) if prev else 0.0
        return {"price": latest, "change_pct": pct, "series": closes[-14:], "live": True}
    except Exception:
        return None


def fetch_yahoo_chart(symbol: str) -> dict | None:
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}"
        "?range=1mo&interval=1d"
    )
    try:
        payload = json.loads(http_get_text(url, timeout=12))
        result = payload["chart"]["result"][0]
        raw_closes = result["indicators"]["quote"][0]["close"]
        closes = [float(c) for c in raw_closes if c is not None]
        if len(closes) < 2:
            return None
        latest, prev = closes[-1], closes[-2]
        pct = ((latest - prev) / prev * 100.0) if prev else 0.0
        return {"price": latest, "change_pct": pct, "series": closes[-14:], "live": True}
    except Exception:
        return None


def fetch_stooq_ticker(stooq_sym: str) -> dict | None:
    url = f"https://stooq.com/q/d/l/?s={urllib.parse.quote(stooq_sym)}&i=d"
    try:
        text = http_get_text(url, timeout=12)
        rows = list(csv.DictReader(io.StringIO(text)))
        closes = [float(r["Close"]) for r in rows[-20:] if r.get("Close") and r["Close"] != "N/D"]
        if len(closes) < 2:
            return None
        latest, prev = closes[-1], closes[-2]
        pct = ((latest - prev) / prev * 100.0) if prev else 0.0
        return {"price": latest, "change_pct": pct, "series": closes[-14:], "live": True}
    except Exception:
        return None


def fetch_coingecko_btc() -> dict | None:
    url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=14&interval=daily"
    try:
        data = json.loads(http_get_text(url, timeout=12))
        prices = [float(p[1]) for p in data.get("prices", []) if len(p) >= 2]
        if len(prices) < 2:
            return None
        latest, prev = prices[-1], prices[-2]
        pct = ((latest - prev) / prev * 100.0) if prev else 0.0
        return {"price": latest, "change_pct": pct, "series": prices[-14:], "live": True}
    except Exception:
        return None


def fetch_macro_signals(offline: bool = False) -> dict:
    result = {k: dict(v) for k, v in FALLBACK_MACRO.items()}
    if offline:
        return result

    sources = {
        "SPX": [
            lambda: fetch_yf_ticker("^GSPC"),
            lambda: fetch_yahoo_chart("^GSPC"),
            lambda: fetch_stooq_ticker("^spx"),
        ],
        "GOLD": [
            lambda: fetch_yf_ticker("GC=F"),
            lambda: fetch_yahoo_chart("GC=F"),
            lambda: fetch_stooq_ticker("xauusd"),
        ],
        "BTC": [
            lambda: fetch_yf_ticker("BTC-USD"),
            lambda: fetch_yahoo_chart("BTC-USD"),
            lambda: fetch_coingecko_btc(),
        ],
    }

    for key, fetchers in sources.items():
        for fn in fetchers:
            data = fn()
            if data:
                result[key].update(data)
                break
    return result


# ---------------------------------------------------------------------------
# SVG Geometry & Formatting Helpers
# ---------------------------------------------------------------------------

def format_compact(val: int) -> str:
    if val >= 1_000_000:
        return f"{val / 1_000_000:.1f}M"
    if val >= 10_000:
        return f"{val / 1_000:.1f}K"
    return f"{val:,}"


def truncate_text(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def ema_series(values: list[float], period: int = 4) -> list[float]:
    if not values:
        return []
    alpha = 2.0 / (period + 1.0)
    out = [float(values[0])]
    for v in values[1:]:
        out.append(alpha * float(v) + (1.0 - alpha) * out[-1])
    return out


def smooth_svg_path(points: list[tuple[float, float]]) -> str:
    """Converts (x, y) coordinates into a smooth Catmull-Rom cubic Bezier SVG path."""
    if not points:
        return ""
    if len(points) == 1:
        return f"M {points[0][0]:.1f} {points[0][1]:.1f}"
    if len(points) == 2:
        return f"M {points[0][0]:.1f} {points[0][1]:.1f} L {points[1][0]:.1f} {points[1][1]:.1f}"

    parts = [f"M {points[0][0]:.1f} {points[0][1]:.1f}"]
    for i in range(len(points) - 1):
        p0 = points[max(i - 1, 0)]
        p1 = points[i]
        p2 = points[i + 1]
        p3 = points[min(i + 2, len(points) - 1)]
        c1x = p1[0] + (p2[0] - p0[0]) / 6.0
        c1y = p1[1] + (p2[1] - p0[1]) / 6.0
        c2x = p2[0] - (p3[0] - p1[0]) / 6.0
        c2y = p2[1] - (p3[1] - p1[1]) / 6.0
        parts.append(f"C {c1x:.1f} {c1y:.1f}, {c2x:.1f} {c2y:.1f}, {p2[0]:.1f} {p2[1]:.1f}")
    return " ".join(parts)


def sparkline_svg(
    values: list[float],
    x0: float,
    y0: float,
    w: float,
    h: float,
    stroke_color: str,
    grad_id: str,
) -> str:
    if len(values) < 2:
        values = [1.0, 1.0]
    lo = min(values)
    hi = max(values)
    span = (hi - lo) if (hi - lo) > 1e-9 else 1.0
    pts: list[tuple[float, float]] = []
    n = len(values)
    for i, val in enumerate(values):
        px = x0 + (i / (n - 1)) * w
        py = y0 + h - ((val - lo) / span) * (h - 6.0) - 3.0
        pts.append((px, py))

    curve = smooth_svg_path(pts)
    area = f"{curve} L {pts[-1][0]:.1f} {y0 + h:.1f} L {pts[0][0]:.1f} {y0 + h:.1f} Z"
    end_x, end_y = pts[-1]
    return (
        f'<path d="{area}" fill="url(#{grad_id})"/>'
        f'<path d="{curve}" fill="none" stroke="{stroke_color}" stroke-width="1.8" stroke-linecap="round"/>'
        f'<circle cx="{end_x:.1f}" cy="{end_y:.1f}" r="2.6" fill="{stroke_color}"/>'
    )


def corner_brackets(x: float, y: float, w: float, h: float, color: str, size: float = 10.0) -> str:
    x2, y2 = x + w, y + h
    return (
        f'<path d="M {x} {y + size} L {x} {y} L {x + size} {y} '
        f'M {x2 - size} {y} L {x2} {y} L {x2} {y + size} '
        f'M {x} {y2 - size} L {x} {y2} L {x + size} {y2} '
        f'M {x2 - size} {y2} L {x2} {y2} L {x2} {y2 - size}" '
        f'fill="none" stroke="{color}" stroke-width="1.4" stroke-opacity="0.7" stroke-linecap="round"/>'
    )


# ---------------------------------------------------------------------------
# SVG 1: Hero Command Center Banner (960 x 276)
# ---------------------------------------------------------------------------

def render_hero_command(stats: dict, theme_name: str) -> str:
    t = THEMES[theme_name]
    org = escape(stats["org"])

    # Hexagon points centered at (126, 134), r=28
    cx, cy, r_hex = 126.0, 134.0, 28.0
    hex_pts = " ".join(
        f"{cx + r_hex * math.cos(math.radians(60 * i - 30)):.1f},"
        f"{cy + r_hex * math.sin(math.radians(60 * i - 30)):.1f}"
        for i in range(6)
    )

    pillars = [
        (28, t["cyan"], "01 // CROSS-PLATFORM APPS", "Web · iOS · Android · Desktop · Edge"),
        (335, t["emerald"], "02 // MARKET INTELLIGENCE", "Quant Pipelines · Live Signals · Macro"),
        (642, t["violet"], "03 // MISSION-CRITICAL AI", "Neural Models · Agents · High-Reliability"),
    ]
    pillar_cards = []
    for px, pcolor, ptitle, psub in pillars:
        pillar_cards.append(
            f"""  <rect x="{px}" y="212" width="290" height="46" rx="9" fill="{t['bg_panel']}" stroke="{t['border']}" stroke-width="1"/>
  <rect x="{px}" y="220" width="3" height="30" rx="1.5" fill="{pcolor}"/>
  <circle cx="{px + 18}" cy="229" r="3" fill="{pcolor}">
    <animate attributeName="opacity" values="1;0.35;1" dur="2.6s" repeatCount="indefinite"/>
  </circle>
  <text x="{px + 29}" y="233" fill="{t['text_primary']}" font-size="10.5" font-weight="700" class="mono">{ptitle}</text>
  <text x="{px + 18}" y="249" fill="{t['text_secondary']}" font-size="10" class="sans">{psub}</text>"""
        )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 276" width="960" height="276" role="img" aria-label="NOVALIS Organization Command Banner">
  <style>
    .sans {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, Helvetica, Arial, sans-serif; }}
    .mono {{ font-family: 'JetBrains Mono', 'Fira Code', 'SF Mono', Consolas, monospace; }}
  </style>
  <defs>
    <linearGradient id="heroBg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{t['bg_outer']}"/>
      <stop offset="100%" stop-color="{t['bg_outer_end']}"/>
    </linearGradient>
    <radialGradient id="glowCyan" cx="22%" cy="46%" r="42%">
      <stop offset="0%" stop-color="{t['cyan']}" stop-opacity="{t['glow_opacity']}"/>
      <stop offset="100%" stop-color="{t['cyan']}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="glowViolet" cx="82%" cy="38%" r="42%">
      <stop offset="0%" stop-color="{t['violet']}" stop-opacity="{t['glow_opacity']}"/>
      <stop offset="100%" stop-color="{t['violet']}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="wordmarkGrad" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{t['wordmark_start']}"/>
      <stop offset="58%" stop-color="{t['wordmark_mid']}"/>
      <stop offset="100%" stop-color="{t['wordmark_end']}"/>
    </linearGradient>
    <linearGradient id="emblemRing" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{t['cyan']}"/>
      <stop offset="50%" stop-color="{t['violet']}"/>
      <stop offset="100%" stop-color="{t['emerald']}"/>
    </linearGradient>
    <linearGradient id="scanBar" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{t['cyan']}" stop-opacity="0"/>
      <stop offset="50%" stop-color="{t['cyan']}" stop-opacity="0.95"/>
      <stop offset="100%" stop-color="{t['violet']}" stop-opacity="0"/>
    </linearGradient>
    <pattern id="heroGrid" width="32" height="32" patternUnits="userSpaceOnUse">
      <path d="M 32 0 L 0 0 0 32" fill="none" stroke="{t['grid']}" stroke-width="0.7" stroke-opacity="{t['grid_opacity']}"/>
    </pattern>
    <clipPath id="heroClip">
      <rect x="0.5" y="0.5" width="959" height="275" rx="16"/>
    </clipPath>
    <clipPath id="scanClip">
      <rect x="218" y="138" width="460" height="3" rx="1.5"/>
    </clipPath>
  </defs>

  <g clip-path="url(#heroClip)">
    <rect x="0" y="0" width="960" height="276" fill="url(#heroBg)"/>
    <rect x="0" y="0" width="960" height="276" fill="url(#heroGrid)"/>
    <rect x="0" y="0" width="960" height="276" fill="url(#glowCyan)"/>
    <rect x="0" y="0" width="960" height="276" fill="url(#glowViolet)"/>
  </g>
  <rect x="0.5" y="0.5" width="959" height="275" rx="16" fill="none" stroke="{t['border']}" stroke-width="1"/>
  {corner_brackets(14, 14, 932, 248, t['cyan'], 9)}

  <!-- Top Telemetry Header -->
  <circle cx="34" cy="29" r="3.6" fill="{t['emerald']}">
    <animate attributeName="opacity" values="1;0.25;1" dur="2.1s" repeatCount="indefinite"/>
  </circle>
  <text x="46" y="33" fill="{t['emerald']}" font-size="10" font-weight="700" class="mono">SYSTEMS OPERATIONAL</text>
  <text x="480" y="33" text-anchor="middle" fill="{t['text_muted']}" font-size="10" font-weight="600" class="mono">NOVALIS  //  ENGINEERING &amp; INTELLIGENCE ORGANIZATION</text>
  <text x="926" y="33" text-anchor="end" fill="{t['text_secondary']}" font-size="10" font-weight="600" class="mono">GITHUB.COM/{org}</text>
  <line x1="28" y1="46" x2="932" y2="46" stroke="{t['border']}" stroke-width="1"/>

  <!-- Left Orbital Emblem -->
  <g>
    <circle cx="{cx:.0f}" cy="{cy:.0f}" r="56" fill="none" stroke="{t['border_bright']}" stroke-width="1" stroke-dasharray="3,5" stroke-opacity="0.75">
      <animateTransform attributeName="transform" type="rotate" from="0 {cx:.0f} {cy:.0f}" to="360 {cx:.0f} {cy:.0f}" dur="36s" repeatCount="indefinite"/>
    </circle>
    <g>
      <animateTransform attributeName="transform" type="rotate" from="360 {cx:.0f} {cy:.0f}" to="0 {cx:.0f} {cy:.0f}" dur="22s" repeatCount="indefinite"/>
      <circle cx="{cx:.0f}" cy="{cy:.0f}" r="42" fill="none" stroke="url(#emblemRing)" stroke-width="1.8" stroke-dasharray="48 18 22 18"/>
      <circle cx="{cx + 42:.0f}" cy="{cy:.0f}" r="3.2" fill="{t['cyan']}"/>
      <circle cx="{cx - 42:.0f}" cy="{cy:.0f}" r="2.8" fill="{t['violet']}"/>
    </g>
    <polygon points="{hex_pts}" fill="{t['bg_panel']}" stroke="url(#emblemRing)" stroke-width="1.8"/>
    <path d="M 116 146 L 116 122 L 136 146 L 136 122" fill="none" stroke="{t['text_primary']}" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="116" cy="122" r="2.4" fill="{t['cyan']}"/>
    <circle cx="136" cy="146" r="2.4" fill="{t['emerald']}"/>
    <circle cx="{cx:.0f}" cy="{cy:.0f}" r="14" fill="{t['cyan']}" fill-opacity="0.10">
      <animate attributeName="r" values="10;19;10" dur="3.4s" repeatCount="indefinite"/>
      <animate attributeName="fill-opacity" values="0.14;0.02;0.14" dur="3.4s" repeatCount="indefinite"/>
    </circle>
  </g>

  <!-- Brand Lockup & Mission Copy -->
  <rect x="218" y="64" width="248" height="22" rx="5" fill="{t['pill_bg']}" stroke="{t['cyan']}" stroke-width="0.7" stroke-opacity="0.45"/>
  <text x="342" y="79" text-anchor="middle" fill="{t['pill_text']}" font-size="9.5" font-weight="700" class="mono">APPLICATIONS · INTELLIGENCE · AI</text>

  <rect x="478" y="64" width="136" height="22" rx="5" fill="{t['pill_violet_bg']}" stroke="{t['violet']}" stroke-width="0.7" stroke-opacity="0.45"/>
  <text x="546" y="79" text-anchor="middle" fill="{t['pill_violet_text']}" font-size="9.5" font-weight="700" class="mono">DEEP-TECH LAB</text>

  <text x="218" y="128" fill="url(#wordmarkGrad)" font-size="42" font-weight="800" letter-spacing="7" class="sans">NOVALIS</text>

  <!-- Animated Signal Bar -->
  <rect x="218" y="138" width="460" height="3" rx="1.5" fill="{t['border']}"/>
  <g clip-path="url(#scanClip)">
    <rect x="118" y="138" width="140" height="3" fill="url(#scanBar)">
      <animate attributeName="x" values="118;678;118" dur="4.6s" repeatCount="indefinite"/>
    </rect>
  </g>

  <text x="218" y="166" fill="{t['text_primary']}" font-size="14.2" font-weight="600" class="sans">Building cross-platform apps, market intelligence, and mission-critical AI</text>
  <text x="218" y="187" fill="{t['text_secondary']}" font-size="13.5" font-weight="500" class="sans">to solve complex real-world problems — engineered for scale, clarity, and reliability.</text>

  <!-- Bottom 3-Pillar Signal Strip -->
{chr(10).join(pillar_cards)}
</svg>
"""


# ---------------------------------------------------------------------------
# SVG 2: System Architecture Blueprint (960 x 326)
# ---------------------------------------------------------------------------

def render_architecture_pillars(theme_name: str) -> str:
    t = THEMES[theme_name]

    modules = [
        {
            "x": 28,
            "num": "01",
            "color": t["cyan"],
            "pill_bg": t["pill_bg"],
            "pill_text": t["pill_text"],
            "title": "CROSS-PLATFORM APPS",
            "subtitle": "Unified Web, Mobile & Desktop Systems",
            "bullets": [
                "Reactive Web & Enterprise Interfaces",
                "Native iOS, Android & Desktop Builds",
                "High-Throughput APIs & Edge Delivery",
            ],
            "stack": "TS · NEXT.JS · FLUTTER · RUST",
            "path": "M 173 216 C 173 242, 340 232, 340 256",
            "dur": "3.1s",
        },
        {
            "x": 335,
            "num": "02",
            "color": t["emerald"],
            "pill_bg": t["pill_emerald_bg"],
            "pill_text": t["pill_emerald_text"],
            "title": "MARKET INTELLIGENCE",
            "subtitle": "Quantitative & Real-Time Decision Engines",
            "bullets": [
                "Streaming Market & Macro Data Feeds",
                "Institutional Flow & Volatility Signals",
                "Resilient Low-Latency Analytics Pipelines",
            ],
            "stack": "PYTHON · FASTAPI · POSTGRES",
            "path": "M 480 216 L 480 256",
            "dur": "2.4s",
        },
        {
            "x": 642,
            "num": "03",
            "color": t["violet"],
            "pill_bg": t["pill_violet_bg"],
            "pill_text": t["pill_violet_text"],
            "title": "MISSION-CRITICAL AI",
            "subtitle": "Deterministic, Production-Grade Intelligence",
            "bullets": [
                "Specialized Neural & Predictive Models",
                "Agentic Workflows with Strict Guardrails",
                "Continuous Evaluation & Zero-Drift Ops",
            ],
            "stack": "PYTORCH · LLMS · MLOPS · GPU",
            "path": "M 787 216 C 787 242, 620 232, 620 256",
            "dur": "3.4s",
        },
    ]

    cards_svg = []
    conduits_svg = []
    for m in modules:
        x = m["x"]
        col = m["color"]
        cards_svg.append(
            f"""  <rect x="{x}" y="52" width="290" height="164" rx="11" fill="{t['bg_panel']}" stroke="{t['border']}" stroke-width="1"/>
  <rect x="{x}" y="52" width="290" height="3.5" rx="1.75" fill="{col}"/>
  <rect x="{x + 14}" y="66" width="30" height="20" rx="5" fill="{m['pill_bg']}" stroke="{col}" stroke-width="0.7" stroke-opacity="0.45"/>
  <text x="{x + 29}" y="80" text-anchor="middle" fill="{m['pill_text']}" font-size="10" font-weight="800" class="mono">{m['num']}</text>
  <text x="{x + 54}" y="80" fill="{t['text_primary']}" font-size="12" font-weight="800" class="mono">{escape(m['title'])}</text>
  <text x="{x + 14}" y="100" fill="{t['text_secondary']}" font-size="10.2" class="sans">{escape(m['subtitle'])}</text>
  <line x1="{x + 14}" y1="110" x2="{x + 276}" y2="110" stroke="{t['border']}" stroke-width="1"/>
  <text x="{x + 16}" y="129" fill="{col}" font-size="11" font-weight="700" class="mono">›</text>
  <text x="{x + 28}" y="129" fill="{t['text_primary']}" font-size="10.6" class="sans">{escape(m['bullets'][0])}</text>
  <text x="{x + 16}" y="149" fill="{col}" font-size="11" font-weight="700" class="mono">›</text>
  <text x="{x + 28}" y="149" fill="{t['text_primary']}" font-size="10.6" class="sans">{escape(m['bullets'][1])}</text>
  <text x="{x + 16}" y="169" fill="{col}" font-size="11" font-weight="700" class="mono">›</text>
  <text x="{x + 28}" y="169" fill="{t['text_primary']}" font-size="10.6" class="sans">{escape(m['bullets'][2])}</text>
  <rect x="{x + 14}" y="182" width="262" height="22" rx="5" fill="{t['bg_subpanel']}" stroke="{t['border']}" stroke-width="0.8"/>
  <text x="{x + 145}" y="196.5" text-anchor="middle" fill="{t['text_secondary']}" font-size="9.3" font-weight="700" class="mono">{escape(m['stack'])}</text>"""
        )

        conduits_svg.append(
            f"""  <path d="{m['path']}" fill="none" stroke="{col}" stroke-width="1.6" stroke-opacity="0.45" stroke-dasharray="4,4"/>
  <circle r="3.2" fill="{col}">
    <animateMotion dur="{m['dur']}" repeatCount="indefinite" path="{m['path']}"/>
  </circle>
  <circle cx="{x + 145}" cy="216" r="3.2" fill="{col}"/>"""
        )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 326" width="960" height="326" role="img" aria-label="NOVALIS Three-Pillar System Architecture Blueprint">
  <style>
    .sans {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, Helvetica, Arial, sans-serif; }}
    .mono {{ font-family: 'JetBrains Mono', 'Fira Code', 'SF Mono', Consolas, monospace; }}
  </style>
  <defs>
    <linearGradient id="archBg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{t['bg_outer']}"/>
      <stop offset="100%" stop-color="{t['bg_outer_end']}"/>
    </linearGradient>
    <linearGradient id="busGrad" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{t['cyan']}" stop-opacity="0.14"/>
      <stop offset="50%" stop-color="{t['emerald']}" stop-opacity="0.14"/>
      <stop offset="100%" stop-color="{t['violet']}" stop-opacity="0.14"/>
    </linearGradient>
    <linearGradient id="busBorder" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{t['cyan']}"/>
      <stop offset="50%" stop-color="{t['emerald']}"/>
      <stop offset="100%" stop-color="{t['violet']}"/>
    </linearGradient>
  </defs>

  <rect x="0.5" y="0.5" width="959" height="325" rx="16" fill="url(#archBg)" stroke="{t['border']}" stroke-width="1"/>

  <!-- Header -->
  <circle cx="34" cy="27" r="3.5" fill="{t['cyan']}">
    <animate attributeName="opacity" values="1;0.3;1" dur="2.2s" repeatCount="indefinite"/>
  </circle>
  <text x="46" y="31" fill="{t['text_primary']}" font-size="11.5" font-weight="800" class="mono">SYSTEM ARCHITECTURE // THREE-PILLAR ENGINEERING MATRIX</text>
  <rect x="738" y="16" width="194" height="20" rx="5" fill="{t['bg_panel']}" stroke="{t['border']}" stroke-width="0.9"/>
  <text x="835" y="29.5" text-anchor="middle" fill="{t['text_secondary']}" font-size="9.2" font-weight="700" class="mono">PRODUCTION · MULTI-DOMAIN</text>

  <!-- 3 Pillar Cards -->
{chr(10).join(cards_svg)}

  <!-- Animated Signal Convergence Conduits -->
{chr(10).join(conduits_svg)}

  <!-- Unified Real-World Execution Bus -->
  <rect x="28" y="256" width="904" height="52" rx="10" fill="{t['bg_panel']}" stroke="url(#busBorder)" stroke-width="1.2"/>
  <rect x="29" y="257" width="902" height="50" rx="9" fill="url(#busGrad)"/>
  <circle cx="340" cy="256" r="3.2" fill="{t['cyan']}"/>
  <circle cx="480" cy="256" r="3.2" fill="{t['emerald']}"/>
  <circle cx="620" cy="256" r="3.2" fill="{t['violet']}"/>

  <rect x="44" y="271" width="164" height="22" rx="5" fill="{t['bg_outer']}" stroke="{t['border_bright']}" stroke-width="0.8"/>
  <text x="126" y="285.5" text-anchor="middle" fill="{t['cyan']}" font-size="9.5" font-weight="800" class="mono">CORE EXECUTION LAYER</text>

  <text x="516" y="286" text-anchor="middle" fill="{t['text_primary']}" font-size="11" font-weight="700" class="mono">LOW-LATENCY APPS  ⇄  DECISION INTELLIGENCE  ⇄  AUTONOMOUS AI</text>

  <circle cx="808" cy="282" r="3.4" fill="{t['emerald']}">
    <animate attributeName="opacity" values="1;0.25;1" dur="1.9s" repeatCount="indefinite"/>
  </circle>
  <text x="819" y="285.5" fill="{t['emerald']}" font-size="9.8" font-weight="800" class="mono">REAL-WORLD OPS</text>
</svg>
"""


# ---------------------------------------------------------------------------
# SVG 3: Organization Live Engineering Telemetry Console (960 x 346)
# ---------------------------------------------------------------------------

def render_org_telemetry(stats: dict, theme_name: str) -> str:
    t = THEMES[theme_name]
    is_genesis = bool(stats.get("genesis", True))
    org = escape(stats["org"])
    updated = escape(stats["updated_utc"])

    status_label = "GENESIS LAUNCHPAD" if is_genesis else f"LIVE · {stats.get('source', 'API')}"
    status_color = t["violet"] if is_genesis else t["emerald"]
    status_bg = t["pill_violet_bg"] if is_genesis else t["pill_emerald_bg"]

    if is_genesis:
        kpis = [
            ("ORG STATUS", "VERIFIED", f"github.com/{org}", t["emerald"]),
            ("CORE PILLARS", "03", "Apps · Market Intel · AI", t["cyan"]),
            ("RELEASE TRACK", "GENESIS", "Foundational R&D Active", t["violet"]),
            ("STANDARDS", "100%", "CI/CD · Security · Docs", t["amber"]),
        ]
        chart_title = "ARCHITECTURE READINESS // MULTI-PILLAR R&D TRAJECTORY"
        chart_badge = "GENESIS PHASE"
    else:
        kpis = [
            ("PUBLIC REPOS", format_compact(stats["public_repos"]), "Active Org Repositories", t["cyan"]),
            ("TOTAL STARS", format_compact(stats["total_stars"]), f"{format_compact(stats['total_forks'])} Community Forks", t["amber"]),
            ("COMMIT PULSE", format_compact(max(stats["total_commits"], sum(stats["velocity"]))), "Tracked Org Commits", t["emerald"]),
            ("CORE TEAM", format_compact(stats["members"]), "Builders & Maintainers", t["violet"]),
        ]
        chart_title = "ENGINEERING VELOCITY // 16-WEEK ORG ACTIVITY CURVE"
        chart_badge = "EMA-4 SMOOTHED"

    # 4 KPI Tiles: width=214, gap=16 -> 28..932
    kpi_svg = []
    for idx, (label, value, sub, accent) in enumerate(kpis):
        kx = 28 + idx * 230
        kpi_svg.append(
            f"""  <rect x="{kx}" y="54" width="214" height="68" rx="10" fill="{t['bg_panel']}" stroke="{t['border']}" stroke-width="1"/>
  <rect x="{kx + 12}" y="66" width="3" height="44" rx="1.5" fill="{accent}"/>
  <text x="{kx + 24}" y="76" fill="{t['text_muted']}" font-size="9.5" font-weight="700" class="mono">{label}</text>
  <text x="{kx + 24}" y="100" fill="{t['text_primary']}" font-size="20" font-weight="800" class="mono">{escape(str(value))}</text>
  <text x="{kx + 24}" y="114" fill="{t['text_secondary']}" font-size="9.5" class="sans">{escape(sub)}</text>"""
        )

    # Left Chart Panel: x=28, y=136, width=548, height=160
    vel = [float(v) for v in stats["velocity"]]
    ema = ema_series(vel, period=4)
    cx0, cy0, cw, ch = 46.0, 174.0, 512.0, 102.0
    max_v = max(max(vel), max(ema), 1.0) * 1.15
    n_pts = len(vel)

    # Gridlines
    grid_lines = []
    for g in range(4):
        gy = cy0 + (g / 3.0) * ch
        grid_lines.append(
            f'  <line x1="{cx0:.1f}" y1="{gy:.1f}" x2="{cx0 + cw:.1f}" y2="{gy:.1f}" stroke="{t["grid"]}" stroke-width="0.9" stroke-dasharray="3,4"/>'
        )

    # Bars + EMA smooth curve
    bar_w = (cw / n_pts) * 0.46
    bars_svg = []
    vel_pts: list[tuple[float, float]] = []
    ema_pts: list[tuple[float, float]] = []
    for i in range(n_pts):
        px = cx0 + (i + 0.5) * (cw / n_pts)
        bh = max((vel[i] / max_v) * (ch - 8.0), 3.0)
        by = cy0 + ch - bh
        bars_svg.append(
            f'  <rect x="{px - bar_w / 2:.1f}" y="{by:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" rx="2.5" fill="{t["cyan"]}" fill-opacity="0.28"/>'
        )
        vel_pts.append((px, by))
        ey = cy0 + ch - max((ema[i] / max_v) * (ch - 8.0), 3.0)
        ema_pts.append((px, ey))

    ema_curve = smooth_svg_path(ema_pts)
    ema_area = f"{ema_curve} L {ema_pts[-1][0]:.1f} {cy0 + ch:.1f} L {ema_pts[0][0]:.1f} {cy0 + ch:.1f} Z"
    end_ex, end_ey = ema_pts[-1]

    # Right Panel: x=592, y=136, width=340, height=160
    # Top: Stack Allocation bar + legend
    langs = stats["languages"][:5]
    bar_x, bar_y, bar_total_w = 608.0, 168.0, 308.0
    total_pct = sum(float(l["pct"]) for l in langs) or 100.0
    lang_segs = []
    lang_legend = []
    cur_x = bar_x
    for idx, lang in enumerate(langs):
        seg_w = (float(lang["pct"]) / total_pct) * bar_total_w
        if idx == len(langs) - 1:
            seg_w = max(bar_x + bar_total_w - cur_x, 0.0)
        lang_segs.append(
            f'  <rect x="{cur_x:.1f}" y="{bar_y:.1f}" width="{max(seg_w - 1.5, 1.5):.1f}" height="8" rx="2" fill="{lang["color"]}"/>'
        )
        cur_x += seg_w

        col_idx = idx % 3
        row_idx = idx // 3
        lx = 608 + col_idx * 105
        ly = 191 + row_idx * 16
        lang_legend.append(
            f'  <circle cx="{lx + 4}" cy="{ly - 3}" r="3.2" fill="{lang["color"]}"/>'
            f'  <text x="{lx + 12}" y="{ly}" fill="{t["text_secondary"]}" font-size="9.3" font-weight="600" class="mono">{escape(truncate_text(lang["name"], 9))} {lang["pct"]:.0f}%</text>'
        )

    # Bottom half of right panel: Active Repos or Genesis Tracks
    repo_rows = []
    if is_genesis:
        list_header = "INCUBATING FLAGSHIP TRACKS"
        for idx, item in enumerate(GENESIS_ROADMAP):
            ry = 244 + idx * 17
            repo_rows.append(
                f'  <circle cx="613" cy="{ry - 3}" r="3" fill="{item["color"]}"/>'
                f'  <text x="623" y="{ry}" fill="{t["text_primary"]}" font-size="9.8" font-weight="700" class="mono">{escape(item["name"])}</text>'
                f'  <text x="916" y="{ry}" text-anchor="end" fill="{item["color"]}" font-size="8.8" font-weight="700" class="mono">{escape(item["status"])}</text>'
            )
    else:
        list_header = "ACTIVE PUBLIC REPOSITORIES"
        for idx, repo in enumerate(stats["repos"][:3]):
            ry = 244 + idx * 17
            rname = truncate_text(repo["name"], 22)
            repo_rows.append(
                f'  <circle cx="613" cy="{ry - 3}" r="3" fill="{repo["language_color"]}"/>'
                f'  <text x="623" y="{ry}" fill="{t["text_primary"]}" font-size="9.8" font-weight="700" class="mono">{escape(rname)}</text>'
                f'  <text x="916" y="{ry}" text-anchor="end" fill="{t["text_secondary"]}" font-size="9" font-weight="600" class="mono">★ {repo["stars"]} · {escape(truncate_text(repo["language"], 10))}</text>'
            )

    ticker_text = (
        f"ORG: {stats['org']}  //  MODE: {'GENESIS LAUNCHPAD' if is_genesis else 'LIVE PRODUCTION'}  //  "
        f"PILLARS: CROSS-PLATFORM · MARKET INTEL · AI  //  AUTO-SYNC: 6H GITHUB ACTIONS"
    )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 346" width="960" height="346" role="img" aria-label="NOVALIS Organization Engineering Telemetry Console">
  <style>
    .sans {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, Helvetica, Arial, sans-serif; }}
    .mono {{ font-family: 'JetBrains Mono', 'Fira Code', 'SF Mono', Consolas, monospace; }}
  </style>
  <defs>
    <linearGradient id="telBg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{t['bg_outer']}"/>
      <stop offset="100%" stop-color="{t['bg_outer_end']}"/>
    </linearGradient>
    <linearGradient id="velArea" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{t['violet']}" stop-opacity="0.34"/>
      <stop offset="100%" stop-color="{t['cyan']}" stop-opacity="0.02"/>
    </linearGradient>
    <linearGradient id="velLine" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{t['cyan']}"/>
      <stop offset="100%" stop-color="{t['violet']}"/>
    </linearGradient>
  </defs>

  <rect x="0.5" y="0.5" width="959" height="345" rx="16" fill="url(#telBg)" stroke="{t['border']}" stroke-width="1"/>

  <!-- Top Header -->
  <circle cx="34" cy="27" r="3.5" fill="{status_color}">
    <animate attributeName="opacity" values="1;0.25;1" dur="2s" repeatCount="indefinite"/>
  </circle>
  <text x="46" y="31" fill="{t['text_primary']}" font-size="11.5" font-weight="800" class="mono">NOVALIS // ORGANIZATION ENGINEERING TELEMETRY</text>
  <rect x="444" y="16" width="144" height="20" rx="5" fill="{status_bg}" stroke="{status_color}" stroke-width="0.7" stroke-opacity="0.5"/>
  <text x="516" y="29.5" text-anchor="middle" fill="{status_color}" font-size="9.2" font-weight="800" class="mono">{escape(status_label)}</text>
  <text x="932" y="31" text-anchor="end" fill="{t['text_muted']}" font-size="9.5" class="mono">SYNC: {updated}</text>

  <!-- 4 Executive KPI Cards -->
{chr(10).join(kpi_svg)}

  <!-- Left Velocity Panel -->
  <rect x="28" y="136" width="548" height="160" rx="10" fill="{t['bg_panel']}" stroke="{t['border']}" stroke-width="1"/>
  <text x="44" y="157" fill="{t['text_primary']}" font-size="10.2" font-weight="800" class="mono">{escape(chart_title)}</text>
  <rect x="458" y="144" width="104" height="18" rx="4" fill="{t['bg_subpanel']}" stroke="{t['border']}" stroke-width="0.8"/>
  <text x="510" y="156.5" text-anchor="middle" fill="{t['cyan']}" font-size="8.6" font-weight="700" class="mono">{escape(chart_badge)}</text>
{chr(10).join(grid_lines)}
{chr(10).join(bars_svg)}
  <path d="{ema_area}" fill="url(#velArea)"/>
  <path d="{ema_curve}" fill="none" stroke="url(#velLine)" stroke-width="2.2" stroke-linecap="round"/>
  <circle cx="{end_ex:.1f}" cy="{end_ey:.1f}" r="6" fill="{t['violet']}" fill-opacity="0.28">
    <animate attributeName="r" values="4;8.5;4" dur="2.4s" repeatCount="indefinite"/>
    <animate attributeName="fill-opacity" values="0.45;0.08;0.45" dur="2.4s" repeatCount="indefinite"/>
  </circle>
  <circle cx="{end_ex:.1f}" cy="{end_ey:.1f}" r="3" fill="{t['violet']}"/>
  <text x="46" y="289" fill="{t['text_muted']}" font-size="8.8" class="mono">T-16W</text>
  <text x="302" y="289" text-anchor="middle" fill="{t['text_muted']}" font-size="8.8" class="mono">ENGINEERING CADENCE</text>
  <text x="558" y="289" text-anchor="end" fill="{t['text_muted']}" font-size="8.8" class="mono">NOW</text>

  <!-- Right Stack & Active Repos Panel -->
  <rect x="592" y="136" width="340" height="160" rx="10" fill="{t['bg_panel']}" stroke="{t['border']}" stroke-width="1"/>
  <text x="608" y="157" fill="{t['text_primary']}" font-size="10.2" font-weight="800" class="mono">CORE STACK MATRIX</text>
  <text x="916" y="157" text-anchor="end" fill="{t['text_muted']}" font-size="8.8" class="mono">{'TARGET ALLOCATION' if is_genesis else 'BY CODEBASE'}</text>
{chr(10).join(lang_segs)}
{chr(10).join(lang_legend)}
  <line x1="608" y1="215" x2="916" y2="215" stroke="{t['border']}" stroke-width="1"/>
  <text x="608" y="229" fill="{t['text_muted']}" font-size="9" font-weight="700" class="mono">{list_header}</text>
{chr(10).join(repo_rows)}

  <!-- Bottom Ticker Strip -->
  <rect x="28" y="308" width="904" height="26" rx="6" fill="{t['bg_ticker']}" stroke="{t['border']}" stroke-width="0.9"/>
  <circle cx="42" cy="321" r="2.8" fill="{t['cyan']}"/>
  <text x="54" y="324.5" fill="{t['text_secondary']}" font-size="9.5" font-weight="600" class="mono">{escape(ticker_text)}</text>
</svg>
"""


# ---------------------------------------------------------------------------
# SVG 4: Global Market & AI Signal Radar HUD (960 x 206)
# ---------------------------------------------------------------------------

def render_intelligence_radar(stats: dict, macro: dict, theme_name: str) -> str:
    t = THEMES[theme_name]
    any_live = any(bool(macro[k].get("live")) for k in ("SPX", "GOLD", "BTC"))
    hud_status = "RADAR: LIVE" if any_live else "RADAR: STANDBY"
    hud_color = t["emerald"] if any_live else t["amber"]
    hud_bg = t["pill_emerald_bg"] if any_live else t["bg_panel"]
    updated = escape(stats["updated_utc"])

    def _fmt_price(key: str, price: float) -> str:
        if key == "SPX":
            return f"{price:,.2f}"
        if key == "GOLD":
            return f"${price:,.2f}"
        return f"${price:,.0f}"

    def _fmt_pct(pct: float) -> tuple[str, str]:
        sign = "+" if pct >= 0 else ""
        color = t["emerald"] if pct >= 0 else t["rose"]
        return f"{sign}{pct:.2f}%", color

    cards = []
    card_specs = [
        ("SPX", 212, "gradSpx", t["emerald"]),
        ("GOLD", 396, "gradGold", t["amber"]),
        ("BTC", 580, "gradBtc", t["cyan"]),
    ]

    for key, x, grad_id, _base_color in card_specs:
        item = macro[key]
        price_str = _fmt_price(key, float(item["price"]))
        pct_str, pct_col = _fmt_pct(float(item["change_pct"]))
        spark = sparkline_svg(
            [float(v) for v in item["series"]],
            x0=x + 14,
            y0=126,
            w=140,
            h=46,
            stroke_color=pct_col,
            grad_id=grad_id,
        )
        cards.append(
            f"""  <rect x="{x}" y="46" width="168" height="142" rx="10" fill="{t['bg_panel']}" stroke="{t['border']}" stroke-width="1"/>
  <text x="{x + 14}" y="66" fill="{t['text_primary']}" font-size="11.5" font-weight="800" class="mono">{escape(item['symbol'])}</text>
  <text x="{x + 154}" y="66" text-anchor="end" fill="{t['text_muted']}" font-size="8.8" font-weight="600" class="mono">{escape(item['name'])}</text>
  <line x1="{x + 14}" y1="74" x2="{x + 154}" y2="74" stroke="{t['border']}" stroke-width="0.9"/>
  <text x="{x + 14}" y="99" fill="{t['text_primary']}" font-size="16" font-weight="800" class="mono">{escape(price_str)}</text>
  <text x="{x + 14}" y="117" fill="{pct_col}" font-size="10.8" font-weight="700" class="mono">{escape(pct_str)}</text>
  {spark}"""
        )

    # Card 5 (x=764): NOVALIS Org Pulse
    nx = 764
    is_genesis = bool(stats.get("genesis", True))
    if is_genesis:
        pulse_val = "ACTIVE"
        pulse_sub = "3 PILLARS ONLINE"
        pulse_col = t["violet"]
    else:
        pulse_val = f"{stats['public_repos']} REPOS"
        pulse_sub = f"★ {format_compact(stats['total_stars'])} · {format_compact(stats['total_commits'])} CMTS"
        pulse_col = t["violet"]

    org_spark = sparkline_svg(
        [float(v) for v in stats["velocity"][-12:]],
        x0=nx + 14,
        y0=126,
        w=140,
        h=46,
        stroke_color=t["violet"],
        grad_id="gradOrg",
    )
    cards.append(
        f"""  <rect x="{nx}" y="46" width="168" height="142" rx="10" fill="{t['bg_panel']}" stroke="{t['border']}" stroke-width="1"/>
  <text x="{nx + 14}" y="66" fill="{t['text_primary']}" font-size="11.5" font-weight="800" class="mono">NOVALIS</text>
  <text x="{nx + 154}" y="66" text-anchor="end" fill="{t['text_muted']}" font-size="8.8" font-weight="600" class="mono">ORG PULSE</text>
  <line x1="{nx + 14}" y1="74" x2="{nx + 154}" y2="74" stroke="{t['border']}" stroke-width="0.9"/>
  <text x="{nx + 14}" y="99" fill="{t['text_primary']}" font-size="16" font-weight="800" class="mono">{escape(pulse_val)}</text>
  <text x="{nx + 14}" y="117" fill="{pulse_col}" font-size="10" font-weight="700" class="mono">{escape(pulse_sub)}</text>
  {org_spark}"""
    )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 206" width="960" height="206" role="img" aria-label="NOVALIS Global Market and AI Signal Radar">
  <style>
    .mono {{ font-family: 'JetBrains Mono', 'Fira Code', 'SF Mono', Consolas, monospace; }}
  </style>
  <defs>
    <linearGradient id="radarBg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{t['bg_outer']}"/>
      <stop offset="100%" stop-color="{t['bg_outer_end']}"/>
    </linearGradient>
    <linearGradient id="radarBeam" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{t['cyan']}" stop-opacity="0.45"/>
      <stop offset="100%" stop-color="{t['emerald']}" stop-opacity="0.02"/>
    </linearGradient>
    <linearGradient id="gradSpx" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{t['emerald']}" stop-opacity="0.25"/>
      <stop offset="100%" stop-color="{t['emerald']}" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="gradGold" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{t['amber']}" stop-opacity="0.25"/>
      <stop offset="100%" stop-color="{t['amber']}" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="gradBtc" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{t['cyan']}" stop-opacity="0.25"/>
      <stop offset="100%" stop-color="{t['cyan']}" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="gradOrg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{t['violet']}" stop-opacity="0.28"/>
      <stop offset="100%" stop-color="{t['violet']}" stop-opacity="0"/>
    </linearGradient>
  </defs>

  <rect x="0.5" y="0.5" width="959" height="205" rx="16" fill="url(#radarBg)" stroke="{t['border']}" stroke-width="1"/>

  <!-- Top Header -->
  <circle cx="34" cy="25" r="3.5" fill="{hud_color}">
    <animate attributeName="opacity" values="1;0.3;1" dur="2s" repeatCount="indefinite"/>
  </circle>
  <text x="46" y="29" fill="{t['text_primary']}" font-size="11.5" font-weight="800" class="mono">MARKET INTELLIGENCE // GLOBAL SIGNAL RADAR HUD</text>
  <rect x="424" y="14" width="118" height="19" rx="5" fill="{hud_bg}" stroke="{hud_color}" stroke-width="0.7" stroke-opacity="0.5"/>
  <text x="483" y="27" text-anchor="middle" fill="{hud_color}" font-size="9.2" font-weight="800" class="mono">{hud_status}</text>
  <text x="932" y="29" text-anchor="end" fill="{t['text_muted']}" font-size="9.3" class="mono">FEEDS: SPX · GOLD · BTC · ORG  //  {updated}</text>

  <!-- Card 1 (x=28): Tactical Signal Radar -->
  <rect x="28" y="46" width="168" height="142" rx="10" fill="{t['bg_panel']}" stroke="{t['border']}" stroke-width="1"/>
  <circle cx="112" cy="117" r="52" fill="none" stroke="{t['grid']}" stroke-width="1.2"/>
  <circle cx="112" cy="117" r="35" fill="none" stroke="{t['grid']}" stroke-width="1" stroke-dasharray="2,3"/>
  <circle cx="112" cy="117" r="18" fill="none" stroke="{t['grid']}" stroke-width="1"/>
  <line x1="56" y1="117" x2="168" y2="117" stroke="{t['grid']}" stroke-width="0.9"/>
  <line x1="112" y1="61" x2="112" y2="173" stroke="{t['grid']}" stroke-width="0.9"/>

  <g>
    <animateTransform attributeName="transform" type="rotate" from="0 112 117" to="360 112 117" dur="5.2s" repeatCount="indefinite"/>
    <path d="M 112 117 L 112 65 A 52 52 0 0 1 157 91 Z" fill="url(#radarBeam)"/>
    <line x1="112" y1="117" x2="112" y2="65" stroke="{t['cyan']}" stroke-width="1.6" stroke-opacity="0.9"/>
  </g>

  <circle cx="136" cy="94" r="2.8" fill="{t['emerald']}">
    <animate attributeName="opacity" values="0.2;1;0.2" dur="2.6s" repeatCount="indefinite"/>
  </circle>
  <circle cx="88" cy="134" r="2.5" fill="{t['violet']}">
    <animate attributeName="opacity" values="0.2;1;0.2" dur="3.3s" repeatCount="indefinite"/>
  </circle>
  <circle cx="141" cy="136" r="2.4" fill="{t['cyan']}">
    <animate attributeName="opacity" values="0.15;1;0.15" dur="3.9s" repeatCount="indefinite"/>
  </circle>
  <circle cx="92" cy="90" r="2.2" fill="{t['amber']}">
    <animate attributeName="opacity" values="0.2;0.95;0.2" dur="2.9s" repeatCount="indefinite"/>
  </circle>
  <circle cx="112" cy="117" r="3" fill="{t['cyan']}"/>

  <!-- 4 Live Telemetry Cards -->
{chr(10).join(cards)}
</svg>
"""


# ---------------------------------------------------------------------------
# README Ecosystem Auto-Sync
# ---------------------------------------------------------------------------

def render_repos_markdown(stats: dict) -> str:
    repos = stats.get("repos") or []
    if not repos:
        return """<table>
  <thead>
    <tr>
      <th align="left">Initiative</th>
      <th align="left">Pillar</th>
      <th align="left">Scope</th>
      <th align="center">Status</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><b><code>novalis-cross-core</code></b></td>
      <td>Cross-Platform Apps</td>
      <td>Shared UI architecture, design tokens &amp; multi-platform client foundations for web, mobile, and desktop</td>
      <td align="center"><img src="https://img.shields.io/badge/Architecture-0EA5E9?style=flat-square" alt="Architecture"/></td>
    </tr>
    <tr>
      <td><b><code>novalis-market-intel</code></b></td>
      <td>Market Intelligence</td>
      <td>Real-time market data ingestion, quantitative signal extraction &amp; macro analytics infrastructure</td>
      <td align="center"><img src="https://img.shields.io/badge/R%26D%20Pipeline-10B981?style=flat-square" alt="R&D Pipeline"/></td>
    </tr>
    <tr>
      <td><b><code>novalis-ai-runtime</code></b></td>
      <td>Mission-Critical AI</td>
      <td>High-reliability neural inference, deterministic agent orchestration &amp; automated evaluation harnesses</td>
      <td align="center"><img src="https://img.shields.io/badge/Incubating-6366F1?style=flat-square" alt="Incubating"/></td>
    </tr>
  </tbody>
</table>"""

    rows = []
    for repo in repos[:6]:
        name = escape(repo["name"])
        url = escape(repo["url"])
        desc = escape(truncate_text(repo["description"] or "Core NOVALIS engineering module.", 96))
        lang = escape(repo["language"])
        stars = int(repo["stars"])
        forks = int(repo["forks"])
        rows.append(
            f"""    <tr>
      <td><a href="{url}"><b><code>{name}</code></b></a></td>
      <td>{desc}</td>
      <td align="center"><code>{lang}</code></td>
      <td align="center">★ {stars} · ⑂ {forks}</td>
    </tr>"""
        )

    return (
        """<table>
  <thead>
    <tr>
      <th align="left">Repository</th>
      <th align="left">Description</th>
      <th align="center">Stack</th>
      <th align="center">Activity</th>
    </tr>
  </thead>
  <tbody>
"""
        + "\n".join(rows)
        + """
  </tbody>
</table>"""
    )


def sync_profile_readme(readme_path: str, stats: dict) -> bool:
    if not os.path.exists(readme_path):
        return False
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    start_marker = "<!-- ORG-REPOS:START -->"
    end_marker = "<!-- ORG-REPOS:END -->"
    if start_marker not in content or end_marker not in content:
        return False

    block = f"{start_marker}\n{render_repos_markdown(stats)}\n{end_marker}"
    updated = re.sub(
        re.escape(start_marker) + r".*?" + re.escape(end_marker),
        block,
        content,
        flags=re.DOTALL,
    )
    if updated != content:
        with open(readme_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(updated)
        return True
    return False


def _should_preserve_live_svg(path: str, is_live: bool, force: bool) -> bool:
    if force or is_live or not os.path.exists(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            existing = f.read()
        return ("RADAR: LIVE" in existing) or ("LIVE · GRAPHQL" in existing)
    except OSError:
        return False


def write_svg(path: str, svg_text: str, is_live: bool, force: bool) -> None:
    if _should_preserve_live_svg(path, is_live=is_live, force=force):
        print(f"[SKIP] Preserving existing live SVG at {path}")
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(svg_text)
    print(f"[OK]   Wrote {path} ({len(svg_text):,} bytes)")


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NOVALIS Organization SVG & Telemetry Engine")
    parser.add_argument("--org", default=os.environ.get("ORG_NAME") or DEFAULT_ORG, help="GitHub organization login")
    parser.add_argument("--assets-dir", default="assets", help="Output directory for generated SVGs")
    parser.add_argument("--readme", default=os.path.join("profile", "README.md"), help="Path to org profile README.md")
    parser.add_argument("--offline", action="store_true", help="Generate clean genesis/standby assets without network calls")
    parser.add_argument("--force", action="store_true", help="Overwrite existing live SVGs even in offline/standby mode")
    args = parser.parse_args(argv)

    token = os.environ.get("ORG_ACCESS_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    stats: dict

    if args.offline:
        print(f"[INFO] Running in offline genesis mode for org '{args.org}'")
        stats = offline_genesis_stats(args.org)
    else:
        stats = None  # type: ignore[assignment]
        if token:
            try:
                stats = fetch_org_stats_graphql(args.org, token)
                print(f"[INFO] Fetched GraphQL telemetry for org '{args.org}' ({stats['public_repos']} public repos)")
            except Exception as exc:
                print(f"[WARN] GraphQL fetch failed ({exc}); falling back to REST API...", file=sys.stderr)
        if not stats:
            try:
                stats = fetch_org_stats_rest(args.org, token or None)
                print(f"[INFO] Fetched REST telemetry for org '{args.org}' ({stats['public_repos']} public repos)")
            except Exception as exc:
                print(f"[WARN] REST fetch failed ({exc}); using Genesis Launchpad baseline.", file=sys.stderr)
                stats = offline_genesis_stats(args.org)

    macro = fetch_macro_signals(offline=args.offline)
    any_macro_live = any(bool(macro[k].get("live")) for k in ("SPX", "GOLD", "BTC"))

    for theme in ("dark", "light"):
        write_svg(
            os.path.join(args.assets_dir, f"hero_command_{theme}.svg"),
            render_hero_command(stats, theme),
            is_live=True,
            force=args.force,
        )
        write_svg(
            os.path.join(args.assets_dir, f"architecture_pillars_{theme}.svg"),
            render_architecture_pillars(theme),
            is_live=True,
            force=args.force,
        )
        write_svg(
            os.path.join(args.assets_dir, f"org_telemetry_{theme}.svg"),
            render_org_telemetry(stats, theme),
            is_live=bool(stats.get("live")),
            force=args.force,
        )
        write_svg(
            os.path.join(args.assets_dir, f"intelligence_radar_{theme}.svg"),
            render_intelligence_radar(stats, macro, theme),
            is_live=any_macro_live,
            force=args.force,
        )

    if sync_profile_readme(args.readme, stats):
        print(f"[OK]   Updated ecosystem table in {args.readme}")
    else:
        print(f"[INFO] No README ecosystem table changes needed ({args.readme})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
