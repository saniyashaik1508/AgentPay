from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models.database import init_db
from app.api import agents, transactions, merchant, payments

app = FastAPI(
    title="AgentPay",
    description="Trust & growth infrastructure for agentic commerce. "
                 "Prototype built for the Razorpay AI Builder Internship 2026. "
                 "Uses Razorpay Test Mode — no real money moves.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo only — restrict in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents.router)
app.include_router(transactions.router)
app.include_router(merchant.router)
app.include_router(payments.router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def root():
    return {
        "product": "AgentPay",
        "tagline": "AI agents should be able to transact on behalf of users without receiving unlimited authority over the user's money.",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
