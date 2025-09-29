#!/usr/bin/env python3
"""
Script to generate valid HMAC-SHA256 signatures for testing webhook endpoints.
"""

import hmac
import hashlib
import os
import json

def generate_signature(payload_file, secret="test_secret"):
    """
    Generate HMAC-SHA256 signature for a given payload file.
    
    Args:
        payload_file (str): Path to the JSON payload file
        secret (str): Shared secret for signature generation
    
    Returns:
        str: HMAC-SHA256 signature in hexadecimal format
    """
    try:
        with open(payload_file, 'r') as f:
            payload = f.read().strip()
        
        signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    except FileNotFoundError:
        print(f"Error: File {payload_file} not found")
        return None
    except Exception as e:
        print(f"Error generating signature for {payload_file}: {e}")
        return None

def main():
    """
    Generate signatures for all mock payload files.
    """
    secret = os.environ.get('WEBHOOK_SECRET', 'test_secret')
    payload_files = [
        'mock_payloads/payment_authorized.json',
        'mock_payloads/payment_captured.json',
        'mock_payloads/payment_failed.json'
    ]
    
    print(f"Generating signatures using secret: '{secret}'")
    print("-" * 60)
    
    for payload_file in payload_files:
        signature = generate_signature(payload_file, secret)
        if signature:
            print(f"File: {payload_file}")
            print(f"Signature: {signature}")
            
            # Generate curl command for easy testing
            print(f"cURL command:")
            print(f'curl -X POST http://localhost:8000/webhook/payments \\')
            print(f'  -H "Content-Type: application/json" \\')
            print(f'  -H "X-Razorpay-Signature: {signature}" \\')
            print(f'  -d @{payload_file}')
            print("-" * 60)

if __name__ == "__main__":
    main()