# AgentX: Autonomous B2B Procurement Orchestrator

AgentX is an autonomous AI agent platform capable of executing end-to-end B2B commerce tasks based on natural language constraints.

---

## System Architecture

```text
                  AGENTX
                    │
             READY_FOR_PAYMENT
                    │
                    ▼
          Financial Revalidation
                    │
                    ▼
          Razorpay Payment Link
                    │
                    ▼
             Customer Pays
                    │
                    ▼
           Razorpay Webhook
                    │
                    ▼
          Signature Verification
                    │
             ┌──────┴──────┐
             │             │
           VALID         INVALID
             │             │
             ▼             ▼
      Update Payment    Reject
          State
             │
             ▼
        COMPLETED
```

---

## Technical Stack

* **Backend Framework:** FastAPI
* **Orchestration:** LangGraph
* **Database:** PostgreSQL (with `pgvector` extension)
* **ORM:** SQLAlchemy 2.x
* **Database Migrations:** Alembic
* **Payments & Webhooks:** Razorpay Python SDK
* **Configuration:** Pydantic Settings
* **Python Version:** Python 3.11 / 3.12

---

## Directory Structure

```text
agentx/
│
├── backend/
│   ├── app/
│   │   ├── main.py                   # FastAPI entry point & router setup
│   │   ├── config.py                 # Pydantic Settings configuration
│   │   │
│   │   ├── database/
│   │   │   ├── connection.py         # DB Engine, SessionLocal & health checker
│   │   │   └── base.py               # DeclarativeBase setup
│   │   │
│   │   ├── models/
│   │   │   ├── user.py               # User model
│   │   │   ├── vendor.py             # Vendor model (GST verification, ratings)
│   │   │   ├── product.py            # Product model (with pgvector embedding)
│   │   │   ├── procurement_request.py # Procurement Request state machine model
│   │   │   ├── negotiation_trace.py  # Negotiation turn trace model
│   │   │   ├── order.py              # Order & Razorpay fields model
│   │   │   └── audit_event.py        # System audit event model
│   │   │
│   │   ├── services/
│   │   │   ├── intent_parser.py      # Prompt intent & constraint parsing
│   │   │   ├── embedding_service.py  # Vector embedding generation
│   │   │   ├── vendor_discovery.py   # Multi-vendor search & offer ranking
│   │   │   ├── buyer_agent.py        # Autonomous buyer negotiation agent
│   │   │   ├── supplier_simulator.py # Synthetic supplier simulator
│   │   │   ├── negotiation_engine.py # LangGraph negotiation FSM
│   │   │   ├── guardrails/           # Feature 5 Financial Guardrails & Policy Engine
│   │   │   │   ├── engine.py         # Policy check & approval orchestrator
│   │   │   │   ├── rules.py          # 8 deterministic validation rules
│   │   │   │   ├── schemas.py        # Guardrail Pydantic schemas
│   │   │   │   └── exceptions.py     # Policy exceptions
│   │   │   └── payments/             # Feature 6 Razorpay Payment & Webhook Integration
│   │   │       ├── razorpay_client.py# Razorpay client & HMAC signature verifier
│   │   │       ├── payment_service.py# Payment link creation & guardrail re-check
│   │   │       ├── webhook_service.py# Webhook HMAC verification & event handler
│   │   │       ├── schemas.py        # Payment Pydantic schemas
│   │   │       ├── exceptions.py     # Payment exceptions
│   │   │       └── constants.py      # Currency multipliers & event constants
│   │   │
│   │   └── routes/
│   │       ├── health.py             # System & DB health endpoints
│   │       ├── procurement.py        # Intent parsing, policy check, approval & payment endpoints
│   │       ├── discovery.py          # Vendor discovery endpoint
│   │       ├── negotiation.py        # Autonomous negotiation endpoint
│   │       └── payments.py           # Webhook & callback endpoints
│   │
│   ├── alembic/
│   │   └── versions/
│   │       ├── 001_initial_schema.py
│   │       ├── 002_add_deal_snapshot_to_orders.py
│   │       └── 003_add_payment_fields_to_orders.py
│   │
│   ├── seed.py                       # Synthetic marketplace seed script
│   └── tests/                        # Automated unit & integration test suites
│       ├── test_intent_parser.py
│       ├── test_vendor_discovery.py
│       ├── test_negotiation.py
│       ├── test_guardrails.py        # Feature 5 test suite
│       └── test_payments.py          # Feature 6 Razorpay & webhook test suite
│
└── README.md                         # Project documentation
```

