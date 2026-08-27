# AgentPay
### Trust & Growth Infrastructure for Agentic Commerce

**Built for the Razorpay AI Builder Internship 2026 — Track: Agentic Commerce**

> AI agents should be able to transact on behalf of users without receiving unlimited authority over the user's money.

---

## 1. The problem

AI shopping agents, procurement bots, and booking assistants are starting to make real purchases on behalf of users. This breaks two assumptions payment systems are built on:

- **Merchants** have no reliable way to tell a legitimate autonomous purchase apart from a compromised agent or a runaway script.
- **Users** have no fine-grained way to say *what* an agent is allowed to buy, *where*, and *how much* — today it's effectively all-or-nothing.

That trust gap is what's currently blocking agentic commerce from being safe to turn on by default. AgentPay is a prototype trust layer that sits between an AI agent and a payment rail (Razorpay, in this build) and answers one question for every transaction: **should this specific proposed payment actually happen?**

## 2. The core design principle

```
AI proposes → Policy decides → Payment executes → Audit records
```

The LLM agent can *request* a purchase using tool calls. It cannot move money. Every proposal — whether it comes from the LLM agent, the REST API, or a test script — passes through the same deterministic policy engine, which independently re-checks spend limits, category rules, merchant allow-lists, agent status, and a risk score before anything is sent to Razorpay. **The LLM has no path around this check.** See `app/agents/llm_agent.py` — it's the only file that imports an LLM client, and its `propose_transaction` tool internally calls the exact same orchestrator (`app/services/transaction_service.py`) used by the public API.

## 3. Architecture

```
                    USER
                      |
                      v
               AI SHOPPING AGENT (Claude, tool-calling)
                      |
                      v
              AGENTPAY API (FastAPI)
                      |
        +-------------+-------------+
        |                           |
        v                           v
 AGENT IDENTITY                USER INTENT
 & SPEND PASSPORT              (structured, scored)
        |                           |
        +-------------+-------------+
                      |
                      v
                POLICY ENGINE  (deterministic ALLOW / REQUIRE_APPROVAL / BLOCK)
                      |
          +-----------+-----------+
          |                       |
          v                       v
     RISK ENGINE            APPROVAL ENGINE
   (velocity, trust,       (auto vs human threshold)
    category signals)
          |                       |
          +-----------+-----------+
                      |
                      v
              PAYMENT SERVICE  (clean abstraction, idempotent)
                      |
                      v
           RAZORPAY TEST MODE API  (or mock adapter if no keys set)
                      |
                      v
                TRANSACTION
                      |
          +-----------+-----------+
          |                       |
          v                       v
      AUDIT LOG             GROWTH ENGINE  →  MERCHANT DASHBOARD DATA
```

### Component responsibilities

| Component | File | Responsibility |
|---|---|---|
| Agent Identity | `app/agents/identity.py` | HMAC-based agent authentication — an agent ID alone is never trusted |
| Spend Passport | `app/models/models.py::SpendPassport` | Scoped, revocable spending permissions (limits, categories, merchants) |
| Intent Engine | `app/intent/engine.py` | Structures user intent and computes an explainable intent-match score |
| Policy Engine | `app/policy/engine.py` | The deterministic authority — ALLOW / REQUIRE_APPROVAL / BLOCK |
| Risk Engine | `app/risk/engine.py` | Velocity, merchant trust, category mismatch, near-limit, repeated-failure signals |
| Payment Service | `app/payments/service.py` | Razorpay Test Mode integration behind an adapter interface, with idempotency |
| Transaction Orchestrator | `app/services/transaction_service.py` | Wires the full flow together end to end |
| LLM Shopping Agent | `app/agents/llm_agent.py` | Claude tool-calling agent that proposes (never executes) purchases |
| Audit Log | `app/audit/service.py` | Append-only event trail for every state change |
| Growth Engine | `app/growth/engine.py` | Merchant analytics + rule-based insights (clearly labeled as demo data) |

## 4. Database schema (ER overview)

```
users ─┬─< agents ─┬─< spend_passports (1:1)
       │            │
       │            ├─< transactions ─┬─< transaction_decisions
       │            │                  ├─< approvals
       │            │                  ├─< payments
       │            │                  └─< risk_events
       │            │
       │            └─< audit_logs
       │
       └─< intents

merchants ─< products ─< transactions
merchants ─< growth_insights
```

Runs on SQLite by default (zero setup for local dev/demo). Set `DATABASE_URL` to a Postgres DSN to switch — the schema uses no SQLite-specific types, so it's a config change, not a code change.

## 5. Security model

- **Agent authentication**: agents authenticate with a server-issued secret; only its HMAC hash is stored (`app/agents/identity.py`).
- **Scoped permissions**: every agent has exactly one Spend Passport — per-transaction limit, daily limit, auto-approval threshold, hard-block threshold, category allow/block lists, merchant allow-list.
- **Instant revocation**: `POST /api/agents/{id}/revoke` immediately blocks all future transactions for that agent.
- **Idempotency**: payment requests are keyed so the same transaction can never be double-charged (`app/payments/service.py::PaymentService`).
- **No hardcoded secrets**: Razorpay keys and the Anthropic API key are read from environment variables only (`.env.example`).
- **Payment signature verification**: `POST /api/payments/verify` validates the Razorpay HMAC signature server-side before accepting a client-reported payment as final.
- **Deterministic policy authority**: the LLM never has a code path to the payment service — see §2.

