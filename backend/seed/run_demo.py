"""
Runs the four demo scenarios end-to-end against the seeded database, using
the MockPaymentAdapter (no Razorpay keys needed to see the full flow).

Usage: python -m seed.run_demo
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database import SessionLocal
from app.models import models
from app.intent.engine import StructuredIntent
from app.services.transaction_service import propose_transaction, approve_pending_transaction
from app.payments.service import PaymentService, MockPaymentAdapter

AGENT_ID = "AGT-shopping7821"


def line(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def run():
    db = SessionLocal()
    agent = db.query(models.Agent).filter(models.Agent.id == AGENT_ID).first()
    if not agent:
        print("Run `python -m seed.seed_data` first.")
        return

    payment_service = PaymentService(adapter=MockPaymentAdapter(failure_rate=0.0))

    # ---------- Scenario A: AUTO APPROVE ----------
    line("SCENARIO A — AUTO APPROVE: Running Shoes ₹4,299 (limit ₹100,000)")
    product = db.query(models.Product).filter(models.Product.id == "PRD-shoes1").first()
    merchant = db.query(models.Merchant).filter(models.Merchant.id == product.merchant_id).first()
    intent = StructuredIntent(category="Footwear", product_type="running shoes", max_amount=5000)
    result = propose_transaction(db, agent, merchant, product, intent, payment_service)
    _print_result(result)

    # ---------- Scenario B: HUMAN APPROVAL ----------
    line("SCENARIO B — HUMAN APPROVAL REQUIRED: Laptop ₹65,000 (approval threshold ₹50,000)")
    product = db.query(models.Product).filter(models.Product.id == "PRD-laptop1").first()
    merchant = db.query(models.Merchant).filter(models.Merchant.id == product.merchant_id).first()
    intent = StructuredIntent(category="Electronics", product_type="laptop", max_amount=100000)
    result = propose_transaction(db, agent, merchant, product, intent, payment_service)
    _print_result(result)
    if result.requires_approval:
        print("\n  -> User approves the transaction...")
        payment = approve_pending_transaction(db, result.transaction, payment_service)
        print(f"  -> Payment status: {payment.status} (mock={payment.is_mock})")

    # ---------- Scenario C: BLOCK (over hard limit / blocked category) ----------
    line("SCENARIO C — BLOCKED: Luxury Watch ₹14,999 (Luxury category is blocked)")
    product = db.query(models.Product).filter(models.Product.id == "PRD-luxwatch1").first()
    merchant = db.query(models.Merchant).filter(models.Merchant.id == product.merchant_id).first()
    intent = StructuredIntent(category="Luxury", product_type="luxury watch", max_amount=20000)
    result = propose_transaction(db, agent, merchant, product, intent, payment_service)
    _print_result(result)

    # ---------- Scenario D: COMPROMISED AGENT / VELOCITY ATTACK ----------
    line("SCENARIO D — COMPROMISED AGENT: rapid-fire transaction attempt")
    # Re-activate the agent in case a prior run suspended it, so the attack is visible fresh
    agent.status = "ACTIVE"
    if agent.passport:
        agent.passport.revoked = False
    db.commit()

    product = db.query(models.Product).filter(models.Product.id == "PRD-headphones1").first()
    merchant = db.query(models.Merchant).filter(models.Merchant.id == product.merchant_id).first()
    intent = StructuredIntent(category="Electronics", product_type="headphones", max_amount=3000)

    for i in range(7):
        result = propose_transaction(db, agent, merchant, product, intent, payment_service)
        print(f"  Attempt {i+1}: decision={result.decision.decision:16s} "
              f"risk={result.decision.risk.score:.2f}  agent_status={agent.status}")
        if agent.status == "SUSPENDED":
            print("  -> Agent suspended mid-burst. Remaining attempts will be blocked at auth.")
            break

    line("Demo complete. Query /api/audit and /api/risk/events to see the full trail.")
    db.close()


def _print_result(result):
    d = result.decision
    print(f"  Intent Match:     {d.intent_match*100:.0f}%")
    print(f"  Spend Limit:      {d.spend_limit_check}")
    print(f"  Category:         {d.category_check}")
    print(f"  Merchant:         {d.merchant_check}")
    print(f"  Agent Status:     {d.agent_status_check}")
    print(f"  Risk Score:       {d.risk.score:.2f} ({d.risk.band})")
    print(f"  DECISION:         {d.decision}")
    print(f"  Reason:           {d.reason}")
    if result.payment:
        print(f"  Payment:          {result.payment.status} (mock={result.payment.is_mock})")


if __name__ == "__main__":
    run()
