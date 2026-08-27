from app.intent.engine import StructuredIntent
from app.services.transaction_service import propose_transaction, approve_pending_transaction
from app.payments.service import PaymentService, MockPaymentAdapter
from app.models import models


def make_intent():
    return StructuredIntent(category="Footwear", product_type="running shoes", max_amount=5000)


def test_end_to_end_auto_approve_pays(db, agent_setup, mock_payment_service):
    result = propose_transaction(db, agent_setup["agent"], agent_setup["merchant"],
                                  agent_setup["product"], make_intent(), mock_payment_service)
    assert result.decision.decision == "ALLOW"
    assert result.payment.status == "SUCCESS"
    assert result.transaction.status == "PAID"


def test_payment_failure_marks_transaction_failed_not_duplicated(db, agent_setup):
    failing_service = PaymentService(adapter=MockPaymentAdapter(failure_rate=1.0))
    result = propose_transaction(db, agent_setup["agent"], agent_setup["merchant"],
                                  agent_setup["product"], make_intent(), failing_service)
    assert result.payment.status == "FAILED"
    assert result.transaction.status == "FAILED"
    assert result.payment.failure_reason is not None


def test_idempotent_payment_request_returns_same_result(mock_payment_service):
    order = mock_payment_service.create_order(4299, "INR", "idem-key-1")
    r1 = mock_payment_service.initiate_and_verify(order.order_id, "idem-key-1")
    r2 = mock_payment_service.initiate_and_verify(order.order_id, "idem-key-1")
    assert r1.payment_id == r2.payment_id
    assert r1.status == r2.status


def test_approval_flow_pays_after_human_approval(db, agent_setup, mock_payment_service):
    agent_setup["agent"].passport.approval_threshold = 1000  # force approval path
    result = propose_transaction(db, agent_setup["agent"], agent_setup["merchant"],
                                  agent_setup["product"], make_intent(), mock_payment_service)
    assert result.requires_approval is True
    assert result.transaction.status == "REQUIRES_APPROVAL"

    payment = approve_pending_transaction(db, result.transaction, mock_payment_service)
    assert payment.status == "SUCCESS"
    assert result.transaction.status == "PAID"


def test_abnormal_velocity_suspends_agent(db, agent_setup, mock_payment_service):
    agent_setup["agent"].passport.max_transaction_amount = 5000
    agent_setup["agent"].passport.daily_limit = 100000
    agent_setup["agent"].passport.approval_threshold = 5000
    agent_setup["agent"].passport.hard_block_threshold = 5000

    last_result = None
    for _ in range(6):
        last_result = propose_transaction(db, agent_setup["agent"], agent_setup["merchant"],
                                           agent_setup["product"], make_intent(), mock_payment_service)

    assert agent_setup["agent"].status == "SUSPENDED"
    risk_events = db.query(models.RiskEvent).filter(
        models.RiskEvent.event_type == "VELOCITY_ANOMALY"
    ).all()
    assert len(risk_events) >= 1
