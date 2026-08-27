# AgentPay Frontend

Next.js + Tailwind dashboards for the AgentPay backend: a **User Console**
(agents, spend passports, proposing transactions, approvals, risk & audit)
and a **Merchant Console** (agent-commerce analytics + growth insights).

This talks to the existing FastAPI backend over its REST API — it doesn't
change or duplicate any backend logic. All policy/risk/payment decisions
still happen server-side; this is purely the view + the forms that call it.

## 1. Run the backend first

From the `backend/` folder of the AgentPay project:

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m seed.seed_data     # prints a demo agent_id + agent_secret — save it
uvicorn app.main:app --reload --port 8000
```

## 2. Run this frontend

```bash
npm install
npm run dev
```

Open http://localhost:3000.

## 3. Point it at your backend

Click the gear icon (top right). Set:

- **API base URL** — `http://localhost:8000` by default.
- **Owner / user id** — `USR-demo1` if you used the seed script as-is.
- **Agent id** / **Agent secret** — from the `seed_data` output, or from a
  new agent you register in the Agents panel (the secret is shown once,
  right after registration, and auto-fills here).

These are stored in your browser's `localStorage` so they persist across
reloads. Nothing is sent anywhere except your own backend at the URL you set.

## What's here

- `app/page.js` — User Console: agents + spend passports, propose a
  transaction (evaluate a specific product, or drive the natural-language
  LLM shopping agent), transactions table, risk events, audit log.
- `app/merchant/page.js` — Merchant Console: per-merchant analytics and
  rule-based growth insights (both labeled `is_demo_data` as the backend
  returns them).
- `app/components/PipelineTrace.jsx` — the signature visual: a literal
  rendering of the backend's own pipeline (Identity → Intent → Policy →
  Risk → Payment → Audit), animated live while a proposal is in flight and
  used again as a static decision trace in the transaction detail modal.
- `app/lib/api.js` — the only place that talks to the backend; every
  documented endpoint in the backend's README has a matching function here.
- `app/lib/store.js` — small `localStorage`-backed hook for the API URL and
  demo credentials.

## Notes

- The product picker in "Evaluate a product" is a static mirror of
  `seed/seed_data.py`'s demo catalog — the backend doesn't currently expose
  a product-listing endpoint, so this is a frontend-only convenience list
  matching the seeded ids/prices/categories.
- Fonts (Space Grotesk / Inter / JetBrains Mono) are bundled locally via
  `@fontsource`, so the build doesn't depend on reaching Google Fonts.
