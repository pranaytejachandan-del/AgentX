import requests
import json

BASE = 'http://127.0.0.1:8000'

print("=" * 80)
print("AGENTX FINAL JUDGE DEMO FLOW VERIFICATION SCRIPT")
print("Target State Machine: CREATED -> PARSING -> DISCOVERY -> NEGOTIATION -> POLICY_CHECK -> APPROVAL_REQUIRED -> [APPROVE DEAL] -> PAYMENT_READY")
print("=" * 80)

# 1. Reset Demo State
print("\n--- 1. RESETTING DEMO STATE ---")
res_reset = requests.post(f'{BASE}/api/procurement/reset-demo')
assert res_reset.status_code == 200, f"Reset failed: {res_reset.text}"
print('[PASS] RESET DEMO:', res_reset.json()['message'])

# 2. Submit Demo Procurement Request (natural language prompt)
print("\n--- 2. SUBMITTING DEMO PROCUREMENT REQUEST ---")
prompt = 'I need 50 enterprise laptops with 16GB RAM, delivery within 10 days, and a target price below ₹70,000 per unit.'
res_orch = requests.post(f'{BASE}/api/procurement/orchestrate', json={'prompt': prompt})
assert res_orch.status_code == 200, f"Orchestrate failed: {res_orch.text}"
data = res_orch.json()

req = data['request']
order = data.get('order')
offers = data.get('discovered_offers', [])
traces = data.get('negotiation_traces', [])
guardrail = data.get('guardrail_result', {})

req_id = req['id']

print(f"[PASS] Request ID: {req_id}")
print(f"[PASS] Parsed Quantity: {req['extracted_constraints']['quantity']}")
print(f"[PASS] Parsed Max Unit Price: INR {float(req['extracted_constraints']['max_unit_price']):,.2f}")
print(f"[PASS] Discovered Offers Count: {len(offers)}")
assert len(offers) > 0, "At least one eligible offer must be discovered"

top_offer = offers[0]
print(f"[PASS] Top Discovered Vendor: {top_offer['vendor_name']}")
print(f"[PASS] Top Product: {top_offer['product_name']}")
print(f"[PASS] Base Unit Price: INR {float(top_offer['base_price']):,.2f}")
print(f"[PASS] Score: {top_offer['overall_score']}")
print(f"[PASS] Eligibility Status: {top_offer['eligibility_status']}")

print(f"[PASS] Negotiation Turns Executed: {len(traces)}")
assert len(traces) > 0, "Multi-turn negotiation must run automatically"

assert guardrail.get('status') == 'APPROVAL_REQUIRED', f"Expected APPROVAL_REQUIRED, got {guardrail.get('status')}"
print(f"[PASS] Financial Guardrail Status: {guardrail.get('status')} (Threshold > INR 100,000)")

assert order is not None, "Order record must be created by negotiation engine"
print(f"[PASS] Order ID: {order['id']}, Negotiated Unit Price: INR {float(order['negotiated_unit_price']):,.2f}, Total Amount: INR {float(order['total_amount']):,.2f}")
print(f"[PASS] Execution Status BEFORE Approval: {req['execution_status']}")
assert req['execution_status'] == 'APPROVAL_REQUIRED', f"Expected APPROVAL_REQUIRED, got {req['execution_status']}"

# 3. Manually Approve Deal (Simulating user clicking "Approve Deal" button)
print("\n--- 3. USER CLICKS [ APPROVE DEAL ] ---")
res_app = requests.post(f'{BASE}/api/procurement/{req_id}/approve', json={'notes': 'Approved by Hackathon Judge'})
assert res_app.status_code == 200, f"Approve API failed: {res_app.text}"
app_data = res_app.json()

print(f"[PASS] Approval Status: {app_data['approval_status']}")
print(f"[PASS] Execution Status AFTER Approval: {app_data['execution_status']}")
print(f"[PASS] Backend Message: {app_data['message']}")

assert app_data['approval_status'] == 'APPROVED', f"Expected APPROVED, got {app_data['approval_status']}"
assert app_data['execution_status'] == 'READY_FOR_PAYMENT', f"Expected READY_FOR_PAYMENT, got {app_data['execution_status']}"

# 4. Verify Final State via GET /api/procurement/{id}
print("\n--- 4. VERIFYING FINAL DEMO STATE (STOP AT PAYMENT READY) ---")
res_final = requests.get(f'{BASE}/api/procurement/{req_id}')
assert res_final.status_code == 200, f"Get detail failed: {res_final.text}"
final_data = res_final.json()

final_req = final_data['request']
final_order = final_data['order']

print(f"[PASS] Final Execution Stage: {final_req['execution_status']}")
print(f"[PASS] Final Order Approval Status: {final_order['approval_status']}")
print(f"[PASS] Final Total Amount: INR {float(final_order['total_amount']):,.2f}")

assert final_req['execution_status'] == 'READY_FOR_PAYMENT', f"Expected READY_FOR_PAYMENT, got {final_req['execution_status']}"
assert final_order['approval_status'] == 'APPROVED', f"Expected APPROVED, got {final_order['approval_status']}"

print("\n" + "=" * 80)
print("FINAL JUDGE DEMO WORKFLOW (CREATED -> PARSING -> DISCOVERY -> NEGOTIATION -> POLICY_CHECK -> APPROVAL -> PAYMENT_READY) VERIFIED 100% SUCCESSFUL!")
print("=" * 80)
