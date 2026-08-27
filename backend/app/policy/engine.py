"""
Policy Engine — the deterministic authority in AgentPay.

Core product principle: AI proposes, policy decides. The LLM agent can
*request* a transaction but every request passes through this module, which
never calls out to the LLM and never trusts client-supplied flags. Every
field in PolicyDecision is meant to be shown to the user/merchant verbatim —
this is the "transaction decision trace" surface.
"""
import datetime as dt
from dataclasses import dataclass, field
from typing import List
from sqlalchemy.orm import Session

from app.models import models
from app.intent.engine import StructuredIntent, compute_intent_match
from app.risk.engine import evaluate_risk, RiskResult


@dataclass
class PolicyDecision:
    decision: str  # ALLOW / REQUIRE_APPROVAL / BLOCK
    reason: str
    intent_match: float
    spend_limit_check: str
    merchant_check: str
    category_check: str
    agent_status_check: str
    velocity_check: str
    risk: RiskResult
    violations: List[str] = field(default_factory=list)


def evaluate_transaction(
    db: Session,
    agent: models.Agent,
    merchant: models.Merchant,
    product: models.Product,
    amount: float,
    intent: StructuredIntent,
) -> PolicyDecision:
    violations = []

    # 1. Agent status
    agent_status_check = "PASS"
    if agent.status != "ACTIVE":
        agent_status_check = "FAIL"
        violations.append(f"Agent status is {agent.status}, not ACTIVE")

    passport = agent.passport
    if passport is None or passport.revoked:
        agent_status_check = "FAIL"
        violations.append("Agent has no active Spend Passport (revoked or missing)")

    # 2. Category check
    category_check = "PASS"
    category_ok = True
    if passport:
        if passport.blocked_categories and product.category in passport.blocked_categories:
            category_check = "FAIL"
            category_ok = False
            violations.append(f"Category '{product.category}' is explicitly blocked")
        elif passport.allowed_categories and product.category not in passport.allowed_categories:
            category_check = "FAIL"
            category_ok = False
            violations.append(f"Category '{product.category}' is not in allowed categories")

    # 3. Merchant check
    merchant_check = "PASS"
    if passport and passport.allowed_merchants and merchant.id not in passport.allowed_merchants:
        merchant_check = "FAIL"
        violations.append(f"Merchant '{merchant.name}' is not in the agent's allowed merchant list")

    # 4. Spend limit checks (per-transaction + daily)
    spend_limit_check = "PASS"
    if passport:
        if amount > passport.max_transaction_amount:
            spend_limit_check = "FAIL"
            violations.append(
                f"Amount ₹{amount} exceeds per-transaction max ₹{passport.max_transaction_amount}"
            )
        today_start = dt.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        spent_today = (
            db.query(models.Transaction)
            .filter(models.Transaction.agent_id == agent.id)
            .filter(models.Transaction.status.in_(["ALLOWED", "APPROVED", "PAID"]))
            .filter(models.Transaction.created_at >= today_start)
            .with_entities(models.Transaction.amount)
            .all()
        )
        total_spent_today = sum(t[0] for t in spent_today)
        if total_spent_today + amount > passport.daily_limit:
            spend_limit_check = "FAIL"
            violations.append(
                f"Would exceed daily limit: ₹{total_spent_today} spent + ₹{amount} "
                f"> ₹{passport.daily_limit}"
            )

    # 5. Intent match
    intent_match = compute_intent_match(intent, product.name, product.category, product.price)
    if intent_match < 0.6:
        violations.append(f"Low intent match ({intent_match * 100:.0f}%) — product may not match user request")

    # 6. Risk evaluation
    risk = evaluate_risk(db, agent, amount, merchant, category_ok)
    velocity_check = "FAIL" if risk.velocity_anomaly else "PASS"

    # ---- Final decision ----
    hard_fail = any([
        agent_status_check == "FAIL",
        category_check == "FAIL",
        merchant_check == "FAIL",
        spend_limit_check == "FAIL",
        velocity_check == "FAIL",
    ])

    if passport and amount > passport.hard_block_threshold:
        hard_fail = True
        violations.append(
            f"Amount ₹{amount} exceeds hard block threshold ₹{passport.hard_block_threshold}"
        )

    if risk.band == "HIGH":
        hard_fail = True
        violations.append(f"Risk score {risk.score} is in the HIGH band")

    if hard_fail:
        decision = "BLOCK"
        reason = "; ".join(violations) if violations else "Policy violation"
    elif passport and amount > passport.approval_threshold:
        decision = "REQUIRE_APPROVAL"
        reason = (
            f"Amount ₹{amount} exceeds auto-approval threshold ₹{passport.approval_threshold}; "
            "routed for human approval."
        )
    elif intent_match < 0.6 or risk.band == "MEDIUM":
        decision = "REQUIRE_APPROVAL"
        reason = "Transaction passed hard checks but has medium risk or uncertain intent match; human approval requested."
    else:
        decision = "ALLOW"
        reason = "Transaction matched user intent and remained within all configured spending policies."

    return PolicyDecision(
        decision=decision,
        reason=reason,
        intent_match=intent_match,
        spend_limit_check=spend_limit_check,
        merchant_check=merchant_check,
        category_check=category_check,
        agent_status_check=agent_status_check,
        velocity_check=velocity_check,
        risk=risk,
        violations=violations,
    )
