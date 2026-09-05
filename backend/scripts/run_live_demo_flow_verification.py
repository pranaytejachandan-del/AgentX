import requests
import json
import hmac
import hashlib

BASE = 'http://127.0.0.1:8000'

print("=" * 80)
print("AGENTX LIVE HACKATHON DEMO END-TO-END VERIFICATION SCRIPT")
print("=" * 80)

# 1. Reset Demo State
print("\n--- 1. RESETTING DEMO STATE ---")
res_reset = requests.post(f'{BASE}/api/procurement/reset-demo')
assert res_reset.status_code == 200, f"Reset failed: {res_reset.text}"
print('[PASS] RESET STATUS:', res_reset.status_code, res_reset.json()['message'])

# 2. Submit Demo Procurement Request
print("\n--- 2. SUBMITTING DEMO PROCUREMENT REQUEST ---")
prompt = 'I need 50 enterprise laptops with 16GB RAM, delivery within 10 days, and a target price below ₹70,000 per unit.'
res_orch = requests.post(f'{BASE}/api/procurement/orchestrate', json={'prompt': prompt})
assert res_orch.status_code == 200, f"Orchestrate failed: {res_orch.text}"
data = res_orch.json()
req = data['request']
order = data.get('order')
req_id = req['id']

print(f"[PASS] Request #{req_id}: Execution Status={req['execution_status']}")
print(f"[PASS] Discovered Offers: {len(data.get('discovered_offers', []))}")
print(f"[PASS] Negotiation Traces: {len(data.get('negotiation_traces', []))}")
print(f"[PASS] Guardrail Result: {data.get('guardrail_result', {}).get('status')}")
assert order is not None, "Order record must exist"
print(f"[PASS] Order #{order.get('id')}: Total={order.get('total_amount')}, Approval={order.get('approval_status')}")
assert req['execution_status'] == 'APPROVAL_REQUIRED', f"Expected APPROVAL_REQUIRED, got {req['execution_status']}"

# 3. Approve Deal
print("\n--- 3. APPROVING DEAL ---")
res_app = requests.post(f'{BASE}/api/procurement/{req_id}/approve', json={'notes': 'Approved by Hackathon Judge'})
assert res_app.status_code == 200, f"Approve failed: {res_app.text}"
app_data = res_app.json()
print('[PASS] APPROVE RESPONSE:', app_data['execution_status'], app_data['message'])
assert app_data['execution_status'] == 'READY_FOR_PAYMENT'

# 4. Create Payment Link
print("\n--- 4. CREATING RAZORPAY PAYMENT LINK ---")
res_pay = requests.post(f'{BASE}/api/procurement/{req_id}/payment')
assert res_pay.status_code == 200, f"Payment link creation failed: {res_pay.text}"
pay_data = res_pay.json()
plink_id = pay_data['razorpay_payment_link_id']
amount = pay_data['amount']
print('[PASS] PAYMENT LINK CREATED:', pay_data['payment_status'], f"ID={plink_id}", f"URL={pay_data['payment_url']}")
assert pay_data['payment_status'] == 'PAYMENT_PENDING'

# 5. Process Verified Webhook
print("\n--- 5. SIMULATING RAZORPAY PAYMENT WEBHOOK ---")
secret = 'dummy_webhook_secret'
payload = {
    'event': 'payment_link.paid',
    'payload': {
        'payment_link': {
            'entity': {
                'id': plink_id,
                'amount': amount,
                'amount_paid': amount,
                'status': 'paid'
            }
        },
        'payment': {
            'entity': {
                'id': 'pay_live_demo_123',
                'amount': amount,
                'currency': 'INR',
                'status': 'captured'
            }
        }
    }
}
raw_body = json.dumps(payload, separators=(',', ':')).encode('utf-8')
sig = hmac.new(secret.encode('utf-8'), raw_body, hashlib.sha256).hexdigest()

res_wh = requests.post(
    f'{BASE}/api/payments/webhook',
    data=raw_body,
    headers={
        'Content-Type': 'application/json',
        'X-Razorpay-Signature': sig
    }
)
assert res_wh.status_code == 200, f"Webhook failed: {res_wh.text}"
print('[PASS] WEBHOOK VERIFIED:', res_wh.json()['message'])

