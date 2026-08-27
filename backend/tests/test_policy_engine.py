from app.intent.engine import StructuredIntent
from app.policy.engine import evaluate_transaction
from app.models import models


def make_intent(category="Footwear", max_amount=5000):
    return StructuredIntent(category=category, product_type="running shoes", max_amount=max_amount)


def test_valid_transaction_allows(db, agent_setup):
    d = evaluate_transaction(db, agent_setup["agent"], agent_setup["merchant"],
                              agent_setup["product"], 4299, make_intent())
    assert d.decision == "ALLOW"


def test_amount_above_limit_blocks(db, agent_setup):
    agent_setup["product"].price = 6000
    d = evaluate_transaction(db, agent_setup["agent"], agent_setup["merchant"],
                              agent_setup["product"], 6000, make_intent(max_amount=6000))
    assert d.decision == "BLOCK"
    assert d.spend_limit_check == "FAIL"


def test_unauthorized_category_blocks(db, agent_setup):
    agent_setup["product"].category = "Electronics"
    d = evaluate_transaction(db, agent_setup["agent"], agent_setup["merchant"],
                              agent_setup["product"], 4299, make_intent(category="Electronics"))
    assert d.decision == "BLOCK"
    assert d.category_check == "FAIL"


def test_blocked_category_blocks(db, agent_setup):
    agent_setup["product"].category = "Luxury"
    d = evaluate_transaction(db, agent_setup["agent"], agent_setup["merchant"],
                              agent_setup["product"], 4299, make_intent(category="Luxury"))
    assert d.decision == "BLOCK"
    assert d.category_check == "FAIL"


def test_unauthorized_merchant_blocks(db, agent_setup):
    agent_setup["agent"].passport.allowed_merchants = ["MER-someone-else"]
    d = evaluate_transaction(db, agent_setup["agent"], agent_setup["merchant"],
                              agent_setup["product"], 4299, make_intent())
    assert d.decision == "BLOCK"
    assert d.merchant_check == "FAIL"


def test_revoked_agent_blocks(db, agent_setup):
    agent_setup["agent"].passport.revoked = True
    d = evaluate_transaction(db, agent_setup["agent"], agent_setup["merchant"],
                              agent_setup["product"], 4299, make_intent())
    assert d.decision == "BLOCK"
    assert d.agent_status_check == "FAIL"


def test_suspended_agent_blocks(db, agent_setup):
    agent_setup["agent"].status = "SUSPENDED"
    d = evaluate_transaction(db, agent_setup["agent"], agent_setup["merchant"],
                              agent_setup["product"], 4299, make_intent())
    assert d.decision == "BLOCK"


def test_medium_amount_requires_approval(db, agent_setup):
    agent_setup["agent"].passport.max_transaction_amount = 10000
    agent_setup["agent"].passport.approval_threshold = 3000
    agent_setup["agent"].passport.hard_block_threshold = 10000
    agent_setup["product"].price = 4299
    d = evaluate_transaction(db, agent_setup["agent"], agent_setup["merchant"],
                              agent_setup["product"], 4299, make_intent())
    assert d.decision == "REQUIRE_APPROVAL"


def test_amount_above_hard_block_blocks(db, agent_setup):
    agent_setup["agent"].passport.max_transaction_amount = 20000
    agent_setup["agent"].passport.hard_block_threshold = 10000
    agent_setup["product"].price = 15000
    d = evaluate_transaction(db, agent_setup["agent"], agent_setup["merchant"],
                              agent_setup["product"], 15000, make_intent(max_amount=15000))
    assert d.decision == "BLOCK"
