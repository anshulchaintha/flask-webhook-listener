# Flask Webhook Listener System

A minimal, secure webhook listener system that accepts mocked payment status updates from payment providers like PayPal or Razorpay.

## Features

- ✅ Secure webhook endpoint with HMAC-SHA256 signature validation
- ✅ Event deduplication using unique event IDs
- ✅ PostgreSQL/SQLite support for event storage
- ✅ RESTful API to query payment events
- ✅ Comprehensive error handling and logging
- ✅ Health check endpoint
- ✅ Mock payload examples included

## Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL (optional, SQLite used by default)
- Git

### Installation

1. **Clone the repository:**
```bash
git clone <your-repo-url>
cd flask-webhook-listener
```

2. **Create a virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables (optional):**
```bash
# Create .env file
echo "WEBHOOK_SECRET=test_secret" > .env
echo "DATABASE_URL=sqlite:///webhooks.db" >> .env
```

5. **Run the application:**
```bash
python app.py
```

The server will start on `http://localhost:8000`

### Using PostgreSQL (Optional)

To use PostgreSQL instead of SQLite:

1. **Install PostgreSQL** and create a database
2. **Set the DATABASE_URL environment variable:**
```bash
export DATABASE_URL="postgresql://username:password@localhost/webhook_db"
```

## Testing the System

### 1. Generate Valid Signatures

First, you need to generate valid HMAC-SHA256 signatures for testing:

```python
import hmac
import hashlib
import json

def generate_signature(payload_file, secret="test_secret"):
    with open(payload_file, 'r') as f:
        payload = f.read()
    
    signature = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    print(f"Signature for {payload_file}: {signature}")

# Generate signatures for all mock files
generate_signature("mock_payloads/payment_authorized.json")
generate_signature("mock_payloads/payment_captured.json")  
generate_signature("mock_payloads/payment_failed.json")
```

### 2. Test Webhook Endpoint

```bash
# Test payment authorized event
curl -X POST http://localhost:8000/webhook/payments \
  -H "Content-Type: application/json" \
  -H "X-Razorpay-Signature: YOUR_GENERATED_SIGNATURE" \
  -d @mock_payloads/payment_authorized.json

# Test payment captured event  
curl -X POST http://localhost:8000/webhook/payments \
  -H "Content-Type: application/json" \
  -H "X-Razorpay-Signature: YOUR_GENERATED_SIGNATURE" \
  -d @mock_payloads/payment_captured.json

# Test payment failed event
curl -X POST http://localhost:8000/webhook/payments \
  -H "Content-Type: application/json" \
  -H "X-Razorpay-Signature: YOUR_GENERATED_SIGNATURE" \
  -d @mock_payloads/payment_failed.json
```

### 3. Query Payment Events

```bash
# Get events for a specific payment
curl http://localhost:8000/payments/pay_014/events

# Health check
curl http://localhost:8000/health
```

### 4. Test Error Scenarios

```bash
# Test invalid signature (should return 403)
curl -X POST http://localhost:8000/webhook/payments \
  -H "Content-Type: application/json" \
  -H "X-Razorpay-Signature: invalid_signature" \
  -d @mock_payloads/payment_authorized.json

# Test missing signature (should return 403)
curl -X POST http://localhost:8000/webhook/payments \
  -H "Content-Type: application/json" \
  -d @mock_payloads/payment_authorized.json

# Test invalid JSON (should return 400)
curl -X POST http://localhost:8000/webhook/payments \
  -H "Content-Type: application/json" \
  -H "X-Razorpay-Signature: test_signature" \
  -d '{"invalid": json}'
```

## Project Structure

```
flask-webhook-listener/
├── app.py                          # Main Flask application
├── requirements.txt                # Python dependencies
├── README.md                       # This file
├── DOCS.md                        # API documentation
├── mock_payloads/                 # Sample webhook payloads
│   ├── payment_authorized.json
│   ├── payment_captured.json
│   └── payment_failed.json
├── tests/                         # Test files (optional)
└── .env                          # Environment variables (create locally)
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `WEBHOOK_SECRET` | Shared secret for signature validation | `test_secret` |
| `DATABASE_URL` | Database connection string | `sqlite:///webhooks.db` |
| `PORT` | Server port | `8000` |

## Production Deployment

### Using Gunicorn

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

### Using Docker (Optional)

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:app"]
```

## Security Considerations

- ✅ HMAC-SHA256 signature validation prevents unauthorized webhook calls
- ✅ Secure signature comparison prevents timing attacks  
- ✅ Input validation on all endpoints
- ✅ SQL injection prevention through SQLAlchemy ORM
- ✅ Error handling without information leakage
- ✅ Request logging for audit trails

## Monitoring and Logging

The application includes comprehensive logging:

- All webhook requests (success/failure)
- Signature validation attempts
- Database operations
- Error conditions

Logs are written to stdout and can be collected by log aggregation systems in production.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.