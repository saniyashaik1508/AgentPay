from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models import models
from app.agents.identity import generate_agent_secret, hash_secret
from app.schemas.schemas import RegisterAgentRequest, RegisterAgentResponse
from app.audit.service import log_event

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.post("/register", response_model=RegisterAgentResponse)
def register_agent(req: RegisterAgentRequest, db: Session = Depends(get_db)):
    owner = db.query(models.User).filter(models.User.id == req.owner_id).first()
    if not owner:
        raise HTTPException(404, "User not found")

    secret = generate_agent_secret()
    agent = models.Agent(
        owner_id=req.owner_id,
        name=req.name,
        agent_type=req.agent_type,
        status="ACTIVE",
        trust_level="MEDIUM",
        api_secret_hash=hash_secret(secret),
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)

    passport = models.SpendPassport(
        agent_id=agent.id,
        max_transaction_amount=req.max_transaction_amount,
        daily_limit=req.daily_limit,
        approval_threshold=req.approval_threshold,
        hard_block_threshold=req.hard_block_threshold,
        allowed_categories=req.allowed_categories,
        blocked_categories=req.blocked_categories,
        allowed_merchants=req.allowed_merchants,
    )
    db.add(passport)
    db.commit()

    log_event(db, "AGENT_REGISTERED", agent_id=agent.id, user_id=owner.id,
              details={"name": agent.name})

    return RegisterAgentResponse(agent_id=agent.id, agent_secret=secret)


@router.get("")
def list_agents(owner_id: str = None, db: Session = Depends(get_db)):
    q = db.query(models.Agent)
    if owner_id:
        q = q.filter(models.Agent.owner_id == owner_id)
    agents = q.all()
    out = []
    for a in agents:
        p = a.passport
        out.append({
            "agent_id": a.id, "name": a.name, "status": a.status,
            "trust_level": a.trust_level,
            "max_transaction_amount": p.max_transaction_amount if p else None,
            "daily_limit": p.daily_limit if p else None,
            "revoked": p.revoked if p else None,
        })
    return out


@router.post("/{agent_id}/revoke")
def revoke_agent(agent_id: str, db: Session = Depends(get_db)):
    agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(404, "Agent not found")
    agent.status = "REVOKED"
    if agent.passport:
        agent.passport.revoked = True
    db.commit()
    log_event(db, "AGENT_REVOKED", agent_id=agent.id, user_id=agent.owner_id)
    return {"agent_id": agent.id, "status": agent.status}
