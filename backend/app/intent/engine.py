"""
Intent Engine
Extracts structured purchase intent from a natural-language user request,
and scores how closely a candidate transaction matches that intent.

Note on the LLM boundary: the LLM (in app/agents/llm_agent.py) is what turns
free text into the structured `category / product_type / max_amount` object.
This module owns the deterministic *scoring* of intent-match — that part is
never delegated to the LLM, because the policy engine has to be able to trust
and explain the number.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class StructuredIntent:
    category: str
    product_type: str
    max_amount: float
    currency: str = "INR"
    merchant_restriction: Optional[str] = None


def compute_intent_match(intent: StructuredIntent, product_name: str,
                          product_category: str, product_price: float) -> float:
    """
    Deterministic, explainable match score in [0, 1].
    Weighs: category match (0.5), price within budget (0.35), name/type
    token overlap (0.15). Kept simple and inspectable on purpose — this is
    a prototype signal, not an ML ranking model.
    """
    score = 0.0

    if product_category.lower() == intent.category.lower():
        score += 0.5

    if product_price <= intent.max_amount:
        # Full credit at or under budget; a small penalty curve isn't needed
        # since anything over max_amount should fail the policy check anyway.
        score += 0.35
    elif product_price <= intent.max_amount * 1.05:
        score += 0.15  # marginal overage — policy engine will still catch this

    type_tokens = set(intent.product_type.lower().split())
    name_tokens = set(product_name.lower().split())
    if type_tokens & name_tokens:
        overlap_ratio = len(type_tokens & name_tokens) / max(len(type_tokens), 1)
        score += 0.15 * overlap_ratio

    return round(min(score, 1.0), 2)