---

## Feature 5: Deterministic Financial Safety Guardrail & Human Approval Layer

* **Server-Side Financial Authority**: All deal amounts (`total_amount = quantity × negotiated_unit_price`) are calculated backend-side from database records. Client-supplied total amounts, unit prices, or product overrides are ignored.
* **LLM Boundary**: The LLM / agent cannot approve deals, alter max budget limits, modify requested quantities, or bypass safety guardrails.
* **Guardrail Validation Rules**: Enforces 8 deterministic rules (Unit Price, Budget, Quantity, Delivery, Certifications, GST, Currency, Entity Integrity).
* **Configurable Approval Threshold**: Default threshold set to `HUMAN_APPROVAL_THRESHOLD = 100000.00` (₹100,000). Deals exceeding ₹100,000 require human authorization (`APPROVAL_REQUIRED`).

---

## Feature 6: Razorpay Payment Execution & Webhook Integration

### 1. Security & Execution Boundaries
* **Strict State Boundary**: Payment link creation is strictly restricted to requests in `READY_FOR_PAYMENT` state (or `PAYMENT_PENDING` with completed approval).
* **Pre-Payment Revalidation**: Re-runs Feature 5 guardrails before creating the Razorpay Payment Link.
* **Server-Side Authoritative Amount**: Payment amount is calculated strictly backend-side in smallest currency unit (paise for INR: `₹72,500 = 7,250,000 paise`). Request-body amount overrides are completely ignored.
* **Raw HMAC-SHA256 Signature Verification**: `POST /api/payments/webhook` verifies `X-Razorpay-Signature` against the exact RAW request bytes using `RAZORPAY_WEBHOOK_SECRET` before parsing JSON.
* **Event Idempotency**: Header `x-razorpay-event-id` is tracked in audit events to prevent duplicate event processing.

### 2. Supported Webhook Events
* `payment_link.paid`: Validates amount, marks order `PAID`, procurement `COMPLETED`, logs `PAYMENT_CONFIRMED`.
* `payment_link.partially_paid`: Records partial payment, retains `PAYMENT_PENDING` status.
* `payment_link.cancelled`: Marks order `CANCELLED`, procurement `CANCELLED`.
* `payment_link.expired`: Marks order `EXPIRED`, procurement `FAILED`.

---

## Available API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Service status identification |
| `GET` | `/health` | DB connectivity check |
| `POST` | `/api/procurement/parse` | Parse prompt into procurement constraints |
| `POST` | `/api/procurement/discover` | Discover and rank matching vendors |
| `POST` | `/api/procurement/negotiate` | Execute LangGraph autonomous negotiation |
| `POST` | `/api/procurement/{id}/policy-check` | Execute deterministic financial guardrails |
| `POST` | `/api/procurement/{id}/approve` | Grant human approval for a pending deal |
| `POST` | `/api/procurement/{id}/reject` | Reject a pending deal |
| `POST` | `/api/procurement/{id}/payment` | Create Razorpay Payment Link for READY_FOR_PAYMENT deal |
| `POST` | `/api/payments/webhook` | Process raw Razorpay HMAC-signed webhooks |
| `GET/POST` | `/api/payments/callback` | Browser user redirect callback endpoint |

---

## Setup & Running Instructions

### 1. Environment Setup & Dependencies
```bash
cd backend
python -m venv .venv
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
pip install pytest pytest-asyncio
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and set Razorpay test credentials:
```env
RAZORPAY_KEY_ID=your_test_key_id
RAZORPAY_KEY_SECRET=your_test_key_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
RAZORPAY_CALLBACK_URL=http://localhost:8000/api/payments/callback
```

### 3. Migrations & Seeding
```bash
alembic upgrade head
python seed.py
```

### 4. Run FastAPI Application
```bash
uvicorn app.main:app --reload
```

### 5. Run Complete Test Suite
```bash
pytest tests/
```
