# API Documentation

## Overview

This document describes the REST API endpoints for the Flask Webhook Listener System. The system provides secure webhook handling for payment status updates with signature validation and event deduplication.

## Base URL

```
http://localhost:8000
```

## Authentication

All webhook endpoints require HMAC-SHA256 signature validation using a shared secret.

**Shared Secret:** `test_secret` (configurable via `WEBHOOK_SECRET` environment variable)

## Endpoints

### 1. Webhook Receiver

Accepts payment status update webhooks from payment providers.

**Endpoint:** `POST /webhook/payments`

**Headers:**
- `Content-Type: application/json` (required)
- `X-Razorpay-Signature: <hmac_signature>` (required)

**Request Body:**
Razorpay webhook payload format:

```json
{
  "event": "payment.authorized",
  "payload": {
    "payment": {
      "entity": {
        "id": "pay_014",
        "status": "authorized",
        "amount": 5000,
        "currency": "INR"
      }
    }
  },
  "created_at": 1751889865,
  "id": "evt_auth_014"
}
```

**Signature Generation:**
```python
import hmac
import hashlib

def generate_signature(payload_body, secret="test_secret"):
    return hmac.new(
        secret.encode('utf-8'),
        payload_body.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
```

**Success Response (200):**
```json
{
  "status": "success",
  "event_id": "evt_auth_014",
  "payment_id": "pay_014"
}
```

**Duplicate Event Response (200):**
```json
{
  "status": "duplicate",
  "message": "Event already processed",
  "event_id": "evt_auth_014"
}
```

**Error Responses:**

*400 Bad Request - Invalid JSON:*
```json
{
  "error": "Invalid JSON format"
}
```

*400 Bad Request - Invalid Payload:*
```json
{
  "error": "Invalid payload structure: Missing required fields"
}
```

*403 Forbidden - Missing Signature:*
```json
{
  "error": "Missing signature header"
}
```

*403 Forbidden - Invalid Signature:*
```json
{
  "error": "Invalid signature"
}
```

*500 Internal Server Error:*
```json
{
  "error": "Internal server error"
}
```

**Example cURL:**
```bash
curl -X POST http://localhost:8000/webhook/payments \
  -H "Content-Type: application/json" \
  -H "X-Razorpay-Signature: a1b2c3d4e5f6..." \
  -d '{
    "event": "payment.authorized",
    "payload": {
      "payment": {
        "entity": {
          "id": "pay_014",
          "status": "authorized",
          "amount": 5000,
          "currency": "INR"
        }
      }
    },
    "created_at": 1751889865,
    "id": "evt_auth_014"
  }'
```

### 2. Payment Events Query

Retrieves all events for a specific payment ID, sorted chronologically.

**Endpoint:** `GET /payments/{payment_id}/events`

**Path Parameters:**
- `payment_id` (string): The payment identifier

**Success Response (200):**
```json
[
  {
    "event_type": "payment.authorized",
    "received_at": "2025-07-08T12:00:00Z"
  },
  {
    "event_type": "payment.captured", 
    "received_at": "2025-07-08T12:01:23Z"
  }
]
```

**Empty Result (200):**
```json
[]
```

**Error Response (500):**
```json
{
  "error": "Internal server error"
}
```

**Example cURL:**
```bash
curl http://localhost:8000/payments/pay_014/events
```

### 3. Health Check

Returns the system health status.

**Endpoint:** `GET /health`

**Success Response (200):**
```json
{
  "status": "healthy",
  "timestamp": "2025-07-08T12:00:00.000000"
}
```

**Example cURL:**
```bash
curl http://localhost:8000/health
```

## Event Types

The system supports the following Razorpay event types:

| Event Type | Description |
|------------|-------------|
| `payment.authorized` | Payment has been authorized |
| `payment.captured` | Payment has been captured |
| `payment.failed` | Payment has failed |

## Error Codes

| HTTP Status | Description |
|-------------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid input |
| 403 | Forbidden - Authentication failed |
| 404 | Not Found - Endpoint doesn't exist |
| 405 | Method Not Allowed - Invalid HTTP method |
| 500 | Internal Server Error |

## Data Models

### Payment Event

```json
{
  "id": 1,
  "event_id": "evt_auth_014",
  "payment_id": "pay_014", 
  "event_type": "payment.authorized",
  "raw_payload": "{...}",
  "received_at": "2025-07-08T12:00:00Z"
}
```

**Field Descriptions:**
- `id`: Auto-generated primary key
- `event_id`: Unique identifier from webhook payload (used for deduplication)
- `payment_id`: Payment identifier extracted from payload
- `event_type`: Type of payment event
- `raw_payload`: Complete webhook payload as JSON string
- `received_at`: Timestamp when event was received (UTC)

## Idempotency

The system ensures idempotency through unique `event_id` constraints:

- Each `event_id` can only be processed once
- Duplicate events return success status but are not re-processed
- This prevents duplicate processing of webhook retries

## Rate Limiting

Currently, no rate limiting is implemented. In production, consider adding:

- Request rate limiting per IP
- Signature validation rate limiting
- Database connection pooling

## Webhook Retry Handling

The system handles webhook retries gracefully:

- Returns 200 status for duplicate events
- Maintains idempotency through event IDs
- Logs all processing attempts

## Testing Guide

### Mock Payloads

Three sample payloads are provided in `mock_payloads/`:

1. **payment_authorized.json** - Payment authorization event
2. **payment_captured.json** - Payment capture event  
3. **payment_failed.json** - Payment failure event

### Signature Generation Script

```python
import hmac
import hashlib
import json

def generate_test_signature(payload_file):
    with open(payload_file, 'r') as f:
        payload = f.read()
    
    signature = hmac.new(
        b'test_secret',
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return signature

# Usage
sig = generate_test_signature('mock_payloads/payment_authorized.json')
print(f"X-Razorpay-Signature: {sig}")
```

### Test Scenarios

1. **Valid Webhook Processing**
   - Send valid payload with correct signature
   - Verify 200 response and database storage

2. **Duplicate Event Handling**
   - Send same event twice
   - Verify second request returns duplicate status

3. **Signature Validation**
   - Test invalid signatures (403 response)
   - Test missing signatures (403 response)

4. **Input Validation**
   - Test malformed JSON (400 response)
   - Test missing required fields (400 response)

5. **Event Querying**
   - Query events for existing payment ID
   - Query events for non-existent payment ID (empty array)

## Security Best Practices

1. **Always validate signatures** - Never process webhooks without signature verification
2. **Use HTTPS in production** - Encrypt all webhook traffic
3. **Implement rate limiting** - Prevent abuse and DoS attacks
4. **Log security events** - Monitor for suspicious activity
5. **Keep secrets secure** - Use environment variables for sensitive data
6. **Validate input thoroughly** - Sanitize all incoming data

## Troubleshooting

### Common Issues

1. **403 Forbidden Responses**
   - Check signature generation algorithm
   - Verify shared secret matches
   - Ensure raw payload is used for signature

2. **400 Bad Request Responses**
   - Validate JSON syntax
   - Check required fields are present
   - Verify payload structure matches expected format

3. **500 Internal Server Error**
   - Check database connectivity
   - Review application logs
   - Verify all dependencies are installed

### Debug Mode

Enable debug logging by setting Flask debug mode:

```python
app.run(debug=True)
```

Or set environment variable:
```bash
export FLASK_DEBUG=1
```