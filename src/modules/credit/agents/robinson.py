"""Robinson (Door Finder) — free credit-building opportunities and local resources."""

from __future__ import annotations

import os
from urllib.parse import urlparse

import httpx

from . import register
from .base import AgentResult, BaseAgent, load_config
from ..types import CreditProfile

_BRIGHT_DATA_ALLOWED_HOST = "api.brightdata.com"
_BRIGHT_DATA_URL = (
    "https://api.brightdata.com/datasets/v3/trigger?dataset_id=jobs_montgomery_al"
)
if httpx.URL(_BRIGHT_DATA_URL).host != _BRIGHT_DATA_ALLOWED_HOST:
    raise RuntimeError("_BRIGHT_DATA_URL host does not match allowlist")


def _check_eligibility(service: dict, profile: CreditProfile) -> bool:
    """Determine if a profile is eligible for a given service."""
    svc_type = service.get("type", "")
    if svc_type == "utility_reporting":
        return profile.account_summary.open_accounts > 0
    if svc_type == "rent_reporting":
        return True
    if svc_type == "secured_card":
        return True
    if svc_type == "credit_builder_loan":
        return True
    return True


def _detect_thin_file(profile: CreditProfile) -> bool:
    """A thin file has fewer than 3 accounts OR average age under 12 months."""
    if profile.account_summary.total_accounts < 3:
        return True
    if profile.average_account_age_months < 12:
        return True
    return False


def _sort_services(services: list[dict]) -> list[dict]:
    """Sort free-first, then by max impact descending within each cost group."""
    return sorted(
        services,
        key=lambda s: (s["cost"] > 0, -s["impact_points"]["max"]),
    )


def _build_free_stack(sorted_services: list[dict]) -> dict:
    """Build the top-3 free services stack with combined impact."""
    free = [s for s in sorted_services if s["cost"] == 0]
    top_3 = free[:3]
    combined_min = sum(a["impact_points"]["min"] for a in top_3)
    combined_max = sum(a["impact_points"]["max"] for a in top_3)
    return {
        "actions": top_3,
        "combined_impact": {"min": combined_min, "max": combined_max},
        "cost": "$0",
    }


def _generate_recommendation(profile: CreditProfile, is_thin: bool) -> str:
    """Generate text recommendation based on profile characteristics."""
    if is_thin:
        return "Start with free credit-building tools to establish history"
    if profile.overall_utilization > 50.0:
        return "Focus on free reporting services while paying down balances"
    return "Use free services to boost score while maintaining good habits"


_STATIC_JOBS = [
    {
        "title": "CNA - Baptist Medical Center",
        "employer": "Baptist Health",
        "credit_check": False,
    },
    {"title": "Warehouse Associate", "employer": "Amazon MGM5", "credit_check": False},
    {"title": "Line Cook", "employer": "Dreamland BBQ", "credit_check": False},
    {"title": "CDL Driver", "employer": "Werner Enterprises", "credit_check": False},
    {
        "title": "Retail Associate",
        "employer": "Walmart Supercenter",
        "credit_check": False,
    },
]


def _fetch_bright_data_jobs() -> dict:
    """Fetch Montgomery job listings via Bright Data, with graceful fallback."""
    api_key = os.environ.get("BRIGHT_DATA_API_KEY", "")
    if not api_key or not api_key.strip():
        return {
            "live_data": False,
            "source": "static",
            "jobs": _STATIC_JOBS,
            "note": "Live data unavailable — set BRIGHT_DATA_API_KEY",
        }

    if urlparse(_BRIGHT_DATA_URL).hostname != _BRIGHT_DATA_ALLOWED_HOST:
        return {
            "live_data": False,
            "source": "static",
            "jobs": _STATIC_JOBS,
            "note": "Blocked — URL host not in allowlist",
        }

    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(
                _BRIGHT_DATA_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
        jobs = [
            {
                "title": j.get("title", ""),
                "employer": j.get("company", ""),
                "credit_check": False,
            }
            for j in data.get("results", [])[:10]
        ]
        return {
            "live_data": True,
            "source": "bright_data",
            "jobs": jobs or _STATIC_JOBS,
        }
    except Exception:
        return {
            "live_data": False,
            "source": "static",
            "jobs": _STATIC_JOBS,
            "note": "Bright Data request failed — using cached results",
        }


@register
class RobinsonAgent(BaseAgent):
    """Finds free credit-building opportunities and local resources."""

    name: str = "robinson"
    description: str = (
        "Door Finder — free credit-building opportunities for Montgomery, AL"
    )

    def _execute(
        self, profile: CreditProfile, context: dict | None = None
    ) -> AgentResult:
        # Load configs
        alt_cfg = load_config("alternative_services")
        res_cfg = load_config("montgomery_resources")

        # Build opportunity list with eligibility
        raw_services = alt_cfg["services"]
        opportunities = []
        for svc in raw_services:
            entry = {
                "name": svc["name"],
                "type": svc["type"],
                "cost": svc["cost"],
                "impact_points": svc["impact_points"],
                "how": svc["how"],
                "eligible": _check_eligibility(svc, profile),
            }
            opportunities.append(entry)

        # Sort and build free stack
        opportunities = _sort_services(opportunities)
        is_thin = _detect_thin_file(profile)
        free_stack = _build_free_stack(opportunities)

        return AgentResult(
            agent_name=self.name,
            status="success",
            data={
                "opportunities": opportunities,
                "is_thin_file": is_thin,
                "free_stack": free_stack,
                "local_resources": res_cfg["resources"],
                "recommendation": _generate_recommendation(profile, is_thin),
                "jobs": _fetch_bright_data_jobs(),
            },
        )
