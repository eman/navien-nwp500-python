#!/usr/bin/env python3
"""
Debug WebSocket URL generation for NaviLink service.
"""

import asyncio
import logging
import sys
import urllib.parse
from navilink import NaviLinkClient
from navilink.utils import create_websocket_url

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def debug_websocket_url(email: str, password: str):
    """Debug WebSocket URL generation."""
    
    try:
        async with NaviLinkClient() as client:
            # Authenticate
            await client.authenticate(email, password)
            
            # Get AWS credentials
            aws_creds = client._auth.aws_credentials
            
            print("=== AWS Credentials ===")
            print(f"Access Key ID: {aws_creds['accessKeyId']}")
            print(f"Secret Key: {aws_creds['secretKey'][:10]}...")
            print(f"Session Token: {aws_creds['sessionToken'][:50]}...")
            
            # Generate WebSocket URL
            ws_url = create_websocket_url(
                base_url="wss://nlus-iot.naviensmartcontrol.com/mqtt",
                access_key=aws_creds["accessKeyId"],
                secret_key=aws_creds["secretKey"],
                session_token=aws_creds["sessionToken"]
            )
            
            print("\n=== Generated WebSocket URL ===")
            print(ws_url)
            
            # Parse the generated URL
            parsed = urllib.parse.urlparse(ws_url)
            params = urllib.parse.parse_qs(parsed.query)
            
            print("\n=== Generated Query Parameters ===")
            for key, values in params.items():
                print(f"{key}: {values[0]}")
            
            print("\n=== HAR File Parameters (for comparison) ===")
            print("X-Amz-Algorithm: AWS4-HMAC-SHA256")
            print("X-Amz-Credential: ASIA2YNF3GZM7OQ6FTXT/20250926/us-east-1/iotdata/aws4_request")
            print("X-Amz-Date: 20250926T204136Z")
            print("X-Amz-SignedHeaders: host")
            print("X-Amz-Signature: 535d4e1adc522ddcb792ef6ac01c003f2aefcb36e6d2b05cf0e63d98c1873604")
            print("X-Amz-Security-Token: FwoGZXIvYXdzEB4aDLkE484/KYTiOZtnNiK0AQmOfh9/J3VhtAIkocnN6rSo55C8TAlQcVjqO08pp...")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

def main():
    if len(sys.argv) != 3:
        print("Usage: python debug_websocket.py <email> <password>")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    
    asyncio.run(debug_websocket_url(email, password))

if __name__ == "__main__":
    main()