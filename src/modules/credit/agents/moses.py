"""Moses (Orchestrator) agent — wires all Baby INERTIA agents with resilience."""

from __future__ import annotations

from ..types import CreditProfile
from . import register
from .base import AgentResult, BaseAgent, load_config
from .resilience import CircuitBreaker, DeadLetterQueue, PerformanceBenchmark

# Ordered agent names for the non-conditional pipeline
_ORDERED_AGENTS = ["parks", "king", "colvin", "robinson", "lewis", "phantom", "truth"]
_CONDITIONAL = {"gray", "tubman"}
_ALL_NAMES = ["parks", "king", "colvin", "robinson", "gray", "tubman", "lewis", "phantom", "truth"]

# ---------------------------------------------------------------------------
# Typed fallbacks
# ---------------------------------------------------------------------------

_PHANTOM_FALLBACK: dict = {
    "total_annual_tax": 3500,
    "methodology_source": "Bristol PFRC (fallback estimate)",
    "components": {},
    "validation": {"in_range": True, "capped": False, "original_total": 3500},
}

_KING_FALLBACK: dict = {
    "phases": [{
        "phase": 1, "name": "Bureau Disputes", "steps": [],
        "why_this_order": "Simplified sequential phasing (fallback)",
    }],
    "total_estimated_days": 30,
}

_PARKS_FALLBACK: dict = {
    "life_barriers": {},
    "doors_analysis": [],
    "cheapest_door": None,
    "roi_per_door": [],
}

_GENERIC_FALLBACK_TMPL = {"placeholder": True}

# ---------------------------------------------------------------------------
# Validation contracts
# ---------------------------------------------------------------------------


def _validate_parks(data: dict) -> bool:
    return isinstance(data.get("doors_analysis"), list)


def _validate_king(data: dict) -> bool:
    return "phases" in data


def _validate_phantom(data: dict) -> bool:
    tax = data.get("total_annual_tax", 0)
    return 1500 <= tax <= 15000 and "methodology_source" in data


_VALIDATORS: dict[str, callable] = {
    "parks": _validate_parks,
    "king": _validate_king,
    "phantom": _validate_phantom,
}

_FALLBACKS: dict[str, dict] = {
    "parks": _PARKS_FALLBACK,
    "king": _KING_FALLBACK,
    "phantom": _PHANTOM_FALLBACK,
}

# ---------------------------------------------------------------------------
# Agent helpers
# ---------------------------------------------------------------------------


def _fallback_result(name: str) -> AgentResult:
    """Return a typed fallback AgentResult for *name*."""
    fb = _FALLBACKS.get(name, _GENERIC_FALLBACK_TMPL)
    if name in _FALLBACKS:
        return AgentResult(agent_name=name, status="success", data=dict(fb))
    return AgentResult(agent_name=name, status="error", data={}, errors=["Agent unavailable"])


def _run_agent(
    agent, profile: CreditProfile, context: dict,
    breaker: CircuitBreaker, dlq: DeadLetterQueue, benchmark: PerformanceBenchmark,
) -> tuple[AgentResult, bool]:
    """Execute a single agent with circuit-breaker + DLQ. Returns (result, used_fallback)."""
    if not breaker.allow_request():
        return _fallback_result(agent.name), True
    try:
        result = agent.execute(profile, context=context)
        if result.status == "error":
            breaker.record_failure()
            err = Exception(result.errors[0] if result.errors else "unknown")
            dlq.add(agent_name=agent.name, error=err)
            return _fallback_result(agent.name), True
        breaker.record_success()
        benchmark.record(agent.name, result.execution_ms)
        # Post-validation
        validator = _VALIDATORS.get(agent.name)
        if validator and not validator(result.data):
            dlq.add(agent_name=agent.name, error=Exception("validation failed"))
            breaker.record_failure()
            return _fallback_result(agent.name), True
        return result, False
    except Exception as exc:
        breaker.record_failure()
        dlq.add(agent_name=agent.name, error=exc)
        return _fallback_result(agent.name), True


def _assemble_plan(results: dict[str, AgentResult], context: dict) -> dict:
    """Build the liberation_plan dict from individual results."""
    plan: dict = {
        "situation": results.get("parks", _fallback_result("parks")).data,
        "monday_morning": results.get("robinson", _fallback_result("robinson")).data,
        "battle_plan": results.get("king", _fallback_result("king")).data,
        "poverty_tax": results.get("phantom", _fallback_result("phantom")).data,
        "impact": results.get("lewis", _fallback_result("lewis")).data,
        "attack_cycles": results.get("colvin", _fallback_result("colvin")).data,
    }
    if "gray" in results:
        plan["legal_rights"] = results["gray"].data
    if "tubman" in results:
        plan["bureau_intelligence"] = results["tubman"].data
    return plan


