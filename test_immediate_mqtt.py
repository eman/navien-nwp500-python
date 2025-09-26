#!/usr/bin/env python3
"""
Test immediate MQTT connection after authentication to minimize timing issues.
"""

import asyncio
import logging
import sys
from navilink import NaviLinkClient
from navilink.utils import create_websocket_url
import websockets

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_immediate_connection(email: str, password: str):
    """Test connecting to WebSocket immediately after authentication."""
    
    try:
        async with NaviLinkClient() as client:
            # Authenticate
            logger.info("Authenticating...")
            await client.authenticate(email, password)
            logger.info("✅ Authentication successful!")
            
            # Get AWS credentials immediately
            aws_creds = client._auth.aws_credentials
            
            # Generate WebSocket URL immediately  
            ws_url = create_websocket_url(
                base_url="wss://nlus-iot.naviensmartcontrol.com/mqtt",
                access_key=aws_creds["accessKeyId"],
                secret_key=aws_creds["secretKey"],
                session_token=aws_creds["sessionToken"]
            )
            
            logger.info("Attempting immediate WebSocket connection...")
            
            try:
                # Try to connect to WebSocket immediately
                websocket = await websockets.connect(
                    ws_url,
                    subprotocols=["mqtt"],
                    additional_headers={
                        "User-Agent": "NaviLink-Python/0.1.0"
                    }
                )
                
                logger.info("✅ WebSocket connection successful!")
                
                # Just test that we can connect, then close
                await websocket.close()
                
                return True
                
            except websockets.exceptions.InvalidStatus as e:
                logger.error(f"❌ WebSocket connection failed: {e}")
                return False
            except Exception as e:
                logger.error(f"❌ Unexpected error: {e}")
                return False
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

def main():
    if len(sys.argv) != 3:
        print("Usage: python test_immediate_mqtt.py <email> <password>")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    
    success = asyncio.run(test_immediate_connection(email, password))
    
    if success:
        print("\n🎉 Immediate WebSocket connection working!")
    else:
        print("\n💥 WebSocket connection still failing.")
        sys.exit(1)

if __name__ == "__main__":
    main()