## 6. Failure handling (implemented, not just described)

| Failure | Behavior |
|---|---|
| Payment gateway failure | Transaction marked `FAILED`, no duplicate charge, reason logged, no silent retry |
| Policy violation | Transaction `BLOCK`ed before any payment is ever attempted |
| Abnormal velocity (compromised agent) | Agent `SUSPENDED` mid-burst, all subsequent attempts blocked at auth, event recorded |
| Duplicate payment request | Same idempotency key returns the original result, never charges twice |

## 7. The four demo scenarios

Run `python -m seed.run_demo` after seeding to see all four executed live against a real (mocked-adapter) payment flow:

- **A — Auto-approve**: Running shoes, ₹4,299, within all limits → `ALLOW` → payment succeeds.
- **B — Human approval**: Laptop, ₹65,000, over the ₹50,000 auto-approval threshold → `REQUIRE_APPROVAL` → user approves → payment succeeds.
- **C — Block**: Luxury watch, ₹14,999, in a blocked category → `BLOCK`, no payment ever attempted.
- **D — Compromised agent**: 7 rapid transaction attempts in quick succession → risk engine flags a velocity anomaly, agent is automatically `SUSPENDED`, remaining attempts are blocked.

## 8. API surface

```
POST /api/agents/register            Register an agent + issue its Spend Passport
GET  /api/agents                     List agents for a user
POST /api/agents/{id}/revoke         Instantly revoke an agent

POST /api/transactions/evaluate      Evaluate a specific product purchase through the full pipeline
POST /api/agents/run                 Run the LLM shopping agent on a natural-language request
POST /api/transactions/approve       Human-approve a REQUIRES_APPROVAL transaction
POST /api/transactions/{id}/reject   Reject a pending transaction
GET  /api/transactions               List transactions (filterable by agent/status)
GET  /api/transactions/{id}/trace    Full explainable decision trace for one transaction

POST /api/payments/verify            Verify a Razorpay client-checkout signature

GET  /api/risk/events                Risk events (velocity anomalies, etc.)
GET  /api/audit                      Full audit log

GET  /api/merchant/list              Demo merchants
GET  /api/merchant/analytics         Merchant-level agent commerce analytics
GET  /api/merchant/recommendations   AI growth engine insights
```

Full interactive docs at `/docs` once the server is running (FastAPI auto-generates OpenAPI/Swagger).

## 9. Local setup

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Fill in RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET from your Razorpay Test Mode
# dashboard to hit the real API. Leave blank to use the mock adapter — the
# whole system, including all four demo scenarios, runs fully without them.

python -m seed.seed_data     # creates the demo user, agent, merchants, products
python -m seed.run_demo      # runs all four scenarios end to end in the terminal

uvicorn app.main:app --reload --port 8000
# Docs: http://localhost:8000/docs
```

### Running the frontend

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```

Click the gear icon in the frontend to point it at the backend (`http://localhost:8000` by default) and enter the demo `agent_id` / `agent_secret` printed by `seed.seed_data`. See `frontend/README.md` for details on the User Console and Merchant Console.

### Running tests

```bash
pytest tests/ -v
```

14 tests covering: valid transaction → ALLOW, over-limit → BLOCK, unauthorized category/merchant → BLOCK, revoked/suspended agent → BLOCK, medium-risk → REQUIRE_APPROVAL, hard-block threshold → BLOCK, full auto-approve→pay flow, payment failure recovery (no duplicate charge), idempotent payment requests, human-approval→pay flow, and abnormal velocity → agent suspension.

## 10. What's implemented vs. what's next

**Implemented and tested:** identity/auth, spend passports, intent scoring, policy engine, risk engine, approval engine, Razorpay Test Mode integration with mock fallback, idempotent payments, audit trail, explainable per-transaction decision trace, merchant growth engine + insights, LLM tool-calling agent with a hard boundary against bypassing the policy engine, 14 passing tests, full REST API.

**Also implemented:** a Next.js/Tailwind frontend (`frontend/`) with a User Console (agents, spend passports, proposing transactions, approvals, risk & audit) and a Merchant Console (agent-commerce analytics + growth insights), including a live animated rendering of the backend's own decision pipeline. It talks to the backend purely over REST — no policy/risk/payment logic is duplicated client-side.

**Roadmap / not yet built:** Postgres deployment config; rate limiting middleware; a real webhook listener for asynchronous Razorpay payment status updates (currently uses synchronous server-side capture, appropriate for a demo but not for production checkout flows).

## 11. On Razorpay

This is a prototype exploring how a payment infrastructure layer could support safe, governed agentic commerce. It is not an official Razorpay product and Razorpay does not endorse this architecture. All payment activity uses Razorpay's Test Mode — no real money moves. When Razorpay credentials aren't configured, a clearly-labeled mock adapter is used instead so the full flow remains demoable.

## 12. Demo data

All merchants (UrbanRun, TechCart, DailyMart, BookNest, LuxeWatch Co) and products are fictional, seeded in INR, and exist purely to demonstrate the flow. Growth-engine insights are computed from this demo dataset and are labeled `is_demo_data: true` everywhere they appear in the API — they are not claims about real-world commerce outcomes.