def _load_community_impact() -> str:
    cfg = load_config("city_config")
    projections = cfg.get("community_impact_projections", {})
    annual = projections.get("annual_community_impact", 14605150)
    millions = round(annual / 1_000_000, 1)
    rate = projections.get("adoption_rate", 10)
    return f"${millions}M/year at {rate}% adoption"


# ---------------------------------------------------------------------------
# Moses Agent
# ---------------------------------------------------------------------------


@register
class MosesAgent(BaseAgent):
    """Orchestrator: wires all Baby INERTIA agents with resilience primitives."""

    name = "moses"
    description = "Orchestrates all agents into a Liberation Plan"

    def __init__(self) -> None:
        self._agents: dict = {}
        self._assessment_svc = None
        self._dispute_svc = None
        self._breakers: dict[str, CircuitBreaker] = {
            n: CircuitBreaker(failure_threshold=3, timeout_seconds=60.0) for n in _ALL_NAMES
        }
        self._dlq = DeadLetterQueue()
        self._benchmark = PerformanceBenchmark()

    # ----- public override -----

    def _execute(self, profile: CreditProfile, context: dict | None = None) -> AgentResult:
        ctx = dict(context or {})
        results: dict[str, AgentResult] = {}
        fallback_names: list[str] = []
        chain: list[str] = []

        self._run_kevin(profile, ctx)
        for name in _ORDERED_AGENTS:
            self._dispatch(name, profile, ctx, results, chain, fallback_names)
        self._run_conditionals(profile, ctx, results, chain, fallback_names)
        return self._assemble_output(results, chain, fallback_names)

    # ----- pipeline stages -----

    def _dispatch(
        self, name: str, profile: CreditProfile, ctx: dict,
        results: dict, chain: list, fallback_names: list,
    ) -> None:
        """Run a single named agent through the resilience pipeline."""
        agent = self._agents.get(name)
        if agent is None:
            return
        agent_ctx = self._build_context(name, ctx, results)
        res, fell_back = _run_agent(
            agent, profile, agent_ctx,
            self._breakers[name], self._dlq, self._benchmark,
        )
        results[name] = res
        chain.append(name)
        if fell_back:
            fallback_names.append(name)

    def _run_conditionals(self, profile, ctx, results, chain, fallback_names) -> None:
        if ctx.get("denial_context"):
            self._dispatch("gray", profile, ctx, results, chain, fallback_names)
        bureaus = ctx.get("bureau_reports", {})
        if isinstance(bureaus, dict) and len(bureaus) >= 2:
            self._dispatch("tubman", profile, ctx, results, chain, fallback_names)

    def _assemble_output(self, results, chain, fallback_names) -> AgentResult:
        liberation_plan = _assemble_plan(results, {})
        circuits_opened = sum(1 for b in self._breakers.values() if b.state == "open")
        passed = len(chain) - len(fallback_names)
        return AgentResult(
            agent_name=self.name,
            status="success",
            data={
                "liberation_plan": liberation_plan,
                "reasoning_chain": chain,
                "validation_summary": {
                    "agents_passed": passed,
                    "agents_fallback": len(fallback_names),
                    "fallback_details": fallback_names,
                    "circuits_opened": circuits_opened,
                    "dlq_count": self._dlq.count,
                },
                "performance": {
                    "per_agent_ms": self._benchmark.per_agent_ms,
                    "total_time_ms": self._benchmark.total_ms,
                },
                "compliance": results.get("truth", _fallback_result("truth")).data,
                "community_impact": _load_community_impact(),
                "why_deterministic": (
                    "Dynatrace study: deterministic agents 12x more "
                    "reliable than LLM-based"
                ),
            },
        )

    # ----- private helpers -----

    def _run_kevin(self, profile: CreditProfile, ctx: dict) -> None:
        """Run Kevin's services and stash results in context."""
        if self._assessment_svc:
            try:
                ctx["assessment_result"] = self._assessment_svc.assess(profile)
            except Exception:
                ctx["assessment_result"] = None
        if self._dispute_svc:
            try:
                ctx["dispute_pathway"] = self._dispute_svc.generate_pathway(profile)
            except Exception:
                ctx["dispute_pathway"] = None

    def _build_context(self, name: str, ctx: dict, results: dict[str, AgentResult]) -> dict:
        """Build per-agent context, threading prior results where needed."""
        agent_ctx = dict(ctx)
        parks_data = results.get("parks")
        if parks_data:
            agent_ctx["parks_result"] = parks_data.data
        if name == "king" and "dispute_pathway" in ctx:
            agent_ctx["dispute_pathway"] = ctx["dispute_pathway"]
        if name == "truth":
            agent_ctx["text_to_check"] = self._summary_text(results)
        return agent_ctx

    @staticmethod
    def _summary_text(results: dict[str, AgentResult]) -> str:
        """Build a summary for Truth compliance checking."""
        parts: list[str] = []
        for name, res in results.items():
            if res.status == "success" and res.data:
                parts.append(f"{name}: {str(res.data)[:200]}")
        return " | ".join(parts) if parts else ""
