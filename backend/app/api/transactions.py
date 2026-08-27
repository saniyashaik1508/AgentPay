from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models import models
from app.agents.identity import verify_agent
from app.intent.engine import StructuredIntent
from app.services.transaction_service import propose_transaction, approve_pending_transaction
from app.agents.llm_agent import run_shopping_agent
from app.payments.service import PaymentService
from app.schemas.schemas import RunAgentRequest, ApproveRequest, EvaluateTransactionRequest
from app.audit.service import log_event

router = APIRouter(prefix="/api", tags=["transactions"])


@router.post("/transactions/evaluate")
def evaluate(req: EvaluateTransactionRequest, db: Session = Depends(get_db)):
    agent = verify_agent(db, req.agent_id, req.agent_secret)
    if not agent:
        raise HTTPException(401, "Agent authentication failed or agent not ACTIVE")

    product = db.query(models.Product).filter(models.Product.id == req.product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    merchant = db.query(models.Merchant).filter(models.Merchant.id == product.merchant_id).first()

    intent = StructuredIntent(category=req.category, product_type=req.product_type, max_amount=req.max_amount)
    result = propose_transaction(db, agent, merchant, product, intent)

    return _serialize_result(result)


@router.post("/agents/run")
def run_agent(req: RunAgentRequest, db: Session = Depends(get_db)):
    """Drive the LLM shopping agent end-to-end for a natural-language request."""
    agent = verify_agent(db, req.agent_id, req.agent_secret)
    if not agent:
        raise HTTPException(401, "Agent authentication failed or agent not ACTIVE")

    intent = StructuredIntent(category=req.category, product_type=req.product_type, max_amount=req.max_amount)
    result = run_shopping_agent(db, agent, req.user_request_text, intent)
    return result


@router.post("/transactions/approve")
def approve_transaction(req: ApproveRequest, db: Session = Depends(get_db)):
    txn = db.query(models.Transaction).filter(models.Transaction.id == req.transaction_id).first()
    if not txn:
        raise HTTPException(404, "Transaction not found")
    if txn.status != "REQUIRES_APPROVAL":
        raise HTTPException(400, f"Transaction is in status {txn.status}, not awaiting approval")
    payment = approve_pending_transaction(db, txn)
    return {"transaction_id": txn.id, "status": txn.status, "payment_status": payment.status}


@router.post("/transactions/{transaction_id}/reject")
def reject_transaction(transaction_id: str, db: Session = Depends(get_db)):
    txn = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not txn:
        raise HTTPException(404, "Transaction not found")
    approval = db.query(models.Approval).filter(models.Approval.transaction_id == txn.id).first()
    if approval:
        approval.status = "REJECTED"
    txn.status = "BLOCKED"
    db.commit()
    log_event(db, "TRANSACTION_REJECTED_BY_USER", agent_id=txn.agent_id, transaction_id=txn.id)
    return {"transaction_id": txn.id, "status": txn.status}


@router.get("/transactions")
def list_transactions(agent_id: str = None, status: str = None, db: Session = Depends(get_db)):
    q = db.query(models.Transaction)
    if agent_id:
        q = q.filter(models.Transaction.agent_id == agent_id)
    if status:
        q = q.filter(models.Transaction.status == status)
    txns = q.order_by(models.Transaction.created_at.desc()).all()
    return [{
        "transaction_id": t.id, "agent_id": t.agent_id, "merchant_id": t.merchant_id,
        "amount": t.amount, "currency": t.currency, "status": t.status,
        "created_at": t.created_at.isoformat(),
    } for t in txns]


@router.get("/transactions/{transaction_id}/trace")
def transaction_trace(transaction_id: str, db: Session = Depends(get_db)):
    txn = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not txn:
        raise HTTPException(404, "Transaction not found")
    trace = db.query(models.TransactionDecision).filter(
        models.TransactionDecision.transaction_id == transaction_id
    ).order_by(models.TransactionDecision.created_at.desc()).first()
    payment = db.query(models.Payment).filter(models.Payment.transaction_id == transaction_id).first()

    return {
        "transaction_id": txn.id,
        "amount": txn.amount,
        "currency": txn.currency,
        "agent_id": txn.agent_id,
        "status": txn.status,
        "decision_trace": None if not trace else {
            "intent_match": trace.intent_match_score,
            "spend_limit_check": trace.spend_limit_check,
            "merchant_check": trace.merchant_check,
            "category_check": trace.category_check,
            "agent_status_check": trace.agent_status_check,
            "velocity_check": trace.velocity_check,
            "risk_score": trace.risk_score,
            "decision": trace.decision,
            "reason": trace.reason,
        },
        "payment": None if not payment else {
            "status": payment.status,
            "razorpay_order_id": payment.razorpay_order_id,
            "razorpay_payment_id": payment.razorpay_payment_id,
            "is_mock": payment.is_mock,
            "failure_reason": payment.failure_reason,
        },
    }


@router.get("/risk/events")
def risk_events(agent_id: str = None, db: Session = Depends(get_db)):
    q = db.query(models.RiskEvent)
    if agent_id:
        q = q.filter(models.RiskEvent.agent_id == agent_id)
    events = q.order_by(models.RiskEvent.created_at.desc()).all()
    return [{
        "id": e.id, "agent_id": e.agent_id, "transaction_id": e.transaction_id,
        "event_type": e.event_type, "risk_score": e.risk_score, "details": e.details,
        "created_at": e.created_at.isoformat(),
    } for e in events]


@router.get("/audit")
def audit_log(agent_id: str = None, transaction_id: str = None, db: Session = Depends(get_db)):
    q = db.query(models.AuditLog)
    if agent_id:
        q = q.filter(models.AuditLog.agent_id == agent_id)
    if transaction_id:
        q = q.filter(models.AuditLog.transaction_id == transaction_id)
    logs = q.order_by(models.AuditLog.timestamp.desc()).all()
    return [{
        "id": l.id, "timestamp": l.timestamp.isoformat(), "event": l.event,
        "agent_id": l.agent_id, "user_id": l.user_id, "transaction_id": l.transaction_id,
        "details": l.details,
    } for l in logs]


def _serialize_result(result):
    return {
        "transaction_id": result.transaction.id,
        "status": result.transaction.status,
        "decision": result.decision.decision,
        "reason": result.decision.reason,
        "intent_match": result.decision.intent_match,
        "risk_score": result.decision.risk.score,
        "risk_band": result.decision.risk.band,
        "requires_approval": result.requires_approval,
        "payment": None if not result.payment else {
            "status": result.payment.status,
            "is_mock": result.payment.is_mock,
            "razorpay_payment_id": result.payment.razorpay_payment_id,
            "failure_reason": result.payment.failure_reason,
        },
    }
