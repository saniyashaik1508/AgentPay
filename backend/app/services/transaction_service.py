"""
Transaction Orchestrator
This is the single place where the full AgentPay flow is wired together:

    AI proposes -> Policy decides -> Payment executes -> Audit records

Nothing here calls an LLM. This module is invoked *after* the agent (see
app/agents/llm_agent.py) has already proposed a candidate transaction as a
structured tool call — this orchestrator treats that proposal exactly like
any other client request and re-validates everything from scratch.
"""
import uuid
from dataclasses import dataclass
from sqlalchemy.orm import Session

from app.models import models
from app.intent.engine import StructuredIntent
from app.policy.engine import evaluate_transaction, PolicyDecision
from app.payments.service import PaymentService
from app.audit.service import log_event


@dataclass
class TransactionResult:
    transaction: models.Transaction
    decision: PolicyDecision
    payment: models.Payment | None
    requires_approval: bool


def propose_transaction(
    db: Session,
    agent: models.Agent,
    merchant: models.Merchant,
    product: models.Product,
    intent: StructuredIntent,
    payment_service: PaymentService = None,
) -> TransactionResult:
    payment_service = payment_service or PaymentService()

    idempotency_key = f"txn-{uuid.uuid4().hex}"
    txn = models.Transaction(
        agent_id=agent.id,
        user_id=agent.owner_id,
        merchant_id=merchant.id,
        product_id=product.id,
        amount=product.price,
        currency=product.currency,
        idempotency_key=idempotency_key,
        status="PENDING",
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)

    log_event(db, "TRANSACTION_PROPOSED", agent_id=agent.id, user_id=agent.owner_id,
              transaction_id=txn.id,
              details={"product": product.name, "amount": product.price, "merchant": merchant.name})

    # ---- POLICY DECISION (deterministic, LLM has no path around this) ----
    decision = evaluate_transaction(db, agent, merchant, product, product.price, intent)

    trace = models.TransactionDecision(
        transaction_id=txn.id,
        intent_match_score=decision.intent_match,
        spend_limit_check=decision.spend_limit_check,
        merchant_check=decision.merchant_check,
        category_check=decision.category_check,
        agent_status_check=decision.agent_status_check,
        velocity_check=decision.velocity_check,
        risk_score=decision.risk.score,
        decision=decision.decision,
        reason=decision.reason,
    )
    db.add(trace)

    if decision.risk.velocity_anomaly:
        db.add(models.RiskEvent(
            agent_id=agent.id, transaction_id=txn.id,
            event_type="VELOCITY_ANOMALY", risk_score=decision.risk.score,
            details="; ".join(decision.risk.signals),
        ))
        # Suspend the agent so subsequent rapid-fire attempts are blocked immediately
        agent.status = "SUSPENDED"
        db.add(agent)
        log_event(db, "AGENT_SUSPENDED", agent_id=agent.id, transaction_id=txn.id,
                  details={"reason": "velocity anomaly", "risk_score": decision.risk.score})

    db.commit()

    if decision.decision == "BLOCK":
        txn.status = "BLOCKED"
        db.commit()
        log_event(db, "TRANSACTION_BLOCKED", agent_id=agent.id, transaction_id=txn.id,
                  details={"reason": decision.reason})
        return TransactionResult(transaction=txn, decision=decision, payment=None, requires_approval=False)

    if decision.decision == "REQUIRE_APPROVAL":
        txn.status = "REQUIRES_APPROVAL"
        db.add(models.Approval(transaction_id=txn.id, status="PENDING"))
        db.commit()
        log_event(db, "APPROVAL_REQUESTED", agent_id=agent.id, transaction_id=txn.id,
                  details={"reason": decision.reason})
        return TransactionResult(transaction=txn, decision=decision, payment=None, requires_approval=True)

    # decision.decision == "ALLOW" -> execute payment now
    txn.status = "ALLOWED"
    db.commit()
    payment = _execute_payment(db, txn, payment_service)
    return TransactionResult(transaction=txn, decision=decision, payment=payment, requires_approval=False)


def approve_pending_transaction(db: Session, txn: models.Transaction,
                                 payment_service: PaymentService = None) -> models.Payment:
    """Called when a human approves a REQUIRES_APPROVAL transaction."""
    payment_service = payment_service or PaymentService()
    approval = db.query(models.Approval).filter(models.Approval.transaction_id == txn.id).first()
    if approval:
        approval.status = "APPROVED"
        import datetime as dt
        approval.resolved_at = dt.datetime.utcnow()
        db.add(approval)
    txn.status = "APPROVED"
    db.commit()
    log_event(db, "TRANSACTION_APPROVED_BY_USER", agent_id=txn.agent_id, transaction_id=txn.id)
    return _execute_payment(db, txn, payment_service)


def _execute_payment(db: Session, txn: models.Transaction, payment_service: PaymentService) -> models.Payment:
    order = payment_service.create_order(txn.amount, txn.currency, txn.idempotency_key)
    payment = models.Payment(
        transaction_id=txn.id,
        razorpay_order_id=order.order_id,
        status="CREATED",
        is_mock=payment_service.is_mock,
    )
    db.add(payment)
    db.commit()

    result = payment_service.initiate_and_verify(order.order_id, txn.idempotency_key)
    payment.razorpay_payment_id = result.payment_id
    payment.status = result.status
    payment.failure_reason = result.failure_reason

    if result.status == "SUCCESS":
        txn.status = "PAID"
        log_event(db, "PAYMENT_SUCCESS", agent_id=txn.agent_id, transaction_id=txn.id,
                  details={"payment_id": result.payment_id, "amount": txn.amount})
    else:
        txn.status = "FAILED"
        log_event(db, "PAYMENT_FAILED", agent_id=txn.agent_id, transaction_id=txn.id,
                  details={"reason": result.failure_reason})

    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment
