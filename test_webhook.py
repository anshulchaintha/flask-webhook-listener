#!/usr/bin/env python3
"""
Test script for the Flask webhook listener system.
"""

import requests
import hmac
import hashlib
import json
import time
from typing import Dict, Any
from test_helpers import clear_payment_events,get_unique_payload
import json

BASE_URL = "http://localhost:8000"
SECRET = "test_secret"

def generate_signature(payload: str, secret: str = SECRET) -> str:
    """Generate HMAC-SHA256 signature for payload."""
    return hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def send_webhook(payload: Dict[Any, Any], signature: str = None) -> requests.Response:
    """Send webhook request to the server."""
    payload_str = json.dumps(payload, separators=(',', ':'))
    
    if signature is None:
        signature = generate_signature(payload_str)
    
    headers = {
        'Content-Type': 'application/json',
        'X-Razorpay-Signature': signature
    }
    
    return requests.post(f"{BASE_URL}/webhook/payments", 
                        headers=headers, 
                        data=payload_str)

def get_payment_events(payment_id: str) -> requests.Response:
    """Get events for a payment ID."""
    return requests.get(f"{BASE_URL}/payments/{payment_id}/events")
from test_helpers import get_unique_payload, clear_payment_events

def test_valid_webhook():
    print("🧪 Testing valid webhook processing...")

    base_payload = {
        "event": "payment.authorized",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_001",
                    "status": "authorized",
                    "amount": 5000,
                    "currency": "INR"
                }
            }
        },
        "created_at": int(time.time()),
        "id": "evt_test_001"  # will be overwritten
    }

    # Get payload with unique event ID
    payload = get_unique_payload(base_payload)

    response = send_webhook(payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    assert response.status_code == 200
    # Adjust assert depending on your webhook response structure:
    # e.g. if response returns {'event_id': ..., 'status': ...}
    assert response.json()["status"] == "success"
    print("✅ Valid webhook test passed\n")
def test_duplicate_event():
    print("🧪 Testing duplicate event handling...")

    payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_002",
                    "status": "captured",
                    "amount": 3000,
                    "currency": "INR"
                }
            }
        },
        "created_at": int(time.time()),
        "id": "evt_test_duplicate"  # fixed for duplicate test
    }

    # Send first time
    response1 = send_webhook(payload)
    print(f"First request - Status: {response1.status_code}")
    print(f"First request - Response: {response1.json()}")

    # Send duplicate
    response2 = send_webhook(payload)
    print(f"Duplicate request - Status: {response2.status_code}")
    print(f"Duplicate request - Response: {response2.json()}")

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response2.json()["status"] == "duplicate"
    print("✅ Duplicate event test passed\n")

def test_invalid_signature():
    """Test invalid signature handling."""
    print("🧪 Testing invalid signature handling...")
    
    payload = {
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_003",
                    "status": "failed",
                    "amount": 2000,
                    "currency": "INR"
                }
            }
        },
        "created_at": int(time.time()),
        "id": "evt_test_003"
    }
    
    response = send_webhook(payload, signature="invalid_signature")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    assert response.status_code == 403
    assert "Invalid signature" in response.json()["error"]
    print("✅ Invalid signature test passed\n")

def test_missing_signature():
    """Test missing signature header."""
    print("🧪 Testing missing signature header...")
    
    payload = {
        "event": "payment.authorized",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_004",
                    "status": "authorized",
                    "amount": 1500,
                    "currency": "INR"
                }
            }
        },
        "created_at": int(time.time()),
        "id": "evt_test_004"
    }
    
    headers = {'Content-Type': 'application/json'}
    response = requests.post(f"{BASE_URL}/webhook/payments", 
                           headers=headers, 
                           json=payload)
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    assert response.status_code == 403
    assert "Missing signature" in response.json()["error"]
    print("✅ Missing signature test passed\n")

def test_invalid_json():
    """Test invalid JSON handling."""
    print("🧪 Testing invalid JSON handling...")
    
    headers = {
        'Content-Type': 'application/json',
        'X-Razorpay-Signature': 'test_signature'
    }
    
    response = requests.post(f"{BASE_URL}/webhook/payments", 
                           headers=headers, 
                           data='{"invalid": json}')
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    assert response.status_code == 400
    assert "Invalid JSON" in response.json()["error"]
    print("✅ Invalid JSON test passed\n")

def test_payment_events_query():
    """Test payment events query."""
    print("🧪 Testing payment events query...")
    
    # First, create some events for a payment
    payment_id = "pay_query_test"
    events = [
        {
            "event": "payment.authorized",
            "payload": {
                "payment": {
                    "entity": {
                        "id": payment_id,
                        "status": "authorized",
                        "amount": 5000,
                        "currency": "INR"
                    }
                }
            },
            "created_at": int(time.time()),
            "id": "evt_query_001"
        },
        {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": payment_id,
                        "status": "captured",
                        "amount": 5000,
                        "currency": "INR"
                    }
                }
            },
            "created_at": int(time.time()) + 60,
            "id": "evt_query_002"
        }
    ]
    
    # Send events
    for event in events:
        response = send_webhook(event)
        assert response.status_code == 200
        print(f"Created event: {event['event']}")
    
    # Query events
    response = get_payment_events(payment_id)
    print(f"Query status: {response.status_code}")
    print(f"Query response: {response.json()}")
    
    assert response.status_code == 200
    events_data = response.json()
    assert len(events_data) == 2
    assert events_data[0]["event_type"] == "payment.authorized"
    assert events_data[1]["event_type"] == "payment.captured"
    print("✅ Payment events query test passed\n")

def test_empty_events_query():
    """Test query for non-existent payment."""
    print("🧪 Testing empty events query...")
    
    response = get_payment_events("pay_nonexistent")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    assert response.status_code == 200
    assert response.json() == []
    print("✅ Empty events query test passed\n")

def test_health_check():
    """Test health check endpoint."""
    print("🧪 Testing health check...")
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    print("✅ Health check test passed\n")

def run_all_tests():
    """Run all tests."""
    print("🚀 Starting webhook system tests...\n")
    clear_payment_events()
    try:
        # Check if server is running
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            raise Exception("Server not responding properly")
    except Exception as e:
        print(f"❌ Error: Server is not running at {BASE_URL}")
        print("Please start the Flask application first: python app.py")
        return False
    
    tests = [
        test_health_check,
        test_valid_webhook,
        test_duplicate_event,
        test_invalid_signature,
        test_missing_signature,
        test_invalid_json,
        test_payment_events_query,
        test_empty_events_query
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed: {e}")
            failed += 1
    
    print(f"\n📊 Test Results:")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Success Rate: {(passed/(passed+failed)*100):.1f}%")
    
    if failed == 0:
        print("\n🎉 All tests passed! The webhook system is working correctly.")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please check the implementation.")
    
    return failed == 0

if __name__ == "__main__":
    run_all_tests()