# 6. Verify Final Completed State
print("\n--- 6. VERIFYING FINAL COMPLETED DEMO STATE ---")
res_final = requests.get(f'{BASE}/api/procurement/{req_id}')
assert res_final.status_code == 200, f"Detail lookup failed: {res_final.text}"
final_data = res_final.json()
print('[PASS] FINAL EXECUTION STATUS:', final_data['request']['execution_status'])
print('[PASS] FINAL PAYMENT STATUS:', final_data['order']['payment_status'])
print('[PASS] TOTAL AMOUNT:', final_data['order']['total_amount'])
assert final_data['request']['execution_status'] == 'COMPLETED'
assert final_data['order']['payment_status'] == 'PAID'

# 7. Repeated Execution Test
print("\n--- 7. SUBMITTING SECOND PROCUREMENT REQUEST (REPEATED EXECUTION TEST) ---")
prompt_2 = 'I need 10 executive business laptops with 16GB RAM, delivery within 7 days, max price ₹80,000 per unit.'
res_orch_2 = requests.post(f'{BASE}/api/procurement/orchestrate', json={'prompt': prompt_2})
assert res_orch_2.status_code == 200
data_2 = res_orch_2.json()
req_2 = data_2['request']
order_2 = data_2.get('order')
req_id_2 = req_2['id']

print(f"[PASS] Second Request #{req_id_2}: Execution Status={req_2['execution_status']}")
print(f"[PASS] Second Discovered Offers: {len(data_2.get('discovered_offers', []))}")
assert order_2 is not None
print(f"[PASS] Second Order #{order_2.get('id')}: Total={order_2.get('total_amount')}, Approval={order_2.get('approval_status')}")

# Approve second deal
res_app_2 = requests.post(f'{BASE}/api/procurement/{req_id_2}/approve', json={'notes': 'Second Approved'})
assert res_app_2.status_code == 200
print('[PASS] SECOND APPROVE STATUS:', res_app_2.json()['execution_status'])

# Create payment link for second deal
res_pay_2 = requests.post(f'{BASE}/api/procurement/{req_id_2}/payment')
assert res_pay_2.status_code == 200
pay_data_2 = res_pay_2.json()
plink_id_2 = pay_data_2['razorpay_payment_link_id']
amount_2 = pay_data_2['amount']
print('[PASS] SECOND PAYMENT LINK STATUS:', pay_data_2['payment_status'])

# Send webhook for second deal
payload_2 = {
    'event': 'payment_link.paid',
    'payload': {
        'payment_link': {
            'entity': {
                'id': plink_id_2,
                'amount': amount_2,
                'amount_paid': amount_2,
                'status': 'paid'
            }
        },
        'payment': {
            'entity': {
                'id': 'pay_live_demo_456',
                'amount': amount_2,
                'currency': 'INR',
                'status': 'captured'
            }
        }
    }
}
raw_body_2 = json.dumps(payload_2, separators=(',', ':')).encode('utf-8')
sig_2 = hmac.new(secret.encode('utf-8'), raw_body_2, hashlib.sha256).hexdigest()

res_wh_2 = requests.post(
    f'{BASE}/api/payments/webhook',
    data=raw_body_2,
    headers={
        'Content-Type': 'application/json',
        'X-Razorpay-Signature': sig_2
    }
)
assert res_wh_2.status_code == 200
print('[PASS] SECOND WEBHOOK STATUS:', res_wh_2.json()['message'])

res_final_2 = requests.get(f'{BASE}/api/procurement/{req_id_2}')
final_data_2 = res_final_2.json()
print('[PASS] SECOND FINAL EXECUTION STATUS:', final_data_2['request']['execution_status'])
print('[PASS] SECOND FINAL PAYMENT STATUS:', final_data_2['order']['payment_status'])
assert final_data_2['request']['execution_status'] == 'COMPLETED'
assert final_data_2['order']['payment_status'] == 'PAID'

print("\n" + "=" * 80)
print("ALL DEMO STAGES AND REPEATED EXECUTION TESTS PASSED FLAWLESSLY 100%!")
print("=" * 80)
