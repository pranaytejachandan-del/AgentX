# AgentX — Razorpay AI Buildathon 2026 Demo Runbook

> **Autonomous B2B Procurement & Negotiation Agent**
> **Platform Version:** 1.0.0 (Buildathon Special Edition)

---

## 1. System Overview & Architecture

AgentX is an end-to-end autonomous agentic B2B procurement engine. It parses natural-language requirements, discovers and ranks verified vendors, negotiates unit prices statefully within hard financial boundaries using LangGraph, enforces deterministic business guardrails, requires human sign-off for high-value transactions (> ₹100,000), and creates Razorpay TEST MODE Payment Links with automated HMAC-SHA256 webhook confirmation.

---

## 2. Environment Variables Required

Ensure `backend/.env` is configured as follows before starting:

```env
# Database Connection (SQLite local database)
DATABASE_URL=sqlite:///./agentx.db

# Application Configuration
APP_NAME=AgentX
LOG_LEVEL=INFO

# LLM & Embedding Providers (Set to 'mock' for deterministic offline demo)
LLM_PROVIDER=mock
OPENAI_API_KEY=
GEMINI_API_KEY=
EMBEDDING_PROVIDER=mock

# Guardrail & Financial Thresholds
HUMAN_APPROVAL_THRESHOLD=100000.00
POLICY_VERSION=v1

# Razorpay Integration (TEST MODE)
RAZORPAY_KEY_ID=rzp_test_dummykey
RAZORPAY_KEY_SECRET=dummy_secret
RAZORPAY_WEBHOOK_SECRET=dummy_webhook_secret
RAZORPAY_CALLBACK_URL=http://localhost:8000/api/payments/callback
```

---

## 3. Database Startup & Migration Commands

Execute in PowerShell from project root (`agentX`):

```powershell
# 1. Navigate to backend directory
cd backend

# 2. Run database migrations
.venv\Scripts\python.exe -m alembic upgrade head

# 3. Seed database with catalog data (vendors, products, laptops)
.venv\Scripts\python.exe seed.py
```

---

## 4. Backend Startup Command

Run backend API server on port 8000:

```powershell
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- **Health check URL:** `http://127.0.0.1:8000/api/health`
- **Swagger Documentation:** `http://127.0.0.1:8000/docs`

---

## 5. Frontend Startup Command

Run Next.js web application on port 3000:

```powershell
cd frontend
npm run dev
```

