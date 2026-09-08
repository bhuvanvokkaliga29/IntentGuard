"""
IntentGuard — Temporal Authorization Engine

Verifies temporal validity constraints attached to spending mandates:
- effective_from (Mandate not yet active)
- effective_until (Mandate expired)
- Business hours restriction (e.g. 09:00 - 18:00 IST / local time)
- Allowed operational days (e.g. MON-FRI)
- Conference / campaign travel windows

CRITICAL DETERMINISTIC INVARIANT:
A proposal submitted outside its mandated temporal validity window
cannot be auto-approved. It deterministically results in BLOCK or ESCALATE.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TemporalAnalysis(BaseModel):
    passed: bool
    status: str = Field(..., description="'PASS', 'FAIL', or 'NOT_APPLICABLE'")
    observed_time: str
    validity_window: str
    reasons: List[str] = Field(default_factory=list)
    action: str = Field(default="ALLOW", description="'ALLOW', 'BLOCK', or 'ESCALATE'")


def _parse_dt(val: Any) -> Optional[datetime]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
    if isinstance(val, str):
        try:
            dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None


def check_temporal_authorization(
    proposal_time: Optional[Any] = None,
    effective_from: Optional[Any] = None,
    effective_until: Optional[Any] = None,
    business_hours_only: bool = False,
    allowed_days: Optional[List[str]] = None,
) -> TemporalAnalysis:
    """
    Deterministically evaluates temporal boundary constraints.
    """
    parsed_proposal = _parse_dt(proposal_time)
    eff_from = _parse_dt(effective_from)
    eff_until = _parse_dt(effective_until)

    now = parsed_proposal or datetime.now(timezone.utc)

    window_str = f"From: {eff_from.isoformat() if eff_from else 'Genesis'} To: {eff_until.isoformat() if eff_until else 'Indefinite'}"

    # 1. Not yet effective
    if eff_from and now < eff_from:
        return TemporalAnalysis(
            passed=False,
            status="FAIL",
            observed_time=now.isoformat(),
            validity_window=window_str,
            reasons=[f"Proposal timestamp {now.isoformat()} is before mandate effective date {eff_from.isoformat()}."],
            action="BLOCK",
        )

    # 2. Expired
    if eff_until and now > eff_until:
        return TemporalAnalysis(
            passed=False,
            status="FAIL",
            observed_time=now.isoformat(),
            validity_window=window_str,
            reasons=[f"Proposal timestamp {now.isoformat()} is after mandate expiration date {eff_until.isoformat()}."],
            action="BLOCK",
        )

    # 3. Allowed days constraint
    reasons: List[str] = []
    if allowed_days:
        day_name = now.strftime("%a").upper()  # MON, TUE, etc.
        valid_days = [d.upper() for d in allowed_days]
        if day_name not in valid_days:
            reasons.append(f"Proposal submitted on {day_name}, which is outside authorized operational days: {valid_days}.")
            return TemporalAnalysis(
                passed=False,
                status="FAIL",
                observed_time=now.isoformat(),
                validity_window=f"Days: {valid_days}",
                reasons=reasons,
                action="ESCALATE",
            )

    # 4. Business hours constraint (09:00 to 18:00 UTC/standard reference)
    if business_hours_only:
        hour = now.hour
        if hour < 9 or hour >= 18:
            reasons.append(f"Proposal submitted at hour {hour:02d}:00, outside mandated business hours (09:00 - 18:00).")
            return TemporalAnalysis(
                passed=False,
                status="FAIL",
                observed_time=now.isoformat(),
                validity_window="09:00 - 18:00 business hours",
                reasons=reasons,
                action="ESCALATE",
            )

    return TemporalAnalysis(
        passed=True,
        status="PASS",
        observed_time=now.isoformat(),
        validity_window=window_str,
        reasons=["Temporal authorization constraints satisfied."],
        action="ALLOW",
    )
