"""
Risk Engine
Lightweight, explainable transaction-risk scoring for the prototype.
This is NOT a claim of enterprise fraud detection — it's a small set of
inspectable heuristic signals, combined and capped at 1.0, with every
contributing signal returned so the decision trace can show its work.
"""
import datetime as dt
from dataclasses import dataclass, field
from typing import List
from sqlalchemy.orm import Session
from app.models import models


@dataclass
class RiskResult:
    score: float
    band: str  # LOW / MEDIUM / HIGH
    signals: List[str] = field(default_factory=list)
    velocity_anomaly: bool = False


VELOCITY_WINDOW_SECONDS = 30
VELOCITY_MAX_TXNS = 5  # more than this many txns by one agent in the window -> anomaly


def _band(score: float) -> str:
    if score <= 0.30:
        return "LOW"
    if score <= 0.70:
        return "MEDIUM"
    return "HIGH"


def evaluate_risk(db: Session, agent: models.Agent, amount: float,
                   merchant: models.Merchant, category_ok: bool) -> RiskResult:
    score = 0.0
    signals = []

    # 1. Velocity check: count this agent's transactions in the last window
    window_start = dt.datetime.utcnow() - dt.timedelta(seconds=VELOCITY_WINDOW_SECONDS)
    recent_count = (
        db.query(models.Transaction)
        .filter(models.Transaction.agent_id == agent.id)
        .filter(models.Transaction.created_at >= window_start)
        .count()
    )
    velocity_anomaly = recent_count >= VELOCITY_MAX_TXNS
    if velocity_anomaly:
        score += 0.7
        signals.append(
            f"Velocity anomaly: {recent_count} transactions in last "
            f"{VELOCITY_WINDOW_SECONDS}s (threshold {VELOCITY_MAX_TXNS})"
        )

    # 2. Merchant trust
    if merchant.trust_score < 0.5:
        score += 0.25
        signals.append(f"Low merchant trust score ({merchant.trust_score})")
    elif merchant.trust_score < 0.75:
        score += 0.1
        signals.append(f"Moderate merchant trust score ({merchant.trust_score})")

    # 3. Category mismatch (agent buying outside intended category)
    if not category_ok:
        score += 0.2
        signals.append("Category does not match user intent")

    # 4. Amount relative to agent's max transaction limit (near-limit = mild signal)
    if agent.passport and agent.passport.max_transaction_amount:
        ratio = amount / agent.passport.max_transaction_amount
        if ratio >= 0.95:
            score += 0.05
            signals.append("Transaction amount close to agent's max limit")

    # 5. Repeated failed payments for this agent recently
    recent_failed = (
        db.query(models.Payment)
        .join(models.Transaction, models.Payment.transaction_id == models.Transaction.id)
        .filter(models.Transaction.agent_id == agent.id)
        .filter(models.Payment.status == "FAILED")
        .filter(models.Payment.created_at >= dt.datetime.utcnow() - dt.timedelta(minutes=10))
        .count()
    )
    if recent_failed >= 2:
        score += 0.15
        signals.append(f"{recent_failed} failed payments in last 10 minutes")

    score = round(min(score, 1.0), 2)
    if not signals:
        signals.append("No anomalous signals detected")

    return RiskResult(score=score, band=_band(score), signals=signals,
                       velocity_anomaly=velocity_anomaly)
