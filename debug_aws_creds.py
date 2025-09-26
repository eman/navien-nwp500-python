#!/usr/bin/env python3
"""
Debug AWS credentials and compare with HAR file.
"""

import asyncio
import json
import logging
import sys
from navilink import NaviLinkClient

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def debug_aws_credentials(email: str, password: str):
    """Debug AWS credentials from authentication."""
    
    try:
        async with NaviLinkClient() as client:
            # Authenticate
            await client.authenticate(email, password)
            
            # Get AWS credentials
            aws_creds = client._auth.aws_credentials
            
            print("=== Current AWS Credentials ===")
            print(f"Access Key ID: {aws_creds['accessKeyId']}")
            print(f"Secret Key: {aws_creds['secretKey']}")
            print(f"Session Token: {aws_creds['sessionToken']}")
            
            print("\n=== HAR File AWS Credentials (for comparison) ===")
            print("Access Key ID: ASIA2YNF3GZM7OQ6FTXT")
            print("Secret Key: uvvI9vyrutgPQ9OcMX8bvHdwhW1eQh+UR6o5isqT")
            print("Session Token: FwoGZXIvYXdzEB4aDLkE484/KYTiOZtnNiK0AQmOfh9/J3VhtAIkocnN6rSo55C8TAlQcVjqO08pp...")
            
            # Compare access key patterns
            print("\n=== Credential Analysis ===")
            print(f"Current Access Key starts with: {aws_creds['accessKeyId'][:10]}...")
            print(f"HAR Access Key starts with:     ASIA2YNF3G...")
            print(f"Pattern match: {aws_creds['accessKeyId'].startswith('ASIA')}")
            
            print(f"Session Token length (current): {len(aws_creds['sessionToken'])}")
            print(f"Session Token length (HAR):     348")  # From previous analysis
            
            # Check if credentials look valid
            if aws_creds['accessKeyId'].startswith('ASIA') and len(aws_creds['sessionToken']) > 300:
                print("✅ Credentials format looks correct")
            else:
                print("❌ Credentials format might be incorrect")
                
            # Test the URL generation one more time
            from navilink.utils import create_websocket_url
            
            ws_url = create_websocket_url(
                base_url="wss://nlus-iot.naviensmartcontrol.com/mqtt",
                access_key=aws_creds["accessKeyId"],
                secret_key=aws_creds["secretKey"],
                session_token=aws_creds["sessionToken"]
            )
            
            print(f"\n=== Generated WebSocket URL ===")
            print(f"URL length: {len(ws_url)}")
            print(f"Contains required params: {all(param in ws_url for param in ['X-Amz-Algorithm', 'X-Amz-Credential', 'X-Amz-Date', 'X-Amz-Signature'])}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

def main():
    if len(sys.argv) != 3:
        print("Usage: python debug_aws_creds.py <email> <password>")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    
    asyncio.run(debug_aws_credentials(email, password))

if __name__ == "__main__":
    main()