# test_helpers.py
import copy
import uuid
import requests

BASE_URL = "http://localhost:8000"

def clear_payment_events():
    """
    Helper to clear payment events from the database before tests.
    Since your tests use HTTP, this requires a dedicated admin endpoint
    or DB access — if none, this can be a no-op or you can add such endpoint.
    """
    # Example: Call an admin API endpoint to clear events (if exists)
    # requests.post(f"{BASE_URL}/admin/clear_events")
    pass

def get_unique_payload(base_payload):
    """
    Returns a deep copy of base_payload with a unique event ID.
    """
    payload = copy.deepcopy(base_payload)
    unique_id = f"evt_test_{uuid.uuid4().hex[:8]}"

    if isinstance(payload, list):
        for event in payload:
            event['id'] = unique_id
    else:
        payload['id'] = unique_id

    return payload
