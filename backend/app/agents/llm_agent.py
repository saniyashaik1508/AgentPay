"""
AI Shopping Agent (LLM tool-calling)

Critical architectural boundary:
    LLM -> tool request -> AgentPay Policy Engine -> Risk Engine ->
    Approval Engine -> Payment API

The LLM has exactly two tools: `search_products` (read-only) and
`propose_transaction` (which internally calls the same deterministic
transaction_service.propose_transaction() used by the REST API — the LLM
gets no special path, no bypass, and no ability to directly call the
payment service). This file is intentionally the *only* place in the
codebase that imports an LLM client.

Requires ANTHROPIC_API_KEY in the environment. Uses Claude's native tool use.
"""
import os
import json
from sqlalchemy.orm import Session

from app.models import models
from app.intent.engine import StructuredIntent
from app.services.transaction_service import propose_transaction
from app.payments.service import PaymentService

TOOLS = [
    {
        "name": "search_products",
        "description": "Search the merchant catalog for products matching a category and budget.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string"},
                "max_price": {"type": "number"},
            },
            "required": ["category"],
        },
    },
    {
        "name": "propose_transaction",
        "description": (
            "Propose a purchase of a specific product to AgentPay. This does NOT "
            "guarantee the purchase happens — AgentPay's policy engine independently "
            "evaluates the proposal and may ALLOW, REQUIRE_APPROVAL, or BLOCK it."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "string"},
            },
            "required": ["product_id"],
        },
    },
]

SYSTEM_PROMPT = (
    "You are AgentPay's shopping assistant. A user has authorized you to shop within "
    "stated limits. Use search_products to find a matching item, then propose_transaction "
    "to request the purchase. You do not have the ability to move money directly — every "
    "proposal you make is independently checked by AgentPay's policy engine, which may "
    "block it or require human approval regardless of what you decide."
)


def _tool_search_products(db: Session, category: str, max_price: float | None):
    q = db.query(models.Product).filter(models.Product.category.ilike(category))
    if max_price:
        q = q.filter(models.Product.price <= max_price)
    results = q.all()
    return [
        {"product_id": p.id, "name": p.name, "price": p.price, "currency": p.currency,
         "merchant_id": p.merchant_id}
        for p in results
    ]


def run_shopping_agent(db: Session, agent: models.Agent, user_request_text: str,
                        intent: StructuredIntent, payment_service: PaymentService = None) -> dict:
    """
    Drives one shopping request end to end using Claude's tool-calling loop.
    Returns a summary dict describing what the agent did and what AgentPay decided.
    Falls back to a deterministic (non-LLM) product search if no API key is set,
    so the rest of the system remains demoable without external dependencies.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return _deterministic_fallback(db, agent, intent, payment_service)

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    messages = [{"role": "user", "content": user_request_text}]
    transcript = []

    for _ in range(4):  # bounded tool-use loop
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        tool_calls = [b for b in response.content if b.type == "tool_use"]
        if not tool_calls:
            transcript.append({"role": "agent_text", "content": _extract_text(response)})
            break

        tool_results = []
        for call in tool_calls:
            if call.name == "search_products":
                result = _tool_search_products(db, call.input.get("category", ""), call.input.get("max_price"))
                transcript.append({"role": "tool_call", "tool": "search_products", "input": call.input, "result": result})
            elif call.name == "propose_transaction":
                product = db.query(models.Product).filter(models.Product.id == call.input["product_id"]).first()
                if not product:
                    result = {"error": "product not found"}
                else:
                    merchant = db.query(models.Merchant).filter(models.Merchant.id == product.merchant_id).first()
                    txn_result = propose_transaction(db, agent, merchant, product, intent, payment_service)
                    result = {
                        "transaction_id": txn_result.transaction.id,
                        "decision": txn_result.decision.decision,
                        "reason": txn_result.decision.reason,
                        "requires_approval": txn_result.requires_approval,
                        "payment_status": txn_result.payment.status if txn_result.payment else None,
                    }
                transcript.append({"role": "tool_call", "tool": "propose_transaction", "input": call.input, "result": result})
            else:
                result = {"error": f"unknown tool {call.name}"}

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": call.id,
                "content": json.dumps(result),
            })

        messages.append({"role": "user", "content": tool_results})

    return {"transcript": transcript}


def _extract_text(response) -> str:
    return "".join(b.text for b in response.content if b.type == "text")


def _deterministic_fallback(db: Session, agent: models.Agent, intent: StructuredIntent,
                             payment_service: PaymentService) -> dict:
    """No-LLM path: pick the cheapest in-budget, in-category product and propose it.
    Keeps demo scenarios runnable without an ANTHROPIC_API_KEY."""
    candidates = (
        db.query(models.Product)
        .filter(models.Product.category.ilike(intent.category))
        .filter(models.Product.price <= intent.max_amount)
        .order_by(models.Product.price.asc())
        .all()
    )
    transcript = [{"role": "tool_call", "tool": "search_products (fallback)",
                   "input": {"category": intent.category, "max_price": intent.max_amount},
                   "result": [{"product_id": p.id, "name": p.name, "price": p.price} for p in candidates]}]

    if not candidates:
        transcript.append({"role": "agent_text", "content": "No matching product found within budget."})
        return {"transcript": transcript}

    product = candidates[0]
    merchant = db.query(models.Merchant).filter(models.Merchant.id == product.merchant_id).first()
    txn_result = propose_transaction(db, agent, merchant, product, intent, payment_service)
    transcript.append({
        "role": "tool_call", "tool": "propose_transaction (fallback)",
        "input": {"product_id": product.id},
        "result": {
            "transaction_id": txn_result.transaction.id,
            "decision": txn_result.decision.decision,
            "reason": txn_result.decision.reason,
            "requires_approval": txn_result.requires_approval,
            "payment_status": txn_result.payment.status if txn_result.payment else None,
        },
    })
    return {"transcript": transcript}
