#!/usr/bin/env python3
"""
Basic authentication test for NaviLink service.
Run this script with your credentials to test authentication and device listing.
"""

import asyncio
import logging
import sys
from navilink import NaviLinkClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_basic_functionality(email: str, password: str):
    """Test basic authentication and device listing without MQTT."""
    
    logger.info(f"Testing authentication for {email}")
    
    try:
        async with NaviLinkClient() as client:
            # Test authentication
            logger.info("Attempting authentication...")
            user_info = await client.authenticate(email, password)
            
            logger.info("✅ Authentication successful!")
            logger.info(f"User ID: {user_info.user_id}")
            logger.info(f"Email: {user_info.email}")
            logger.info(f"User Type: {user_info.user_type}")
            logger.info(f"Group ID: {user_info.group_id}")
            logger.info(f"Has Session Token: {bool(user_info.session_token)}")
            logger.info(f"Token Expires: {user_info.token_expires_at}")
            
            # Check AWS credentials
            aws_creds = client._auth.aws_credentials
            if aws_creds:
                logger.info("✅ AWS credentials received:")
                logger.info(f"Access Key ID: {aws_creds.get('accessKeyId', 'N/A')[:10]}...")
                logger.info(f"Has Secret Key: {bool(aws_creds.get('secretKey'))}")
                logger.info(f"Has Session Token: {bool(aws_creds.get('sessionToken'))}")
            else:
                logger.warning("❌ No AWS credentials received")
            
            # Test device listing
            logger.info("\nGetting device list...")
            devices = await client.get_devices()
            
            logger.info(f"✅ Found {len(devices)} devices")
            
            for i, device in enumerate(devices):
                logger.info(f"\nDevice {i+1}:")
                logger.info(f"  Name: {device.name}")
                logger.info(f"  MAC Address: {device.mac_address}")
                logger.info(f"  Device Type: {device.device_type}")
                logger.info(f"  Additional Value: {device.additional_value}")
                logger.info(f"  Home Seq: {device.home_seq}")
                logger.info(f"  Connected: {device.connected}")
                if device.location:
                    logger.info(f"  Location: {device.location.get('city', '')}, {device.location.get('state', '')}")
                
                # Test getting device info
                try:
                    logger.info("  Getting device info...")
                    device_info = await client.get_device_info(device.mac_address)
                    if device_info:
                        logger.info(f"  ✅ Device info retrieved")
                        logger.info(f"    Device Type: {device_info.device_type}")
                        logger.info(f"    Controller S/N: {device_info.controller_serial_number}")
                    else:
                        logger.warning("  ❌ No device info returned")
                except Exception as e:
                    logger.error(f"  ❌ Failed to get device info: {e}")
                    import traceback
                    traceback.print_exc()
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    if len(sys.argv) != 3:
        print("Usage: python test_basic_auth.py <email> <password>")
        print("Example: python test_basic_auth.py user@example.com mypassword")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    
    success = asyncio.run(test_basic_functionality(email, password))
    
    if success:
        print("\n🎉 Basic authentication and device listing working!")
    else:
        print("\n💥 Tests failed. Check the logs above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()