- **Dashboard UI URL:** [http://localhost:3000](http://localhost:3000)

---

## 6. Demo Authentication

- **Role:** Procurement Manager
- **Default User:** `manager@company.com` (Pre-seeded into database)
- **No login required** for localhost buildathon demo.

---

## 7. Main Demo Flow (5–7 Minutes)

### Step 1: Submit Natural Language Procurement Request
Enter the following prompt into the AgentX search box on [http://localhost:3000](http://localhost:3000):

> `"Need 50 enterprise laptops with 16GB RAM, delivery within 10 days, and target price below ₹70,000 per unit."`

### Step 2: Intent & Constraint Extraction
Verify extracted JSON constraints displayed in UI:
- **Category:** Electronics / Laptops
- **Quantity:** `50`
- **Target Unit Price:** `₹70,000.00`
- **Max Unit Price:** `₹70,000.00`
- **Max Lead Time:** `10 days`
- **Certifications:** `["ISO-9001", "CE"]`

### Step 3: Vendor & Product Discovery
Show discovered offers hard-filtered and ranked by weighted score (Price 40%, Lead Time 30%, Rating 20%, GST 10%):
- **Top Offer:** `Enterprise Laptop 16GB RAM` (Vendor: OfficePro Supplies, GST Verified)
- **Base Price:** `₹75,000.00` | **Supplier Floor:** `₹62,000.00`

### Step 4: Multi-Turn Autonomous Negotiation (LangGraph FSM)
Show stateful multi-turn negotiation between **Buyer Agent** and **Synthetic Supplier**:
- **Turn 1:** Buyer offers `₹63,000` → Supplier counters `₹66,500`
- **Turn 2:** Buyer counters `₹64,750` → Supplier counters `₹65,000`
- **Turn 3:** Buyer counters `₹64,875` → Supplier **ACCEPTS** `₹64,875`
- **Agreed Deal:** Unit Price: `₹64,875.00` | Quantity: `50` | Total: `₹3,243,750.00`
- **Savings:** `₹506,250.00` below budget ceiling!

### Step 5: Financial Guardrail Check
Deterministic rule evaluation:
- ✓ `validate_max_unit_price`: Passed (`₹64,875 <= ₹70,000`)
- ✓ `validate_max_budget`: Passed (`Total <= ₹3,500,000`)
- ✓ `validate_quantity_integrity`: Passed (`50 units`)
- ✓ `validate_delivery_time`: Passed (`5 days <= 10 days`)
- ✓ `validate_certifications`: Passed (`ISO-9001, CE`)
- ✓ `validate_gst_verification`: Passed
- **Approval Check:** Total amount `₹3,243,750` > `₹100,000` threshold → **Status: APPROVAL_REQUIRED**

### Step 6: Human Approval Workflow
1. Click **Approve Deal** in the dashboard UI.
2. System re-validates guardrails and freezes immutable deal snapshot.
3. Deal state transitions to **READY_FOR_PAYMENT / PAYMENT_PENDING**.

### Step 7: Razorpay TEST MODE Payment Link Creation
1. Click **Initiate Razorpay Payment**.
2. Server calculates total in paise (`324,375,000 paise`).
3. Generates Razorpay Payment Link (`plink_xxx`).
4. Click **Simulate Webhook Success** to send HMAC-SHA256 signed event (`payment_link.paid`).
5. Order state updates to **PAID** and Procurement Request updates to **COMPLETED**.

### Step 8: Execution Trace Inspection
View the full timeline trace on the dashboard showing all 10 state transitions:
`REQUEST_CREATED` → `CONSTRAINTS_PARSED` → `OFFERS_DISCOVERED` → `NEGOTIATION_STARTED` → `DEAL_AGREED` → `POLICY_CHECK` → `APPROVAL_REQUIRED` → `APPROVED` → `PAYMENT_CREATED` → `WEBHOOK_RECEIVED` → `PAID`

---

## 8. Failure Demo Scenario (Budget Exceeded Guardrail)

To demonstrate deterministic safety enforcement:

1. Submit prompt:
   > `"Need 10 enterprise laptops with max budget ceiling ₹40,000 per unit."`
2. Discovery finds lowest vendor minimum price is `₹62,000`.
3. Negotiation fails (`NEGOTIATION_FAILED`): Supplier minimum price exceeds buyer maximum budget.
4. Attempting to force payment returns `HTTP 404 / 400`: **Payment Creation Blocked**.

---

## 9. Troubleshooting & Recovery Procedure

| Problem | Cause | Solution |
| :--- | :--- | :--- |
| `psycopg2.OperationalError` | DATABASE_URL set to Postgres | Set `DATABASE_URL=sqlite:///./agentx.db` in `backend/.env` |
| `Port 8000 already in use` | Old uvicorn process running | Run `Stop-Process -Name python -Force` in PowerShell |
| `Port 3000 already in use` | Old node process running | Run `Stop-Process -Name node -Force` in PowerShell |
| `Missing seed data` | Fresh database | Run `.venv\Scripts\python.exe seed.py` in `backend` |

---

## 10. Backup Demo Strategy

If an live network issue occurs:
1. Run local test script `.venv\Scripts\python.exe scripts/run_e2e_integration_tests.py` to output full colored terminal execution log.
2. Use pre-rendered execution traces on the local SQLite dashboard at `http://localhost:3000/dashboard`.
