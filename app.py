import os
import hmac
import hashlib
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, DateTime, Text, UniqueConstraint
from sqlalchemy.exc import IntegrityError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///webhooks.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WEBHOOK_SECRET'] = os.environ.get('WEBHOOK_SECRET', 'test_secret')

db = SQLAlchemy(app)

# Database Model
class PaymentEvent(db.Model):
    __tablename__ = 'payment_events'
    
    id = Column(Integer, primary_key=True)
    event_id = Column(String(100), unique=True, nullable=False)
    payment_id = Column(String(100), nullable=False)
    event_type = Column(String(50), nullable=False)
    raw_payload = Column(Text, nullable=False)
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Ensure unique event_id for idempotency
    __table_args__ = (
        UniqueConstraint('event_id', name='unique_event_id'),
    )
    
    def to_dict(self):
        return {
            'event_type': self.event_type,
            'received_at': self.received_at.isoformat() + 'Z'
        }

# Utility Functions
def verify_signature(payload_body: bytes, signature: str, secret: str) -> bool:
    """
    Verify webhook signature using HMAC-SHA256
    """
    try:
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload_body,
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures securely to prevent timing attacks
        return hmac.compare_digest(signature, expected_signature)
    except Exception as e:
        logger.error(f"Signature verification error: {e}")
        return False

def parse_razorpay_payload(payload: dict) -> tuple:
    """
    Parse Razorpay webhook payload to extract required fields
    Returns: (event_type, event_id, payment_id)
    """
    try:
        event_type = payload.get('event')
        event_id = payload.get('id')
        payment_id = payload.get('payload', {}).get('payment', {}).get('entity', {}).get('id')
        
        if not all([event_type, event_id, payment_id]):
            raise ValueError("Missing required fields in payload")
            
        return event_type, event_id, payment_id
    except Exception as e:
        logger.error(f"Payload parsing error: {e}")
        raise ValueError(f"Invalid payload structure: {e}")

# Routes
@app.route('/webhook/payments', methods=['POST'])
def webhook_payments():
    """
    Webhook endpoint to receive payment status updates
    """
    try:
        # Get raw payload for signature verification
        raw_payload = request.get_data()

        # Validate JSON
        try:
            payload = request.get_json(force=True)
        except Exception:
            logger.warning("Invalid JSON received")
            return jsonify({'error': 'Invalid JSON format'}), 400

        # Check for signature header
        signature = request.headers.get('X-Razorpay-Signature')
        if not signature:
            logger.warning("Missing signature header")
            return jsonify({'error': 'Missing signature header'}), 403

        # Verify signature
        if not verify_signature(raw_payload, signature, app.config['WEBHOOK_SECRET']):
            logger.warning("Invalid signature")
            return jsonify({'error': 'Invalid signature'}), 403

        # Handle list or single event
        events = payload if isinstance(payload, list) else [payload]

        results = []
        for event in events:
            try:
                event_type, event_id, payment_id = parse_razorpay_payload(event)

                new_event = PaymentEvent(
                    event_id=event_id,
                    payment_id=payment_id,
                    event_type=event_type,
                    raw_payload=json.dumps(event),
                    received_at=datetime.utcnow()
                )

                db.session.add(new_event)
                db.session.commit()

                logger.info(f"Successfully processed event {event_id} for payment {payment_id}")
                results.append({'event_id': event_id, 'status': 'success'})

            except IntegrityError:
                db.session.rollback()
                logger.warning(f"Duplicate event {event.get('id')} ignored")
                results.append({'event_id': event.get('id'), 'status': 'duplicate'})

            except ValueError as e:
                logger.error(f"Payload parsing failed for event {event.get('id')}: {e}")
                results.append({'event_id': event.get('id'), 'status': 'failed', 'error': str(e)})

        # Return single event result (for tests expecting a single dict)
        if len(results) == 1:
            return jsonify(results[0]), 200
        else:
            return jsonify(results), 200

    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/payments/<payment_id>/events', methods=['GET'])
def get_payment_events(payment_id):
    """
    Get all events for a specific payment ID, sorted chronologically
    """
    try:
        events = PaymentEvent.query.filter_by(payment_id=payment_id)\
                                 .order_by(PaymentEvent.received_at.asc())\
                                 .all()
        
        if not events:
            return jsonify([]), 200
        
        return jsonify([event.to_dict() for event in events]), 200
        
    except Exception as e:
        logger.error(f"Error fetching events for payment {payment_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    """
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}), 200

# Error Handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'error': 'Method not allowed'}), 405

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500

# Database initialization
@app.before_request
def create_tables():
    """
    Create database tables before first request
    """
    try:
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")

if __name__ == '__main__':
    # Create tables if they don't exist
    with app.app_context():
        db.create_all()
        logger.info("Database initialized")
    
    # Run the app
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=True)