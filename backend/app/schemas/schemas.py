from typing import Optional, List
from pydantic import BaseModel


class RegisterAgentRequest(BaseModel):
    owner_id: str
    name: str
    agent_type: str = "Shopping Assistant"
    max_transaction_amount: float
    daily_limit: float
    approval_threshold: float
    hard_block_threshold: float
    allowed_categories: List[str] = []
    blocked_categories: List[str] = []
    allowed_merchants: List[str] = []


class RegisterAgentResponse(BaseModel):
    agent_id: str
    agent_secret: str  # returned once at registration only


class IntentRequest(BaseModel):
    user_id: str
    text: str
    category: str
    product_type: str
    max_amount: float
    currency: str = "INR"
    merchant_restriction: Optional[str] = None


class RunAgentRequest(BaseModel):
    agent_id: str
    agent_secret: str
    user_request_text: str
    category: str
    product_type: str
    max_amount: float


class ApproveRequest(BaseModel):
    transaction_id: str


class EvaluateTransactionRequest(BaseModel):
    agent_id: str
    agent_secret: str
    product_id: str
    category: str
    product_type: str
    max_amount: float
