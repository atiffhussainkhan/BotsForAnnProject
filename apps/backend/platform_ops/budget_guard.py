"""
Agent Echo (Agent 5) — Monthly Budget Guard & Cost Forecaster (`budget_guard.py`).

Satisfies:
- FR-039: Single branded cloud application under £30/month target ceiling.
- FR-050: Monthly budget monitor with itemised hosting/AI/storage spend, per-1,000-reply cost estimator,
  and hard monthly spend cap that automatically downgrades to `DRAFT`/template fallback.
- NFR-07: Hard monthly token/GBP budget meter with automatic fallback to deterministic templates/drafts.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .kill_switch import KillSwitchController, PlatformMode


@dataclass
class SpendEntry:
    entry_id: str
    category: str  # "ai_tokens", "hosting", "storage", "other"
    amount_gbp: float
    tokens_used: int
    description: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class BudgetStatusReport:
    month_key: str
    hard_monthly_ceiling_gbp: float
    ai_monthly_subcap_gbp: float
    hosting_fixed_gbp: float
    storage_fixed_gbp: float
    ai_variable_spend_gbp: float
    other_spend_gbp: float
    total_spend_gbp: float
    remaining_total_gbp: float
    remaining_ai_gbp: float
    utilization_pct: float
    ai_utilization_pct: float
    cap_reached: bool
    deterministic_fallback_active: bool
    effective_reply_mode: str
    estimated_cost_per_1000_replies_gbp: float
    replies_generated_count: int


class BudgetGuard:
    """
    Enforces a hard £30.00/month total cloud ceiling and a configurable £5.00/month AI token sub-cap.
    When either threshold is reached, paid LLM invocations are blocked, the system switches to
    deterministic template fallback, and platforms in `SAFE_AUTO` are automatically downgraded to `DRAFT`.
    """

    DEFAULT_TOTAL_CEILING_GBP = 30.00
    DEFAULT_AI_SUBCAP_GBP = 5.00
    DEFAULT_HOSTING_GBP = 7.00
    DEFAULT_STORAGE_GBP = 0.50
    # Default blended cost per 1,000 replies (~250 input + 90 output tokens per reply on lightweight model)
    DEFAULT_GBP_PER_1K_TOKENS = 0.0012
    DEFAULT_AVG_TOKENS_PER_REPLY = 340

    def __init__(
        self,
        hard_monthly_ceiling_gbp: float = DEFAULT_TOTAL_CEILING_GBP,
        ai_monthly_subcap_gbp: float = DEFAULT_AI_SUBCAP_GBP,
        hosting_monthly_gbp: float = DEFAULT_HOSTING_GBP,
        storage_monthly_gbp: float = DEFAULT_STORAGE_GBP,
        kill_switch: Optional[KillSwitchController] = None,
        month_key: str = "2026-10",
    ) -> None:
        if hard_monthly_ceiling_gbp > 30.00:
            raise ValueError("Hard monthly ceiling cannot exceed £30.00 per PRD FR-039/FR-050.")
        self._lock = threading.RLock()
        self.hard_monthly_ceiling_gbp = round(float(hard_monthly_ceiling_gbp), 4)
        self.ai_monthly_subcap_gbp = round(float(ai_monthly_subcap_gbp), 4)
        self.hosting_monthly_gbp = round(float(hosting_monthly_gbp), 4)
        self.storage_monthly_gbp = round(float(storage_monthly_gbp), 4)
        self.kill_switch = kill_switch
        self.month_key = month_key

        self._ai_spend_gbp: float = 0.0
        self._other_spend_gbp: float = 0.0
        self._total_tokens_used: int = 0
        self._replies_generated: int = 0
        self._deterministic_fallback_active: bool = False
        self._ledger: List[SpendEntry] = []

    def estimate_cost_per_1000_replies(
        self,
        avg_tokens_per_reply: int = DEFAULT_AVG_TOKENS_PER_REPLY,
        gbp_per_1k_tokens: float = DEFAULT_GBP_PER_1K_TOKENS,
    ) -> float:
        """FR-050: Calculate expected AI cost in GBP per 1,000 generated replies."""
        total_tokens_for_1000 = avg_tokens_per_reply * 1000
        cost = (total_tokens_for_1000 / 1000.0) * gbp_per_1k_tokens
        return round(cost, 4)

    def can_invoke_llm(self, estimated_call_cost_gbp: float = 0.0005) -> tuple[bool, str]:
        """Check whether an LLM call is permitted within both the AI sub-cap and total £30 ceiling."""
        with self._lock:
            if self._deterministic_fallback_active:
                return (
                    False,
                    "Budget cap reached: using deterministic UK-English template fallback in DRAFT mode.",
                )
            projected_ai = round(self._ai_spend_gbp + estimated_call_cost_gbp, 6)
            projected_total = round(
                self.hosting_monthly_gbp
                + self.storage_monthly_gbp
                + self._other_spend_gbp
                + projected_ai,
                6,
            )
            if projected_ai > self.ai_monthly_subcap_gbp:
                self._activate_budget_fallback_locked(
                    f"AI monthly sub-cap (£{self.ai_monthly_subcap_gbp:.2f}) reached"
                )
                return False, "AI monthly sub-cap reached: auto-downgraded to DRAFT + templates."
            if projected_total > self.hard_monthly_ceiling_gbp:
                self._activate_budget_fallback_locked(
                    f"Total monthly budget ceiling (£{self.hard_monthly_ceiling_gbp:.2f}) reached"
                )
                return False, "Total £30.00 monthly ceiling reached: auto-downgraded to DRAFT + templates."
            return True, "Within monthly budget limits."

    def record_ai_usage(
        self,
        cost_gbp: float,
        tokens_used: int = 340,
        description: str = "Comment reply generation",
    ) -> BudgetStatusReport:
        """
        Record AI token usage. If the spend hits or exceeds the AI sub-cap (£5.00) or total ceiling (£30.00),
        caps spend at the ceiling and immediately downgrades active platforms to `DRAFT` mode.
        """
        with self._lock:
            allowed, _ = self.can_invoke_llm(cost_gbp)
            if not allowed:
                return self.get_status()

            self._ai_spend_gbp = round(self._ai_spend_gbp + float(cost_gbp), 6)
            self._total_tokens_used += int(tokens_used)
            self._replies_generated += 1
            self._ledger.append(
                SpendEntry(
                    entry_id=f"spend-{len(self._ledger) + 1}",
                    category="ai_tokens",
                    amount_gbp=float(cost_gbp),
                    tokens_used=int(tokens_used),
                    description=description,
                )
            )

            total = (
                self.hosting_monthly_gbp
                + self.storage_monthly_gbp
                + self._other_spend_gbp
                + self._ai_spend_gbp
            )
            if self._ai_spend_gbp >= self.ai_monthly_subcap_gbp or total >= self.hard_monthly_ceiling_gbp:
                self._activate_budget_fallback_locked("Monthly spend limit reached upon usage commit")

            return self.get_status()

    def record_infrastructure_spend(
        self, category: str, amount_gbp: float, description: str = "Cloud addon"
    ) -> BudgetStatusReport:
        """Record non-AI spend and trigger fallback if total approaches/reaches £30.00 ceiling."""
        with self._lock:
            self._other_spend_gbp = round(self._other_spend_gbp + float(amount_gbp), 6)
            self._ledger.append(
                SpendEntry(
                    entry_id=f"spend-{len(self._ledger) + 1}",
                    category=category,
                    amount_gbp=float(amount_gbp),
                    tokens_used=0,
                    description=description,
                )
            )
            total = (
                self.hosting_monthly_gbp
                + self.storage_monthly_gbp
                + self._other_spend_gbp
                + self._ai_spend_gbp
            )
            if total >= self.hard_monthly_ceiling_gbp:
                self._activate_budget_fallback_locked(
                    f"Total monthly ceiling (£{self.hard_monthly_ceiling_gbp:.2f}) reached"
                )
            return self.get_status()

    def _activate_budget_fallback_locked(self, reason: str) -> None:
        self._deterministic_fallback_active = True
        if self.kill_switch is not None:
            for platform in self.kill_switch.SUPPORTED_PLATFORMS:
                snap = self.kill_switch.get_platform_snapshot(platform)
                if snap.mode == PlatformMode.SAFE_AUTO:
                    self.kill_switch.set_platform_mode(
                        platform,
                        PlatformMode.DRAFT,
                        actor="BudgetGuard",
                        reason=f"Budget cap auto-downgrade to DRAFT: {reason}",
                    )

    def generate_reply_with_budget_guard(
        self,
        comment_text: str,
        llm_callable: Optional[Any] = None,
        deterministic_template: str = "Thank you so much lovely! I really appreciate you being here.",
        estimated_cost_gbp: float = 0.0004,
    ) -> Dict[str, Any]:
        """
        Execute LLM generation only if within budget; otherwise seamlessly return the deterministic
        Ann Reveals UK-English template in `DRAFT` mode (`FR-050`, `NFR-07`).
        """
        with self._lock:
            allowed, reason = self.can_invoke_llm(estimated_cost_gbp)
            if not allowed or llm_callable is None:
                return {
                    "reply_text": deterministic_template,
                    "source": "deterministic_template_fallback",
                    "mode": PlatformMode.DRAFT.value,
                    "cost_gbp": 0.0,
                    "budget_reason": reason,
                }

            reply_text = llm_callable(comment_text)
            self.record_ai_usage(cost_gbp=estimated_cost_gbp, tokens_used=340)
            status = self.get_status()
            return {
                "reply_text": reply_text,
                "source": "llm_live",
                "mode": status.effective_reply_mode,
                "cost_gbp": estimated_cost_gbp,
                "budget_reason": "Within budget",
            }

    def get_status(self) -> BudgetStatusReport:
        with self._lock:
            total_spend = round(
                self.hosting_monthly_gbp
                + self.storage_monthly_gbp
                + self._other_spend_gbp
                + self._ai_spend_gbp,
                4,
            )
            rem_total = max(0.0, round(self.hard_monthly_ceiling_gbp - total_spend, 4))
            rem_ai = max(0.0, round(self.ai_monthly_subcap_gbp - self._ai_spend_gbp, 4))
            util_pct = round((total_spend / self.hard_monthly_ceiling_gbp) * 100.0, 2)
            ai_util_pct = round((self._ai_spend_gbp / self.ai_monthly_subcap_gbp) * 100.0, 2)
            cap_hit = (
                self._deterministic_fallback_active
                or total_spend >= self.hard_monthly_ceiling_gbp
                or self._ai_spend_gbp >= self.ai_monthly_subcap_gbp
            )
            return BudgetStatusReport(
                month_key=self.month_key,
                hard_monthly_ceiling_gbp=self.hard_monthly_ceiling_gbp,
                ai_monthly_subcap_gbp=self.ai_monthly_subcap_gbp,
                hosting_fixed_gbp=self.hosting_monthly_gbp,
                storage_fixed_gbp=self.storage_monthly_gbp,
                ai_variable_spend_gbp=round(self._ai_spend_gbp, 4),
                other_spend_gbp=round(self._other_spend_gbp, 4),
                total_spend_gbp=total_spend,
                remaining_total_gbp=rem_total,
                remaining_ai_gbp=rem_ai,
                utilization_pct=util_pct,
                ai_utilization_pct=ai_util_pct,
                cap_reached=cap_hit,
                deterministic_fallback_active=self._deterministic_fallback_active,
                effective_reply_mode=PlatformMode.DRAFT.value if cap_hit else "NORMAL",
                estimated_cost_per_1000_replies_gbp=self.estimate_cost_per_1000_replies(),
                replies_generated_count=self._replies_generated,
            )
